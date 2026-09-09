"""Tester för dw.fakta_rost-logiken."""

from datetime import date

from src.transform.fakta_rost import _bygg_fakta_rad, _extrahera_utskottskod


def test_extrahera_utskottskod_med_siffra():
    assert _extrahera_utskottskod("FiU22") == "FiU"


def test_extrahera_utskottskod_med_en_siffra():
    assert _extrahera_utskottskod("SoU5") == "SoU"


def test_extrahera_utskottskod_saknas():
    assert _extrahera_utskottskod(None) is None


def test_extrahera_utskottskod_tom_strang():
    assert _extrahera_utskottskod("") is None


def _fejkade_lookups():
    """Fejkade uppslagstabeller för att testa _bygg_fakta_rad isolerat."""
    return {
        "ledamot_lookup": {"0001": 10},
        "parti_lookup": {"S": 20},
        "votering_lookup": {"abc-123": 30},
        "utskott_lookup": {"FiU": 40},
        "rost_lookup": {"Ja": 50},
        "datum_lookup": {date(2023, 5, 10): 60},
    }


def test_bygg_fakta_rad_med_alla_kopplingar():
    lookups = _fejkade_lookups()
    rad = {
        "intressent_id": "0001",
        "parti": "S",
        "votering_id": "abc-123",
        "beteckning": "FiU22",
        "rost": "Ja",
        "datum": "2023-05-10 00:00:00",
    }
    resultat = _bygg_fakta_rad(
        rad,
        lookups["ledamot_lookup"],
        lookups["parti_lookup"],
        lookups["votering_lookup"],
        lookups["utskott_lookup"],
        lookups["rost_lookup"],
        lookups["datum_lookup"],
    )
    assert resultat["ledamot_nyckel"] == 10
    assert resultat["parti_nyckel"] == 20
    assert resultat["votering_nyckel"] == 30
    assert resultat["utskott_nyckel"] == 40
    assert resultat["rost_nyckel"] == 50
    assert resultat["datum_nyckel"] == 60


def test_bygg_fakta_rad_saknar_ledamot_ger_none():
    """ledamot_nyckel är obligatorisk — utan matchning ska hela raden hoppas över."""
    lookups = _fejkade_lookups()
    rad = {
        "intressent_id": "OKÄND",
        "parti": "S",
        "votering_id": "abc-123",
        "beteckning": "FiU22",
        "rost": "Ja",
        "datum": "2023-05-10 00:00:00",
    }
    resultat = _bygg_fakta_rad(
        rad,
        lookups["ledamot_lookup"],
        lookups["parti_lookup"],
        lookups["votering_lookup"],
        lookups["utskott_lookup"],
        lookups["rost_lookup"],
        lookups["datum_lookup"],
    )
    assert resultat is None


def test_bygg_fakta_rad_saknar_parti_ger_null_parti_men_gar_igenom():
    """parti_nyckel är valfri — saknad matchning ska inte stoppa hela raden."""
    lookups = _fejkade_lookups()
    rad = {
        "intressent_id": "0001",
        "parti": "OKÄNT_PARTI",
        "votering_id": "abc-123",
        "beteckning": "FiU22",
        "rost": "Ja",
        "datum": "2023-05-10 00:00:00",
    }
    resultat = _bygg_fakta_rad(
        rad,
        lookups["ledamot_lookup"],
        lookups["parti_lookup"],
        lookups["votering_lookup"],
        lookups["utskott_lookup"],
        lookups["rost_lookup"],
        lookups["datum_lookup"],
    )
    assert resultat is not None
    assert resultat["parti_nyckel"] is None
