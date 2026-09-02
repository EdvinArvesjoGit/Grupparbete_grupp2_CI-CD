"""Tests for the pipeline orchestrator.

These run without a database — they exercise step selection, entry-point
resolution and CLI wiring, not actual loading.
"""

import pytest

from src.run_pipeline import STEPS, Step, select_steps


def test_steps_are_in_dependency_order() -> None:
    """A step must never appear before something it depends on."""
    seen: set[str] = set()
    for step in STEPS:
        for dep in step.depends_on:
            assert dep in seen, f"{step.name} runs before its dependency {dep}"
        seen.add(step.name)


def test_step_names_are_unique() -> None:
    names = [s.name for s in STEPS]
    assert len(names) == len(set(names))


def test_every_step_targets_a_known_layer() -> None:
    for step in STEPS:
        assert step.layer in {"stg", "dw"}


def test_select_steps_defaults_to_everything() -> None:
    assert select_steps(None, None) == list(STEPS)


def test_select_steps_only() -> None:
    chosen = select_steps(["dim_ledamot"], None)
    assert [s.name for s in chosen] == ["dim_ledamot"]


def test_select_steps_skip() -> None:
    chosen = select_steps(None, ["voteringar"])
    assert "voteringar" not in [s.name for s in chosen]


def test_select_steps_preserves_order() -> None:
    """Filtering must not reorder — order is the dependency contract."""
    chosen = select_steps(["dim_ledamot", "ledamoter"], None)
    assert [s.name for s in chosen] == ["ledamoter", "dim_ledamot"]


def test_unknown_step_is_rejected() -> None:
    with pytest.raises(SystemExit):
        select_steps(["does_not_exist"], None)


def test_declared_dependencies_exist() -> None:
    names = {s.name for s in STEPS}
    for step in STEPS:
        for dep in step.depends_on:
            assert dep in names, f"{step.name} depends on unknown step {dep}"


def test_step_is_immutable() -> None:
    """Steps are frozen so a step cannot be mutated mid-run."""
    with pytest.raises(Exception):
        STEPS[0].name = "changed"


def test_step_construction_defaults() -> None:
    s = Step(name="x", module="m", layer="stg", description="d")
    assert s.depends_on == ()
