# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the plugin that fails a Python test which skips without declaring it (US-2440)."""

import ast

import pytest

from wftools import REPOSITORY, unexecuted

pytestmark = pytest.mark.requirement("WF-QUA-0010-A")

PLUGIN = 'pytest_plugins = ("wftools.unexecuted",)\n'


def run(pytester: pytest.Pytester, source: str) -> pytest.RunResult:
    """Run these tests with the plugin, as the back and the tools load it."""
    pytester.makeconftest(PLUGIN)
    pytester.makepyfile(source)
    return pytester.runpytest_inprocess("-p", "no:cacheprovider", "--strict-markers", "-rA")


def test_a_test_that_skips_without_the_mark_fails(pytester: pytest.Pytester) -> None:
    result = run(
        pytester,
        """
import pytest

def test_played() -> None: ...

def test_skipped() -> None:
    pytest.skip("no schema")

@pytest.mark.skipif(True, reason="no docker")
def test_skipped_by_a_mark() -> None: ...
""",
    )
    result.assert_outcomes(passed=1, failed=1, errors=1)
    result.stdout.fnmatch_lines(["*skipped without @pytest.mark.unexecuted(<reason>): no schema*"])
    result.stdout.fnmatch_lines(["*skipped without @pytest.mark.unexecuted(<reason>): no docker*"])


def test_a_test_that_declares_its_skip_on_itself_its_class_or_its_module_is_skipped(
    pytester: pytest.Pytester,
) -> None:
    result = run(
        pytester,
        """
import pytest

pytestmark = pytest.mark.unexecuted("skipped without docker")

def test_module() -> None:
    pytest.skip("no docker")

@pytest.mark.unexecuted("skipped without the schema")
class TestSchema:
    @pytest.mark.unexecuted("skipped without the schema, here too")
    def test_valid(self) -> None:
        pytest.skip("no schema")

@pytest.mark.xfail(reason="not yet", strict=True)
def test_expected_to_fail() -> None:
    raise AssertionError
""",
    )
    result.assert_outcomes(skipped=2, xfailed=1)


def test_an_expected_failure_that_is_not_run_is_a_skip(pytester: pytest.Pytester) -> None:
    result = run(
        pytester,
        """
import pytest

@pytest.mark.xfail(run=False, reason="breaks the worker")
def test_not_run() -> None: ...

@pytest.mark.unexecuted("breaks the worker")
@pytest.mark.xfail(run=False, reason="breaks the worker")
def test_not_run_declared() -> None: ...
""",
    )
    result.assert_outcomes(errors=1, xfailed=1)
    result.stdout.fnmatch_lines(
        ["*skipped without @pytest.mark.unexecuted(<reason>): breaks the worker*"]
    )


def test_a_mark_without_a_reason_declares_nothing(pytester: pytest.Pytester) -> None:
    result = run(
        pytester,
        """
import pytest

@pytest.mark.unexecuted
def test_skipped() -> None:
    pytest.skip("no schema")
""",
    )
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*@pytest.mark.unexecuted gives no reason: no schema*"])


def test_a_module_that_skips_as_it_is_imported_fails(pytester: pytest.Pytester) -> None:
    result = run(
        pytester,
        """
import pytest

pytest.importorskip("a_module_no_one_installed")

def test_never_collected() -> None: ...
""",
    )
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*the module skips as it is imported*"])


@pytest.mark.parametrize("conftest", ["backend/tests/conftest.py", "tools/tests/conftest.py"])
def test_the_tests_of_the_back_and_of_the_tools_load_the_plugin(conftest: str) -> None:
    tree = ast.parse((REPOSITORY / conftest).read_text(encoding="utf-8"))
    loaded = [
        element.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "pytest_plugins" for t in node.targets)
        and isinstance(node.value, ast.Tuple)
        for element in node.value.elts
        if isinstance(element, ast.Constant)
    ]
    assert unexecuted.__name__ in loaded
