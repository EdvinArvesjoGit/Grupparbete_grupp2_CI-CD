"""Export the warehouse to Parquet for downstream consumers.

Produces one Parquet file per table in dw/, plus stg.votering, so reports can
read the data without a database:

    import pandas as pd
    df = pd.read_parquet("https://github.com/<org>/<repo>/releases/latest/download/dw_dim_ledamot.parquet")

Some Postgres types (uuid, inet, json, arrays) come back as Python objects that
Arrow cannot infer a type for. Rather than failing the whole export, those
columns are converted to text and the conversion is reported.

    python scripts/export_artifacts.py --out artifacts/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import inspect, text

from src.common.db import get_engine

EXTRA_TABLES = [("stg", "votering")]

# Types Arrow handles natively; anything else in an object column is stringified.
_SAFE = (str, bytes, bool, int, float, type(None))


def _coerce_objects(df: pd.DataFrame, label: str) -> list[str]:
    """Stringify object columns Arrow cannot infer. Returns names coerced."""
    coerced: list[str] = []
    for col in df.columns:
        if df[col].dtype != "object":
            continue
        sample = df[col].dropna()
        if sample.empty:
            continue
        if not isinstance(sample.iloc[0], _SAFE):
            df[col] = df[col].map(lambda v: None if v is None else str(v))
            coerced.append(col)
    if coerced:
        print(f"    {label}: konverterade till text -> {', '.join(coerced)}")
    return coerced


def export(out_dir: Path) -> int:
    engine = get_engine()
    insp = inspect(engine)
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = [("dw", t) for t in sorted(insp.get_table_names(schema="dw"))]
    for schema, table in EXTRA_TABLES:
        if table in insp.get_table_names(schema=schema):
            targets.append((schema, table))

    if not targets:
        print("Inga tabeller att exportera.", file=sys.stderr)
        return 0

    failures: list[str] = []
    total_rows = 0

    for schema, table in targets:
        label = f"{schema}.{table}"
        try:
            df = pd.read_sql(text(f'SELECT * FROM {schema}."{table}"'), engine)
        except Exception as exc:
            print(f"    {label}: KUNDE INTE LÄSAS - {type(exc).__name__}: {exc}", file=sys.stderr)
            failures.append(label)
            continue

        _coerce_objects(df, label)
        path = out_dir / f"{schema}_{table}.parquet"
        try:
            df.to_parquet(path, compression="zstd", index=False)
        except Exception as exc:
            # Retry once with everything as text - better a usable file than none.
            print(f"    {label}: to_parquet misslyckades ({type(exc).__name__}), "
                  f"försöker igen med allt som text", file=sys.stderr)
            try:
                df.astype(str).to_parquet(path, compression="zstd", index=False)
            except Exception as exc2:
                print(f"    {label}: MISSLYCKADES - {type(exc2).__name__}: {exc2}", file=sys.stderr)
                failures.append(label)
                continue

        total_rows += len(df)
        print(f"{label:<28} {len(df):>9,} rader  ->  {path.name} "
              f"({path.stat().st_size / 1e6:.1f} MB)")

    print(f"\n{len(targets) - len(failures)} av {len(targets)} tabeller, "
          f"{total_rows:,} rader totalt")
    if failures:
        print(f"Misslyckades: {', '.join(failures)}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Export warehouse tables to Parquet.")
    ap.add_argument("--out", default="artifacts", help="output directory")
    args = ap.parse_args()
    return export(Path(args.out))


if __name__ == "__main__":
    sys.exit(main())