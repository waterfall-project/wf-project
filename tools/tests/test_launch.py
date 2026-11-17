# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The launcher of the guard and of the slots fails closed under an older Python (US-2450).

The hook of ``.claude/settings.json`` and the ``SLOTS`` of the Makefile run
``tools/src/wftools/launch.py`` by the ``python3`` of the workstation. Under a Python older than
3.14, ``guard.py`` raised ``NameError`` at its import, by the code 1, and Claude Code let every
command pass (#3711). The hook is run here as Claude Code runs it, by an older ``python3``: the
oldest interpreter present on the workstation, when there is one — the test may then skip —, and
always by the interpreter of the tests made to say it is 3.13, which only the version check of the
launcher reads. The hook, as the settings write it, refuses too what the launcher cannot see: no
``python3``, one that cannot read the launcher, a process killed. A tool of the repository: the
tests that hold a criterion of US-2450 cite it; the others keep what the launcher must not break,
a decision of the guard and the name of a tool.
"""

import ast
import builtins
import json
import os
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, Any, cast

import pytest

from wftools import REPOSITORY

if TYPE_CHECKING:
    from pathlib import Path

LAUNCH = REPOSITORY / "tools" / "src" / "wftools" / "launch.py"
SETTINGS = REPOSITORY / ".claude" / "settings.json"
REQUIRED = (3, 14)
UNUSABLE = "the command guard cannot be used, it needs Python 3.14"
# A python3 that runs the interpreter of the tests, made to say it is 3.13 to what it runs.
OLDER = (
    "#!/bin/sh\n"
    'exec {python} -c \'import runpy, sys; sys.version_info = (3, 13, 0, "final", 0); '
    'del sys.argv[0]; runpy.run_path(sys.argv[0], run_name="__main__")\' "$@"\n'
)


def oldest_interpreter() -> str | None:
    """Return the oldest Python older than 3.14 that uv finds on the workstation, if any."""
    uv = shutil.which("uv")
    if uv is None:
        return None
    listed = subprocess.run(
        [uv, "python", "list", "--only-installed", "--output-format", "json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if listed.returncode != 0:
        return None
    found: list[tuple[int, int, str]] = []
    for entry in cast("list[dict[str, Any]]", json.loads(listed.stdout)):
        parts = cast("dict[str, int]", entry["version_parts"])
        if (parts["major"], parts["minor"]) < REQUIRED and entry.get("path"):
            found.append((parts["major"], parts["minor"], cast("str", entry["path"])))
    return min(found)[2] if found else None


def older_python(tmp_path: Path) -> Path:
    """Return a directory whose ``python3`` says it is 3.13, to put first on the ``PATH``."""
    directory = tmp_path / "older"
    directory.mkdir()
    script = directory / "python3"
    script.write_text(OLDER.format(python=sys.executable), encoding="utf-8")
    script.chmod(0o755)
    return directory


def hook() -> str:
    """Return the command of the ``PreToolUse`` hook on ``Bash``, as the settings declare it."""
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    [entry] = settings["hooks"]["PreToolUse"]
    [declared] = entry["hooks"]
    return cast("str", declared["command"])


def run_hook(command: str, python: Path) -> subprocess.CompletedProcess[str]:
    """Run the hook as Claude Code does, the ``python3`` of the directory ``python`` first."""
    return run_hook_on(command, f"{python}{os.pathsep}{os.environ.get('PATH', '')}")


def run_hook_on(command: str, path: str) -> subprocess.CompletedProcess[str]:
    """Run the hook as Claude Code does, by a shell, under the ``PATH`` ``path``."""
    event = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    environment = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "VIRTUAL_ENV"}}
    environment |= {"CLAUDE_PROJECT_DIR": str(REPOSITORY), "PATH": path}
    bash = shutil.which("bash")
    assert bash is not None
    return subprocess.run(
        [bash, "-c", hook()],
        input=event,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.story("US-2450")
def test_the_hook_and_the_makefile_run_the_launcher() -> None:
    assert hook() == 'python3 "$CLAUDE_PROJECT_DIR/tools/src/wftools/launch.py" guard || exit 2'
    makefile = (REPOSITORY / "Makefile").read_text(encoding="utf-8")
    assert "\nSLOTS = python3 $(CURDIR)/tools/src/wftools/launch.py slots\n" in makefile


@pytest.mark.story("US-2450")
@pytest.mark.parametrize("command", ["pkill -f make", "ls"])
def test_under_an_older_python_the_hook_refuses_every_command(command: str, tmp_path: Path) -> None:
    """The guard cannot judge: it refuses, by the code 2, and says which version it expects."""
    ran = run_hook(command, older_python(tmp_path))
    assert ran.returncode == 2, ran.stderr
    assert UNUSABLE in ran.stderr
    assert "python3 is 3.13.0" in ran.stderr


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    "python3",
    [
        None,
        "#!/bin/sh\necho 'SyntaxError: invalid syntax' >&2\nexit 1\n",
        "#!/bin/sh\nkill -KILL $$\n",
    ],
    ids=["no python3", "a python3 that cannot read the launcher", "a python3 killed"],
)
def test_the_hook_refuses_when_the_launcher_does_not_run_to_a_decision(
    python3: str | None, tmp_path: Path
) -> None:
    """The shell of the hook turns any code but 0 into 2: 127, 1 and 137 refuse the command."""
    if python3 is not None:
        script = tmp_path / "python3"
        script.write_text(python3, encoding="utf-8")
        script.chmod(0o755)
    ran = run_hook_on("ls", str(tmp_path))
    assert ran.returncode == 2, ran.stderr


@pytest.mark.story("US-2450")
@pytest.mark.unexecuted("skipped when the workstation has no Python older than 3.14")
def test_the_oldest_python_of_the_workstation_runs_the_hook_to_a_refusal(tmp_path: Path) -> None:
    """``pkill -f make``, by the oldest interpreter: code 2 and the message, no ``NameError``."""
    oldest = oldest_interpreter()
    if oldest is None:
        pytest.skip("no Python older than 3.14 on the workstation")
    directory = tmp_path / "oldest"
    directory.mkdir()
    (directory / "python3").symlink_to(oldest)
    ran = run_hook("pkill -f make", directory)
    assert ran.returncode == 2, ran.stderr
    assert UNUSABLE in ran.stderr
    assert "NameError" not in ran.stderr
    assert "Traceback" not in ran.stderr


@pytest.mark.story("US-2450")
def test_the_launcher_is_written_in_the_grammar_of_python_3_8() -> None:
    """No syntax after 3.8, and no annotation an older interpreter could not evaluate."""
    tree = ast.parse(LAUNCH.read_text(encoding="utf-8"), feature_version=(3, 8))
    annotations: list[ast.expr] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            annotations += [a.annotation for a in arguments if a.annotation is not None]
            annotations += [node.returns] if node.returns is not None else []
        if isinstance(node, ast.AnnAssign):
            annotations.append(node.annotation)
    assert annotations
    for annotation in annotations:
        assert isinstance(annotation, ast.Name), ast.unparse(annotation)
        assert hasattr(builtins, annotation.id), annotation.id
    imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert {name.split(".")[0] for name in imported} <= sys.stdlib_module_names


def launch_beside(tmp_path: Path, guard: str, command: str) -> subprocess.CompletedProcess[str]:
    """Run a copy of the launcher beside the guard ``guard``, as the hook runs it."""
    shutil.copy(LAUNCH, tmp_path / "launch.py")
    (tmp_path / "guard.py").write_text(guard, encoding="utf-8")
    event = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    return subprocess.run(
        [sys.executable, str(tmp_path / "launch.py"), "guard"],
        input=event,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.story("US-2450")
@pytest.mark.parametrize("command", ["ls", "pkill -f make"])
def test_a_guard_that_raises_while_judging_refuses_the_command(
    command: str, tmp_path: Path
) -> None:
    raising = "import json, sys\njson.load(sys.stdin)\nraise RecursionError('too deep')\n"
    ran = launch_beside(tmp_path, raising, command)
    assert ran.returncode == 2
    assert "failed while judging the command (RecursionError: too deep)" in ran.stderr


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    ("guard", "said"),
    [
        ("import sys\nsys.exit(1)\n", "ended by the code 1"),
        ("def main():\n    return 0\n", "ended without a decision"),
        ("def main(:\n", "SyntaxError"),
    ],
)
def test_a_guard_that_gives_no_decision_refuses_the_command(
    guard: str, said: str, tmp_path: Path
) -> None:
    ran = launch_beside(tmp_path, guard, "ls")
    assert ran.returncode == 2
    assert said in ran.stderr


# The interpreter of the tests runs the launcher of the repository, the guard of the repository
# beside it, after it made shlex.split raise: refusal raises deep in its judgement, as a defect of
# the guard would.
RAISING_SPLIT = (
    "import runpy, shlex, sys\n"
    "def split(*arguments, **options):\n"
    "    raise RecursionError('too deep')\n"
    "shlex.split = split\n"
    "del sys.argv[0]\n"
    "runpy.run_path(sys.argv[0], run_name='__main__')\n"
)


@pytest.mark.story("US-2450")
@pytest.mark.parametrize("command", ["ls", "pkill -f make"])
def test_the_guard_of_the_repository_that_raises_refuses_the_command(command: str) -> None:
    event = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    ran = subprocess.run(
        [sys.executable, "-c", RAISING_SPLIT, str(LAUNCH), "guard"],
        input=event,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ran.returncode == 2, ran.stderr
    assert "failed while judging the command (RecursionError: too deep)" in ran.stderr


@pytest.mark.parametrize(("command", "code"), [("ls", 0), ("pkill -f make", 2)])
def test_the_launcher_keeps_the_decision_of_the_guard(command: str, code: int) -> None:
    event = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    ran = subprocess.run(
        [sys.executable, str(LAUNCH), "guard"],
        input=event,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ran.returncode == code
    assert ("`pkill`" in ran.stderr) == (code == 2)
    assert "Refused: the command guard" not in ran.stderr


@pytest.mark.story("US-2450")
def test_under_an_older_python_the_slots_say_the_version_they_expect(tmp_path: Path) -> None:
    ran = subprocess.run(
        [str(older_python(tmp_path) / "python3"), str(LAUNCH), "slots", "processors"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert ran.returncode == 2
    assert ran.stdout == ""
    assert "the tool of the slots did not run, it needs Python 3.14" in ran.stderr


@pytest.mark.parametrize("arguments", [[], ["mergequeue"]])
def test_a_tool_the_launcher_does_not_know_is_refused(arguments: list[str]) -> None:
    ran = subprocess.run(
        [sys.executable, str(LAUNCH), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    assert ran.returncode == 2
    assert "name a tool among guard, slots" in ran.stderr
