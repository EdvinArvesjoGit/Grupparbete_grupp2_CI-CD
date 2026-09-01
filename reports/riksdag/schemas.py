from enum import StrEnum

from pydantic import BaseModel


class Parti(StrEnum):
    SOCIALDEMOKRATERNA = "S"
    MODERATERNA = "M"
    SVERIGEDEMOKRATERNA = "SD"
    CENTERPARTIET = "C"
    VANSTERPARTIET = "V"
    KRISTDEMOKRATERNA = "KD"
    LIBERALERNA = "L"
    MILJOPARTIET = "MP"


class Kon(StrEnum):
    MAN = "man"
    KVINNA = "kvinna"


class Aldersgrupp(StrEnum):
    UNDER_30 = "Under 30"
    AGE_30_39 = "30–39"
    AGE_40_49 = "40–49"
    AGE_50_59 = "50–59"
    AGE_60_69 = "60–69"
    OVER_70 = "70+"


class Ledamot(BaseModel):
    intressent_id: str
    fornamn: str
    efternamn: str
    fullstandigt_namn: str
    kon: Kon | None = None
    fodelse_ar: int | None = None
    alder: int | None = None
    aktuellt_parti: str | None = None
    valkrets: str | None = None
    ort: str | None = None
    status: str | None = None
    ar_aktiv: bool
