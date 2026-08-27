import pandas as pd

from voting.schemas import VOTING_COLUMNS

# Path to the voting data CSV file
VOTING_FILE = "data/votering-202223.csv"

# File containing the IDs of the 349 current members of parliament
MEMBER_FILE = "data/current_member_ids.csv"


def main():

    votes = pd.read_csv(
        VOTING_FILE,
        header=None,
        names=VOTING_COLUMNS,
    )
    current_members = pd.read_csv(MEMBER_FILE)

    # Display the columns in both datasets
    print("Voting columns:")
    print(votes.columns.tolist())

    print("\nCurrent member columns:")
    print(current_members.columns.tolist())

    # Check that the required column exists
    if "intressent_id" not in votes.columns:
        raise ValueError("intressent_id is missing from the voting data")

    if "intressent_id" not in current_members.columns:
        raise ValueError("intressent_id is missing from current_member_ids.csv")

    # Remove missing values and get unique member IDs
    vote_ids = set(votes["intressent_id"].dropna().astype(str))
    current_ids = set(current_members["intressent_id"].dropna().astype(str))

    # Find people who appear in the voting data
    # but are not among the current members
    missing_ids = vote_ids - current_ids


    print("\n--- Results ---")
    print(f"Unique people in voting data: {len(vote_ids)}")
    print(f"Current members: {len(current_ids)}")
    print(f"People missing from current member data: {len(missing_ids)}")

    # Save missing IDs to a CSV file
    missing_df = pd.DataFrame(
        sorted(missing_ids),
        columns=["intressent_id"]
    )

    missing_df.to_csv(
        "data/missing_member_ids.csv",
        index=False
    )

    print("\nMissing IDs saved to: data/missing_member_ids.csv")




if __name__ == "__main__":
    main()