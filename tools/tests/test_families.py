# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Each family wakes on what its checks run: its workflow, its local actions, its tools.

A family of checks runs a target of the Makefile in its workflow, and whatever the workflow and the
harness of Playwright start besides; those targets run modules of wftools and scripts that import
them. Each module and each script must wake the family, or a pull request could weaken a check
without the chain running it (tools/paths.toml). Read from the Makefile, the workflows and the
imports, never declared a second time.
"""

import ast
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from wftools import REPOSITORY, paths

if TYPE_CHECKING:
    from collections.abc import Iterator

WORKFLOWS = REPOSITORY / ".github" / "workflows"
TOOLS = REPOSITORY / "tools" / "src" / "wftools"
# The harness of the end-to-end paths starts the fake back by the Makefile (`make -C .. mock`).
HARNESS = "frontend/playwright.config.ts"


def makefile() -> tuple[str, dict[str, str], dict[str, tuple[list[str], list[str]]]]:
    """Return the Makefile, its continued lines joined, its variables, and each rule.

    A rule is its prerequisites and its recipe; the text is given for what is read from no rule.
    """
    text = re.sub(r"\\\n", " ", (REPOSITORY / "Makefile").read_text(encoding="utf-8"))
    variables: dict[str, str] = {}
    rules: dict[str, tuple[list[str], list[str]]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("\t"):
            if current is not None:
                rules[current][1].append(line)
            continue
        current = None
        if defined := re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:?=\s*(.*)$", line):
            variables[defined.group(1)] = defined.group(2)
        elif (rule := re.match(r"^([a-z][a-z0-9-]*):([^=#]*)(?:#.*)?$", line)) and not re.match(
            r"\s*export\b", rule.group(2)
        ):
            name = rule.group(1)
            rules.setdefault(name, ([], []))[0].extend(rule.group(2).split())
            current = name
    return text, variables, rules


def expand(text: str, variables: dict[str, str]) -> str:
    """Replace the variables of the Makefile a text names, as long as one is left to replace."""
    for _ in range(5):
        text = re.sub(
            r"\$\(([A-Za-z_][A-Za-z0-9_-]*)\)", lambda m: variables.get(m.group(1), ""), text
        )
    return text


def _recipes(rules: dict[str, tuple[list[str], list[str]]], targets: set[str]) -> str:
    """Return the recipes of the targets, joined."""
    return "\n".join(line for target in sorted(targets) for line in rules[target][1])


def reached(targets: list[str]) -> tuple[set[str], set[str]]:
    """Return the modules of wftools and the scripts the targets run, their prerequisites included.

    Both tiers are counted: the prerequisites of `full-else` and `full-only` alike.
    """
    text, variables, rules = makefile()
    modules: set[str] = set()
    scripts: set[str] = set()
    pending, seen = list(targets), set[str]()
    while pending:
        target = pending.pop()
        if target in seen or target not in rules:
            continue
        seen.add(target)
        prerequisites, recipe = rules[target]
        pending += re.findall(r"[a-z][a-z0-9-]+", " ".join(prerequisites))
        for line in recipe:
            modules.update(re.findall(r"\$\(WFTOOLS\)\.(\w+)", line))
            for called in re.findall(r"\$\(MAKE\)([^;&|]*)", line):
                pending += re.findall(r"[a-z][a-z0-9-]+", called)
            expanded = expand(line, {**variables, "CURDIR": "."})
            scripts.update(re.findall(r"python3? \.?/?([\w./-]+\.py)", expanded))
    # What the launcher runs is run by the Makefile too: `launch.py slots` runs slots.py (US-2450).
    launched = {
        f"tools/src/wftools/{tool}.py"
        for tool in re.findall(r"launch\.py (\w+)", expand(_recipes(rules, seen), variables))
    }
    # A target given its variables by `slot-export` asks the register of the slots for them
    # (`launch.py slots which --variables`), which is no line of a recipe.
    for names in re.findall(r"^\$\(call slot-export,([^,]+),", text, flags=re.MULTILINE):
        if seen & set(names.split()):
            launched |= {"tools/src/wftools/launch.py", "tools/src/wftools/slots.py"}
    return modules, scripts | launched


def imported(path: Path) -> Iterator[str]:
    """Yield the modules of wftools a Python file imports."""
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("wftools"):
            if node.module == "wftools":
                yield from (alias.name for alias in node.names)
            else:
                yield node.module.split(".")[1]
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("wftools."):
                    yield alias.name.split(".")[1]


def closure(modules: set[str], scripts: set[str]) -> set[str]:
    """Return the files of wftools the modules and the scripts import, themselves included."""
    pending = [*modules, *(name for script in scripts for name in imported(REPOSITORY / script))]
    found: set[str] = set()
    while pending:
        name = pending.pop()
        path = TOOLS / f"{name}.py"
        if name in found or not path.exists():
            continue
        found.add(name)
        pending += imported(path)
    return {f"tools/src/wftools/{name}.py" for name in found}


def workflow(path: Path) -> dict[Any, Any]:
    """Read a workflow."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def families_of_the_chain() -> dict[str, list[str]]:
    """Return, by family, the workflows the chain runs it with (ci.yml, by the outputs it reads)."""
    found: dict[str, list[str]] = {}
    for job in workflow(WORKFLOWS / "ci.yml")["jobs"].values():
        uses = job.get("uses", "")
        if not uses.startswith("./.github/workflows/"):
            continue
        woken = re.search(r"outputs\.([a-z-]+) == 'true'", job.get("if", ""))
        family = woken.group(1) if woken else Path(uses).stem
        found.setdefault(family, []).append(uses.removeprefix("./"))
    return found


def entries(family: paths.Family) -> list[str]:
    """Return the targets a family runs: its own, its workflows', and its harness's."""
    targets = [family.target]
    for name in families_of_the_chain().get(family.name, []):
        text = (REPOSITORY / name).read_text(encoding="utf-8")
        targets += re.findall(r"\bmake ([a-z][a-z0-9-]*)", text)
    if family.always or family.is_touched_by(HARNESS):
        text = (REPOSITORY / HARNESS).read_text(encoding="utf-8")
        targets += re.findall(r"make -C \.\. ([a-z][a-z0-9-]*)", text)
    return targets


def wakes(declaration: paths.Declaration, family: paths.Family, path: str) -> bool:
    """Tell whether a change of the path runs the family."""
    return family in declaration.touched([path])


@pytest.mark.story("US-2480")
def test_each_family_wakes_on_the_tools_its_checks_run() -> None:
    declaration = paths.read()
    missing: list[str] = []
    for family in declaration.families:
        modules, scripts = reached(entries(family))
        found = sorted(closure(modules, scripts) | scripts)
        missing += [
            f"{family.name}: {path}" for path in found if not wakes(declaration, family, path)
        ]
    assert missing == []


READ_ONLY_MOUNT = re.compile(
    r"^\s*- (\.{1,2}/[^:\s]+):[^:\s]+:(?:[^:\s]*,)?ro\b[^\n]*$", re.MULTILINE
)


def read_only(text: str) -> list[str]:
    """Return what a Compose file mounts read-only from a relative path, `ro` at any place."""
    return READ_ONLY_MOUNT.findall(text)


def mounted() -> list[str]:
    """Return what compose.service.yaml mounts read-only from the repository."""
    compose = REPOSITORY / "deploy" / "compose"
    text = (compose / "compose.service.yaml").read_text(encoding="utf-8")
    return sorted(
        (compose / name).resolve().relative_to(REPOSITORY.resolve()).as_posix()
        for name in read_only(text)
    )


@pytest.mark.story("US-2800")
def test_a_mount_is_read_only_whatever_the_place_of_ro_in_its_options() -> None:
    # [US-2800] #3911: `ro` leads the options, follows another, or is the one; a mount that is
    # writable, or only named `rotate`, is not taken.
    text = """
    volumes:
      - ./a.sql:/a.sql:ro
      - ./b.sql:/b.sql:z,ro
      - ../c.sql:/c.sql:delegated,ro
      - ./d.sql:/d.sql:ro,z
      - ./e.sql:/e.sql:rw
      - ./f.sql:/f.sql:rotate
      - data:/var/lib:ro
    """
    assert read_only(text) == ["./a.sql", "./b.sql", "../c.sql", "./d.sql"]


@pytest.mark.story("US-2480")
def test_what_the_service_platform_mounts_wakes_a_family_that_starts_it() -> None:
    declaration = paths.read()
    callers = [
        family
        for family in declaration.families
        if "deploy/compose/compose.service.yaml" in family.paths
    ]
    assert callers
    missing = [
        path
        for path in mounted()
        if not any(wakes(declaration, family, path) for family in callers)
    ]
    assert missing == []


@pytest.mark.story("US-2480")
def test_each_family_wakes_on_its_workflows_and_the_local_actions_they_take() -> None:
    declaration = paths.read()
    missing: list[str] = []
    for family in declaration.families:
        for name in families_of_the_chain().get(family.name, []):
            taken = [name]
            for job in workflow(REPOSITORY / name)["jobs"].values():
                taken += [
                    step["uses"].removeprefix("./") + "/action.yml"
                    for step in job.get("steps", [])
                    if step.get("uses", "").startswith("./")
                ]
            missing += [
                f"{family.name}: {path}" for path in taken if not wakes(declaration, family, path)
            ]
    assert missing == []


@pytest.mark.story("US-2480")
def test_the_reading_sees_what_it_must() -> None:
    # The guard above is only as good as what it reads: what each family is known to run.
    declaration = paths.read()
    by_name = {family.name: family for family in declaration.families}
    front = closure(*reached(entries(by_name["front"])))
    assert {"tools/src/wftools/catalogs.py", "tools/src/wftools/mock.py"} <= front
    contract = reached(entries(by_name["contract"]))
    assert "docs/api/tools/inventory.py" in contract[1]
    assert "tools/src/wftools/projection.py" in closure(*contract)
    assert "tools/src/wftools/codecoverage.py" in closure(*reached(["check-keycloak"]))
    # The scripts run by `python3 $(CURDIR)/…`, and the tools the launcher runs.
    launched = reached(["check-back"])[1]
    assert {"tools/src/wftools/launch.py", "tools/src/wftools/slots.py"} <= launched
    for target in ("check-service", "check-keycloak", "check-front-image"):
        assert {"tools/src/wftools/launch.py", "tools/src/wftools/slots.py"} <= reached([target])[1]
    assert {
        "deploy/compose/garage.toml",
        "deploy/compose/storage-buckets.sh",
        "fixtures/api",
        "deploy/keycloak/development",
    } <= set(mounted())
    assert families_of_the_chain()["front"] == [
        ".github/workflows/front.yml",
        ".github/workflows/e2e.yml",
    ]
