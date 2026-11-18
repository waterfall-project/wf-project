# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the confrontation of the measure reports (WF-QUA-0060-A)."""

import json
import math
from typing import TYPE_CHECKING, Any, cast

import pytest

from wftools import measures

if TYPE_CHECKING:
    from pathlib import Path

    from wftools.measures import Report

UNSERVED = {"portfolio-view": "EP-11"}


def cache(cold_cell_s: float = 0.3) -> dict[str, object]:
    """Return the cost of the entries of the cache of the indicators, as the core measure says."""
    return {
        "subprojects": 3,
        "scopes": 5,
        "cell_bytes": 11000,
        "all_bytes": 52000,
        "cold_cell_s": cold_cell_s,
        "hot_cell_s": 0.002,
        "cold_all_s": 0.5,
        "hot_all_s": 0.004,
        "extrapolation": [
            {
                "subprojects": 100,
                "cell_bytes": 11000,
                "cold_cell_s": cold_cell_s,
                "hot_cell_s": 0.002,
                "all_bytes": 1_100_000,
                "cold_all_s": 9.0,
                "hot_all_s": 0.05,
            }
        ],
    }


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
            if line.id == measures.CACHED:
                entry["cache"] = cache()
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
def test_an_improvement_and_an_operation_unserved_twice_signal_nothing() -> None:
    before = parsed(report("0.4.0", {"mark-revision": 50}))
    latest = parsed(report("0.5.0", {"mark-revision": 20}))
    assert latest.operations["portfolio-view"].unserved == "EP-11"
    assert measures.confront(latest, before) == []


@pytest.mark.requirement("WF-QUA-0060-A")
def test_an_operation_unserved_then_served_is_held_to_its_objective_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The grids compared, unserved by a report taken before EP-27 and served by the next (US-2390).
    earlier = report("0.4.0")
    for entry in cast("list[dict[str, object]]", earlier["operations"]):
        if entry["id"] in {"open-compared-grid", "recompute-compared"}:
            for key in measures.DURATIONS:
                del entry[key]
            entry["unserved"] = "EP-27"
    write(tmp_path, earlier)
    write(tmp_path, report("0.5.0", {"open-compared-grid": 1.5, "recompute-compared": 1.8}))
    code, out = run(tmp_path, capsys)
    assert (code, "::warning::" in out) == (0, False)
    assert "open-compared-grid: 1.5 s, no previous measure (objective 2 s)" in out
    write(tmp_path, report("0.5.0", {"recompute-compared": 2.4}))
    code, out = run(tmp_path, capsys)
    assert code == 1
    assert "2.4 s, above its objective of 2 s" in out


@pytest.mark.requirement("WF-QUA-0060-A")
def test_an_operation_served_then_unserved_is_signalled_and_fails_unless_documented(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, report("0.4.0"))
    later = report("0.5.0")
    entry = cast("list[dict[str, object]]", later["operations"])[0]
    for key in measures.DURATIONS:
        del entry[key]
    entry["unserved"] = "EP-30"
    write(tmp_path, later)
    code, out = run(tmp_path, capsys)
    assert code == 1
    assert "Open a grid of a thousand tasks: served by 0.4.0, no longer served" in out
    entry["note"] = "the grid is rebuilt"
    write(tmp_path, later)
    code, out = run(tmp_path, capsys)
    assert (code, "::warning::" in out, "::error::" in out) == (0, True, False)


@pytest.mark.requirement("WF-QUA-0060-A")
def test_every_served_operation_shows_its_median_and_the_previous_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, report("0.4.0", {"open-grid": 0.4}))
    write(tmp_path, report("0.5.0", {"open-grid": 0.5}))
    code, out = run(tmp_path, capsys)
    assert code == 0
    assert "open-grid: 0.5 s, 0.4 s before (objective 1 s)" in out
    assert "mark-revision: 30 s, 30 s before (objective 60 s)" in out
    assert "portfolio-view" not in out
    assert out.count(" s before (objective") == len(measures.TABLE) - len(UNSERVED)


@pytest.mark.requirement("WF-QUA-0060-A")
def test_a_median_above_a_previous_median_of_zero_is_a_degradation() -> None:
    before = parsed(report("0.4.0", {"open-grid": 0}))
    findings = measures.confront(parsed(report("0.5.0", {"open-grid": 0.1})), before)
    assert [finding.operation for finding in findings] == ["open-grid"]
    assert measures.confront(parsed(report("0.5.0", {"open-grid": 0})), before) == []


@pytest.mark.requirement("WF-QUA-0060-A")
def test_without_a_report_of_a_version_the_check_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(tmp_path / "absent", capsys)[0] == 0
    (tmp_path / "reference.json").write_text("not even read", "utf-8")
    (tmp_path / "processes.json").write_text("not even read", "utf-8")
    assert run(tmp_path, capsys)[0] == 0


@pytest.mark.requirement("WF-QUA-0060-A")
def test_the_repository_reports_hold(capsys: pytest.CaptureFixture[str]) -> None:
    # Reads the real docs/measures/: it checks nothing until US-2300/L3 pays in the first report.
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
@pytest.mark.parametrize(
    ("key", "value"), [("median_s", math.nan), ("worst_s", math.inf), ("dispersion_s", -math.inf)]
)
def test_a_duration_that_is_not_finite_is_refused(key: str, value: float) -> None:
    body = report("0.4.0")
    cast("list[dict[str, object]]", body["operations"])[0][key] = value
    with pytest.raises(ValueError, match="number of seconds"):
        measures.parse(json.dumps(body), "0.4.0")


@pytest.mark.requirement("WF-QUA-0060-A")
def test_an_operation_that_is_not_an_object_is_refused() -> None:
    body = report("0.4.0")
    cast("list[object]", body["operations"])[0] = "open-grid"
    with pytest.raises(TypeError, match="an operation is an object"):
        measures.parse(json.dumps(body), "0.4.0")


@pytest.mark.requirement("WF-QUA-0060-A")
def test_a_report_that_is_not_an_object_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "0.4.0.json").write_text("[]", "utf-8")
    code, out = run(tmp_path, capsys)
    assert (code, "::error::0.4.0: a report is an object" in out) == (1, True)
    for operations in ("{}", "[3]"):
        text = f'{{"version": "0.4.0", "operations": {operations}}}'
        (tmp_path / "0.4.0.json").write_text(text, "utf-8")
        code, out = run(tmp_path, capsys)
        assert (code, out.startswith("::error::0.4.0: ")) == (1, True)


@pytest.mark.requirement("WF-QUA-0060-A")
@pytest.mark.parametrize("name", ["0.4", "v0.4.0", "1.2.3.4", "latest"])
def test_a_version_is_numbered_as_x_y_z(name: str) -> None:
    with pytest.raises(ValueError, match=r"numbered as 0\.4\.0"):
        measures.version_key(name)
    assert measures.version_key("0.10.2") == (0, 10, 2)


@pytest.mark.requirement("WF-QUA-0060-A")
def test_a_report_not_named_for_a_version_fails_the_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "latest.json").write_text("{}", "utf-8")
    code, out = run(tmp_path, capsys)
    assert code == 1
    assert "named for its version" in out


@pytest.mark.requirement("WF-ARC-0080-A")
def test_the_processes_report_keeps_the_shape_the_defaults_are_read_from() -> None:
    # The report of the journey at one, two and four processes (US-2230/L2) is not a version's: it
    # is kept beside them, and the defaults of the deployment are checked against its choice.
    assert "processes" in measures.NOT_VERSIONS
    found = json.loads((measures.MEASURES / "processes.json").read_text(encoding="utf-8"))
    chosen = found["chosen"]
    assert {"processes", "service_platform", "production_example"} <= set(chosen)
    assert [run["processes"] for run in found["runs"]] == [1, 2, 4]
    for run in found["runs"]:
        assert [level["users"] for level in run["levels"]] == [1, 4, 8]
        assert run["max_connections"] == 15 * run["processes"] + 200
        for level in run["levels"]:
            assert level["steps"]
            for step in level["steps"].values():
                assert {"usable_ms", "api_ms", "worst_usable_ms", "spread_ms"} <= set(step)
    measured = {run["processes"] for run in found["runs"]}
    assert chosen["processes"] in measured
    assert chosen["service_platform"] in measured
    assert chosen["production_example"] in measured


@pytest.mark.requirement("WF-ARC-0080-A")
def test_the_figures_of_the_compose_readme_are_the_ones_of_the_processes_report() -> None:
    # The README of deploy/compose quotes the report of the processes (#3440): a drift of either
    # would otherwise pass unseen.
    found = json.loads((measures.MEASURES / "processes.json").read_text(encoding="utf-8"))
    runs = {run["processes"]: run for run in found["runs"]}
    readme = (measures.MEASURES.parents[1] / "deploy/compose/README.md").read_text("utf-8")
    text = " ".join(readme.split())

    def level(processes: int, users: int) -> dict[str, Any]:
        return next(x for x in runs[processes]["levels"] if x["users"] == users)

    def usable(processes: int, users: int, step: str) -> float:
        return float(level(processes, users)["steps"][step]["usable_ms"])

    def french(value: float, decimals: int, unit: str) -> str:  # 4222.6 ms -> "4,2 s"
        return f"{value:.{decimals}f}".replace(".", ",") + f" {unit}"

    def seconds(processes: int, users: int, step: str, decimals: int = 1) -> str:
        return french(usable(processes, users, step) / 1000, decimals, "s")

    def chain(step: str) -> str:
        return f"de {seconds(1, 8, step)} à {seconds(2, 8, step)} puis {seconds(4, 8, step)}"

    assert "l'ouverture du planning passe " + chain("planning.by-address") in text
    assert "le devis " + chain("estimate.from-planning") in text
    me = [round(level(n, 8)["get_me"]["api_ms"]) for n in (1, 2, 4)]
    assert f"`getMe` de {me[0]} ms à {me[1]} ms puis {me[2]} ms" in text
    assert f"de {seconds(2, 8, 'planning.label', 2)} (deux processus)" in text
    assert f"à {seconds(4, 8, 'planning.label', 2)} (quatre)" in text
    four = seconds(2, 4, "planning.duration", 2)
    slower = f"({four} contre {seconds(1, 4, 'planning.duration', 2)})"
    assert slower in text
    resident = [p["rss_mb"] / 1000 for p in runs[4]["memory"]["processes"]]
    assert round(min(resident), 1) >= 0.6
    assert round(max(resident), 1) <= 0.7
    assert f"quatre processus, {french(sum(resident), 1, 'Go')}" in text
    assert f"({french(runs[1]['memory']['processes'][0]['rss_mb'] / 1000, 1, 'Go')} quand" in text
    assert f"À un processus, le serveur accepte {runs[1]['max_connections']} connexions" in text
    assert f"à quatre, {runs[4]['max_connections']}" in text


def _indicators(body: dict[str, object]) -> dict[str, object]:
    return next(
        each
        for each in cast("list[dict[str, object]]", body["operations"])
        if each["id"] == "indicators"
    )


@pytest.mark.requirement("WF-QUA-0060-A")
def test_the_indicators_served_carry_the_cost_of_the_entry_of_the_cache() -> None:
    result = parsed(report("0.5.0"))

    cached = result.operations["indicators"].cache
    assert cached is not None
    assert (cached.scopes, cached.cell_bytes, cached.all_bytes) == (5, 11000, 52000)
    assert cached.extrapolated == 1
    assert any(
        "entry of the cache 11000 bytes a scope, 52000 for 5 scopes" in line
        for line in measures.compare(result, None)
    )


@pytest.mark.requirement("WF-QUA-0060-A")
def test_one_scope_read_cold_over_the_objective_is_signalled_and_fails_unless_documented(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    slow = report("0.5.0")
    _indicators(slow)["cache"] = cache(1.5)
    write(tmp_path, slow)
    code, out = run(tmp_path, capsys)
    assert code == 1
    assert "the entry of one scope read cold, 1.5 s" in out
    _indicators(slow)["note"] = "a note of the operation, which does not speak of the cache"
    write(tmp_path, slow)
    code, _ = run(tmp_path, capsys)
    assert code == 1
    cast("dict[str, Any]", _indicators(slow)["cache"])["note"] = "an issue to settle"
    write(tmp_path, slow)
    code, _ = run(tmp_path, capsys)
    assert code == 0


@pytest.mark.requirement("WF-QUA-0060-A")
@pytest.mark.parametrize(
    "change",
    [
        "missing",
        "scopes",
        "no-rows",
        "negative",
        "lighter",
        "row",
        "elsewhere",
        "unsorted",
        "duplicate",
        "note",
    ],
)
def test_a_cost_of_the_cache_that_does_not_hold_is_refused(change: str) -> None:
    body = report("0.5.0")
    entry = _indicators(body)
    given = cast("dict[str, Any]", entry["cache"])
    if change == "missing":
        del entry["cache"]
    elif change == "scopes":
        given["scopes"] = 9
    elif change == "no-rows":
        given["extrapolation"] = []
    elif change == "negative":
        given["hot_cell_s"] = -1
    elif change == "lighter":
        given["all_bytes"] = 10
    elif change == "row":
        del given["extrapolation"][0]["cold_cell_s"]
    elif change == "unsorted":
        given["extrapolation"].append({**given["extrapolation"][0], "subprojects": 50})
    elif change == "duplicate":
        given["extrapolation"].append(dict(given["extrapolation"][-1]))
    elif change == "note":
        given["note"] = 3
    else:
        other = next(
            each
            for each in cast("list[dict[str, object]]", body["operations"])
            if each["id"] == "open-grid"
        )
        other["cache"] = cache()
    with pytest.raises((ValueError, TypeError)):
        parsed(body)


@pytest.mark.requirement("WF-QUA-0060-A")
def test_an_operation_unserved_has_no_cost_of_the_cache() -> None:
    body = report("0.5.0")
    entry = _indicators(body)
    for key in measures.DURATIONS:
        del entry[key]
    entry["unserved"] = "EP-10"
    with pytest.raises(ValueError, match="no duration"):
        parsed(body)
