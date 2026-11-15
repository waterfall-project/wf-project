# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the reference of the measures of the grids (US-2210)."""

import json
from typing import TYPE_CHECKING, Any

from wftools import measurereference

if TYPE_CHECKING:
    from pathlib import Path


def _step(next_ms: float, browser_ms: float) -> dict[str, Any]:
    return {"next_ms": {"median": next_ms}, "browser_ms": {"median": browser_ms}}


JOURNEY = {
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
    ]
}
CORE: dict[str, Any] = {"subject": {"project": "PRJ-001"}, "measures": []}


def test_target_is_the_second_less_next_and_the_browser_of_a_user_alone() -> None:
    reference = measurereference.assemble(CORE, JOURNEY)
    assert reference["targets"]["objective_ms"] == 1000.0
    assert reference["targets"]["api_target_ms"] == {"planning": 840.8, "estimate": 849.6}


def test_the_reports_are_kept_as_written(tmp_path: Path) -> None:
    core = tmp_path / "core.json"
    journey = tmp_path / "journey.json"
    output = tmp_path / "measures" / "reference.json"
    core.write_text(json.dumps(CORE), encoding="utf-8")
    journey.write_text(json.dumps(JOURNEY), encoding="utf-8")
    assert measurereference.main([str(core), str(journey), str(output)]) == 0
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["core"] == CORE
    assert written["journey"] == JOURNEY
