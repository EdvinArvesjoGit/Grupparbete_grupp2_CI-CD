from src.ingest.ledamoter import (
    ensure_list,
    extract_single_value,
    get_personer,
    parse_person,
    parse_person_uppdrag,
    parse_person_uppgift,
)


def test_ensure_list():
    """Ensure values are normalized into lists."""
    assert ensure_list(None) == []
    assert ensure_list("value") == ["value"]
    assert ensure_list(["value"]) == ["value"]


def test_extract_single_value():
    """Ensure single values are extracted from the API's list structure."""
    assert extract_single_value(None) is None
    assert extract_single_value([]) is None
    assert extract_single_value(["true"]) == "true"
    assert extract_single_value(["Stockholm"]) == "Stockholm"

    # Structured values should be preserved as JSON text.
    assert extract_single_value([{}]) == "{}"


def test_parse_person():
    """Ensure person fields are correctly mapped from the API response."""
    person = {
        "intressent_id": "123",
        "hangar_id": "456",
        "tilltalsnamn": "Anna",
        "efternamn": "Andersson",
        "parti": "S",
        "status": "Tjänstgörande",
    }

    result = parse_person(person)

    assert result["intressent_id"] == "123"
    assert result["hangar_id"] == "456"
    assert result["tilltalsnamn"] == "Anna"
    assert result["efternamn"] == "Andersson"
    assert result["parti"] == "S"
    assert result["status"] == "Tjänstgörande"


def test_parse_person_uppdrag():
    """Ensure assignment data is correctly mapped from the API response."""
    person = {
        "personuppdrag": {
            # The API may return a single assignment as an object
            # instead of a list.
            "uppdrag": {
                "organ_kod": "FiU",
                "roll_kod": "Ledamot",
                "ordningsnummer": "1",
                "status": "Tjänstgörande",
                "typ": "utskottsuppdrag",
                "from": "2022-10-01",
                "tom": "2024-01-01",
                "uppgift": ["example"],
                "intressent_id": "123",
                "hangar_id": "456",
                "sortering": "10",
                "organ_sortering": "20",
                "uppdrag_rollsortering": "30",
                "uppdrag_statussortering": "40",
            }
        }
    }

    result = parse_person_uppdrag(person)

    # A single API object should result in one staging row.
    assert len(result) == 1

    uppdrag = result[0]

    assert uppdrag["organ_kod"] == "FiU"
    assert uppdrag["roll_kod"] == "Ledamot"
    assert uppdrag["fran_datum"] == "2022-10-01"
    assert uppdrag["tom_datum"] == "2024-01-01"
    assert uppdrag["uppgift"] == "example"


def test_parse_person_uppdrag_handles_empty_string():
    """Ensure missing assignment data is handled without raising an error."""
    person = {
        # This structure has been observed in the API when assignments
        # are missing for a person.
        "personuppdrag": "",
    }

    assert parse_person_uppdrag(person) == []


def test_parse_person_uppgift():
    """Ensure person details are correctly mapped from the API response."""
    person = {
        "personuppgift": {
            # The API may return a single detail as an object
            # instead of a list.
            "uppgift": {
                "kod": "Bostadsort",
                "uppgift": ["Stockholm"],
                "typ": "biografi",
                "intressent_id": "123",
                "hangar_id": "456",
            }
        }
    }

    result = parse_person_uppgift(person)

    # A single API object should result in one staging row.
    assert len(result) == 1

    uppgift = result[0]

    assert uppgift["kod"] == "Bostadsort"
    assert uppgift["uppgift"] == "Stockholm"
    assert uppgift["typ"] == "biografi"
    assert uppgift["intressent_id"] == "123"
    assert uppgift["hangar_id"] == "456"


def test_get_personer():
    """Ensure persons are extracted from the API response as a list."""
    data = {
        "personlista": {
            "person": {
                "intressent_id": "123",
                "tilltalsnamn": "Anna",
            }
        }
    }

    result = get_personer(data)

    assert len(result) == 1
    assert result[0]["intressent_id"] == "123"
    assert result[0]["tilltalsnamn"] == "Anna"


def test_parse_person_uppgift_handles_missing_data():
    """Ensure missing person details are handled without raising an error."""
    person = {
        "personuppgift": "",
    }

    assert parse_person_uppgift(person) == []
