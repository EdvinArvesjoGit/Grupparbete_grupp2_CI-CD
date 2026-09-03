"""Tester för dw.dim_ledamot-logiken (SCD-2)."""

from src.transform.dim_ledamot import _har_andrats, _rensa_person, _sakert_heltal


def test_har_andrats_inget_andrat():
    befintlig = {"parti": "S", "valkrets": "Stockholms kommun"}
    ny = {"parti": "S", "valkrets": "Stockholms kommun"}
    assert _har_andrats(befintlig, ny) is False


def test_har_andrats_parti_andrat():
    befintlig = {"parti": "S", "valkrets": "Stockholms kommun"}
    ny = {"parti": "C", "valkrets": "Stockholms kommun"}
    assert _har_andrats(befintlig, ny) is True


def test_har_andrats_valkrets_andrat():
    befintlig = {"parti": "S", "valkrets": "Stockholms kommun"}
    ny = {"parti": "S", "valkrets": "Stockholms län"}
    assert _har_andrats(befintlig, ny) is True


def test_rensa_person_saknar_id_ger_none():
    person = {"intressent_id": "", "tilltalsnamn": "Anna"}
    assert _rensa_person(person) is None


def test_rensa_person_partilos_normaliseras():
    person = {"intressent_id": "0001", "parti": "-", "tilltalsnamn": "Elsa", "efternamn": "W"}
    resultat = _rensa_person(person)
    assert resultat["parti"] == "Partilös"


def test_rensa_person_trimmar_mellanslag():
    person = {"intressent_id": " 0001 ", "tilltalsnamn": " Anna ", "efternamn": "A"}
    resultat = _rensa_person(person)
    assert resultat["intressent_id"] == "0001"
    assert resultat["fornamn"] == "Anna"


def test_sakert_heltal_giltig_sträng():
    assert _sakert_heltal("1975") == 1975


def test_sakert_heltal_tom_sträng_ger_none():
    assert _sakert_heltal("") is None


def test_sakert_heltal_none_ger_none():
    assert _sakert_heltal(None) is None
