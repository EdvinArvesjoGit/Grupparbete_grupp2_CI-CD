import altair as alt
import pandas as pd
import requests
import streamlit as st

import reports.riksdag.schemas as schemas

API_URL = "http://127.0.0.1:8000"

# --------------------------------------------------
# Mandatfördelning
# --------------------------------------------------

st.title("Mandatfördelning 2022-2026")
st.caption("Fördelningen av riksdagens 349 mandat efter valet 2022.")

response_mandat = requests.get(f"{API_URL}/riksdagen/mandat")
response_mandat.raise_for_status()

mandat_data = response_mandat.json()["mandat"]

total_mandat = sum(row["mandat_2022"] for row in mandat_data)

antal_partier = len(mandat_data)

# KPI
kpi1, kpi2 = st.columns(2)

kpi1.metric(
    "Antal platser",
    total_mandat,
)
kpi2.metric(
    "Antal partier",
    antal_partier,
)

# Bar chart
mandat_df = pd.DataFrame(mandat_data)

mandat_chart = (
    alt.Chart(mandat_df)
    .mark_bar(color="#1F4E79")
    .encode(
        x=alt.X(
            "mandat_2022:Q",
            axis=None,
        ),
        y=alt.Y(
            "partinamn:N",
            title=None,
            sort="-x",
        ),
        tooltip=[
            alt.Tooltip(
                "partinamn:N",
                title="Parti",
            ),
            alt.Tooltip("mandat_2022:Q", title="mandat"),
        ],
    )
    .properties(height=350)
)
st.altair_chart(
    mandat_chart,
    use_container_width=True,
)

# --------------------------------------------------
# Riksdagens sammansättning
# --------------------------------------------------

st.title("Riksdagens sammansättning")
st.caption("Visar riksdagens sammansättning efter parti, kön och ålder.")

# Filter
selected_parti = st.selectbox(
    "Parti",
    [None, *schemas.Parti],
    format_func=lambda parti: "Alla partier" if parti is None else parti.display_name,
    label_visibility="collapsed",
)

# Parameters
params = {}

if selected_parti is not None:
    params["parti"] = selected_parti.value

# KPI
response_stats = requests.get(
    f"{API_URL}/riksdagen/statistik",
    params=params,
)
response_stats.raise_for_status()

stats = response_stats.json()

andel_kvinnor = stats["antal_kvinnor"] / stats["antal_ledamoter"] * 100

medianalder = stats["medianalder"]

kpi1, kpi2, kpi3 = st.columns(3)

with kpi1:
    st.metric(
        "Antal ledamöter",
        stats["antal_ledamoter"],
    )

with kpi2:
    st.metric(
        "Medianålder",
        round(medianalder) if medianalder is not None else "-",
    )
with kpi3:
    st.metric(
        "Andel kvinnor",
        f"{andel_kvinnor:.0f} %",
    )

col1, col2 = st.columns(2)

# BAR CHART - ÅLDERSFÖRDELNING

with col1:
    st.subheader("Åldersfördelning")
    st.caption("Staplarna visar antalet ledamöter i varje åldersgrupp")

    response_age = requests.get(f"{API_URL}/riksdagen/aldersfördelning", params=params)

    if response_age.status_code == 200:
        age_data = response_age.json()["aldersfordelning"]
        age_df = pd.DataFrame(age_data)
        age_order = [group.value for group in schemas.Aldersgrupp]

        age_chart = (
            alt.Chart(age_df)
            .mark_bar(color="#1F4E79")
            .encode(
                x=alt.X(
                    "antal:Q",
                    title=None,
                ),
                y=alt.Y("aldersgrupp:N", title=None, sort=age_order),
                tooltip=[
                    alt.Tooltip("aldersgrupp:N", title=None),
                    alt.Tooltip(
                        "antal:Q",
                        title=None,
                    ),
                ],
            )
            .properties(height=300)
        )

        st.altair_chart(
            age_chart,
            use_container_width=True,
        )

    else:
        st.error(f"Kunde inte hämta åldersfördelning: {response_age.status_code}")

# PIE CHART "KÖNSFÖRDELNING

with col2:
    st.subheader("Könsfördelning")
    st.caption("Mörkblå färg visar män och ljusblå färg visar kvinnor")

    if stats is not None:
        gender_count = pd.DataFrame(
            {
                "Kön": ["Kvinnor", "Män"],
                "Antal": [
                    stats["antal_kvinnor"],
                    stats["antal_man"],
                ],
            }
        )
        gender_chart = (
            alt.Chart(gender_count)
            .mark_arc()
            .encode(
                theta=alt.Theta("Antal:Q"),
                color=alt.Color(
                    "Kön:N",
                    legend=None,
                    scale=alt.Scale(
                        domain=["Män", "Kvinnor"],
                        range=["#1F4E79", "#9DC3E6"],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("Kön:N", title="Kön"),
                    alt.Tooltip("Antal:Q", title="Antal"),
                ],
            )
            .properties(
                height=300,
            )
        )
        st.altair_chart(
            gender_chart,
            use_container_width=True,
        )
