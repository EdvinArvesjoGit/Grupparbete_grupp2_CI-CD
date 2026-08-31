import json

import requests

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


if __name__ == "__main__":
    # Temporary manual check before database loading is implemented.
    data = fetch_ledamoter()
    personer = get_personer(data)

    print(f"Hämtade {len(personer)} personer")

    if personer:
        person = personer[0]

        parsed_person = parse_person(person)
        print("Person:")
        print(parsed_person)

        parsed_uppdrag = parse_person_uppdrag(person)
        print(f"Antal uppdrag: {len(parsed_uppdrag)}")

        if parsed_uppdrag:
            print("Första uppdraget:")
            print(parsed_uppdrag[0])

        parsed_uppgifter = parse_person_uppgift(person)
        print(f"Antal personuppgifter: {len(parsed_uppgifter)}")

        if parsed_uppgifter:
            print("Första personuppgiften:")
            print(parsed_uppgifter[0])
