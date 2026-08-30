import os
import time

import psycopg
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://data.riksdagen.se/voteringlista/"

RIKSMOTEN = [
    "2025/26",
    "2024/25",
    "2023/24",
    "2022/23",
]

API_SIZE = 10000  # API returned max 10,000 rows in testing
REQUEST_DELAY = 0.05


def ensure_list(value) -> list:
    """Normalize API result to a list."""

    if not value:
        return []

    if isinstance(value, dict):
        return [value]

    return value


def fetch_voting_groups(rm: str) -> list[dict]:
    """
    Fetch all bet + punkt combinations for one riksmöte.

    The API is grouped by 'bet', which represents a combination
    of beteckning and punkt.
    """

    params = {
        "rm": rm,
        "sz": API_SIZE,
        "utformat": "json",
        "gruppering": "bet",
    }

    response = requests.get(API_URL, params=params, timeout=60)
    response.raise_for_status()

    data = response.json()

    groups = data["voteringlista"].get("votering", [])

    return ensure_list(groups)


def fetch_voteringar(
    rm: str,
    bet: str,
    punkt: str,
) -> list[dict]:
    """
    Fetch detailed voting records for one rm + bet + punkt combination.
    """

    params = {
        "rm": rm,
        "bet": bet,
        "punkt": punkt,
        "sz": API_SIZE,
        "utformat": "json",
    }

    response = requests.get(API_URL, params=params, timeout=60)
    response.raise_for_status()

    data = response.json()

    votes = data["voteringlista"].get("votering", [])

    return ensure_list(votes)


def get_expected_count(group: dict) -> int:
    """
    Calculate expected number of detailed voting records
    from the grouped API response.
    """

    vote_types = [
        "Ja",
        "Nej",
        "Avstår",
        "Frånvarande",
    ]

    return sum(int(group.get(vote_type) or 0) for vote_type in vote_types)


def validate_group(
    rm: str,
    bet: str,
    punkt: str,
    votes: list[dict],
    expected_count: int,
) -> None:
    """
    Validate that the detailed API response is complete.
    """

    actual_count = len(votes)

    if actual_count >= API_SIZE:
        raise ValueError(
            f"Possible API truncation for {rm} {bet} punkt {punkt}: received {actual_count} rows."
        )

    if actual_count != expected_count:
        raise ValueError(
            f"Row count mismatch for "
            f"{rm} {bet} punkt {punkt}: "
            f"expected {expected_count}, "
            f"received {actual_count}."
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


def get_existing_groups(conn, rm: str) -> set[tuple[str, str]]:
    """Get already loaded beteckning + punkt combinations for one riksmöte."""

    sql = """
        SELECT DISTINCT beteckning, punkt
        FROM stg.votering
        WHERE rm = %s;
    """

    with conn.cursor() as cursor:
        cursor.execute(sql, (rm,))
        return set(cursor.fetchall())


def get_new_groups(
    groups: list[dict],
    existing_groups: set[tuple[str, str]],
) -> list[dict]:
    """Return voting groups that have not yet been loaded."""

    return [group for group in groups if (group["bet"], group["punkt"]) not in existing_groups]


def insert_voteringar(conn, votes: list[dict]) -> int:
    """Insert voting records into stg.votering."""

    sql = """
        INSERT INTO stg.votering (
            hangar_id,
            rm,
            beteckning,
            punkt,
            punkttyp,
            votering_id,
            intressent_id,
            namn,
            fornamn,
            efternamn,
            valkrets,
            iort,
            parti,
            banknummer,
            kon,
            fodd,
            rost,
            avser,
            votering,
            votering_url_xml,
            dok_id,
            systemdatum
        )
        VALUES (
            %(hangar_id)s,
            %(rm)s,
            %(beteckning)s,
            %(punkt)s,
            %(punkttyp)s,
            %(votering_id)s,
            %(intressent_id)s,
            %(namn)s,
            %(fornamn)s,
            %(efternamn)s,
            %(valkrets)s,
            %(iort)s,
            %(parti)s,
            %(banknummer)s,
            %(kon)s,
            %(fodd)s,
            %(rost)s,
            %(avser)s,
            %(votering)s,
            %(votering_url_xml)s,
            %(dok_id)s,
            %(systemdatum)s
        );
    """

    inserted = 0

    with conn.cursor() as cursor:
        for vote in votes:
            cursor.execute(sql, vote)
            inserted += 1

    conn.commit()

    return inserted


def main():
    conn = get_connection()

    try:
        total_inserted = 0

        for rm in RIKSMOTEN:
            print(f"\nChecking voting groups for {rm}...")

            groups = fetch_voting_groups(rm)
            existing_groups = get_existing_groups(conn, rm)

            new_groups = get_new_groups(groups, existing_groups)

            print(f"Found {len(groups)} groups, {len(new_groups)} new.")

            rm_inserted = 0

            for index, group in enumerate(new_groups, start=1):
                bet = group["bet"]
                punkt = group["punkt"]
                expected_count = get_expected_count(group)

                print(f"[{index}/{len(new_groups)}] Fetching new group: {rm} {bet} punkt {punkt}")

                votes = fetch_voteringar(
                    rm=rm,
                    bet=bet,
                    punkt=punkt,
                )

                validate_group(
                    rm=rm,
                    bet=bet,
                    punkt=punkt,
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
