# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the reference of the measures of the grids (US-2210)."""

import json
from typing import TYPE_CHECKING, Any

import pytest

from wftools import measurereference

if TYPE_CHECKING:
    from pathlib import Path


def _step(next_ms: float, browser_ms: float) -> dict[str, Any]:
    return {"next_ms": {"median": next_ms}, "browser_ms": {"median": browser_ms}}


JOURNEY = {
    "taken_at": "2026-11-15T00:32:28.415Z",
    "levels": [
        {
            "users": 4,
            "steps": {
                "planning.by-address": _step(1, 1),
                "estimate.from-planning": _step(1, 1),
            },
        },
        {
            "users": 1,
            "steps": {
                "planning.by-address": _step(83.7, 75.5),
                "estimate.from-planning": _step(92.9, 57.5),
            },
        },
    ],
}
COMMIT = "47295ed4"
CORE: dict[str, Any] = {"subject": {"project": "PRJ-001"}, "measures": []}


def test_target_is_the_second_less_next_and_the_browser_of_a_user_alone() -> None:
    reference = measurereference.assemble(CORE, JOURNEY, COMMIT)
    assert reference["targets"]["objective_ms"] == 1000.0
    assert reference["targets"]["api_target_ms"] == {"planning": 840.8, "estimate": 849.6}


def test_the_reports_are_kept_as_written(tmp_path: Path) -> None:
    core = tmp_path / "core.json"
    journey = tmp_path / "journey.json"
    output = tmp_path / "measures" / "reference.json"
    core.write_text(json.dumps(CORE), encoding="utf-8")
    journey.write_text(json.dumps(JOURNEY), encoding="utf-8")
    assert measurereference.main([str(core), str(journey), str(output), "--commit", COMMIT]) == 0
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["core"] == CORE
    assert written["journey"] == JOURNEY
    assert written["commit"] == COMMIT
    assert written["taken_at"] == "2026-11-15T00:32:28.415Z"


def test_a_report_without_a_level_at_one_user_is_refused_readably() -> None:
    journey = {"levels": [JOURNEY["levels"][0]]}
    with pytest.raises(SystemExit, match="no level at one user"):
        measurereference.assemble(CORE, journey, COMMIT)


def test_a_report_without_the_expected_step_is_refused_readably() -> None:
    journey = {"levels": [{"users": 1, "steps": {"planning.by-address": _step(1, 1)}}]}
    with pytest.raises(SystemExit, match=r"no step estimate\.from-planning"):
        measurereference.assemble(CORE, journey, COMMIT)


def test_a_step_without_its_medians_is_refused_readably() -> None:
    steps = {"planning.by-address": {}, "estimate.from-planning": _step(1, 1)}
    with pytest.raises(SystemExit, match="lacks its medians"):
        measurereference.assemble(CORE, {"levels": [{"users": 1, "steps": steps}]}, COMMIT)
