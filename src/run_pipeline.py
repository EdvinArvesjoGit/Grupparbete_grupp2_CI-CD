"""Pipeline orchestrator.

Runs the full chain in dependency order:

    stg.person / stg.person_uppdrag   (P1)
    stg.votering                      (P2)
        -> dw.dim_ledamot             (P3)

One run id (korning_id) ties every step together in ops.load_log, so a failed
nightly run can be traced back to the exact step that broke.

    python -m src.run_pipeline                    # everything
    python -m src.run_pipeline --list             # show steps, run nothing
    python -m src.run_pipeline --only dim_ledamot # one step
    python -m src.run_pipeline --skip voteringar  # everything except one
    python -m src.run_pipeline --continue-on-error

Exit code is 0 only if every executed step succeeded.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import sys
import time
from dataclasses import dataclass, field

from src.common.db import get_engine
from src.common.pipeline import new_korning_id, setup_logging


@dataclass(frozen=True)
class Step:
    """One runnable unit of the pipeline."""

    name: str
    module: str
    layer: str
    description: str
    depends_on: tuple[str, ...] = field(default_factory=tuple)


# Order matters: this list IS the dependency order.
STEPS: tuple[Step, ...] = (
    Step(
        name="ledamoter",
        module="src.ingest.ledamoter",
        layer="stg",
        description="Members -> stg.person, stg.person_uppdrag, stg.person_uppgift",
    ),
    Step(
        name="voteringar",
        module="src.ingest.voteringar",
        layer="stg",
        description="Votes -> stg.votering",
    ),
    Step(
        name="dim_ledamot",
        module="src.transform.dim_ledamot",
        layer="dw",
        description="stg.person -> dw.dim_ledamot (SCD-2)",
        depends_on=("ledamoter",),
    ),
)


class StepFailed(Exception):
    """Raised when a pipeline step does not complete."""


def _resolve_callable(module_name: str):
    """Find a module's entry point and describe how it should be called.

    Preferred contract:  run(engine, korning_id=...) -> int
    Legacy fallbacks:    load_<something>()  or  main()

    The fallback exists so the pipeline runs before every module has been
    migrated. Delete it once all three expose run().
    """
    module = importlib.import_module(module_name)

    for attr in ("run", "main"):
        fn = getattr(module, attr, None)
        if callable(fn):
            return fn, attr, _accepted_kwargs(fn)

    # Transform modules currently use load_<name> instead of run/main.
    for attr in dir(module):
        if attr.startswith("load_") and callable(getattr(module, attr)):
            fn = getattr(module, attr)
            return fn, attr, _accepted_kwargs(fn)

    raise StepFailed(f"{module_name} exposes no run(), main() or load_*() callable")


def _accepted_kwargs(fn) -> dict[str, bool]:
    """Which of our standard arguments does this callable accept?"""
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return {"engine": False, "korning_id": False}
    return {
        "engine": "engine" in params,
        "korning_id": "korning_id" in params,
    }


@dataclass
class StepResult:
    name: str
    status: str
    seconds: float
    rows: int | None = None
    error: str | None = None


def run_step(step: Step, engine, korning_id: str) -> StepResult:
    """Execute one step, returning its outcome rather than raising."""
    logger = setup_logging()
    fn, attr, accepts = _resolve_callable(step.module)

    if attr != "run":
        logger.warning(
            "%s uses legacy entry point %s() — should expose run(engine, korning_id)",
            step.module,
            attr,
        )

    kwargs = {}
    if accepts["engine"]:
        kwargs["engine"] = engine
    if accepts["korning_id"]:
        kwargs["korning_id"] = korning_id

    started = time.perf_counter()
    try:
        result = fn(**kwargs)
    except Exception as exc:
        elapsed = time.perf_counter() - started
        logger.error("step %-14s FAILED after %5.1fs", step.name, elapsed)
        return StepResult(step.name, "FAILED", elapsed, None, f"{type(exc).__name__}: {exc}")

    elapsed = time.perf_counter() - started
    rows = result if isinstance(result, int) else None
    if rows is None:
        logger.warning("%s returned no row count — run() should return int", step.module)
    logger.info("step %-14s OK     in %5.1fs  rader=%s", step.name, elapsed, rows)
    return StepResult(step.name, "OK", elapsed, rows)


def select_steps(only: list[str] | None, skip: list[str] | None) -> list[Step]:
    """Filter STEPS by --only / --skip, preserving dependency order."""
    names = {s.name for s in STEPS}
    for given in (only or []) + (skip or []):
        if given not in names:
            raise SystemExit(f"Unknown step {given!r}. Known: {', '.join(sorted(names))}")

    chosen = [s for s in STEPS if (not only or s.name in only) and s.name not in (skip or [])]

    selected = {s.name for s in chosen}
    for step in chosen:
        missing = [d for d in step.depends_on if d not in selected]
        if missing:
            setup_logging().warning(
                "%s depends on %s, which is not in this run — results may be stale",
                step.name,
                ", ".join(missing),
            )
    return chosen


def print_summary(results: list[StepResult], korning_id: str) -> None:
    logger = setup_logging()
    total = sum(r.seconds for r in results)
    logger.info("-" * 62)
    logger.info("Run %s finished in %.1fs", korning_id, total)
    for r in results:
        rows = "-" if r.rows is None else str(r.rows)
        logger.info("  %-14s %-7s %6.1fs  rader=%s", r.name, r.status, r.seconds, rows)
        if r.error:
            logger.info("      %s", r.error)
    logger.info("-" * 62)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the riksdag ETL pipeline.")
    parser.add_argument("--only", action="append", help="run only this step (repeatable)")
    parser.add_argument("--skip", action="append", help="skip this step (repeatable)")
    parser.add_argument("--list", action="store_true", help="list steps and exit")
    parser.add_argument("--dry-run", action="store_true", help="resolve steps but run nothing")
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="keep going after a failed step instead of stopping",
    )
    args = parser.parse_args(argv)

    logger = setup_logging()

    if args.list:
        for s in STEPS:
            print(f"{s.name:<14} [{s.layer}]  {s.description}")
        return 0

    steps = select_steps(args.only, args.skip)
    korning_id = new_korning_id()
    logger.info("Pipeline run %s — %d step(s)", korning_id, len(steps))

    if args.dry_run:
        for s in steps:
            fn, attr, accepts = _resolve_callable(s.module)
            logger.info(
                "would call %s.%s(%s)",
                s.module,
                attr,
                ", ".join(k for k, v in accepts.items() if v),
            )
        return 0

    engine = get_engine()
    results: list[StepResult] = []

    for step in steps:
        result = run_step(step, engine, korning_id)
        results.append(result)
        if result.status == "FAILED" and not args.continue_on_error:
            logger.error("Stopping. Use --continue-on-error to run remaining steps.")
            break

    print_summary(results, korning_id)
    return 0 if all(r.status == "OK" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
