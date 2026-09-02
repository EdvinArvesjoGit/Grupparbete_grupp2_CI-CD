import pytest

import src.ingest.voteringar as voteringar
from src.ingest.voteringar import (
    ensure_list,
    get_expected_count,
    get_new_voting_events,
    incremental_load,
    initial_load,
    upsert_voting_summaries,
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

    assert ensure_list(value) == [value]


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

    assert ensure_list(value) == value


def test_get_expected_count():
    event = {
        "Ja": "200",
        "Nej": "50",
        "Avstår": "10",
        "Frånvarande": "89",
    }

    assert get_expected_count(event) == 349


def test_get_expected_count_with_empty_values():
    event = {
        "Ja": "200",
        "Nej": "50",
        "Avstår": "",
        "Frånvarande": None,
    }

    assert get_expected_count(event) == 250


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

    result = get_new_voting_events(events, existing_votering_ids)

    assert result == [{"votering_id": "01141903-9E9E-4477-93E9-7E2A5081AD00"}]


def test_get_new_voting_events_when_all_exist():
    events = [
        {"votering_id": "00178723-112D-4742-8BE9-B606161A44DF"},
        {"votering_id": "00EB3729-40F0-4746-A701-5D5E369747DB"},
    ]

    existing_votering_ids = {
        "00178723-112d-4742-8be9-b606161a44df",
        "00eb3729-40f0-4746-a701-5d5e369747db",
    }

    assert get_new_voting_events(events, existing_votering_ids) == []


class FakeResult:
    def __init__(self, rowcount=1):
        self.rowcount = rowcount


class FakeConnection:
    def __init__(self):
        self.executed_rows = []
        self.committed = False

    def execute(self, sql, params):
        self.executed_rows.append(params)
        return FakeResult()

    def commit(self):
        self.committed = True


def test_upsert_voting_summaries():
    conn = FakeConnection()

    events = [
        {
            "votering_id": "00178723-112D-4742-8BE9-B606161A44DF",
            "Ja": "264",
            "Nej": "33",
            "Frånvarande": "52",
            "Avstår": "0",
        },
        {
            "votering_id": "00EB3729-40F0-4746-A701-5D5E369747DB",
            "Ja": "233",
            "Nej": "20",
            "Frånvarande": "62",
            "Avstår": "34",
        },
    ]

    result = upsert_voting_summaries(
        conn=conn,
        rm="2025/26",
        events=events,
        run_id="test-run-id",
    )

    assert result == 2
    assert conn.committed is True

    assert conn.executed_rows[0] == {
        "votering_id": "00178723-112D-4742-8BE9-B606161A44DF",
        "rm": "2025/26",
        "ja": 264,
        "nej": 33,
        "franvarande": 52,
        "avstar": 0,
        "_kalla": "https://data.riksdagen.se/voteringlista/",
        "_korning_id": "test-run-id",
    }


def test_validate_voting_event_success():
    votering_id = "24315A72-DA70-49D3-9498-F15C5504F256"

    votes = [
        {"votering_id": votering_id, "intressent_id": "111", "rost": "Ja"},
        {"votering_id": votering_id, "intressent_id": "222", "rost": "Nej"},
        {"votering_id": votering_id, "intressent_id": "333", "rost": "Avstår"},
    ]

    validate_voting_event(
        votering_id=votering_id,
        votes=votes,
        expected_count=3,
    )


def test_validate_voting_event_raises_on_count_mismatch():
    votering_id = "24315A72-DA70-49D3-9498-F15C5504F256"

    votes = [
        {"votering_id": votering_id, "intressent_id": "111", "rost": "Ja"},
        {"votering_id": votering_id, "intressent_id": "222", "rost": "Nej"},
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
        {"votering_id": votering_id, "intressent_id": "111"},
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


def test_initial_load_loads_all_events(monkeypatch):
    events_by_rm = {
        "2024/25": [
            {"votering_id": "id-1"},
            {"votering_id": "id-2"},
        ],
        "2025/26": [
            {"votering_id": "id-3"},
        ],
    }

    summary_calls = []
    detail_calls = []

    monkeypatch.setattr(voteringar, "RIKSMOTEN", ["2024/25", "2025/26"])
    monkeypatch.setattr(
        voteringar,
        "fetch_voting_events",
        lambda rm: events_by_rm[rm],
    )

    def fake_upsert(conn, rm, events, run_id):
        summary_calls.append(
            {
                "rm": rm,
                "events": events,
                "run_id": run_id,
            }
        )
        return len(events)

    def fake_load_details(conn, events, run_id=None):
        detail_calls.append(events)
        return len(events) * 349

    monkeypatch.setattr(voteringar, "upsert_voting_summaries", fake_upsert)
    monkeypatch.setattr(voteringar, "load_voting_details", fake_load_details)

    initial_load(conn=object(), run_id="run-123")

    assert summary_calls == [
        {
            "rm": "2024/25",
            "events": events_by_rm["2024/25"],
            "run_id": "run-123",
        },
        {
            "rm": "2025/26",
            "events": events_by_rm["2025/26"],
            "run_id": "run-123",
        },
    ]

    assert detail_calls == [
        events_by_rm["2024/25"],
        events_by_rm["2025/26"],
    ]


def test_incremental_load_only_loads_missing_events(monkeypatch):
    existing_id = "00178723-112D-4742-8BE9-B606161A44DF"
    new_id = "00EB3729-40F0-4746-A701-5D5E369747DB"

    events = [
        {"votering_id": existing_id},
        {"votering_id": new_id},
    ]

    summary_calls = []
    detail_calls = []

    monkeypatch.setattr(voteringar, "RIKSMOTEN", ["2025/26"])
    monkeypatch.setattr(voteringar, "fetch_voting_events", lambda rm: events)
    monkeypatch.setattr(
        voteringar,
        "get_existing_votering_ids",
        lambda conn, rm: {existing_id.lower()},
    )

    def fake_upsert(conn, rm, events, run_id):
        summary_calls.append(events)
        return len(events)

    def fake_load_details(conn, events, run_id=None):
        detail_calls.append(events)
        return len(events) * 349

    monkeypatch.setattr(voteringar, "upsert_voting_summaries", fake_upsert)
    monkeypatch.setattr(voteringar, "load_voting_details", fake_load_details)

    incremental_load(conn=object(), run_id="run-456")

    # Summary always stores/updates every event returned by the list API.
    assert summary_calls == [events]

    # Detail loading only receives events missing from stg.votering.
    assert detail_calls == [[{"votering_id": new_id}]]


def test_incremental_load_loads_no_details_when_all_exist(monkeypatch):
    events = [
        {"votering_id": "id-1"},
        {"votering_id": "id-2"},
    ]

    detail_calls = []

    monkeypatch.setattr(voteringar, "RIKSMOTEN", ["2025/26"])
    monkeypatch.setattr(voteringar, "fetch_voting_events", lambda rm: events)
    monkeypatch.setattr(
        voteringar,
        "get_existing_votering_ids",
        lambda conn, rm: {"id-1", "id-2"},
    )
    monkeypatch.setattr(
        voteringar,
        "upsert_voting_summaries",
        lambda conn, rm, events, run_id: len(events),
    )

    def fake_load_details(conn, events, run_id=None):
        detail_calls.append(events)
        return 0

    monkeypatch.setattr(voteringar, "load_voting_details", fake_load_details)

    incremental_load(conn=object(), run_id="run-789")

    assert detail_calls == [[]]
