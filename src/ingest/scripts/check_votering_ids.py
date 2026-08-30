"""
Validation script for Riksdagen voting data.

Purpose
-------
This script checks whether a combination of:

    rm + beteckning (bet) + punkt

always corresponds to exactly one `votering_id`.

The check is important because the voting API is queried by `rm`, `bet`,
and `punkt` when fetching detailed voting records. If one combination can
contain multiple voting events, `rm + bet + punkt` must not be treated as
a unique identifier for a voting event.

Method
------
For each riksmöte from 2022/23 to 2025/26:

1. Fetch all `bet + punkt` combinations using `gruppering=bet`.
2. Fetch the detailed voting records for each combination.
3. Count the number of distinct `votering_id` values.
4. Report combinations containing more than one `votering_id`.

Result
------
The validation found 18 combinations with multiple `votering_id` values:

    2025/26: 7 combinations
    2024/25: 3 combinations
    2023/24: 5 combinations
    2022/23: 3 combinations

All 18 cases contained:
    - 2 distinct votering_id values
    - 698 rows in total (2 x 349)

Conclusion
----------
`rm + bet + punkt` is NOT guaranteed to uniquely identify a voting event.

`votering_id` should therefore be used to distinguish separate voting
events. For an individual member's vote, the combination of
`votering_id` and `intressent_id` is a candidate unique key and should
be validated separately before adding a database constraint.

The largest `rm + bet + punkt` group observed in these four riksmöten
contained 698 rows, which is well below the tested API response limit
of 10,000 rows. The ingestion pipeline should still validate response
sizes instead of assuming that this will always remain true.

This is a development/validation script and is not part of the production
ingestion pipeline.
"""

import time

import requests

API_URL = "https://data.riksdagen.se/voteringlista/"

RIKSMOTEN = [
    "2025/26",
    "2024/25",
    "2023/24",
    "2022/23",
]


def fetch_groups(rm: str) -> list[dict]:
    params = {
        "rm": rm,
        "sz": 10000,
        "utformat": "json",
        "gruppering": "bet",
    }

    response = requests.get(API_URL, params=params, timeout=60)
    response.raise_for_status()

    data = response.json()
    return data["voteringlista"]["votering"]


def fetch_votes(rm: str, bet: str, punkt: str) -> list[dict]:
    params = {
        "rm": rm,
        "bet": bet,
        "punkt": punkt,
        "sz": 10000,
        "utformat": "json",
    }

    response = requests.get(API_URL, params=params, timeout=60)
    response.raise_for_status()

    data = response.json()
    votes = data["voteringlista"].get("votering", [])

    if isinstance(votes, dict):
        votes = [votes]

    return votes


def main():
    multiple_votering_ids = []

    for rm in RIKSMOTEN:
        print(f"\nChecking {rm}...")

        groups = fetch_groups(rm)
        print(f"Found {len(groups)} bet + punkt groups.")

        for index, group in enumerate(groups, start=1):
            bet = group["bet"]
            punkt = group["punkt"]

            votes = fetch_votes(rm, bet, punkt)

            votering_ids = {
                vote.get("votering_id")
                for vote in votes
                if vote.get("votering_id")
            }

            if len(votering_ids) > 1:
                multiple_votering_ids.append(
                    {
                        "rm": rm,
                        "bet": bet,
                        "punkt": punkt,
                        "row_count": len(votes),
                        "votering_id_count": len(votering_ids),
                        "votering_ids": sorted(votering_ids),
                    }
                )

                print(
                    f"FOUND: {rm} {bet} punkt {punkt} "
                    f"has {len(votering_ids)} votering_ids "
                    f"and {len(votes)} rows."
                )

            if index % 100 == 0:
                print(f"Checked {index}/{len(groups)}")

            time.sleep(0.05)

    print("\n--- RESULT ---")

    if not multiple_votering_ids:
        print(
            "No bet + punkt combination had more than one votering_id "
            "in the checked riksmöten."
        )
    else:
        print(
            f"Found {len(multiple_votering_ids)} combinations "
            "with multiple votering_ids:"
        )

        for item in multiple_votering_ids:
            print(
                f"{item['rm']} | {item['bet']} | punkt {item['punkt']} | "
                f"{item['votering_id_count']} votering_ids | "
                f"{item['row_count']} rows"
            )

            for votering_id in item["votering_ids"]:
                print(f"    {votering_id}")


if __name__ == "__main__":
    main()
