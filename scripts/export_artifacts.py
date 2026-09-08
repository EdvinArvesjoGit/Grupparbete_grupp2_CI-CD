"""Export the warehouse to Parquet for downstream consumers.

Produces one Parquet file per table under dw/, plus stg.votering, so that
reports can read the data without a database at all:

    import pandas as pd
    df = pd.read_parquet("https://github.com/<org>/<repo>/releases/latest/download/dw_fakta_rost.parquet")

Run:
    python scripts/export_artifacts.py --out artifacts/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import inspect, text

from src.common.db import get_engine

# stg.votering is exported too: it is large but it is what the reports
# aggregate from if a dw fact table is not yet available.
EXTRA_TABLES = [("stg", "votering")]


def export(out_dir: Path) -> int:
    engine = get_engine()
    insp = inspect(engine)
    out_dir.mkdir(parents=True, exist_ok=True)

    targets: list[tuple[str, str]] = [("dw", t) for t in sorted(insp.get_table_names(schema="dw"))]
    for schema, table in EXTRA_TABLES:
        if table in insp.get_table_names(schema=schema):
            targets.append((schema, table))

    if not targets:
        print("No tables found to export.", file=sys.stderr)
        return 0

    total_rows = 0
    for schema, table in targets:
        df = pd.read_sql(text(f'SELECT * FROM {schema}."{table}"'), engine)
        path = out_dir / f"{schema}_{table}.parquet"
        df.to_parquet(path, compression="zstd", index=False)
        size_mb = path.stat().st_size / 1e6
        total_rows += len(df)
        print(f"{schema}.{table:<24} {len(df):>9,} rader  ->  {path.name} ({size_mb:.1f} MB)")

    print(f"\n{len(targets)} tabeller, {total_rows:,} rader totalt")
    return total_rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Export warehouse tables to Parquet.")
    ap.add_argument("--out", default="artifacts", help="output directory")
    args = ap.parse_args()
    export(Path(args.out))
    return 0

# end

if __name__ == "__main__":
    sys.exit(main())

# tempo

# niehfienfkoenlkfnek
