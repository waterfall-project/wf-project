# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The controls of the chain that the merge queue caught late (US-1320).

Two things a quick check could see and did not: a module of the core that the contract of the
import-linter does not order (#2124), and an image of the Compose of service that a recipe of the
Makefile starts without building (#2083, #2218). Both are read from the files, never declared a
second time; the tools import nothing beyond the standard library and the YAML of the repository.
"""

import json
import os
import re
import subprocess
import tomllib
from typing import Any

import pytest

from wftools import REPOSITORY

CORE = REPOSITORY / "backend" / "src" / "waterfall" / "core"
COMPOSE = REPOSITORY / "deploy" / "compose" / "compose.service.yaml"
# The recipes that start the services of the service platform, and so must build their images.
RECIPES = ("service-up", "service-install", "e2e-service")


def ordered_modules() -> set[str]:
    """Name the modules of the core that the layers of the contract `layers` hold."""
    contracts = tomllib.loads((REPOSITORY / "backend" / "pyproject.toml").read_text("utf-8"))[
        "tool"
    ]["importlinter"]["contracts"]
    layered = [
        contract
        for contract in contracts
        if contract["type"] == "layers" and contract.get("containers") == ["waterfall.core"]
    ]
    assert len(layered) == 1, "one contract `layers` has `waterfall.core` for its container"
    return {name.strip() for layer in layered[0]["layers"] for name in layer.split("|")}


def test_every_package_of_the_core_is_ordered_by_the_contract_of_the_layers() -> None:
    packages = {path.parent.name for path in CORE.glob("*/__init__.py")}
    missing = sorted(packages - ordered_modules())
    assert not missing, (
        f"{missing} are not in the `layers` of the import-linter contract of"
        " backend/pyproject.toml:"
        " put each in the layer its imports require (docs/dev/python.md)"
    )


def test_every_layer_of_the_contract_names_a_package_of_the_core() -> None:
    packages = {path.parent.name for path in CORE.glob("*/__init__.py")}
    assert sorted(ordered_modules() - packages) == []


def recipe(makefile: str, target: str) -> list[str]:
    """Give the lines of the recipe of a target, those that continue one joined.

    A target also has lines of variables (`e2e-service: export …`) that no recipe follows: the
    first line of the target that one follows is the rule.
    """
    lines = makefile.splitlines()
    for start, line in enumerate(lines):
        if not re.match(rf"{re.escape(target)}:(?!=)", line):
            continue
        found: list[str] = []
        for each in lines[start + 1 :]:
            if not each.startswith("\t"):
                if found or each.strip() != "":
                    break
                continue
            if found and found[-1].endswith("\\"):
                found[-1] = found[-1][:-1] + " " + each.strip()
            else:
                found.append(each.strip())
        if found:
            return found
    pytest.fail(f"the Makefile has no recipe for {target}")


def stand_ins(makefile: str) -> dict[str, str]:
    """Read the stand-in values `lint-compose` gives the secrets of the Compose of service."""
    found: dict[str, str] = {}
    for line in recipe(makefile, "lint-compose"):
        found.update(
            re.findall(r"\b([A-Z][A-Z0-9_]*)=(\S+)", line.split("$(COMPOSE_SERVICE_FILE)")[0])
        )
        if "$(COMPOSE_SERVICE_FILE)" in line:
            break
    return found


def built_when_started(config: dict[str, Any], makefile: str) -> set[str]:
    """Name the services the recipes build: named by `up --build` or `build`, or built with them.

    A service that `up --build` starts as a dependency is built with it, and one that shares the
    image of a built service is built by it.
    """
    services: dict[str, Any] = config["services"]
    named: set[str] = set()
    building: set[str] = set()
    for target in RECIPES:
        for line in recipe(makefile, target):
            # Only the command that starts or builds names its services: what follows a `||`, a
            # `&&`, a `;` or a pipe (a `logs`, a message) is another command.
            for command in re.split(r"\|\||&&|;|\|", line):
                words = command.split()
                for verb in ("up --build", "build"):
                    if f" {verb} " in f" {command} ":
                        names = {word for word in words if word in services}
                        named |= names
                        # `--no-deps` leaves the dependencies of a service as they are.
                        if verb == "up --build" and "--no-deps" not in words:
                            building |= names
    pending = list(building)
    while pending:
        for dependency in services[pending.pop()].get("depends_on", {}):
            if dependency not in building:
                building.add(dependency)
                pending.append(dependency)
    built = named | building
    images = {services[name]["image"] for name in built if "image" in services[name]}
    return built | {name for name, each in services.items() if each.get("image") in images}


def not_built(config: dict[str, Any], makefile: str) -> list[str]:
    """Name the services that declare a `build` and that no recipe builds."""
    declared = {name for name, each in config["services"].items() if "build" in each}
    return sorted(declared - built_when_started(config, makefile))


def test_every_service_that_builds_is_built_by_the_recipes_that_start_it() -> None:
    """Read the Compose of service as Docker shows it: the test needs Docker.

    The runner of the family `repo` has it; the guide does not say so yet (#2304).
    """
    makefile = (REPOSITORY / "Makefile").read_text("utf-8")
    prism = re.search(
        r'^\s*"@stoplight/prism-cli":\s*"([^"]+)"',
        (REPOSITORY / "frontend/package.json").read_text("utf-8"),
        re.MULTILINE,
    )
    assert prism is not None
    shown = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(COMPOSE),
            "--profile",
            "e2e",
            "--profile",
            "install",
            "--profile",
            "witness",
            "config",
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, **stand_ins(makefile), "PRISM_VERSION": prism[1]},
    )
    assert shown.returncode == 0, shown.stderr
    config = json.loads(shown.stdout)
    assert any("build" in each for each in config["services"].values())
    assert not_built(config, makefile) == [], (
        "these services declare a build and no recipe of `service-up`, `service-install` or"
        " `e2e-service` builds them (`up --build` or `build`): a local start would run a stale"
        " image"
    )


DRAFT_MAKEFILE = (
    "service-up:\n"
    "\t@$(COMPOSE_SERVICE) up --build --detach --wait db api\n"
    "\t@$(COMPOSE_SERVICE) up --detach --wait restore\n"
    "\n"
    "service-install:\n"
    "\t@$(COMPOSE_SERVICE) build --quiet install\n"
    "\n"
    "e2e-service:\n"
    "\t@true\n"
    "\n"
    "other:\n"
    "\t@$(COMPOSE_SERVICE) build restore\n"
)
DRAFT_COMPOSE: dict[str, Any] = {
    "services": {
        "db": {"image": "postgres"},
        "migrate": {"build": {}, "depends_on": {"db": {}}},
        "api": {"build": {}, "depends_on": {"migrate": {}}},
        "install": {"build": {}},
        "restore": {"build": {}},
        "realm": {"build": {}, "image": "shared"},
        "keycloak": {"build": {}, "image": "shared"},
    }
}


def test_a_service_that_builds_and_starts_unbuilt_is_found_by_its_name() -> None:
    # `restore` is only started, and named by a recipe that is not one of the three; `migrate`
    # is built with `api` that depends on it, `realm` with `keycloak` that shares its image.
    draft = DRAFT_MAKEFILE.replace("db api", "db api keycloak")
    assert not_built(DRAFT_COMPOSE, draft) == ["restore"]
    assert (
        not_built(DRAFT_COMPOSE, draft.replace("up --detach --wait restore", "up --build restore"))
        == []
    )


def test_only_the_command_that_starts_names_the_services_it_builds() -> None:
    # `--no-deps` builds `api` and not `migrate`, which it depends on; a service named after a
    # `||` (the logs of a failed start) is not built by it.
    draft = (
        "service-up:\n"
        "\t@$(COMPOSE_SERVICE) up --build --no-deps --detach api || { \\\n"
        "\t  $(COMPOSE_SERVICE) logs restore; exit 1; }\n"
        "\n"
        "service-install:\n"
        "\t@true\n"
        "\n"
        "e2e-service:\n"
        "\t@true\n"
    )
    assert built_when_started(DRAFT_COMPOSE, draft) == {"api"}


def make_variable(name: str) -> str:
    """Return the value `make` gives a variable of the Makefile."""
    shown = subprocess.run(
        ["make", "-pn", "help"], check=True, capture_output=True, text=True, cwd=REPOSITORY
    ).stdout
    found = re.search(rf"^{name} :?= (.*)$", shown, re.MULTILINE)
    assert found is not None, name
    return found[1]


def test_redocly_and_prism_are_pinned_exactly_and_the_makefile_reads_the_pin() -> None:
    """Pin the two tools of the contract to a version, the one that Compose names too (#2913)."""
    package = json.loads((REPOSITORY / "frontend/package.json").read_text("utf-8"))
    pinned = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
    for name in ("@redocly/cli", "@stoplight/prism-cli"):
        assert re.fullmatch(r"\d+\.\d+\.\d+", pinned[name]), f"{name} is not an exact version"
    assert make_variable("PRISM_VERSION") == pinned["@stoplight/prism-cli"]


def test_a_lock_file_newer_than_the_installation_installs_the_front_again() -> None:
    """Install before running the tools of the contract when the lock file was raised (#2913)."""
    witness = REPOSITORY / "frontend/node_modules/.modules.yaml"
    if not witness.exists():
        pytest.skip("the front is not installed: the witness is missing, and the install is due")
    newer = subprocess.run(
        ["make", "-n", "-W", "frontend/pnpm-lock.yaml", "lint-openapi"],
        check=True,
        capture_output=True,
        text=True,
        cwd=REPOSITORY,
    ).stdout
    assert "pnpm install --frozen-lockfile" in newer
    older = subprocess.run(
        [
            "make",
            "-n",
            "-o",
            "frontend/pnpm-lock.yaml",
            "-o",
            "frontend/package.json",
            "lint-openapi",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=REPOSITORY,
    ).stdout
    assert "pnpm install" not in older


def test_the_download_of_pandoc_is_cut_by_a_stalled_transfer_and_by_a_total_time() -> None:
    """Bound the download of pandoc by the stall of a transfer and by four minutes in all."""
    workflow = (REPOSITORY / ".github/workflows/spec.yml").read_text("utf-8")
    assert re.search(r"timeout 240 curl\b[^|]*--speed-limit \d+ --speed-time \d+", workflow)
    assert "--max-time" not in workflow
