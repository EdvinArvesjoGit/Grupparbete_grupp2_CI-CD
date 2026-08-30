import pytest

from src.ingest.voteringar import (
    ensure_list,
    get_expected_count,
    get_new_groups,
    validate_group,
)


def test_ensure_list_with_none():
    assert ensure_list(None) == []


def test_ensure_list_with_empty_dict():
    assert ensure_list({}) == []


def test_ensure_list_with_dict():
    value = {"bet": "AU10", "punkt": "3"}

    result = ensure_list(value)

    assert result == [value]


def test_ensure_list_with_list():
    value = [
        {"bet": "AU10", "punkt": "3"},
        {"bet": "AU10", "punkt": "13"},
    ]

    result = ensure_list(value)

    assert result == value


def test_get_expected_count():
    group = {
        "Ja": "200",
        "Nej": "50",
        "Avstår": "10",
        "Frånvarande": "89",
    }

    result = get_expected_count(group)

    assert result == 349


def test_get_expected_count_with_empty_values():
    group = {
        "Ja": "200",
        "Nej": "50",
        "Avstår": "",
        "Frånvarande": None,
    }

    result = get_expected_count(group)

    assert result == 250


def test_get_new_groups():
    groups = [
        {"bet": "AU10", "punkt": "1"},
        {"bet": "AU10", "punkt": "2"},
        {"bet": "AU10", "punkt": "3"},
    ]

    existing_groups = {
        ("AU10", "1"),
        ("AU10", "2"),
    }

    result = get_new_groups(groups, existing_groups)

    assert result == [
        {"bet": "AU10", "punkt": "3"},
    ]


def test_get_new_groups_when_all_exist():
    groups = [
        {"bet": "AU10", "punkt": "1"},
        {"bet": "AU10", "punkt": "2"},
    ]

    existing_groups = {
        ("AU10", "1"),
        ("AU10", "2"),
    }

    result = get_new_groups(groups, existing_groups)

    assert result == []


def test_validate_group_success():
    votes = [
        {"rost": "Ja"},
        {"rost": "Nej"},
        {"rost": "Avstår"},
    ]

    validate_group(
        rm="2025/26",
        bet="AU10",
        punkt="3",
        votes=votes,
        expected_count=3,
    )


def test_validate_group_raises_on_count_mismatch():
    votes = [
        {"rost": "Ja"},
        {"rost": "Nej"},
    ]

    with pytest.raises(ValueError, match="Row count mismatch"):
        validate_group(
            rm="2025/26",
            bet="AU10",
            punkt="3",
            votes=votes,
            expected_count=3,
        )
