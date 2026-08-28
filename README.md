# riksdag-etl

An ETL pipeline over Swedish parliamentary open data, built as a six-person team
project at Nackademin (Data Engineering, YH).

Members and votes are extracted from `data.riksdagen.se`, landed in a PostgreSQL
staging layer, transformed into a star schema, and presented through two
Streamlit reports.

> **Källa: Sveriges riksdag.** The data is free to reuse; attribution is
> required and must appear in any published output.

---

## Architecture

```
data.riksdagen.se
      │
      │  Python extractors (src/ingest)
      ▼
┌─────────────┐
│  stg  (bronze)  raw, source-faithful, text-typed
└─────────────┘
      │
      │  Python transform (src/transform)
      ▼
┌─────────────┐
│  dw   (silver)  star schema — dim_* / fakta_rost
└─────────────┘
      │
      │  Streamlit (reports/)
      ▼
  Two reports: Riksdag composition · Voting behaviour
```

Full data model, naming rules and DDL ownership: **[DATABASE.md](DATABASE.md)**

**Scope:** riksmöten 2022/23 – 2025/26 (the 2022–2026 mandate period). Large
enough to be non-trivial, small enough to rebuild in a couple of minutes.

---

## Team and responsibilities

| # | Area | Owns |
|---|---|---|
| P1 | Ingest — ledamöter | `src/ingest/ledamoter.py`, `sql/1*_stg_person*.sql` |
| P2 | Ingest — voteringar | `src/ingest/voteringar.py`, `sql/2*_stg_votering.sql` |
| P3 | Transform — star schema | `src/transform/`, `sql/3*_dw_*.sql` |
| P4 | Report — Riksdag composition | `reports/riksdag/` |
| P5 | Report — voting behaviour | `reports/voting/` |
| P6 | Platform, CI/CD, orchestration | `.github/`, `sql/00_init.sql`, `src/common/` |

One folder, one owner. This keeps merge conflicts rare — if you find yourself
editing someone else's folder, talk to them first.

---

## Repository layout

```
├── .github/workflows/     # CI pipelines                      (P6)
├── src/
│   ├── common/            # shared config + db connection     (P6)
│   ├── ingest/            # API → stg                         (P1, P2)
│   └── transform/         # stg → dw                          (P3)
├── reports/
│   ├── riksdag/           # Streamlit app                     (P4)
│   └── voting/            # Streamlit app                     (P5)
├── sql/                   # DDL, numbered for execution order
├── data/raw/              # local downloads — gitignored
├── tests/
├── DATABASE.md            # the data model contract
├── requirements.txt       # runtime dependencies
└── requirements-dev.txt   # ruff, pytest
```

---

## Getting started

Requires **Python 3.11+**, **Git**, and a local **PostgreSQL** install.
Takes about ten minutes. If you are stuck longer than that, say so in the team
channel — a broken setup step is a bug in this document, not your fault.

### 1. Clone

```bash
cd /c/projects        # or wherever you keep repos
git clone https://github.com/<org-or-user>/riksdag-etl.git
cd riksdag-etl
```

### 2. Virtual environment

```bash
python -m venv .venv
```

Activate it — the command differs per shell:

| Shell | Command |
|---|---|
| Git Bash (Windows) | `source .venv/Scripts/activate` |
| PowerShell | `.\.venv\Scripts\Activate.ps1` |
| CMD | `.venv\Scripts\activate.bat` |
| macOS / Linux | `source .venv/bin/activate` |

Your prompt should now start with `(.venv)`. Then install:

```bash
python -m pip install -r requirements-dev.txt
```

> **permission denied?** The venv is not active and pip is writing to your
> system Python. Activate it first. Do not use `sudo`, do not run the terminal
> as administrator, and do not add `--user` — all three "work" but install
> outside the venv, and your environment then differs from everyone else's.
> Check with `which python` — the path must contain `.venv`.

> **PowerShell execution policy error?**
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 3. Configuration

```bash
cp .env.example .env
```

Edit `.env` and set `PGPASSWORD` to your local Postgres password.

### 4. Database

```bash
createdb riksdag
psql -d riksdag -f sql/00_init.sql
```

The script prints the three schemas it created: `stg`, `dw`, `ops`.
If you do not see all three, stop and ask before continuing.

### 5. Verify

```bash
ruff check .
ruff format --check .
pytest
```

All three must pass — they are exactly what CI runs. Then check the database
connection:

```bash
python -c "from src.common.db import check_connection; print(check_connection())"
```

Should print `True`.

### 6. VS Code

`Ctrl+Shift+P` → **Python: Select Interpreter** → choose the one under
`.venv` inside this repo. Close and reopen the terminal; `(.venv)` should
appear automatically.

Recommended extensions: **Python**, **Pylance**, **Ruff**.

**Never commit:** `.env`, `.venv/`, `data/raw/`. All three are in `.gitignore` —
if `git status` shows them, stop and say so in the team channel.

---

## Working conventions

**Branches** — one branch per task, named by area:

```
ingest/ledamoter-extractor
transform/dim-ledamot
report/voting-cohesion
ci/ruff-workflow
```

**Never commit directly to `main`.** Open a pull request; **two** approvals are
required. CI must be green before merge.

**Commits** — imperative, one logical change:

```
Add stg.person DDL with audit columns
Fix single-child node handling in personlista parser
```

**Line endings** are normalised via `.gitattributes` (`* text=auto eol=lf`).
If you see a diff where an entire file appears changed but nothing was edited,
that is a line-ending problem — flag it rather than committing it.

---

## Continuous integration

`.github/workflows/ci.yml` runs on every pull request and on pushes to `main`:

| Step | Tool |
|---|---|
| Lint | `ruff check .` |
| Format check | `ruff format --check .` |
| Tests | `pytest -q` |

Run all three locally before pushing — it is faster than waiting for the runner.
Ruff config lives in `pyproject.toml` and starts deliberately lenient (`E`, `F`,
`I`, `UP`). Rules get added by team agreement, not unilaterally.

---

## Status

Sprint 0 — scaffolding. The database contract is agreed; DDL and extractors are
in progress. See the GitHub Projects board for current assignments.

Four data design decisions (D1–D4 in [DATABASE.md](DATABASE.md)) remain open and
must be resolved before the reports are finalised.
