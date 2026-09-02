# Entry point contract

**Status:** proposed by P6, needs team agreement.
**Affects:** P1, P2, P3. Roughly 20 minutes of work each.

## Why

`src/run_pipeline.py` runs the whole chain in order, logs each step to
`ops.load_log` under one shared run id, and reports row counts. To do that it
has to call your module. Right now the three modules have three different
shapes, none of which accept an engine or return a count:

| Module | Entry point | Takes engine? | Returns count? |
|---|---|---|---|
| `src/ingest/ledamoter.py` | `main()` | no | no |
| `src/ingest/voteringar.py` | `main()` | no — builds its own psycopg connection | no |
| `src/transform/dim_ledamot.py` | `load_dim_ledamot()` | no — calls `get_engine()` itself | no |

The orchestrator currently works around this and logs a warning per module.
The workaround is temporary and should be deleted once everyone has migrated.

## The contract

Every runnable module exposes exactly this:

```python
def run(engine, korning_id: str | None = None) -> int:
    """Do the work. Return the number of rows affected."""
```

Three rules:

1. **Accept the engine, do not create one.** The orchestrator passes a shared
   engine from `src.common.db.get_engine()`. This is what makes all six of us
   use one connection configuration instead of three.
2. **Accept `korning_id` and pass it through** to whatever you write into
   `ops.load_log` and into your `_korning_id` audit columns. One run id across
   all steps is what lets us trace a failed nightly run.
3. **Return an int.** Rows inserted, updated or affected. The orchestrator
   prints it and CI asserts on it.

Keep your `__main__` block so you can still run standalone:

```python
if __name__ == "__main__":
    from src.common.db import get_engine

    print(run(get_engine()))
```

## Per-module notes

### P1 — `ledamoter.py`
Cleanest migration. Rename `main` to `run`, take `engine` and `korning_id` as
parameters instead of generating the uuid inside, and return the summed row
count. Keep the prints or switch them to `logging` — your call.

**Separate issue:** you load `stg.person_uppgift`, which is not in
`DATABASE.md`. Please add it to the table inventory or drop it, so the doc
stays the source of truth.

### P2 — `voteringar.py`
Two changes beyond the rename:

- **Use the shared engine.** Replace `get_connection()` / raw `psycopg` with
  the `engine` parameter. If you need a raw DBAPI connection,
  `engine.raw_connection()` gives you one.
- **`KORNING_ID` and `INGEST_MODE` are module-level globals**, so they are
  bound at import time. The orchestrator cannot pass a run id or select a mode
  without mutating `os.environ` first. Move both into the signature:

```python
def run(engine, korning_id=None, mode="incremental") -> int:
    if mode not in {"init", "incremental"}:
        raise ValueError(f"Invalid mode={mode!r}")
```

Keep reading the env var as the default in `__main__` so your standalone
workflow does not change.

### P3 — `dim_ledamot.py`
Rename `load_dim_ledamot` to `run`, take `engine` as a parameter instead of
calling `get_engine()` inside, and count the inserts/closes you perform so you
can return a total.

## Not urgent, but worth knowing

`load_dim_ledamot` runs one `SELECT` per person inside a Python loop. At ~350
members that is fine and not worth changing now. It would become the first
bottleneck if we ever extend the scope to earlier mandate periods.
