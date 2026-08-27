import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

from src.voting.schemas import VOTING_COLUMNS

VOTING_FILE = "data/votering-202223.csv"


def create_db_engine():
    load_dotenv()

    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_NAME")
    username = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    connection_string = (
        f"mssql+pyodbc://{username}:{password}@{server}/{database}"
        "?driver=ODBC+Driver+18+for+SQL+Server"
        "&TrustServerCertificate=yes"
    )

    return create_engine(connection_string)


def read_voting_data():
    # The Riksdagen voting CSV file does not contain a header row.
    return pd.read_csv(
        VOTING_FILE,
        header=None,
        names=VOTING_COLUMNS,
    )


def load_to_staging(df, engine):
    # Append the raw voting data to the staging table.
    df.to_sql(
        name="stg_votering",
        con=engine,
        schema="dbo",
        if_exists="append",
        index=False,
    )


def main():
    df = read_voting_data()

    print(f"Rows read from CSV: {len(df)}")
    print(df.head())

    engine = create_db_engine()

    load_to_staging(df, engine)

    print(f"Loaded {len(df)} rows into dbo.stg_votering")


if __name__ == "__main__":
    main()