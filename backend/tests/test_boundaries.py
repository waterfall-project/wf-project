# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The contracts of the core reject what WF-ARC-0010 forbids.

The core has no module yet, so the contracts of ``pyproject.toml`` are applied, unchanged
but for the name of the root package, to a sample package built for each test.
"""

import ast
import importlib
import inspect
import os
import pkgutil
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import cast

import pytest

PROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def layered() -> tuple[str, ...]:
    """Name the modules the contract of the layers of the core orders, as the project file does."""
    contracts = tomllib.loads(PROJECT.read_text(encoding="utf-8"))["tool"]["importlinter"][
        "contracts"
    ]
    ordered = [
        contract
        for contract in contracts
        if contract["type"] == "layers" and contract.get("containers") == ["waterfall.core"]
    ]
    assert len(ordered) == 1
    return tuple(name.strip() for layer in ordered[0]["layers"] for name in layer.split("|"))


LAYERED = layered()
LAYOUT = {
    "witness/__init__.py": "",
    "bootstrap.py": "",
    "restore/__init__.py": "",
    "api/__init__.py": "",
    "worker/__init__.py": "",
    "migrations/__init__.py": "",
    "schema.py": "",
    "core/__init__.py": "",
    "platform/__init__.py": "",
    "core/accounts/__init__.py": "",
    "core/accounts/interface.py": "from sample.core.accounts import tables\n",
    "core/accounts/tables.py": "",
    "core/projects/__init__.py": "",
    "core/projects/interface.py": "",
    "core/projects/tables.py": "",
    # An interface in a package: one file per object, re-exported by the package.
    "core/settings/__init__.py": "",
    "core/settings/interface/__init__.py": (
        "from sample.core.settings.interface.rates import RATE\n"
    ),
    "core/settings/interface/rates.py": "from sample.core.settings import tables\nRATE = 1\n",
    "core/settings/tables.py": "",
    # The modules the contract of the layers orders, by their names (#2124).
    **{f"core/{name}/{each}.py": "" for name in LAYERED for each in ("__init__", "interface")},
}
# The modules of the reference (EP-05), and the files of the interface of each, one per object.
REFERENCE_INTERFACES: dict[str, set[str]] = {
    "cost_settings": {
        "reference_settings",
        "readiness",
        "cost_types",
        "cost_categories",
        "hourly_rates",
        "actual_cost_mapping",
    },
    "resource_settings": {
        "readiness",
        "org_nodes",
        "resource_roles",
        "calendars",
        "duration_units",
        "extensions",
    },
    "risk_settings": set(),
    "indicator_settings": set(),
}
# The modules of the projects and of the revisions (EP-04), one file per subject.
PROJECT_INTERFACES: dict[str, set[str]] = {
    "projects": {
        "projects",
        "contributors",
        "subprojects",
        "work_breakdown",
        "lifecycle",
        "attachments",
        "skeleton",
        "days",
    },
    "revisions": {"revisions", "structures", "marking", "reference", "shared", "closing"},
}
# The modules of the planning, the history and the exchanges (EP-06), one file per story or
# subject, laid by the socle (US-1380/L1) so that no later story opens their ``__init__``.
PLANNING_INTERFACES: dict[str, set[str]] = {
    "planning": {
        "closing",
        "facets",
        "lines",
        "loading",
        "msproject",
        "nodes",
        "paste",
        "predecessors",
        "progress",
        "reference",
        "skeleton",
        "snapshots",
        "structures",
        "task_tree",
        "timelines",
        "tracking",
        "work_breakdown",
    },
    "history": {"closing", "plans", "purge", "recording", "undo"},
    "exchanges": {"exports", "imports", "purge", "xml"},
}
# What the design names of each (EP-04, "Modules"), declared from US-0910/L1 on, which the other
# stories call before theirs fill them.
DESIGNED: dict[str, set[str]] = {
    "projects": {
        "read_project",
        "list_projects",
        "create_project",
        "update_project",
        "contributor_kind",
        "next_state",
        "advance",
        "exit_project",
        "list_state_transitions",
        "no_background_task_running",
        "project_label",
        "project_code",
        "load_project",
    },
    "revisions": {
        "list_revisions",
        "read_revision",
        "create_revision",
        "copy_revision",
        "abandon_revision",
        "mark_revision",
        "designate_reference",
        "revision_has_tasks_and_lines",
        "compute_indicators",
        "current_revision",
        "revision_draft",
        "create_project_partitions",
        "load_revision",
    },
    # EP-06, "Modules": what each story calls of another before it fills its own.
    "planning": {
        "list_nodes",
        "create_node",
        "update_task_facet",
        "delete_node",
        "move_nodes",
        "resolve_row_number",
        "computed_value_dependencies",
        "set_predecessors",
        "update_cost_structure",
        "set_task_progress",
        "list_timelines",
        "create_timeline",
        "delete_timeline",
        "set_node_tracking",
        "generate_skeleton",
        "reschedule",
        "revision_has_tasks",
        "copy_nodes",
        "delete_nodes",
        "work_breakdown_item_cited",
        "detach_work_breakdown_item",
        "tasks_left_idle",
        "reschedule_current_structures",
        "lines_of",
        "register_facet",
        "calendar_of",
        "snapshot",
        "restore",
        "preview_paste",
        "apply_paste",
    },
    "history": {
        "recording",
        "undo",
        "redo",
        "depth",
        "close_history",
        "keep_plan",
        "read_plan",
        "drop_plan",
        "purge",
    },
    "exchanges": {
        "register_format",
        "register_exporter",
        "deposit",
        "open_import",
        "read_import",
        "list_imports",
        "abandon_import",
        "apply_import",
        "run_analysis",
        "run_apply",
        "run_export",
        "result_of",
        "consumed",
        "purge",
        "remove_purged",
        "stored_before",
        "hardened_parser",
    },
}


def contracts_for(package: str) -> str:
    """Write the import contracts of the project for another root package."""
    settings = tomllib.loads(PROJECT.read_text(encoding="utf-8"))["tool"]["importlinter"]
    lines = [f'[tool.importlinter]\nroot_package = "{package}"\n']
    for contract in settings["contracts"]:
        lines.append("[[tool.importlinter.contracts]]")
        for key, value in contract.items():
            lines.append(f"{key} = {_toml(value, package)}")
        lines.append("")
    return "\n".join(lines)


def _toml(value: object, package: str) -> str:
    if isinstance(value, list):
        items = cast("list[object]", value)
        return "[" + ", ".join(_toml(item, package) for item in items) + "]"
    text = str(value).replace("waterfall", package)
    return f'"{text}"'


@pytest.fixture
def sample(tmp_path: Path) -> Path:
    """Build a package named ``sample`` laid out like ``waterfall``, and its contracts."""
    for name, content in LAYOUT.items():
        path = tmp_path / "sample" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (tmp_path / "sample" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "contracts.toml").write_text(contracts_for("sample"), encoding="utf-8")
    return tmp_path


def lint(sample: Path, module: str, code: str) -> subprocess.CompletedProcess[str]:
    """Add an import to a module of the sample, and run the contracts on it."""
    path = sample / "sample" / f"{module.replace('.', '/')}.py"
    path.write_text(code, encoding="utf-8")
    environment = {**os.environ, "PYTHONPATH": str(sample)}
    return subprocess.run(
        ["lint-imports", "--config", str(sample / "contracts.toml"), "--no-cache"],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )


def test_a_module_may_use_the_interface_of_another(sample: Path) -> None:
    result = lint(sample, "core.projects.tables", "from sample.core.accounts import interface\n")
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize(
    ("below", "above"), [("resource_settings", "users"), ("users", "cost_settings")]
)
def test_a_module_of_the_core_may_not_import_one_of_a_layer_above_it_by_its_interface(
    sample: Path, below: str, above: str
) -> None:
    # The cycle of #2124: the interface is the way the independence contract allows, not this one.
    result = lint(sample, f"core.{below}.interface", f"from sample.core.{above} import interface\n")
    assert result.returncode == 1
    assert f"sample.core.{below} is not allowed to import sample.core.{above}" in result.stdout


def test_two_modules_of_a_same_layer_may_not_import_each_other(sample: Path) -> None:
    result = lint(
        sample, "core.access_roles.interface", "from sample.core.backups import interface\n"
    )
    assert result.returncode == 1
    assert "sample.core.access_roles.interface -> sample.core.backups" in result.stdout


@pytest.mark.parametrize(
    ("importer", "imported_module"),
    [("resource_settings", "users"), ("users", "resource_settings")],
)
def test_a_module_of_the_core_may_not_reach_the_tables_of_another(
    sample: Path, importer: str, imported_module: str
) -> None:
    # Not through its interface: refused whatever the layers say of the two (the second pair is
    # one the layers allow, so that only the independence of the modules refuses it).
    result = lint(
        sample, f"core.{importer}.interface", f"from sample.core.{imported_module} import tables\n"
    )
    assert result.returncode == 1
    assert f"sample.core.{importer}.interface -> sample.core.{imported_module}" in result.stdout


def test_a_module_of_the_core_may_import_one_of_a_layer_below_it_by_its_interface(
    sample: Path,
) -> None:
    result = lint(
        sample, "core.users.interface", "from sample.core.resource_settings import interface\n"
    )
    assert result.returncode == 0, result.stdout


@pytest.mark.requirement("WF-ARC-0010-A")
def test_a_module_that_reads_the_tables_of_another_is_rejected(sample: Path) -> None:
    result = lint(sample, "core.projects.tables", "from sample.core.accounts import tables\n")
    assert result.returncode == 1
    assert "sample.core.projects.tables -> sample.core.accounts.tables" in result.stdout


def test_the_core_may_not_import_the_api(sample: Path) -> None:
    result = lint(sample, "core.projects.tables", "import sample.api\n")
    assert result.returncode == 1


def test_the_api_may_not_import_the_worker(sample: Path) -> None:
    result = lint(sample, "api.__init__", "import sample.worker\n")
    assert result.returncode == 1


def test_the_platform_may_be_imported_by_the_core_the_api_and_the_worker(sample: Path) -> None:
    for module in ("core.projects.tables", "api.__init__", "worker.__init__"):
        result = lint(sample, module, "import sample.platform\n")
        assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("imported", ["core.projects.interface", "api", "worker"])
def test_the_platform_may_not_import_the_core_the_api_or_the_worker(
    sample: Path, imported: str
) -> None:
    result = lint(sample, "platform.__init__", f"import sample.{imported}\n")
    assert result.returncode == 1
    assert f"sample.platform -> sample.{imported}" in result.stdout


@pytest.mark.requirement("WF-ARC-0010-A")
def test_the_core_may_not_import_the_schema(sample: Path) -> None:
    result = lint(sample, "core.projects.tables", "from sample import schema\n")
    assert result.returncode == 1
    assert "sample.core.projects.tables -> sample.schema" in result.stdout


def test_the_entry_points_may_import_the_schema_which_may_import_the_core(sample: Path) -> None:
    (sample / "sample" / "schema.py").write_text("from sample.core.projects import tables\n")
    result = lint(sample, "api.__init__", "from sample import schema\n")
    assert result.returncode == 0, result.stdout


def test_the_core_may_not_import_the_migrations(sample: Path) -> None:
    result = lint(sample, "core.projects.tables", "from sample import migrations\n")
    assert result.returncode == 1


def test_the_bootstrap_may_apply_the_migrations(sample: Path) -> None:
    # The bootstrap applies the migrations, which the API may not import (US-0420).
    imports = "import sample.migrations\nimport sample.api\nimport sample.core.accounts.interface\n"
    result = lint(sample, "bootstrap", imports)
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("module", ["api.__init__", "migrations.__init__", "core.projects.tables"])
def test_nothing_imports_the_bootstrap(sample: Path, module: str) -> None:
    result = lint(sample, module, "import sample.bootstrap\n")
    assert result.returncode == 1
    assert f"sample.{module.removesuffix('.__init__')} -> sample.bootstrap" in result.stdout


def test_the_service_of_the_restoration_may_apply_the_migrations_and_run_as_the_worker(
    sample: Path,
) -> None:
    # The restoration applies the migrations and runs as the worker does (#953).
    imports = (
        "import sample.migrations\nimport sample.worker\nimport sample.core.accounts.interface\n"
    )
    result = lint(sample, "restore.__init__", imports)
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize("module", ["worker.__init__", "api.__init__", "core.projects.tables"])
def test_nothing_imports_the_service_of_the_restoration(sample: Path, module: str) -> None:
    result = lint(sample, module, "import sample.restore\n")
    assert result.returncode == 1
    assert f"sample.{module.removesuffix('.__init__')} -> sample.restore" in result.stdout


@pytest.mark.requirement("WF-ARC-0010-A")
def test_a_module_may_use_an_interface_in_a_package_but_none_of_its_files(sample: Path) -> None:
    through = lint(
        sample, "core.projects.tables", "from sample.core.settings.interface import RATE\n"
    )
    assert through.returncode == 0, through.stdout
    beside = "from sample.core.settings.interface.rates import RATE\n"
    result = lint(sample, "core.projects.tables", beside)
    assert result.returncode == 1
    assert "sample.core.projects.tables -> sample.core.settings.interface.rates" in result.stdout


@pytest.mark.requirement("WF-QUA-0040-A")
@pytest.mark.parametrize("module", ["bootstrap", "api.__init__", "core.projects.tables"])
def test_nothing_imports_the_loader_of_the_witness(sample: Path, module: str) -> None:
    result = lint(sample, module, "import sample.witness\n")
    assert result.returncode == 1
    assert f"sample.{module.removesuffix('.__init__')} -> sample.witness" in result.stdout


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_loader_of_the_witness_may_run_the_bootstrap_and_write_through_the_interfaces(
    sample: Path,
) -> None:
    # It passes on what is not its own to the bootstrap, and reads the models of the contract.
    imports = "import sample.bootstrap\nimport sample.api\nimport sample.core.accounts.interface\n"
    result = lint(sample, "witness.__init__", imports)
    assert result.returncode == 0, result.stdout


@pytest.mark.requirement("WF-ARC-0010-A")
@pytest.mark.parametrize(("module", "files"), REFERENCE_INTERFACES.items())
def test_each_module_of_the_reference_offers_its_interface_as_a_package_of_one_file_per_object(
    module: str, files: set[str]
) -> None:
    interface = importlib.import_module(f"waterfall.core.{module}.interface")
    held = {info.name for info in pkgutil.iter_modules(interface.__path__)}
    assert held == files


@pytest.mark.requirement("WF-ARC-0010-A")
@pytest.mark.parametrize(("module", "files"), PROJECT_INTERFACES.items())
def test_the_projects_and_the_revisions_offer_their_interface_as_a_package_by_subject(
    module: str, files: set[str]
) -> None:
    interface = importlib.import_module(f"waterfall.core.{module}.interface")
    held = {info.name for info in pkgutil.iter_modules(interface.__path__)}
    assert held == files
    offered = set(interface.__all__)
    assert DESIGNED[module] <= offered
    # Each name is the one its file declares, re-exported: a function of a file alone, or of the
    # package alone, would be another.
    for name in offered:
        declared = getattr(interface, name)
        source = getattr(declared, "__module__", f"{interface.__name__}.?")
        assert source.rsplit(".", 1)[0] == interface.__name__, name


def own_names(interface: object, prefix: str) -> set[str]:
    """Name what a package offers of its own files: a name whose object one of them declares."""
    return {
        name
        for name, value in vars(interface).items()
        if not name.startswith("_") and str(getattr(value, "__module__", "")).startswith(prefix)
    }


@pytest.mark.requirement("WF-ARC-0010-A")
@pytest.mark.parametrize(("module", "files"), PLANNING_INTERFACES.items())
def test_the_planning_the_history_and_the_exchanges_offer_every_function_of_their_files(
    module: str, files: set[str]
) -> None:
    # The socle lays every file and re-exports every function of each (EP-06, "Modules"): a story
    # fills the body of its own and never opens the ``__init__`` another story fills beside it.
    interface = importlib.import_module(f"waterfall.core.{module}.interface")
    held = {info.name for info in pkgutil.iter_modules(interface.__path__)}
    assert held == files
    prefix = f"{interface.__name__}."
    offered = own_names(interface, prefix)
    assert DESIGNED[module] <= offered
    declared = {
        name
        for file in files
        for name, value in vars(importlib.import_module(f"{prefix}{file}")).items()
        if not name.startswith("_")
        and inspect.isfunction(value)
        and value.__module__ == f"{prefix}{file}"
    }
    assert declared - offered == set()


STUB_STATEMENTS = 2
# The functions the design leaves silent until a story fills them: each gives a documented result,
# without effect, and a caller relies on it — a stub in their place would refuse every caller.
SILENT = {
    "projects": {"no_background_task_running", "advance"},
    "revisions": {"revision_has_tasks_and_lines", "compute_indicators"},
    # What a registry of EP-04 or EP-05 calls before the story that fills it.
    "planning": {
        "copy_nodes",
        "delete_nodes",
        "tasks_left_idle",
        "reschedule_current_structures",
        "work_breakdown_item_cited",
        "detach_work_breakdown_item",
    },
    "history": {"close_history"},
}


def names_not_implemented(node: ast.expr | None) -> bool:
    """Tell whether an expression names ``NotImplementedError``, bare or as ``builtins`` has it."""
    if isinstance(node, ast.Name):
        return node.id == "NotImplementedError"
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "NotImplementedError"
        and isinstance(node.value, ast.Name)
        and node.value.id == "builtins"
    )


def stub_message(function: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """Give the message of a stub — a docstring at most, ``msg = "..."``, then the raise — or None.

    The raise names ``NotImplementedError`` bare: any other form is no stub.
    """
    body = list(function.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body.pop(0)
    if len(body) != STUB_STATEMENTS:
        return None
    assign, raised = body
    if not (
        isinstance(assign, ast.Assign)
        and len(assign.targets) == 1
        and isinstance(assign.targets[0], ast.Name)
        and assign.targets[0].id == "msg"
        and isinstance(assign.value, ast.Constant)
        and isinstance(assign.value.value, str)
        and isinstance(raised, ast.Raise)
        and isinstance(raised.exc, ast.Call)
        and isinstance(raised.exc.func, ast.Name)
        and raised.exc.func.id == "NotImplementedError"
        and len(raised.exc.args) == 1
        and isinstance(raised.exc.args[0], ast.Name)
        and raised.exc.args[0].id == "msg"
        and not raised.exc.keywords
    ):
        return None
    return assign.value.value


def functions(tree: ast.AST) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """List every function of a tree, nested ones and ``async`` ones included."""
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]


def refuses(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Tell whether a function's own body (not a nested one's) raises NotImplementedError."""
    pending: list[ast.AST] = list(function.body)
    while pending:
        node = pending.pop()
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            continue
        if isinstance(node, ast.Raise):
            target = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            if names_not_implemented(target):
                return True
        pending.extend(ast.iter_child_nodes(node))
    return False


def malformed_stubs(source: str) -> list[str]:
    """Name the functions of a source that raise NotImplementedError without being a stub."""
    tree = ast.parse(source)
    return [f.name for f in functions(tree) if refuses(f) and stub_message(f) is None]


def interface_sources() -> list[tuple[str, str]]:
    """List (file, source) of each file of the interfaces in a package, subpackages included.

    Each file is named by its path under the interface, after its module: two files of the same
    name in two subpackages are two.
    """
    found: list[tuple[str, str]] = []
    for module in (*PROJECT_INTERFACES, *PLANNING_INTERFACES):
        interface = importlib.import_module(f"waterfall.core.{module}.interface")
        for directory in interface.__path__:
            found.extend(
                (
                    f"{module}/{path.relative_to(directory).as_posix()}",
                    path.read_text(encoding="utf-8"),
                )
                for path in sorted(Path(directory).rglob("*.py"))
            )
    return found


def stubs() -> list[tuple[str, str, str]]:
    """List (file, function, message) of each stub the files of the interfaces declare.

    Read from the code, not from a list: a function a story fills leaves it alone. The silent ones
    (the design gives them a documented result without effect) are not stubs.
    """
    return [
        (file, node.name, message)
        for file, source in interface_sources()
        for node in functions(ast.parse(source))
        if (message := stub_message(node)) is not None
    ]


@pytest.mark.requirement("WF-ARC-0010-A")
def test_no_function_of_the_interfaces_raises_not_implemented_without_being_a_stub() -> None:
    # True whatever the number of stubs left, none included: the sweep and `stub_message` agree.
    assert [(f, m) for f, s in interface_sources() for m in malformed_stubs(s)] == []


@pytest.mark.requirement("WF-ARC-0010-A")
@pytest.mark.parametrize(
    "source",
    [
        "def f():\n    raise NotImplementedError('f is filled by US-0001')\n",
        "async def f():\n    msg = 1\n    raise NotImplementedError(msg)\n",
        "async def f():\n    raise NotImplementedError\n",
        "def g():\n    def f():\n        raise NotImplementedError('x')\n    return f\n",
        (
            "class C:\n    def f(self):\n        msg = 'x'\n        print(msg)\n"
            "        raise NotImplementedError(msg)\n"
        ),
        # Named through ``builtins``, the refusal is one all the same, and no stub.
        "def f():\n    msg = 'x'\n    raise builtins.NotImplementedError(msg)\n",
        "def f():\n    msg = 'x'\n    raise NotImplementedError(msg, msg)\n",
    ],
)
def test_the_sweep_of_the_stubs_rejects_a_malformed_or_async_or_nested_stub(source: str) -> None:
    assert malformed_stubs(source) == ["f"]


@pytest.mark.requirement("WF-ARC-0010-A")
@pytest.mark.parametrize(
    "source",
    [
        "async def f():\n    msg = 'f is filled by US-0001'\n    raise NotImplementedError(msg)\n",
        (
            "def g():\n    def f():\n        msg = 'f is filled by US-0001'\n"
            "        raise NotImplementedError(msg)\n"
        ),
    ],
)
def test_the_sweep_of_the_stubs_accepts_a_well_formed_stub_async_or_nested(source: str) -> None:
    assert malformed_stubs(source) == []


@pytest.mark.requirement("WF-ARC-0010-A")
def test_a_stub_of_an_interface_refuses_naming_the_story_that_fills_it() -> None:
    # A caller that reaches a function before its story fills it must fail, not read or write
    # nothing: a green test would hide a refusal (`revision_draft`) that does not exist yet. One
    # test over them all, not one per stub: once the last is filled, it still runs, and passes.
    assert [
        (file, message)
        for file, name, message in stubs()
        if not re.fullmatch(rf"{name} is filled by US-\d{{4}}(/L\d+)?", message)
    ] == []


@pytest.mark.requirement("WF-ARC-0010-A")
def test_the_functions_the_design_leaves_silent_do_not_refuse() -> None:
    # Made a stub by mistake, one of them would refuse a caller that relies on its result: the
    # marking, the designation of the reference, a transition of the cycle of life. Filled by
    # their story, they still do not refuse; renamed or removed, this list must follow.
    declared = {
        module: {
            node.name: node
            for file, source in interface_sources()
            if file.startswith(f"{module}/")
            for node in functions(ast.parse(source))
        }
        for module in SILENT
    }
    assert {module: names & set(declared[module]) for module, names in SILENT.items()} == SILENT
    assert [
        name
        for module, names in SILENT.items()
        for name in names
        if refuses(declared[module][name])
    ] == []


def imported(statement: str) -> str:
    """Run a statement in a fresh interpreter, and give what it prints."""
    done = subprocess.run(
        [sys.executable, "-c", statement], capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


@pytest.mark.requirement("WF-ARC-0010-A")
def test_importing_a_module_of_the_core_declares_the_tables_of_no_other() -> None:
    # The tables of every module are declared together by ``waterfall.schema``, which the entry
    # points import: the core itself imports no module's tables by way of another.
    statement = (
        "import sys, waterfall.core.users.interface;"
        "print(sorted(m for m in sys.modules if m.endswith('.tables')))"
    )
    # An account is attached to a node of the resource settings: it asks that module, by its
    # interface, which brings its own tables — and theirs alone, the resource settings reading no
    # other module (#2109, #2114). Exactly the tables of the two modules, no fewer, no more.
    users, resources = "waterfall.core.users.tables", "waterfall.core.resource_settings.tables"
    assert set(ast.literal_eval(imported(statement))) == {users, resources}
    # The package of the core, alone, holds the tables of none.
    statement = "import sys, waterfall.core; print(any(m.endswith('.tables') for m in sys.modules))"
    assert imported(statement) == "False"


def interfaces() -> list[str]:
    """Name the interface of every module of the core, as a package or as a file."""
    core = Path(importlib.import_module("waterfall.core").__file__ or "").parent
    return sorted(
        f"waterfall.core.{module.name}.interface"
        for module in pkgutil.iter_modules([str(core)])
        if (core / module.name / "interface.py").exists()
        or (core / module.name / "interface" / "__init__.py").exists()
    )


@pytest.mark.requirement("WF-ARC-0010-A")
def test_the_resource_settings_import_nothing_of_the_cost_settings_which_read_them() -> None:
    # The cost settings ask the resource settings what binds a category (``category_has_roles``);
    # the roles are told of their category by their caller: no cycle between the two.
    statement = (
        "import sys, waterfall.core.resource_settings.interface;"
        "print(sorted(m for m in sys.modules if m.startswith('waterfall.core.cost_settings')))"
    )
    assert ast.literal_eval(imported(statement)) == []


@pytest.mark.requirement("WF-ARC-0010-A")
@pytest.mark.parametrize("interface", interfaces())
def test_the_interface_of_each_module_of_the_core_is_imported_alone(interface: str) -> None:
    # In a fresh interpreter, first: a cycle between two interfaces fails the import of one.
    assert imported(f"import {interface}; print('imported')") == "imported"


@pytest.mark.requirement("WF-ARC-0010-A")
def test_the_schema_declares_the_tables_of_every_module_and_the_entry_points_import_it() -> None:
    statement = (
        "import waterfall.schema; from waterfall.platform.database import Base;"
        "print(len(Base.metadata.tables))"
    )
    # An entry point alone declares what a foreign key of the reference names (``user_account``).
    entry = (
        "import waterfall.{}, waterfall.platform.database as d;"
        "print('user_account' in d.Base.metadata.tables and 'cost_type' in d.Base.metadata.tables)"
    )
    assert int(imported(statement)) >= 10
    for module in ("api.app", "worker.main", "bootstrap", "witness.main"):
        assert imported(entry.format(module)) == "True", module
    # The environment of the migrations runs on import, against a database: its source is read.
    env = Path(__file__).resolve().parents[1] / "src/waterfall/migrations/env.py"
    calls = [
        node
        for node in ast.walk(ast.parse(env.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "declared"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "schema"
    ]
    assert calls


def test_the_package_itself_keeps_its_contracts() -> None:
    result = subprocess.run(
        ["lint-imports", "--no-cache"],
        cwd=PROJECT.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout


# A code, a condition or a set of states several modules judge by, and the one module that declares
# it: the others import it from that module (its interface, for a module of the core), never copy
# it (#2471, #2555).
SHARED = {
    "STATE_FORBIDS_OPERATION": "platform/errors.py",
    "BEFORE_IN_PROGRESS": "core/projects/commands.py",
    "NO_BACKGROUND_TASK_RUNNING": "core/projects/commands.py",
    "PROJECT_BEFORE_IN_PROGRESS": "core/projects/commands.py",
    "PROJECT_NOT_TERMINAL": "core/projects/commands.py",
    "TERMINAL": "core/projects/commands.py",
}


def _shared_names_declared(source: str) -> set[str]:
    """The shared names a module declares at its top level, plainly or with an annotation."""
    names: set[str] = set()
    for statement in ast.parse(source).body:
        if isinstance(statement, ast.Assign):
            targets = statement.targets
        elif isinstance(statement, ast.AnnAssign):
            targets = [statement.target]
        else:
            targets = []
        names |= {t.id for t in targets if isinstance(t, ast.Name) and t.id in SHARED}
    return names


def test_a_copy_of_a_shared_name_is_seen_annotated_or_not() -> None:
    # A detail of the code, which reprises no Vérif: it cites no requirement.
    assert _shared_names_declared('TERMINAL = ("lost",)') == {"TERMINAL"}
    assert _shared_names_declared('TERMINAL: Final = ("lost",)') == {"TERMINAL"}
    assert _shared_names_declared("from x import TERMINAL\nOTHER = 1") == set()


def test_a_name_several_modules_judge_by_is_declared_by_the_one_that_owns_it() -> None:
    # A detail of the code, which reprises no Vérif: it cites no requirement.
    package = Path(cast("str", importlib.import_module("waterfall").__file__)).parent
    declared: dict[str, set[str]] = {name: set() for name in SHARED}
    for path in sorted(package.rglob("*.py")):
        for name in _shared_names_declared(path.read_text(encoding="utf-8")):
            declared[name].add(path.relative_to(package).as_posix())
    assert declared == {name: {owner} for name, owner in SHARED.items()}
