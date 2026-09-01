"""Tester för dw.dim_ledamot-logiken (SCD-2)."""

from src.transform.dim_ledamot import _har_andrats


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
