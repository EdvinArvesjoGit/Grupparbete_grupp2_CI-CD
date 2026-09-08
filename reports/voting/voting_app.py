from __future__ import annotations

import html
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from voting_sql import get_filter_options, get_summary, get_voteringar

st.set_page_config(
    page_title="Voteringar | Riksdagen",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
        --riksdag-blue: #005a9c;
        --riksdag-dark: #16324f;
        --riksdag-light: #eef5f9;
        --riksdag-border: #cbd6df;
    }
    .stApp { background: #fff; }
    .block-container { max-width: 1180px; padding-top: 0.8rem; }
    .topline { height: 7px; background: var(--riksdag-blue); margin: -1rem -2rem 1rem; }
    .brand { border-bottom: 1px solid var(--riksdag-border); padding: .45rem 0 .8rem; }
    .brand-kicker { color: #555; font-size: .8rem; letter-spacing: .04em; text-transform: uppercase; }
    .brand-title { color: var(--riksdag-dark); font-size: 1.9rem; font-weight: 700; margin: .05rem 0 0; }
    .crumb { color: #555; font-size: .85rem; margin: .8rem 0 1.1rem; }
    .page-title { color: var(--riksdag-dark); font-size: 2rem; font-weight: 700; margin-bottom: .15rem; }
    .intro { color: #444; margin-bottom: 1.2rem; }
    .filter-box { background: var(--riksdag-light); border: 1px solid var(--riksdag-border); padding: 1rem 1.1rem .55rem; margin-bottom: 1.2rem; }
    .section-title { color: var(--riksdag-dark); font-size: 1.35rem; font-weight: 700; border-bottom: 3px solid var(--riksdag-blue); padding-bottom: .35rem; margin: 1.2rem 0 .8rem; }
    .condition { background: #f7f7f7; border-left: 4px solid var(--riksdag-blue); padding: .65rem .8rem; margin-bottom: .9rem; }
    .result-count { font-size: .95rem; color: #333; margin: .3rem 0 .8rem; }
    .vote-pill { display:inline-block; border:1px solid #bbb; border-radius: 999px; padding:.12rem .5rem; font-size:.8rem; }
    .footer { border-top: 1px solid var(--riksdag-border); margin-top: 2rem; padding-top: 1rem; color:#555; font-size:.82rem; }
    div[data-testid="stDataFrame"] { border: 1px solid var(--riksdag-border); }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="topline"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="brand"><div class="brand-kicker">Sveriges riksdag</div>'
    '<div class="brand-title">Öppna data</div></div>',
    unsafe_allow_html=True,
)
st.markdown('<div class="crumb">Start › Data › Voteringar</div>', unsafe_allow_html=True)
st.markdown('<div class="page-title">Sök bland voteringar</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="intro">Filtrera bland voteringsresultaten på samma sätt som på Riksdagens '
    "öppna data-sida. Resultaten hämtas från projektets eget data warehouse.</div>",
    unsafe_allow_html=True,
)

try:
    options = get_filter_options()
    db_error = None
except Exception as exc:  # Streamlit should render a useful setup error instead of crashing.
    options = {
        "riksmoten": [],
        "partier": [],
        "valkretsar": [],
        "roster": [],
        "ledamoter": [],
        "beteckningar": [],
    }
    db_error = exc

with st.container(border=True):
    st.markdown('<div class="section-title">Villkor</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        riksmote = st.selectbox(
            "Riksmöte", [""] + options["riksmoten"], format_func=lambda x: "Alla" if x == "" else x
        )
        beteckning = st.text_input("Beteckning", placeholder="t.ex. AU1")
        punkt = st.text_input("Förslagspunkt", placeholder="t.ex. 2")
    with col2:
        parti = st.selectbox(
            "Parti", [""] + options["partier"], format_func=lambda x: "Alla" if x == "" else x
        )
        valkrets = st.selectbox(
            "Valkrets", [""] + options["valkretsar"], format_func=lambda x: "Alla" if x == "" else x
        )
    with col3:
        rost = st.selectbox(
            "Röst", [""] + options["roster"], format_func=lambda x: "Alla" if x == "" else x
        )
        ledamot = st.selectbox(
            "Ledamot", [""] + options["ledamoter"], format_func=lambda x: "Alla" if x == "" else x
        )
        antal = st.selectbox("Antal svar", [100, 250, 500, 1000, 5000], index=2)

    search = st.button("Sök", type="primary", use_container_width=False)

filters = {
    "riksmote": riksmote,
    "beteckning": beteckning,
    "punkt": punkt,
    "parti": parti,
    "valkrets": valkrets,
    "rost": rost,
    "ledamot": ledamot,
}

if db_error:
    st.error(
        "Kunde inte ansluta till databasen. Kontrollera .env och att PostgreSQL körs "
        "samt att dw-tabellerna är skapade."
    )
    st.caption(f"Tekniskt fel: {db_error}")
else:
    # Show results on first load too; the button is there to match the source site's interaction.
    try:
        with st.spinner("Hämtar voteringsresultat …"):
            df = get_voteringar(filters, limit=antal)
            summary = get_summary(filters)
    except Exception as exc:
        st.error("Kunde inte läsa voteringsresultaten från data warehouse.")
        st.caption(f"Tekniskt fel: {exc}")
        df = pd.DataFrame()
        summary = pd.DataFrame()

    if search or not df.empty:
        st.markdown(
            '<div class="section-title">Voteringar – resultat</div>', unsafe_allow_html=True
        )
        active = [f"{k}={v}" for k, v in filters.items() if v]
        condition = ", ".join(active) if active else "inga filter"
        st.markdown(
            f'<div class="condition"><strong>Villkor:</strong> {html.escape(condition)}</div>',
            unsafe_allow_html=True,
        )

        if not df.empty:
            st.markdown(
                f'<div class="result-count"><strong>{len(df):,}</strong> svar visas</div>',
                unsafe_allow_html=True,
            )

            display = df.rename(
                columns={
                    "riksmote": "Riksmöte",
                    "beteckning": "Beteckning",
                    "punkt": "Punkt",
                    "avser": "Avser",
                    "datum": "Datum",
                    "ledamot": "Ledamot",
                    "parti": "Parti",
                    "valkrets": "Valkrets",
                    "rost": "Röst",
                    "votering_id": "Votering-ID",
                }
            )
            st.dataframe(display, use_container_width=True, hide_index=True)

            if not summary.empty:
                st.markdown(
                    '<div class="section-title">Sammanfattning</div>', unsafe_allow_html=True
                )
                chart = summary.set_index("rost")["antal"]
                st.bar_chart(chart)

                csv = df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "Ladda ner resultat som CSV",
                    csv,
                    file_name="voteringar.csv",
                    mime="text/csv",
                )
        else:
            st.info("Inga voteringar matchar de valda villkoren.")

st.markdown(
    '<div class="footer">Källa: Sveriges riksdag, öppna data. Den här rapporten använder '
    "projektets eget data warehouse för visning och analys.</div>",
    unsafe_allow_html=True,
)
