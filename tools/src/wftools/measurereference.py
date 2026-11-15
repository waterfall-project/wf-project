# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Assemble the reference of the measures of the grids, before any correction (US-2210/L4).

``make measure-core`` and ``make measure`` each write a JSON report. The reference keeps both as
they were written, and adds the target of the API for opening a grid: the second of the table 15
(§4.6.2) less the parts of Next and of the browser, medians of a user alone. It is not the report
of a version, which ``docs/measures/<version>.json`` is.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, NoReturn

OBJECTIVE_MS = 1000.0
# The step of the journey that opens each grid by itself: the planning by its address, the quote by
# the navigation from the planning.
OPENINGS = {"planning": "planning.by-address", "estimate": "estimate.from-planning"}


def _refuse(message: str) -> NoReturn:
    """Stop with a message, not a trace."""
    raise SystemExit(message)


def api_target(step: dict[str, Any]) -> float:
    """Return what the API may take of the objective once Next and the browser have taken theirs."""
    return round(OBJECTIVE_MS - step["next_ms"]["median"] - step["browser_ms"]["median"], 1)


def _opening_steps(journey: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return the steps that open each grid, at one user, or stop saying what the report lacks."""
    alone = next((level for level in journey.get("levels", []) if level.get("users") == 1), None)
    if alone is None:
        _refuse("the report of make measure has no level at one user: the target needs it")
    steps: dict[str, dict[str, Any]] = {}
    for grid, name in OPENINGS.items():
        step = alone.get("steps", {}).get(name)
        if step is None:
            _refuse(f"the report of make measure has no step {name} at one user")
        steps[grid] = step
    return steps


def assemble(core: dict[str, Any], journey: dict[str, Any], commit: str) -> dict[str, Any]:
    """Return the reference of the two reports, the commit measured and the target of the API."""
    steps = _opening_steps(journey)
    try:
        targets = {grid: api_target(step) for grid, step in steps.items()}
    except (KeyError, TypeError) as error:
        _refuse(f"a step of the report of make measure lacks its medians: {error}")
    return {
        "reference": "before the corrections of EP-26 (US-2210)",
        "commit": commit,
        "taken_at": journey.get("taken_at"),
        "targets": {
            "objective_ms": OBJECTIVE_MS,
            "api_target_ms": targets,
            "from": {grid: f"journey, one user, step {name}" for grid, name in OPENINGS.items()},
        },
        "core": core,
        "journey": journey,
    }


def main(arguments: list[str]) -> int:
    """Write the reference from the two reports."""
    parser = argparse.ArgumentParser(prog="wftools.measurereference", description=__doc__)
    parser.add_argument("core", type=Path, help="the JSON of make measure-core")
    parser.add_argument("journey", type=Path, help="the JSON of make measure")
    parser.add_argument("output", type=Path, help="the reference to write")
    parser.add_argument("--commit", required=True, help="the commit of epic/EP-26 measured")
    options = parser.parse_args(arguments)
    reference = assemble(
        json.loads(options.core.read_text(encoding="utf-8")),
        json.loads(options.journey.read_text(encoding="utf-8")),
        options.commit,
    )
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(reference, indent=2) + "\n", encoding="utf-8")
    print(f"  -> {options.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
