# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The report of a measure: what it measured, readable and as JSON."""

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from measure.figures import Summary

type Scalar = str | int | float

_MILLISECOND = 1000


@dataclass(frozen=True, slots=True)
class Measure:
    """One measured operation: its summary if it repeats, what it counted, and its table.

    The durations of a summary are in seconds; ``facts`` and ``rows`` carry their units in their
    names. ``notes`` say what a figure leaves out or what to doubt in it.
    """

    name: str
    summary: Summary | None = None
    facts: Mapping[str, Scalar] = field(default_factory=dict[str, Scalar])
    rows: tuple[Mapping[str, Scalar], ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Report:
    """The measures of one passage, and what they ran on."""

    subject: Mapping[str, Scalar]
    measures: tuple[Measure, ...]


def _milliseconds(seconds: float) -> float:
    return round(seconds * _MILLISECOND, 1)


def _figure(value: Scalar) -> str:
    return f"{value:g}" if isinstance(value, float) else str(value)


def _summary_of(summary: Summary) -> dict[str, Scalar]:
    return {
        "runs": summary.runs,
        "median_ms": _milliseconds(summary.median),
        "worst_ms": _milliseconds(summary.worst),
        "spread_ms": _milliseconds(summary.spread),
    }


def as_dict(report: Report) -> dict[str, object]:
    """Give a report as plain values: the durations of a summary in milliseconds."""
    return {
        "subject": dict(report.subject),
        "measures": [
            {
                "name": each.name,
                **({} if each.summary is None else {"summary": _summary_of(each.summary)}),
                "facts": dict(each.facts),
                "rows": [dict(row) for row in each.rows],
                "notes": list(each.notes),
            }
            for each in report.measures
        ],
    }


def render_json(report: Report) -> str:
    """Write a report as JSON, readable by a person and by a tool."""
    return json.dumps(as_dict(report), ensure_ascii=False, indent=2) + "\n"


def _row(row: Mapping[str, Scalar]) -> str:
    return "    " + "  ".join(f"{key}={_figure(value)}" for key, value in row.items())


def render_text(report: Report) -> str:
    """Write a report for a terminal: one block per measure, its facts and its table beneath."""
    lines = ["  ".join(f"{key}={_figure(value)}" for key, value in report.subject.items()), ""]
    for each in report.measures:
        head = each.name
        if each.summary is not None:
            summary = each.summary
            head += (
                f"  median {summary.median * _MILLISECOND:.0f} ms"
                f"  worst {summary.worst * _MILLISECOND:.0f} ms"
                f"  spread {summary.spread * _MILLISECOND:.0f} ms  ({summary.runs} runs)"
            )
        lines.append(head)
        lines.extend(f"    {key}: {_figure(value)}" for key, value in each.facts.items())
        lines.extend(_row(row) for row in each.rows)
        lines.extend(f"    note: {note}" for note in each.notes)
        lines.append("")
    return "\n".join(lines)
