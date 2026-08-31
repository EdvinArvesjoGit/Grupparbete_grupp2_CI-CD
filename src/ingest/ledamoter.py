import json
from uuid import uuid4

import requests
from sqlalchemy import text

from src.common.db import get_engine

API_URL = "https://data.riksdagen.se/personlista/"

PARAMS = {
    "rdlstatus": "tjanst",
    "utformat": "json",
}


def fetch_ledamoter():
    """Fetch member data from the Swedish Parliament API."""
    response = requests.get(
        API_URL,
        params=PARAMS,
        timeout=30,
    )

    # Stop execution if the API request was unsuccessful.
    response.raise_for_status()

    return response.json()


def ensure_list(value):
    """Normalize a value so the result is always a list."""
    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


def extract_single_value(value):
    """Extract a single value from the API's list structure."""
    if value is None:
        return None

    # The API returns 'uppgift' as a list even when it contains
    # only one value.
    if isinstance(value, list):
        if not value:
            return None

        value = value[0]

    # Preserve structured values as JSON text.
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)

    return str(value)


def get_personer(data):
    """Extract the list of persons from the API response."""
    personer = data["personlista"]["person"]

    return ensure_list(personer)


def parse_person(person):
    """Convert an API person into a row for stg.person."""
    return {
        "hangar_guid": person.get("hangar_guid"),
        "sourceid": person.get("sourceid"),
        "intressent_id": person.get("intressent_id"),
        "hangar_id": person.get("hangar_id"),
        "fodd_ar": person.get("fodd_ar"),
        "kon": person.get("kon"),
        "efternamn": person.get("efternamn"),
        "tilltalsnamn": person.get("tilltalsnamn"),
        "sorteringsnamn": person.get("sorteringsnamn"),
        "iort": person.get("iort"),
        "parti": person.get("parti"),
        "valkrets": person.get("valkrets"),
        "status": person.get("status"),
        "person_url_xml": person.get("person_url_xml"),
        "bild_url_80": person.get("bild_url_80"),
        "bild_url_192": person.get("bild_url_192"),
        "bild_url_max": person.get("bild_url_max"),
    }


def parse_person_uppdrag(person):
    """Convert a person's assignments into rows for stg.person_uppdrag."""
    personuppdrag = person.get("personuppdrag")

    # The API may return an empty string instead of an object
    # when assignment data is missing.
    if not isinstance(personuppdrag, dict):
        return []

    uppdrag = ensure_list(personuppdrag.get("uppdrag"))
    parsed_uppdrag = []

    for item in uppdrag:
        if not isinstance(item, dict):
            continue

        parsed_uppdrag.append(
            {
                "organ_kod": item.get("organ_kod"),
                "roll_kod": item.get("roll_kod"),
                "ordningsnummer": item.get("ordningsnummer"),
                "status": item.get("status"),
                "typ": item.get("typ"),
                # Rename "from" because FROM is an SQL keyword.
                "fran_datum": item.get("from"),
                "tom_datum": item.get("tom"),
                "uppgift": extract_single_value(item.get("uppgift")),
                "intressent_id": item.get("intressent_id"),
                "hangar_id": item.get("hangar_id"),
                "sortering": item.get("sortering"),
                "organ_sortering": item.get("organ_sortering"),
                "uppdrag_rollsortering": item.get("uppdrag_rollsortering"),
                "uppdrag_statussortering": item.get("uppdrag_statussortering"),
            }
        )

    return parsed_uppdrag


def parse_person_uppgift(person):
    """Convert person details into rows for stg.person_uppgift."""
    personuppgift = person.get("personuppgift")

    if not isinstance(personuppgift, dict):
        return []

    uppgifter = ensure_list(personuppgift.get("uppgift"))
    parsed_uppgifter = []

    for item in uppgifter:
        if not isinstance(item, dict):
            continue

        parsed_uppgifter.append(
            {
                "kod": item.get("kod"),
                "uppgift": extract_single_value(item.get("uppgift")),
                "typ": item.get("typ"),
                "intressent_id": item.get("intressent_id"),
                "hangar_id": item.get("hangar_id"),
            }
        )

    return parsed_uppgifter


def load_personer(personer, korning_id):
    """Load parsed person rows into stg.person."""
    rows = []

    for person in personer:
        row = parse_person(person)
        row["_kalla"] = API_URL
        row["_korning_id"] = korning_id
        rows.append(row)

    sql = text(
        """
        INSERT INTO stg.person (
            hangar_guid,
            sourceid,
            intressent_id,
            hangar_id,
            fodd_ar,
            kon,
            efternamn,
            tilltalsnamn,
            sorteringsnamn,
            iort,
            parti,
            valkrets,
            status,
            person_url_xml,
            bild_url_80,
            bild_url_192,
            bild_url_max,
            _kalla,
            _korning_id
        )
        VALUES (
            :hangar_guid,
            :sourceid,
            :intressent_id,
            :hangar_id,
            :fodd_ar,
            :kon,
            :efternamn,
            :tilltalsnamn,
            :sorteringsnamn,
            :iort,
            :parti,
            :valkrets,
            :status,
            :person_url_xml,
            :bild_url_80,
            :bild_url_192,
            :bild_url_max,
            :_kalla,
            :_korning_id
        )
        """
    )

    with get_engine().begin() as conn:
        conn.execute(text("TRUNCATE stg.person"))
        conn.execute(sql, rows)

    return len(rows)


def load_person_uppdrag(personer, korning_id):
    """Load parsed assignment rows into stg.person_uppdrag."""
    rows = []

    for person in personer:
        rows.extend(parse_person_uppdrag(person))

    for row in rows:
        row["_kalla"] = API_URL
        row["_korning_id"] = korning_id

    sql = text(
        """
        INSERT INTO stg.person_uppdrag (
            organ_kod,
            roll_kod,
            ordningsnummer,
            status,
            typ,
            fran_datum,
            tom_datum,
            uppgift,
            intressent_id,
            hangar_id,
            sortering,
            organ_sortering,
            uppdrag_rollsortering,
            uppdrag_statussortering,
            _kalla,
            _korning_id
        )
        VALUES (
            :organ_kod,
            :roll_kod,
            :ordningsnummer,
            :status,
            :typ,
            :fran_datum,
            :tom_datum,
            :uppgift,
            :intressent_id,
            :hangar_id,
            :sortering,
            :organ_sortering,
            :uppdrag_rollsortering,
            :uppdrag_statussortering,
            :_kalla,
            :_korning_id
        )
        """
    )

    with get_engine().begin() as conn:
        conn.execute(text("TRUNCATE stg.person_uppdrag"))
        conn.execute(sql, rows)

    return len(rows)


def load_person_uppgift(personer, korning_id):
    """Load parsed person detail rows into stg.person_uppgift."""
    rows = []

    for person in personer:
        rows.extend(parse_person_uppgift(person))

    for row in rows:
        row["_kalla"] = API_URL
        row["_korning_id"] = korning_id

    sql = text(
        """
        INSERT INTO stg.person_uppgift (
            kod,
            uppgift,
            typ,
            intressent_id,
            hangar_id,
            _kalla,
            _korning_id
        )
        VALUES (
            :kod,
            :uppgift,
            :typ,
            :intressent_id,
            :hangar_id,
            :_kalla,
            :_korning_id
        )
        """
    )

    with get_engine().begin() as conn:
        conn.execute(text("TRUNCATE stg.person_uppgift"))
        conn.execute(sql, rows)

    return len(rows)


def main():
    """Fetch, parse, and load member data into the staging database."""
    korning_id = str(uuid4())

    data = fetch_ledamoter()
    personer = get_personer(data)

    print(f"Fetched {len(personer)} persons")

    antal_personer = load_personer(personer, korning_id)
    print(f"Loaded {antal_personer} rows into stg.person")

    antal_uppdrag = load_person_uppdrag(personer, korning_id)
    print(f"Loaded {antal_uppdrag} rows into stg.person_uppdrag")

    antal_uppgifter = load_person_uppgift(personer, korning_id)
    print(f"Loaded {antal_uppgifter} rows into stg.person_uppgift")


if __name__ == "__main__":
    main()
