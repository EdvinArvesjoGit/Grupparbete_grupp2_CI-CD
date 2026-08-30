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
