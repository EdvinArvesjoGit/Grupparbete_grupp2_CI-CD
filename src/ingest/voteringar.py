import os
import time
import xml.etree.ElementTree as ET

import psycopg
import requests
from dotenv import load_dotenv

load_dotenv()

VOTING_LIST_URL = "https://data.riksdagen.se/voteringlista/"
VOTING_DETAIL_URL = "https://data.riksdagen.se/votering/{votering_id}"

RIKSMOTEN = [
    "2025/26",
    "2024/25",
    "2023/24",
    "2022/23",
]

API_SIZE = 10000
REQUEST_DELAY = 0.05


def ensure_list(value) -> list:
    """Normalize an API result to a list."""

    if not value:
        return []

    if isinstance(value, dict):
        return [value]

    return value


def fetch_voting_events(rm: str) -> list[dict]:
    """
    Fetch voting events for one riksmöte.

    The list endpoint is grouped by votering_id, so each returned item
    represents one voting event and contains the vote totals for that event.
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


def fetch_votering_xml(votering_id: str) -> tuple[list[dict], str]:
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


def get_connection():
    """Create a PostgreSQL database connection."""

    return psycopg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "riksdag"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def get_existing_votering_ids(conn, rm: str) -> set[str]:
    """Get voting event IDs already loaded for one riksmöte."""

    sql = """
        SELECT DISTINCT votering_id::text
        FROM stg.votering
        WHERE rm = %s;
    """

    with conn.cursor() as cursor:
        cursor.execute(sql, (rm,))
        return {row[0].lower() for row in cursor.fetchall()}


def get_new_voting_events(
    events: list[dict],
    existing_votering_ids: set[str],
) -> list[dict]:
    """Return voting events whose votering_id has not yet been loaded."""

    return [event for event in events if event["votering_id"].lower() not in existing_votering_ids]


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
            _kalla
        )
        VALUES (
            %(dok_id)s,
            %(votering_id)s,
            %(punkt)s,
            %(punkttyp)s,
            %(namn)s,
            %(intressent_id)s,
            %(parti)s,
            %(valkrets)s,
            %(valkretsnummer)s,
            %(iort)s,
            %(rost)s,
            %(avser)s,
            %(votering)s,
            %(banknummer)s,
            %(fornamn)s,
            %(efternamn)s,
            %(kon)s,
            %(fodd)s,
            %(rm)s,
            %(beteckning)s,
            %(kalla)s,
            %(datum)s,
            %(systemdatum)s,
            %(_kalla)s
        )
        ON CONFLICT (votering_id, intressent_id)
        DO NOTHING;
    """

    inserted = 0

    with conn.cursor() as cursor:
        for vote in votes:
            cursor.execute(sql, vote)
            inserted += cursor.rowcount

    conn.commit()

    return inserted


def main():
    conn = get_connection()

    try:
        total_inserted = 0

        for rm in RIKSMOTEN:
            print(f"\nChecking voting events for {rm}...")

            events = fetch_voting_events(rm)
            existing_votering_ids = get_existing_votering_ids(conn, rm)
            new_events = get_new_voting_events(events, existing_votering_ids)

            print(f"Found {len(events)} voting events, {len(new_events)} new.")

            rm_inserted = 0

            for index, event in enumerate(new_events, start=1):
                votering_id = event["votering_id"]
                expected_count = get_expected_count(event)

                print(f"[{index}/{len(new_events)}] Fetching votering_id {votering_id}...")

                votes, _ = fetch_votering_xml(votering_id)

                validate_voting_event(
                    votering_id=votering_id,
                    votes=votes,
                    expected_count=expected_count,
                )

                inserted = insert_voteringar(conn, votes)

                rm_inserted += inserted
                total_inserted += inserted

                time.sleep(REQUEST_DELAY)

            print(f"Finished {rm}: {rm_inserted} new rows inserted.")

        print(f"\nDone. Total new rows inserted: {total_inserted}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
