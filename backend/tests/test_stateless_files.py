# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""No service reads a file it wrote on its own disk in an earlier request or task (US-2820).

WF-ARC-0080-A: the API, the worker and the service of the restoration keep no state on their local
disk between two requests or two tasks. A file of work lives as long as the request or the task that
writes it. This holds it without a cluster, on the code of the three services: every place that
writes to the local disk is named below with what it is for, and a place that is not named — a new
cache, a file kept between two tasks — fails here until it is named and its life is shown to be that
of a request or a task. The trial of the chart holds the rest on a cluster
(``wftools.chartstateless``).
"""

import ast
import re
from pathlib import Path

import pytest

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
    "share: the service of the restoration writes the request and reads the answer, which "
    "keycloak-realm wrote; the folder is that of one restoration",
    "platform/metrics.py": "the counters of the processes of the API, in a folder made at its "
    "start and removed at its end: what is measured, not what a request answers",
}
# What a ``with`` must wrap: a temporary folder that a ``finally`` or the end of a block removes.
LIVES = ("worker/backup.py", "restore/task.py", "platform/metrics.py")


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
