# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the confrontation of the measure reports (WF-QUA-0060-A)."""

import json
from typing import TYPE_CHECKING, cast

import pytest

from wftools import measures

if TYPE_CHECKING:
    from pathlib import Path

    from wftools.measures import Report

UNSERVED = {"portfolio-view": "EP-11", "open-compared-grid": "EP-27"}


def report(
    version: str,
    medians: dict[str, float] | None = None,
    notes: dict[str, str] | None = None,
) -> dict[str, object]:
    """Return a report of ``version``: every operation at half its objective, but ``medians``."""
    operations: list[dict[str, object]] = []
    for line in measures.TABLE:
        entry: dict[str, object] = {"id": line.id, "objective_s": line.objective_s}
        if line.id in UNSERVED:
            entry["unserved"] = UNSERVED[line.id]
        else:
            median = (medians or {}).get(line.id, line.objective_s / 2)
            entry |= {"median_s": median, "worst_s": median * 2, "dispersion_s": median / 10}
        if notes and line.id in notes:
            entry["note"] = notes[line.id]
        operations.append(entry)
    return {"version": version, "operations": operations}


def write(directory: Path, body: dict[str, object]) -> None:
    (directory / f"{body['version']}.json").write_text(json.dumps(body), "utf-8")


def parsed(body: dict[str, object]) -> Report:
    return measures.parse(json.dumps(body), str(body["version"]))


def run(directory: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = measures.main([str(directory)])
    return code, capsys.readouterr().out


@pytest.mark.requirement("WF-QUA-0060-A")
def test_a_slowdown_of_thirty_percent_is_signalled_and_fails_unless_documented(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, report("0.4.0", {"open-grid": 0.5}))
    write(tmp_path, report("0.5.0", {"open-grid": 0.5 * 1.3}))
    code, out = run(tmp_path, capsys)
    assert code == 1
    assert "::warning::Open a grid of a thousand tasks: 0.65 s, 30% above the 0.5 s of 0.4.0" in out
    assert "::error::open-grid: not documented in the report 0.5.0" in out


@pytest.mark.requirement("WF-QUA-0060-A")
def test_a_documented_slowdown_is_signalled_and_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, report("0.4.0", {"open-grid": 0.5}))
    write(tmp_path, report("0.5.0", {"open-grid": 0.65}, {"open-grid": "the new column"}))
    code, out = run(tmp_path, capsys)
    assert code == 0
    assert "::warning::" in out
    assert "::error::" not in out


@pytest.mark.requirement("WF-QUA-0060-A")
def test_a_slowdown_of_a_quarter_is_not_a_degradation() -> None:
    before = parsed(report("0.4.0", {"open-grid": 0.4}))
    assert measures.confront(parsed(report("0.5.0", {"open-grid": 0.5})), before) == []
    findings = measures.confront(parsed(report("0.5.0", {"open-grid": 0.51})), before)
    assert [finding.operation for finding in findings] == ["open-grid"]


@pytest.mark.requirement("WF-QUA-0060-A")
def test_an_objective_exceeded_is_held_without_a_previous_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, report("0.4.0", {"filter-sort-search": 2.4}))
    code, out = run(tmp_path, capsys)
    assert code == 1
    assert "2.4 s, above its objective of 2 s" in out
    write(tmp_path, report("0.4.0", {"filter-sort-search": 2.4}, {"filter-sort-search": "#3171"}))
    assert run(tmp_path, capsys)[0] == 0


@pytest.mark.requirement("WF-QUA-0060-A")
def test_only_the_two_last_versions_are_confronted_and_ten_follows_nine(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, report("0.1.0", {"open-grid": 0.1}))
    write(tmp_path, report("0.9.0", {"open-grid": 0.5}))
    write(tmp_path, report("0.10.0", {"open-grid": 0.6}))
    code, out = run(tmp_path, capsys)
    assert code == 0
    assert out.startswith("report 0.10.0, against 0.9.0")
    assert "::warning::" not in out


@pytest.mark.requirement("WF-QUA-0060-A")
def test_an_improvement_and_an_unserved_operation_signal_nothing() -> None:
    before = parsed(report("0.4.0", {"mark-revision": 50}))
    assert measures.confront(parsed(report("0.5.0", {"mark-revision": 20})), before) == []


@pytest.mark.requirement("WF-QUA-0060-A")
def test_without_a_report_of_a_version_the_check_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(tmp_path / "absent", capsys)[0] == 0
    (tmp_path / "reference.json").write_text("not even read", "utf-8")
    assert run(tmp_path, capsys)[0] == 0


@pytest.mark.requirement("WF-QUA-0060-A")
def test_the_repository_reports_hold(capsys: pytest.CaptureFixture[str]) -> None:
    assert measures.main([]) == 0
    assert "::error::" not in capsys.readouterr().out


@pytest.mark.requirement("WF-QUA-0060-A")
def test_an_unserved_operation_is_named_with_its_epic_and_no_duration() -> None:
    result = parsed(report("0.4.0"))
    unserved = result.operations["portfolio-view"]
    assert (unserved.unserved, unserved.median_s) == ("EP-11", None)
    assert result.operations["open-grid"].worst_s == 1.0


def mutated(change: str) -> dict[str, object]:
    body = report("0.4.0")
    operations = cast("list[dict[str, object]]", body["operations"])
    first, unserved = operations[0], operations[3]
    match change:
        case "missing":
            operations.pop()
        case "twice":
            operations.append(first)
        case "unknown":
            first["id"] = "open-the-moon"
        case "objective":
            first["objective_s"] = 5
        case "worst":
            first["worst_s"] = 0.1
        case "negative":
            first["median_s"] = -1
        case "text":
            first["median_s"] = "fast"
        case "epic":
            unserved["unserved"] = "later"
        case "duration":
            unserved["median_s"] = 1
        case "note":
            first["note"] = 3
        case "version":
            body["version"] = "0.5.0"
        case "operations":
            body["operations"] = {}
        case _:
            raise AssertionError(change)
    return body


@pytest.mark.requirement("WF-QUA-0060-A")
@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "twice",
        "unknown",
        "objective",
        "worst",
        "negative",
        "text",
        "epic",
        "duration",
        "note",
        "version",
        "operations",
    ],
)
def test_a_report_that_does_not_hold_to_the_table_is_refused(change: str) -> None:
    with pytest.raises((ValueError, TypeError)):
        measures.parse(json.dumps(mutated(change)), "0.4.0")


@pytest.mark.requirement("WF-QUA-0060-A")
def test_a_report_that_is_not_an_object_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "0.4.0.json").write_text("[]", "utf-8")
    code, out = run(tmp_path, capsys)
    assert (code, "::error::0.4.0: a report is an object" in out) == (1, True)


@pytest.mark.requirement("WF-QUA-0060-A")
def test_a_report_not_named_for_a_version_fails_the_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "latest.json").write_text("{}", "utf-8")
    code, out = run(tmp_path, capsys)
    assert code == 1
    assert "named for its version" in out
