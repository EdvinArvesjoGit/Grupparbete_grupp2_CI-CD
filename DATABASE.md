# Database structure — riksdag-etl

Agreed data model for the project. This document is the **contract** between team
members: it fixes schema names, table names, ownership and layer rules so that
everyone can write code in parallel against a known shape, before any real data
exists.

**Source:** Sveriges riksdag open data — `data.riksdagen.se`
**Attribution required in all output:** *Källa: Sveriges riksdag*
**Warehouse:** PostgreSQL
**Scope:** riksmöten **2022/23 – 2025/26** (the 2022–2026 mandate period)

> **Status of this document.** Schema names, layer rules and ownership were
> agreed in the team meeting (high confidence). Column lists below are taken
> from riksdagen's published dataset field documentation and are a **starting
> point for the DDL owners, not a final specification** (medium confidence) —
> the owner of each table confirms the real columns against a live extract and
> updates this file in the same PR as their DDL.

---

## 1. Layers

| Schema | Layer | Contains | Written by | Read by |
|---|---|---|---|---|
| `stg` | Bronze | Raw landing zone, mirrors the source | P1, P2 | P3 only |
| `dw` | Silver | Conformed star schema | P3 | P4, P5 |
| `ops` | — | Pipeline run metadata | P6 | anyone |

**Three rules that keep the layers usable:**

1. **`stg` mirrors the source.** Source fields are preserved except for minimal
   identifier normalization required by the project's naming conventions.
   No filtering, no deduplication, no type cleverness. Text stays text. All
   cleaning happens in the transform step, where it is visible in a diff and
   testable.
2. **Reports never read `stg`.** P4 and P5 query `dw` exclusively. If something
   needed for a report is missing from `dw`, that is a change request to P3, not
   a shortcut into staging.
3. **Loads are re-runnable.** Running the pipeline twice produces the same
   result as running it once. No append-only-by-accident tables.

---

## 2. Naming conventions

Decided so that nobody has to quote identifiers or guess casing.

| Rule | Example |
|---|---|
| lowercase `snake_case` for all objects | `stg.person_uppdrag` |
| no Swedish characters in object names | `fodd_ar`, not `född_år` |
| no reserved words as column names | `fran_datum` / `tom_datum`, never `from` / `to` |
| dimensions prefixed `dim_` | `dw.dim_ledamot` |
| facts prefixed `fakta_` | `dw.fakta_rost` |
| surrogate keys suffixed `_nyckel` | `ledamot_nyckel` |
| source/business keys keep the source name | `intressent_id` |

Domain vocabulary stays Swedish (`votering`, `ledamot`, `parti`) because that is
what the source calls things and translating it invites mismatches. Structural
vocabulary is English (`dim_`, `fakta_`, `_nyckel`).

### Audit columns on every `stg` table

Cheap, and they make load problems diagnosable instead of mysterious:

| Column | Type | Meaning |
|---|---|---|
| `_laddad_tidpunkt` | `TIMESTAMPTZ DEFAULT now()` | when the row landed |
| `_kalla` | `TEXT` | source endpoint or dataset file |
| `_korning_id` | `TEXT` | ties the row to a row in `ops.load_log` |

---

## 3. Table inventory

### 3.1 Bronze — `stg`

| Table | Owner | Grain | Business key |
|---|---|---|---|
| `stg.person` | **P1** | one row per person | TBD — unique source key to be confirmed |
| `stg.person_uppdrag` | **P1** | one row per assignment (uppdrag) | TBD — no unique source key verified |
| `stg.person_uppgift` | **P1** | one row per person detail (uppgift) | TBD — no unique source key verified |
| `stg.votering` | **P2** | one row per member per vote | `votering_id` + `intressent_id` |
| `stg.organ` | *open* | one row per committee/body | `organ_kod` |
| `stg.roll` | *open* | one row per role type | `roll_kod` |
| `stg.riksmote` | *open* | one row per parliamentary year | `rm` |

**`stg.votering`** — documented dataset fields:

```
rm, beteckning, votering_id, punkt, namn, intressent_id, parti,
valkrets, rost, avser, banknummer, kon, fodd, datum
```

**`stg.person`** — verified top-level fields from the live member API,
following the project's `snake_case` naming conventions:

```text
hangar_guid, sourceid, intressent_id, hangar_id, fodd_ar, kon,
efternamn, tilltalsnamn, sorteringsnamn, iort, parti, valkrets,
status, person_url_xml, bild_url_80, bild_url_192, bild_url_max
```

**`stg.person_uppdrag`** — verified fields from `personuppdrag.uppdrag`,
following the project's `snake_case` naming conventions:

```text
organ_kod, roll_kod, ordningsnummer, status, typ, fran_datum,
tom_datum, uppgift, intressent_id, hangar_id, sortering,
organ_sortering, uppdrag_rollsortering, uppdrag_statussortering
```

The source fields `from` and `tom` are stored as `fran_datum` and
`tom_datum` to follow the project's naming conventions.

**`stg.person_uppgift`** — verified fields from `personuppgift.uppgift`,
following the project's `snake_case` naming conventions:

```text
kod, uppgift, typ, intressent_id, hangar_id
```

The live API inspection showed that person details such as residence,
official email address, telephone number and titles are provided through
`personuppgift` rather than as direct top-level person fields.

> The member dataset contains person data with nested assignments and person
> details. Splitting it into `stg.person` (one row per person),
> `stg.person_uppdrag` (one row per assignment) and `stg.person_uppgift`
> (one row per person detail) keeps the staging structure aligned with the
> source while separating the three different row grains.

### 3.2 Silver — `dw` (all owned by **P3**)

| Table | Type | Grain |
|---|---|---|
| `dw.fakta_rost` | Fact | one row per member per vote |
| `dw.dim_ledamot` | Dimension, **SCD-2** | one row per member per validity period |
| `dw.dim_parti` | Dimension | one row per party |
| `dw.dim_votering` | Dimension | one row per vote event (`votering_id`) |
| `dw.dim_utskott` | Dimension | one row per committee |
| `dw.dim_datum` | Dimension | one row per calendar day |
| `dw.dim_rost` | Dimension | one row per vote value (Ja / Nej / Avstår / Frånvarande) |

`dw.fakta_rost` carries foreign keys to every dimension plus a degenerate
`votering_id`. Party membership is a slowly changing attribute — see open
decision D1.

### 3.3 `ops`

| Table | Owner | Purpose |
|---|---|---|
| `ops.load_log` | **P6** | one row per load step per run |

Created by `sql/00_init.sql`. Proposal from P6, not yet ratified by the team.

---

## 4. DDL ownership

One person owns each file. This is what makes parallel work possible without
merge conflicts.

| File | Owner |
|---|---|
| `sql/00_init.sql` | P6 |
| `sql/10_stg_person.sql` | P1 |
| `sql/11_stg_person_uppdrag.sql` | P1 |
| `sql/12_stg_person_uppgift.sql` | P1 |
| `sql/20_stg_votering.sql` | P2 |
| `sql/30_dw_dimensions.sql` | P3 |
| `sql/31_dw_fakta_rost.sql` | P3 |

Numeric prefixes give a deterministic execution order. Scripts must be
idempotent (`CREATE TABLE IF NOT EXISTS`) so a teammate can re-run the whole
`sql/` folder without dropping their database.

**Unassigned:** the reference tables `stg.organ`, `stg.roll`, `stg.riksmote`.
They are small and shared. Suggest P1 takes them since they sit closest to the
member data, but the team should confirm.

---

## 5. Open decisions

These change report numbers, so they need answers before P4 and P5 finalise
anything. None of them block starting.

| # | Decision | Why it matters |
|---|---|---|
| **D1** | Party at time of vote, or current party? | `parti` in the vote row is the party *at voting time*; `parti` in the member list is *current*. They differ for anyone who switched. |
| **D2** | Age reference date — vote date, or a fixed cut-off? | Affects every age distribution in the composition report. |
| **D3** | Filter `avser` to *sakfrågan*, or count both? | The same point can have both a sakfråga and a motivfråga vote. Double counting is easy here. |
| **D4** | Which member `status` values count as sitting members? | Changes headcounts and attendance denominators. |

---

## 6. Known source quirks

Worth writing down now so nobody debugs them twice.

- **Single-child nodes** come back as an object, not a list. Extractors must
  normalise this or they crash on exactly the records with one child.
- **Acclamation decisions** produce no vote rows at all. Absence is not an error.
- **Documented gaps** exist in some riksmöten (notably ~80 missing votes in
  2002/03). Reconciliation tests must tolerate these rather than fail on them.
- **FP → L**: Folkpartiet became Liberalerna on 2015-11-22. Outside the current
  scope, but relevant if history is extended.
- **Multiple votes per point**: `punkt` must be part of the key, or aggregates
  are wrong.
- **Missing assignment container:** `personuppdrag` can be returned as an empty
  string rather than an object. The extractor handles this as no assignments.
- **Nested `uppgift` values:** values inside assignment and person-detail records
  may be wrapped in a list even when only one value is present. The extractor
  normalises these before loading them into the text-based staging columns.
---

## 7. Local setup

```bash
createdb riksdag
psql -d riksdag -f sql/00_init.sql
# then, once table DDL exists:
for f in sql/[1-3]*.sql; do psql -d riksdag -f "$f"; done
```

Connection settings come from `.env` (copy `.env.example`). Never commit `.env`.
