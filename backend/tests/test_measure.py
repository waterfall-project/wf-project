# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The logic of the measure of the core that needs no database: its figures and its report.

The measure itself runs on the service platform (``make measure-core``) and is no test: it never
fails on a duration. What it computes and writes is tested here: a tool of the repository, whose
tests cite no requirement.
"""

import json

import pytest

from measure.__main__ import main
from measure.figures import ratio, summarise
from measure.report import Measure, Report, render_json, render_text
from measure.target import MeasureError, address_from_environment


def test_a_summary_gives_the_median_the_worst_and_the_spread_of_its_runs() -> None:
    summary = summarise([0.30, 0.10, 0.20, 0.50, 0.40])

    assert summary.runs == 5
    assert summary.median == pytest.approx(0.30)
    assert summary.worst == pytest.approx(0.50)
    assert summary.spread == pytest.approx(0.40)


def test_the_median_of_an_even_number_of_runs_is_the_mean_of_the_two_middle_ones() -> None:
    assert summarise([0.1, 0.2, 0.3, 0.4]).median == pytest.approx(0.25)


def test_a_single_run_has_no_spread() -> None:
    summary = summarise([0.2])

    assert (summary.median, summary.worst, summary.spread) == (0.2, 0.2, 0.0)


def test_a_summary_of_no_run_is_refused() -> None:
    with pytest.raises(ValueError, match="at least one run"):
        summarise([])


def test_a_ratio_is_the_numerator_over_the_denominator_and_zero_over_nothing() -> None:
    assert ratio(0.9, 0.3) == pytest.approx(3.0)
    assert ratio(0.9, 0.0) == 0.0


def _report() -> Report:
    return Report(
        {"project": "PRJ-001", "runs": 3},
        (
            Measure(
                "read all",
                summarise([0.4, 0.45, 0.5]),
                {"nodes": 5999, "body_mb": 7.83},
            ),
            Measure("by processes", rows=({"processes": 2, "reads_per_second": 4.13},)),
        ),
    )


def test_the_json_of_a_report_gives_the_durations_in_milliseconds() -> None:
    written = json.loads(render_json(_report()))

    assert written["subject"] == {"project": "PRJ-001", "runs": 3}
    first, second = written["measures"]
    assert first["name"] == "read all"
    assert first["summary"] == {
        "runs": 3,
        "median_ms": 450.0,
        "worst_ms": 500.0,
        "spread_ms": 100.0,
    }
    assert first["facts"] == {"nodes": 5999, "body_mb": 7.83}
    assert "summary" not in second
    assert second["rows"] == [{"processes": 2, "reads_per_second": 4.13}]


def test_the_text_of_a_report_reads_one_block_per_measure() -> None:
    text = render_text(_report())

    assert "project=PRJ-001  runs=3" in text
    assert "read all  median 450 ms  worst 500 ms  spread 100 ms  (3 runs)" in text
    assert "    nodes: 5999" in text
    assert "    processes=2  reads_per_second=4.13" in text


def test_the_address_is_that_of_the_slot_and_the_role_of_the_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WATERFALL_SERVICE_DATABASE_PASSWORD", "p@ss/word")
    monkeypatch.setenv("WATERFALL_POSTGRES_PORT", "20410")

    address = address_from_environment()

    assert address == "postgresql://waterfall_service:p%40ss%2Fword@127.0.0.1:20410/waterfall"


def test_the_address_without_the_password_of_the_service_says_what_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WATERFALL_SERVICE_DATABASE_PASSWORD", raising=False)

    with pytest.raises(MeasureError, match="WATERFALL_SERVICE_DATABASE_PASSWORD"):
        address_from_environment()


def test_a_port_that_is_no_number_is_refused_by_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WATERFALL_SERVICE_DATABASE_PASSWORD", "secret")
    monkeypatch.setenv("WATERFALL_POSTGRES_PORT", "twenty")

    with pytest.raises(MeasureError, match="WATERFALL_POSTGRES_PORT"):
        address_from_environment()


@pytest.mark.parametrize("runs", ["0", "-2", "many"])
def test_a_number_of_runs_under_one_is_refused_by_the_parser(
    runs: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit):
        main(["--runs", runs])

    assert "at least 1" in capsys.readouterr().err


def test_the_notes_of_a_measure_are_written_in_the_text_and_in_the_json() -> None:
    report = Report({"runs": 1}, (Measure("read all", notes=("one pass",)),))

    assert "    note: one pass" in render_text(report)
    assert json.loads(render_json(report))["measures"][0]["notes"] == ["one pass"]
