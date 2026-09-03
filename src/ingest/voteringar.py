import os
import time
import xml.etree.ElementTree as ET

import requests
from sqlalchemy import Engine, text

from src.common.db import get_engine
from src.common.pipeline import log_step, new_korning_id

VOTING_LIST_URL = "https://data.riksdagen.se/voteringlista/"
VOTING_DETAIL_URL = "https://data.riksdagen.se/votering/{votering_id}"

RIKSMOTEN = [
    rm.strip()
    for rm in os.getenv(
        "RIKSMOTEN",
        "2022/23,2023/24,2024/25,2025/26",
    ).split(",")
    if rm.strip()
]

API_SIZE = 10000
REQUEST_DELAY = 0

SESSION = requests.Session()


def ensure_list(value) -> list:
    """Normalize an API result to a list."""

    if not value:
        return []

    if isinstance(value, dict):
        return [value]

    return value


def fetch_voting_events(rm: str) -> list[dict]:
    """
    Fetch voting summaries for one riksmöte.

    The list endpoint is grouped by votering_id, so each returned item
    represents one voting event and contains aggregated vote totals.
    """

    params = {
        "rm": rm,
        "sz": API_SIZE,
        "utformat": "json",
        "gruppering": "votering_id",
    }

    response = requests.get(VOTING_LIST_URL, params=params, timeout=60)
    response.raise_for_status()

    data = response.json()
    voting_list = data["voteringlista"]
    events = ensure_list(voting_list.get("votering", []))

    reported_count = int(voting_list.get("@antal") or 0)

    if reported_count and len(events) != reported_count:
        raise ValueError(
            f"Voting event count mismatch for {rm}: "
            f"API reports {reported_count}, received {len(events)}."
        )

    if len(events) >= API_SIZE:
        raise ValueError(f"Possible API truncation for {rm}: received {len(events)} voting events.")

    return events


def get_expected_count(event: dict) -> int:
    """Calculate the expected number of member rows for one voting event."""

    vote_types = [
        "Ja",
        "Nej",
        "Avstår",
        "Frånvarande",
    ]

    return sum(int(event.get(vote_type) or 0) for vote_type in vote_types)


def fetch_votering_xml(
    votering_id: str,
    run_id: str | None = None,
) -> tuple[list[dict], str]:
    """
    Fetch and parse the XML detail response for one voting event.

    The XML contains one direct <votering> child under <dokvotering>
    for each member's voting record.
    """

    source_url = VOTING_DETAIL_URL.format(votering_id=votering_id)

    response = requests.get(source_url, timeout=60)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    vote_elements = root.findall(".//dokvotering/votering")

    votes = []

    for vote in vote_elements:
        votes.append(
            {
                "dok_id": vote.findtext("dok_id"),
                "votering_id": vote.findtext("votering_id"),
                "punkt": vote.findtext("punkt"),
                "punkttyp": vote.findtext("punkttyp"),
                "namn": vote.findtext("namn"),
                "intressent_id": vote.findtext("intressent_id"),
                "parti": vote.findtext("parti"),
                "valkrets": vote.findtext("valkrets"),
                "valkretsnummer": vote.findtext("valkretsnummer"),
                "iort": vote.findtext("iort"),
                "rost": vote.findtext("rost"),
                "avser": vote.findtext("avser"),
                "votering": vote.findtext("votering"),
                "banknummer": vote.findtext("banknummer"),
                "fornamn": vote.findtext("fornamn"),
                "efternamn": vote.findtext("efternamn"),
                "kon": vote.findtext("kon"),
                "fodd": vote.findtext("fodd"),
                "rm": vote.findtext("rm"),
                "beteckning": vote.findtext("beteckning"),
                "kalla": vote.findtext("källa"),
                "datum": vote.findtext("datum"),
                "systemdatum": vote.findtext("systemdatum"),
                "_kalla": source_url,
                "_korning_id": run_id,
            }
        )

    return votes, source_url


def validate_voting_event(
    votering_id: str,
    votes: list[dict],
    expected_count: int,
) -> None:
    """Validate the XML rows for one voting event before loading them."""

    actual_count = len(votes)

    if actual_count != expected_count:
        raise ValueError(
            f"Row count mismatch for votering_id {votering_id}: "
            f"expected {expected_count}, received {actual_count}."
        )

    unexpected_ids = {
        vote["votering_id"]
        for vote in votes
        if vote.get("votering_id") and vote["votering_id"].lower() != votering_id.lower()
    }

    if unexpected_ids:
        raise ValueError(
            f"Unexpected votering_id values in XML for {votering_id}: {sorted(unexpected_ids)}"
        )


def get_existing_votering_ids(conn, rm: str) -> set[str]:
    """Get voting event IDs already loaded in the detail table."""

    sql = """
        SELECT DISTINCT votering_id::text
        FROM stg.votering
        WHERE rm = :rm;
    """

    result = conn.execute(text(sql), {"rm": rm})
    return {row[0].lower() for row in result.fetchall()}


def get_new_voting_events(
    events: list[dict],
    existing_votering_ids: set[str],
) -> list[dict]:
    """Return voting events whose detail rows have not yet been loaded."""

    return [event for event in events if event["votering_id"].lower() not in existing_votering_ids]


def upsert_voting_summaries(
    conn,
    rm: str,
    events: list[dict],
    run_id: str | None = None,
) -> int:
    """
    Store voting summary rows in stg.votering_summary.

    One row represents one voting event. Existing rows are updated so
    aggregated vote totals can reflect later source corrections.
    """

    sql = """
        INSERT INTO stg.votering_summary (
            votering_id,
            rm,
            ja,
            nej,
            franvarande,
            avstar,
            _kalla,
            _korning_id
        )
        VALUES (
            :votering_id,
            :rm,
            :ja,
            :nej,
            :franvarande,
            :avstar,
            :_kalla,
            :_korning_id
        )
        ON CONFLICT (votering_id)
        DO UPDATE SET
            rm = EXCLUDED.rm,
            ja = EXCLUDED.ja,
            nej = EXCLUDED.nej,
            franvarande = EXCLUDED.franvarande,
            avstar = EXCLUDED.avstar,
            _kalla = EXCLUDED._kalla,
            _korning_id = EXCLUDED._korning_id;
    """

    rows = [
        {
            "votering_id": event["votering_id"],
            "rm": rm,
            "ja": int(event.get("Ja") or 0),
            "nej": int(event.get("Nej") or 0),
            "franvarande": int(event.get("Frånvarande") or 0),
            "avstar": int(event.get("Avstår") or 0),
            "_kalla": VOTING_LIST_URL,
            "_korning_id": run_id,
        }
        for event in events
    ]

    affected = 0

    statement = text(sql)
    for row in rows:
        result = conn.execute(statement, row)
        affected += result.rowcount

    conn.commit()

    return affected


def insert_voteringar(conn, votes: list[dict]) -> int:
    """Insert parsed XML voting records into stg.votering."""

    sql = """
        INSERT INTO stg.votering (
            dok_id,
            votering_id,
            punkt,
            punkttyp,
            namn,
            intressent_id,
            parti,
            valkrets,
            valkretsnummer,
            iort,
            rost,
            avser,
            votering,
            banknummer,
            fornamn,
            efternamn,
            kon,
            fodd,
            rm,
            beteckning,
            kalla,
            datum,
            systemdatum,
            _kalla,
            _korning_id
        )
        VALUES (
            :dok_id,
            :votering_id,
            :punkt,
            :punkttyp,
            :namn,
            :intressent_id,
            :parti,
            :valkrets,
            :valkretsnummer,
            :iort,
            :rost,
            :avser,
            :votering,
            :banknummer,
            :fornamn,
            :efternamn,
            :kon,
            :fodd,
            :rm,
            :beteckning,
            :kalla,
            :datum,
            :systemdatum,
            :_kalla,
            :_korning_id
        )
        ON CONFLICT (votering_id, intressent_id)
        DO NOTHING;
    """

    inserted = 0

    statement = text(sql)
    for vote in votes:
        result = conn.execute(statement, vote)
        inserted += result.rowcount

    conn.commit()

    return inserted


def load_voting_details(
    conn,
    events: list[dict],
    run_id: str | None = None,
) -> int:
    """Fetch, validate, and load XML detail rows for voting events."""

    inserted_total = 0

    for index, event in enumerate(events, start=1):
        votering_id = event["votering_id"]
        expected_count = get_expected_count(event)

        print(f"[{index}/{len(events)}] Fetching votering_id {votering_id}...")

        votes, _ = fetch_votering_xml(
            votering_id=votering_id,
            run_id=run_id,
        )

        validate_voting_event(
            votering_id=votering_id,
            votes=votes,
            expected_count=expected_count,
        )

        inserted_total += insert_voteringar(conn, votes)
        time.sleep(REQUEST_DELAY)

    return inserted_total


def incremental_load(
    conn,
    run_id: str | None = None,
) -> int:
    """
    Load all events on an empty detail table, then only missing events on later runs.

    For each configured riksmöte:
    1. Fetch current voting summaries.
    2. Compare API IDs with IDs already present in stg.votering.
    3. Upsert summaries into stg.votering_summary.
    4. Fetch XML details only for missing voting events.

    stg.votering is used as the checkpoint for detail ingestion.
    Tables must already exist. Completed events are skipped when a run is resumed.
    """

    total_summary_rows = 0
    total_detail_rows = 0

    print("Starting incremental load...")

    for rm in RIKSMOTEN:
        print(f"\nChecking voting events for {rm}...")

        events = fetch_voting_events(rm)

        existing_votering_ids = get_existing_votering_ids(conn, rm)
        new_events = get_new_voting_events(
            events,
            existing_votering_ids,
        )

        summary_rows = upsert_voting_summaries(
            conn=conn,
            rm=rm,
            events=events,
            run_id=run_id,
        )
        total_summary_rows += summary_rows

        print(f"Stored {len(events)} voting summaries. Found {len(new_events)} new voting events.")

        detail_rows = load_voting_details(
            conn=conn,
            events=new_events,
            run_id=run_id,
        )
        total_detail_rows += detail_rows

        print(f"Finished {rm}: {detail_rows} new detail rows inserted.")

    print(
        f"\nIncremental load done. "
        f"Summary rows inserted/updated: {total_summary_rows}. "
        f"New detail rows inserted: {total_detail_rows}."
    )

    return total_detail_rows


def run(
    engine: Engine,
    korning_id: str | None = None,
) -> int:
    """Load votes with a shared run ID and return newly inserted detail rows.

    Uses incremental loading for both first and subsequent runs.
    An empty detail table makes every source event eligible for loading.
    The same ID is written to summaries, new detail rows, and ops.load_log.
    The log row covers this ingest step; antal_rader counts detail inserts only.
    """
    if korning_id is None:
        korning_id = new_korning_id()

    with log_step(
        engine,
        kalla="voteringar",
        mallager="stg",
        malltabell="votering",
        korning_id=korning_id,
    ) as step:
        # Each summary batch and voting event commits separately in the loaders.
        with engine.connect() as conn:
            rows = incremental_load(conn, run_id=korning_id)

        step.antal_rader = rows
        return rows


def main() -> int:
    """Support standalone execution with the same loading and logging logic."""
    return run(
        get_engine(),
        korning_id=os.getenv("KORNING_ID") or None,
    )


if __name__ == "__main__":
    main()
