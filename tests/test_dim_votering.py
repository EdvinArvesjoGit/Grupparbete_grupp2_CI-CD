"""Tester för dw.dim_votering-logiken."""

from src.transform.dim_votering import _rensa_votering


def test_rensa_votering_saknar_id_ger_none():
    votering = {"votering_id": None, "datum": "2023-05-10 00:00:00"}
    assert _rensa_votering(votering) is None


def test_rensa_votering_extraherar_datumdel():
    votering = {
        "votering_id": "abc-123",
        "datum": "2023-05-10 00:00:00",
        "rm": "2022/23",
        "beteckning": "UU15",
        "punkt": "5",
        "avser": "sakfrågan",
    }
    resultat = _rensa_votering(votering)
    assert resultat["datum"] == "2023-05-10"


def test_rensa_votering_saknat_datum_ger_none_datum():
    votering = {"votering_id": "abc-123", "datum": None}
    resultat = _rensa_votering(votering)
    assert resultat["datum"] is None
