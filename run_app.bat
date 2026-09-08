@echo off
start cmd /k "uvicorn reports.riksdag.riksdagen_api:app --reload"
set PYTHONPATH=.
streamlit run reports/riksdag/riksdagen.py