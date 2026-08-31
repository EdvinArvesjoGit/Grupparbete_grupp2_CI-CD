import pytest

from src.ingest.voteringar import (
    ensure_list,
    get_expected_count,
    get_new_voting_events,
    validate_voting_event,
)


def test_ensure_list_with_none():
    assert ensure_list(None) == []


def test_ensure_list_with_empty_dict():
    assert ensure_list({}) == []


def test_ensure_list_with_dict():
    value = {
        "votering_id": "00178723-112D-4742-8BE9-B606161A44DF",
        "Ja": "264",
    }

    result = ensure_list(value)

    assert result == [value]


def test_ensure_list_with_list():
    value = [
        {
            "votering_id": "00178723-112D-4742-8BE9-B606161A44DF",
            "Ja": "264",
        },
        {
            "votering_id": "00EB3729-40F0-4746-A701-5D5E369747DB",
            "Ja": "233",
        },
    ]

    result = ensure_list(value)

    assert result == value


def test_get_expected_count():
    event = {
        "Ja": "200",
        "Nej": "50",
        "Avstår": "10",
        "Frånvarande": "89",
    }

    result = get_expected_count(event)

    assert result == 349


def test_get_expected_count_with_empty_values():
    event = {
        "Ja": "200",
        "Nej": "50",
        "Avstår": "",
        "Frånvarande": None,
    }

    result = get_expected_count(event)

    assert result == 250


def test_get_new_voting_events():
    events = [
        {"votering_id": "00178723-112D-4742-8BE9-B606161A44DF"},
        {"votering_id": "00EB3729-40F0-4746-A701-5D5E369747DB"},
        {"votering_id": "01141903-9E9E-4477-93E9-7E2A5081AD00"},
    ]

    existing_votering_ids = {
        "00178723-112d-4742-8be9-b606161a44df",
        "00eb3729-40f0-4746-a701-5d5e369747db",
    }

    result = get_new_voting_events(
        events,
        existing_votering_ids,
    )

    assert result == [
        {
            "votering_id": "01141903-9E9E-4477-93E9-7E2A5081AD00",
        }
    ]


def test_get_new_voting_events_when_all_exist():
    events = [
        {"votering_id": "00178723-112D-4742-8BE9-B606161A44DF"},
        {"votering_id": "00EB3729-40F0-4746-A701-5D5E369747DB"},
    ]

    existing_votering_ids = {
        "00178723-112d-4742-8be9-b606161a44df",
        "00eb3729-40f0-4746-a701-5d5e369747db",
    }

    result = get_new_voting_events(
        events,
        existing_votering_ids,
    )

    assert result == []


def test_validate_voting_event_success():
    votering_id = "24315A72-DA70-49D3-9498-F15C5504F256"

    votes = [
        {
            "votering_id": votering_id,
            "intressent_id": "111",
            "rost": "Ja",
        },
        {
            "votering_id": votering_id,
            "intressent_id": "222",
            "rost": "Nej",
        },
        {
            "votering_id": votering_id,
            "intressent_id": "333",
            "rost": "Avstår",
        },
    ]

    validate_voting_event(
        votering_id=votering_id,
        votes=votes,
        expected_count=3,
    )


def test_validate_voting_event_raises_on_count_mismatch():
    votering_id = "24315A72-DA70-49D3-9498-F15C5504F256"

    votes = [
        {
            "votering_id": votering_id,
            "intressent_id": "111",
            "rost": "Ja",
        },
        {
            "votering_id": votering_id,
            "intressent_id": "222",
            "rost": "Nej",
        },
    ]

    with pytest.raises(ValueError, match="Row count mismatch"):
        validate_voting_event(
            votering_id=votering_id,
            votes=votes,
            expected_count=3,
        )


def test_validate_voting_event_raises_on_wrong_votering_id():
    votering_id = "24315A72-DA70-49D3-9498-F15C5504F256"

    votes = [
        {
            "votering_id": votering_id,
            "intressent_id": "111",
        },
        {
            "votering_id": "00178723-112D-4742-8BE9-B606161A44DF",
            "intressent_id": "222",
        },
    ]

    with pytest.raises(ValueError, match="Unexpected votering_id"):
        validate_voting_event(
            votering_id=votering_id,
            votes=votes,
            expected_count=2,
        )
