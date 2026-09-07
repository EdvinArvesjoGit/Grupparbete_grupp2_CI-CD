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

    @property
    def display_name(self) -> str:
        names = {
            "SOCIALDEMOKRATERNA": "Socialdemokraterna",
            "MODERATERNA": "Moderaterna",
            "SVERIGEDEMOKRATERNA": "Sverigedemokraterna",
            "CENTERPARTIET": "Centerpartiet",
            "VANSTERPARTIET": "Vänsterpartiet",
            "KRISTDEMOKRATERNA": "Kristdemokraterna",
            "LIBERALERNA": "Liberalerna",
            "MILJOPARTIET": "Miljöpartiet",
        }
        return names[self.name]


class Kon(StrEnum):
    MAN = "man"
    KVINNA = "kvinna"


class Aldersgrupp(StrEnum):
    AGE_20_29 = "20–29"
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


class Riksmote(StrEnum):
    RM_2022_23 = "2022/23"
    RM_2023_24 = "2023/24"
    RM_2024_25 = "2024/25"
    RM_2025_26 = "2025/26"
