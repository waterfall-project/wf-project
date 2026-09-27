# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the rules of source files: no suppression comment, 1,000 lines at most."""

import pytest

from wftools import paths, sources

# Written in pieces, so that this file does not carry the comments it looks for.
NOQA = "no" + "qa"
IGNORE = "type" + ": ignore"


@pytest.mark.parametrize(
    "line",
    [
        f"x = 1  # {NOQA}",
        f"x = 1  # {NOQA}: E501",
        f"# ruff: {NOQA}",
        f"x: int = 'a'  # {IGNORE}",
        "x = f()  # pyright" + ": ignore[reportUnknownVariableType]",
        "# pyright" + ": basic",
        "# pyright" + ": reportUnusedFunction=false",
        "# fmt" + ": off",
        "if debug:  # pragma" + ": no cover",
    ],
)
def test_a_python_suppression_is_a_breach(line: str) -> None:
    (breach,) = sources.breaches("backend/src/a.py", f"{line}\n")
    assert breach.line == 1
    assert breach.reason.startswith("suppression comment")


@pytest.mark.parametrize(
    "line",
    [
        "// eslint" + "-disable-next-line no-console",
        "/* eslint" + "-disable */",
        "// @ts" + "-ignore",
        "// @ts" + "-expect-error",
        "// prettier" + "-ignore",
        "/* v8" + " ignore next */",
        "{/* eslint" + "-disable-line */}",
    ],
)
def test_a_typescript_suppression_is_a_breach(line: str) -> None:
    assert sources.breaches("frontend/src/a.tsx", f"{line}\n")


def test_a_shell_suppression_is_a_breach() -> None:
    assert sources.breaches("deploy/run.sh", "# shellcheck" + " disable=SC2086\n")


@pytest.mark.parametrize(
    ("path", "text"),
    [
        ("backend/src/a.py", f'MESSAGE = "a comment may not say {NOQA}"\n'),
        ("backend/src/a.py", "# Ruff reports what it finds; nothing here silences it.\n"),
        ("frontend/src/a.ts", "const rule = 'eslint" + "-disable is refused';\n"),
    ],
)
def test_naming_a_suppression_outside_a_comment_is_not_one(path: str, text: str) -> None:
    assert sources.breaches(path, text) == []


def test_a_file_of_a_thousand_lines_passes() -> None:
    assert sources.breaches("backend/src/a.py", "x = 1\n" * sources.MAX_LINES) == []


def test_a_file_of_a_thousand_and_one_lines_is_named_with_its_size() -> None:
    (breach,) = sources.breaches("backend/src/a.py", "x = 1\n" * (sources.MAX_LINES + 1))
    assert str(breach) == "backend/src/a.py:1001: 1001 lines, 1000 at most"


def test_generated_and_excepted_paths_are_left_out() -> None:
    declaration = paths.read()
    checked = sources.sources(declaration)
    assert "tools/src/wftools/sources.py" in checked
    assert not any(path.startswith("docs/spec/tools/") for path in checked)


def test_the_repository_keeps_the_rules(capsys: pytest.CaptureFixture[str]) -> None:
    assert sources.main() == 0, capsys.readouterr().err


TODO = "TO" + "DO"


@pytest.mark.parametrize(
    ("line", "breach"),
    [
        (f"// {TODO}(#12): pick the column order", False),
        (f"// {TODO}: pick the column order", True),
        (f"/* {TODO} later */", True),
        (f" * {TODO}(#12): in a block comment", False),
        (f" * {TODO} in a block comment", True),
        ("// FIX" + "ME: broken on Safari", True),
        ("// HA" + "CK around the grid", True),
        (f"const label = '{TODO}';", False),
    ],
)
def test_a_typescript_todo_cites_its_issue(line: str, breach: bool) -> None:
    assert bool(sources.breaches("frontend/src/a.ts", f"{line}\n")) is breach


def test_a_python_todo_is_left_to_ruff() -> None:
    assert sources.breaches("backend/src/a.py", f"# {TODO}: Ruff reports this one\n") == []
