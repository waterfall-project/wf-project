# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The plugin of Pytest that fails a test which skips without declaring it (US-2440).

The coverage of the requirements is read in the test files without running them
(``wftools.coverage``): a test that may skip says so by the mark
``@pytest.mark.unexecuted("<reason>")``, on the test, its class or its module, and its citations
cover nothing. This plugin makes the mark compulsory: a test that skips — by ``pytest.skip``, a
``skipif`` or ``importorskip`` — without it, or with a mark that gives no reason, fails, and so
does a module that skips whole as it is imported, which no mark can declare. An expected failure
(``xfail``) is no skip — but ``xfail(run=False)``, which never runs the test, is one.

The tests of the back and those of the tools load it, by the ``pytest_plugins`` of their
``conftest.py``: one implementation for both packages, the back finding it on its ``pythonpath``.
"""

from typing import TYPE_CHECKING

import pytest

from wftools.marks import MARK

if TYPE_CHECKING:
    from collections.abc import Generator

NOT_RUN = "[NOTRUN]"
"""What Pytest prefixes the reason of an ``xfail(run=False)`` with, which it reports as skipped."""


def pytest_configure(config: pytest.Config) -> None:
    """Declare the mark, which ``--strict-markers`` would refuse otherwise."""
    config.addinivalue_line(
        "markers",
        f"{MARK}(reason): this test may skip, and covers no requirement it cites (US-2440)",
    )


def _undeclared(item: pytest.Item) -> str | None:
    """Return why the skip of this test is not declared, or ``None`` when it is."""
    mark = item.get_closest_marker(MARK)
    if mark is None:
        return f"skipped without @pytest.mark.{MARK}(<reason>)"
    if not (mark.args and isinstance(mark.args[0], str) and mark.args[0].strip()):
        return f"@pytest.mark.{MARK} gives no reason"
    return None


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo[None]
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    """Fail the report of a test that skipped without declaring it."""
    del call
    report = yield
    if report.skipped and _is_skip(report):
        undeclared = _undeclared(item)
        if undeclared is not None:
            report.outcome = "failed"
            report.longrepr = f"{undeclared}: {_reason(report)}"
    return report


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_make_collect_report(
    collector: pytest.Collector,
) -> Generator[None, pytest.CollectReport, pytest.CollectReport]:
    """Fail a module that skips whole as it is imported: its tests could bear no mark."""
    report = yield
    if report.skipped and isinstance(collector, pytest.Module):
        report.outcome = "failed"
        report.longrepr = (
            f"the module skips as it is imported, which no @pytest.mark.{MARK} declares: "
            f"{_reason(report)}"
        )
    return report


def _is_skip(report: pytest.TestReport) -> bool:
    """Tell a skip from an expected failure, which reports as skipped too, but for ``run=False``."""
    expected = getattr(report, "wasxfail", None)
    return expected is None or str(expected).startswith(NOT_RUN)


def _reason(report: pytest.TestReport | pytest.CollectReport) -> str:
    """Return the reason a skip gave, which Pytest keeps last in a triple."""
    if (expected := getattr(report, "wasxfail", None)) is not None:
        return str(expected).removeprefix(NOT_RUN).strip()
    longrepr = report.longrepr
    match longrepr:
        case (str(), int(), str() as reason):
            return reason.removeprefix("Skipped: ")
        case _:
            return str(longrepr)
