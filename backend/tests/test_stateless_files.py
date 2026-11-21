# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""No service reads a file it wrote on its own disk in an earlier request or task (US-2820).

WF-ARC-0080-A: the API, the worker and the service of the restoration keep no state on their local
disk between two requests or two tasks. A file of work lives as long as the request or the task that
writes it. This holds it without a cluster, on the code of the three services: every place that
writes to the local disk *that this control sees* is named below with what it is for, and a place
that is not named — a new cache, a file kept between two tasks — fails here until it is named and
its life is shown to be that of a request or a task.

What it sees: the calls that name a writer — ``open`` with a literal mode that writes, the writing
functions of ``shutil``, ``os``, ``sqlite3``, ``shelve``, the writing methods of a path, the
temporary files. What it does not see is held apart (``test_what_the_control_does_not_see``): a
mode that is not a literal, and the modules that start a subprocess or open a log file or a pickle
must be named too. A subprocess that writes to a file a module of the list does not name is not seen
at all: the writing of a command (``pg_dump``) is held by the folder of the task it is given. The
trial of the chart holds the rest on a cluster (``wftools.chartstateless``).
"""

import ast
import os
import re
from pathlib import Path

import pytest

from waterfall.platform.metrics import MULTIPROCESS, shared_between_processes

SOURCE = Path(__file__).resolve().parents[1] / "src" / "waterfall"

pytestmark = [pytest.mark.requirement("WF-ARC-0080-A"), pytest.mark.story("US-2820")]

# What writes a file by a function of a module (``shutil.copyfile``), by a method of a path
# (``Path.write_text``), or by what a call creates (a temporary folder).
MODULE_WRITERS = {
    "shutil": {"copy", "copy2", "copyfile", "copyfileobj", "copytree", "move"},
    "os": {"makedirs", "mkdir", "rename", "replace", "symlink", "link"},
    "sqlite3": {"connect"},
    "shelve": {"open"},
}
METHOD_WRITERS = {"write_text", "write_bytes", "mkdir", "touch", "rename", "symlink_to"}
TEMPORARY = {
    "TemporaryDirectory",
    "NamedTemporaryFile",
    "TemporaryFile",
    "SpooledTemporaryFile",
    "mkdtemp",
    "mkstemp",
}
WRITING_MODE = re.compile(r"^[rwxabt+]{1,4}(:\w+)?$")

# Every module that writes to the local disk, and what its file lives for. A file is read by what
# wrote it only within the request or the task: the folder of a task is a ``TemporaryDirectory``
# that its ``with`` removes (held below), and what is shared is written by one service and read by
# the other.
ALLOWED = {
    "worker/backup.py": "the dumps and the archive of a backup, in the temporary folder of its "
    "task",
    "restore/task.py": "the archive of a restoration and its dumps, in the temporary folder of its "
    "task",
    "worker/restore.py": "the dumps of a restoration, taken out of its archive into the folder of "
    "its task (restore/task.py)",
    "restore/provider.py": "the request to keycloak-realm, a file of a folder the two services "
    "share: the emptyDir in memory of the pod of the restoration, which passes from one request to "
    "the next and which each request cleans (``apply`` removes the answers of an earlier one, and "
    "its own once read); the service writes the request and reads the answer keycloak-realm wrote",
    # An exception, named: the counters are not read by any route but ``getMetrics``, and live and
    # die with the process of the API (held below). Whether a state of a service that serves
    # several instances, which the metrics of the instances sum up, fits WF-ARC-0080-A is a finding
    # of the specification, to be decided: issue #4351.
    "platform/metrics.py": "the counters of the processes of the API, in a folder made at its "
    "start and removed at its end, in the mode of several processes alone: what is measured, which "
    "only ``getMetrics`` reads, not what a request answers (exception of #4351, to be decided)",
}
# What a ``with`` must wrap: a temporary folder that a ``finally`` or the end of a block removes.
# ``worker/restore.py`` makes none and ``restore/provider.py`` neither: the first writes in the
# folder of its caller, held below; the second in the folder of the chart, not of the code.
LIVES = ("worker/backup.py", "restore/task.py", "platform/metrics.py")
# What starts a process, or opens a file by what a call does not name.
INDIRECT = {"subprocess", "FileHandler", "RotatingFileHandler", "WatchedFileHandler", "pickle"}


def parsed() -> dict[str, ast.Module]:
    """Read every module of the services."""
    return {
        str(path.relative_to(SOURCE)): ast.parse(path.read_text(encoding="utf-8"))
        for path in sorted(SOURCE.rglob("*.py"))
        if "migrations" not in path.parts
    }


def writes_to_disk(call: ast.Call) -> bool:
    """Tell whether a call writes to the local disk: a file opened to write, a folder made."""
    function = call.func
    name = function.attr if isinstance(function, ast.Attribute) else getattr(function, "id", "")
    if name in TEMPORARY:
        return True
    if isinstance(function, ast.Attribute):
        owner = getattr(function.value, "id", "")
        if function.attr in MODULE_WRITERS.get(owner, set()):
            return True
        if function.attr in METHOD_WRITERS and owner not in MODULE_WRITERS:
            return True
    if name == "open":
        modes = [
            argument.value
            for argument in [*call.args, *(each.value for each in call.keywords)]
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
        ]
        return any(WRITING_MODE.match(mode) and set(mode) & set("wax+") for mode in modes)
    return False


def sites() -> dict[str, list[int]]:
    """Give, by module, the lines that write to the local disk."""
    found: dict[str, list[int]] = {}
    for module, tree in parsed().items():
        lines = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and writes_to_disk(node)
        ]
        if lines:
            found[module] = lines
    return found


def test_every_place_that_writes_to_the_local_disk_is_named_with_what_its_file_lives_for() -> None:
    unnamed = {module: lines for module, lines in sites().items() if module not in ALLOWED}
    assert not unnamed, (
        f"a service writes to its local disk where nothing says what the file lives for: {unnamed}"
        " (WF-ARC-0080-A: a file of work lives as long as the request or the task that writes it)"
    )


def test_a_place_named_as_writing_to_the_disk_still_does() -> None:
    assert set(ALLOWED) == set(sites()), "a module of ALLOWED no longer writes to the disk"


def test_a_temporary_folder_lives_as_long_as_the_block_of_the_task_that_made_it() -> None:
    trees = parsed()
    for module in LIVES:
        tree = trees[module]
        made = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") in TEMPORARY
        ]
        assert made, f"{module} makes no temporary folder"
        # ``TemporaryDirectory`` is the item of a ``with`` that removes it at its end; ``mkdtemp``
        # is removed by the ``finally`` of the function that made it.
        contexts = {
            id(item.context_expr)
            for node in ast.walk(tree)
            if isinstance(node, ast.With)
            for item in node.items
        }
        for call in made:
            if getattr(call.func, "attr", "") == "mkdtemp":
                assert removed_by_finally(tree, call), f"{module}:{call.lineno} is never removed"
            else:
                assert id(call) in contexts, f"{module}:{call.lineno} is not a ``with`` item"


def removed_by_finally(tree: ast.Module, call: ast.Call) -> bool:
    """Tell whether the function that made a folder removes it, in a ``finally``."""
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef):
            continue
        if not any(node is call for node in ast.walk(function)):
            continue
        for node in ast.walk(function):
            if isinstance(node, ast.Try):
                removals = [
                    each
                    for statement in node.finalbody
                    for each in ast.walk(statement)
                    if isinstance(each, ast.Call) and getattr(each.func, "attr", "") == "rmtree"
                ]
                if removals:
                    return True
    return False


def test_a_write_to_the_disk_that_nothing_names_is_found_by_the_control() -> None:
    kept = ast.parse(
        "import tempfile, shutil\n"
        "def f(p):\n"
        "    p.write_text('x')\n"
        "    open('cache.bin', 'wb')\n"
        "    open('settings.toml')\n"
        "    tempfile.mkdtemp()\n"
        "    shutil.copyfile(a, b)\n"
    )
    lines = [
        node.lineno
        for node in ast.walk(kept)
        if isinstance(node, ast.Call) and writes_to_disk(node)
    ]
    assert lines == [3, 4, 6, 7]


def names_of(tree: ast.AST) -> set[str]:
    """Give every name, and attribute, a tree mentions."""
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
        node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
    }


def test_what_the_control_does_not_see_is_named_too() -> None:
    # A subprocess, a log file or a pickle writes where the control above reads no call, and an
    # ``open`` whose mode is not a literal may write: a module that has any is a named one.
    unseen: dict[str, list[str]] = {}
    for module, tree in parsed().items():
        found = sorted(names_of(tree) & INDIRECT)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "open":
                modes = [
                    *node.args[1:2],
                    *(each.value for each in node.keywords if each.arg == "mode"),
                ]
                if any(not isinstance(mode, ast.Constant) for mode in modes):
                    found.append(f"open:{node.lineno}")
        if found:
            unseen[module] = found
    outside = {module: found for module, found in unseen.items() if module not in ALLOWED}
    assert not outside, (
        f"a service starts a process or opens a file by what no call names: {outside}"
    )


def test_the_control_sees_a_subprocess_and_a_mode_that_is_not_a_literal() -> None:
    kept = ast.parse(
        "import subprocess\ndef f(mode):\n    subprocess.run(['x'])\n    open('a', mode)\n"
    )
    assert names_of(kept) & INDIRECT == {"subprocess"}
    opens = [
        node
        for node in ast.walk(kept)
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "open"
    ]
    assert [not isinstance(call.args[1], ast.Constant) for call in opens] == [True]


def test_the_restoration_writes_in_the_temporary_folder_of_its_task_alone() -> None:
    # ``worker/restore.py`` makes no folder: it is given one, and the only caller gives it the
    # ``TemporaryDirectory`` its ``with`` removes at the end of the task.
    trees = parsed()
    callers = [
        (module, function)
        for module, tree in trees.items()
        for function in ast.walk(tree)
        if isinstance(function, ast.FunctionDef)
        for call in ast.walk(function)
        if isinstance(call, ast.Call) and getattr(call.func, "id", "") == "extracted"
    ]
    assert {module for module, _ in callers} == {"restore/task.py"}
    for module, function in callers:
        made = [
            item.context_expr
            for node in ast.walk(function)
            if isinstance(node, ast.With)
            for item in node.items
            if getattr(getattr(item.context_expr, "func", None), "attr", "") == "TemporaryDirectory"
        ]
        assert made, f"{module}:{function.name} gives ``extracted`` no temporary folder of its own"
    assert not names_of(trees["worker/restore.py"]) & TEMPORARY


def test_the_realm_request_removes_the_answer_of_an_earlier_one_before_it_writes() -> None:
    # The folder is the pod's, from one request to the next: an answer left by an earlier request
    # must not be read as the answer of this one.
    tree = parsed()["restore/provider.py"]
    apply = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "apply"
    )
    lines = {
        name: [
            call.lineno
            for call in ast.walk(apply)
            if isinstance(call, ast.Call) and getattr(call.func, "attr", "") == name
        ]
        for name in ("unlink", "write_text", "rename")
    }
    assert min(lines["unlink"]) < min(lines["write_text"]) < min(lines["rename"])
    assert len(lines["unlink"]) >= 3, "the answers read are removed too: ``.done`` and ``.failed``"


def test_the_counters_folder_is_read_by_no_route_but_the_metrics_and_dies_with_its_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The exception of ``platform/metrics.py`` (#4351): only ``getMetrics`` reads the folder, by
    # ``generate_latest`` over the collectors of the registry; it exists in the mode of several
    # processes alone, and is removed with the process that made it.
    mentions = {
        module: [
            name
            for name in names_of(tree)
            | {
                str(node.value)
                for node in ast.walk(tree)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
            }
            if "MULTIPROC" in name.upper()
        ]
        for module, tree in parsed().items()
    }
    assert {module for module, nodes in mentions.items() if nodes} == {"platform/metrics.py"}
    trees = parsed()
    exposing = {
        module
        for module, tree in trees.items()
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "expose"
    }
    assert exposing == {"api/system.py"}
    operations = {
        keyword.value.value
        for node in ast.walk(trees["api/system.py"])
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg == "operation_id" and isinstance(keyword.value, ast.Constant)
    }
    assert "getMetrics" in operations
    # ``shared_between_processes()`` when there are several processes, ``nullcontext()`` if not.
    choices = [
        node
        for node in ast.walk(trees["api/main.py"])
        if isinstance(node, ast.IfExp)
        and isinstance(node.test, ast.Compare)
        and ast.unparse(node.test) == "settings.api_processes > 1"
    ]
    assert [(ast.unparse(choice.body), ast.unparse(choice.orelse)) for choice in choices] == [
        ("shared_between_processes()", "nullcontext()")
    ]
    # The folder, made and removed with the context of the process that serves.
    monkeypatch.delenv(MULTIPROCESS, raising=False)
    with shared_between_processes():
        folder = Path(os.environ[MULTIPROCESS])
        assert folder.is_dir()
    assert not folder.exists()
    assert MULTIPROCESS not in os.environ
