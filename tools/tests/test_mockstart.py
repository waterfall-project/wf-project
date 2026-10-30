# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the start of the planning of a project without a revision in progress (US-0490/L4).

They try the examples against the contract and the universe they illustrate: the project lists the
generation of the skeleton while it has no revision in progress, judged on the revision its opening
would create, and the opening answers a revision that lists it in turn — not the Vérif of a
requirement, which the screens close (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import json
import re
from typing import Any, cast

from wftools import REPOSITORY, mockwitness
from wftools.mockids import universe
from wftools.mockwitness import fixture

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"
SKELETON = "generate_skeleton"
WITHOUT_TASKS = "main_structure_without_tasks"
ORDER = [
    "project_not_terminal",
    "no_background_task_running",
    WITHOUT_TASKS,
    "may_create_revision",
]
"""The conditions of the command of the project, in the order the contract says them: those of the
state first, as for `declare_risk`, then its own, then the permission to open the revision."""

CREATED, PRICING, WITNESS = universe(3), universe(2), universe(1)
WITH_TASKS = {WITNESS}
"""The projects whose last marked revision bears tasks: the witness, whose revision in progress was
abandoned (`project_without_current_revision`); the offer in pricing and the project created today
have none (`revisions_empty`)."""


def _projects() -> list[tuple[str, Entry]]:
    """Return every reading of a project that lists its commands, with the example it is in."""
    found: list[tuple[str, Entry]] = []

    def walk(name: str, value: object) -> None:
        if isinstance(value, dict):
            entry = cast("Entry", value)
            if {"project_id", "current_revision_id", "available_commands"} <= entry.keys():
                found.append((name, entry))
            for each in entry.values():
                walk(name, each)
        elif isinstance(value, list):
            for each in cast("list[object]", value):
                walk(name, each)

    for path in sorted(mockwitness.FIXTURES.rglob("*.json")):
        walk(path.stem, json.loads(path.read_text(encoding="utf-8"))["value"])
    return found


def _names(project: Entry) -> list[str]:
    return [each["command"] for each in project["available_commands"]]


def _command(project: Entry, command: str) -> Entry:
    [entry] = [each for each in project["available_commands"] if each["command"] == command]
    return entry


def _summary(name: str) -> str:
    path = mockwitness.FIXTURES / f"{name}.json"
    return cast("str", json.loads(path.read_text(encoding="utf-8"))["summary"])


def _flat(text: str) -> str:
    return " ".join(text.split())


def _schema(file: str, name: str) -> str:
    text = (API / "components" / "schemas" / file).read_text(encoding="utf-8")
    return _flat(re.split(r"\n(?=\S)", text.split(f"\n{name}:\n", 1)[1], maxsplit=1)[0])


def test_a_project_without_a_revision_lists_the_skeleton_before_the_imports() -> None:
    # WF-IHM-0090: the project says ahead whether the skeleton would be generated, while it has no
    # revision in progress, to whoever may write the planning — `manage_timelines` is listed
    # under the same permission —, and never once a revision is in progress, which lists it.
    projects = _projects()
    without = [(name, each) for name, each in projects if each["current_revision_id"] is None]
    assert {"project_created", "project_pricing", "project_without_current_revision"} <= {
        name for name, _ in without
    }
    for name, project in projects:
        names = _names(project)
        if project["current_revision_id"] is not None or "manage_timelines" not in names:
            assert SKELETON not in names, name
            continue
        assert names.index(SKELETON) == names.index("import_planning") - 1, name


def test_the_skeleton_of_the_project_is_judged_on_the_revision_its_opening_would_create() -> None:
    # « Elle n'est plus proposée dès que la structure principale comporte une tâche » (Vérif de
    # WF-PRJ-0030), on the copy of the last marked revision that the opening creates (WF-REV-0010).
    seen: set[str] = set()
    for name, project in _projects():
        if SKELETON not in _names(project):
            continue
        entry = _command(project, SKELETON)
        # A terminal project lists no command, the skeleton included (US-0702/L3).
        assert project["state"] != "completed", name
        missing = [WITHOUT_TASKS] if project["project_id"] in WITH_TASKS else []
        assert entry["missing_conditions"] == missing, name
        assert entry["is_available"] is (not missing), name
        seen.add(project["project_id"])
    assert seen == {CREATED, PRICING, WITNESS}
    # The declaration of a risk judges the same revision: a task there, or none.
    for name in ("project_created", "project_pricing", "project_without_current_revision"):
        project = fixture(name)
        declared = _command(project, "declare_risk")["missing_conditions"]
        skeleton = _command(project, SKELETON)["missing_conditions"]
        assert ("at_least_one_task" in declared) is (WITHOUT_TASKS not in skeleton), name


def test_the_opening_answers_the_revision_on_which_the_skeleton_is_generated() -> None:
    # The two writes of the skeleton on the project created today: the revision opened answers
    # `generate_skeleton` available, on a main structure that reads empty, and the skeleton is
    # generated there (`skeleton_generated`), as the contract says the screen chains them.
    created, opened = fixture("project_created"), fixture("revision_created")
    assert (created["project_id"], created["current_revision_id"]) == (CREATED, None)
    assert _command(created, SKELETON) == {
        "command": SKELETON,
        "is_available": True,
        "missing_conditions": [],
    }
    assert _command(created, "create_revision")["is_available"] is True
    assert _command(created, "import_planning")["is_available"] is True
    assert opened["project_id"] == CREATED
    entry = _command(opened, SKELETON)
    assert (entry["is_available"], entry["missing_conditions"]) == (True, [])
    assert fixture("project_revision_opened")["current_revision_id"] == opened["revision_id"]
    assert SKELETON not in _names(fixture("project_revision_opened"))
    assert "revision_without_tasks" in _summary("skeleton_generated")
    assert "offre de démarrer son planning" in _summary("project_created")


def test_the_contract_says_the_command_its_conditions_and_the_writes_it_chains() -> None:
    text = (API / "components" / "schemas" / "projects.yaml").read_text(encoding="utf-8")
    block = text.split("\nProjectCommand:\n", 1)[1].split("\nProjectCommandAvailability:", 1)[0]
    values = block.split("enum:\n", 1)[1].split("description:", 1)[0]
    listed = [line.strip()[2:] for line in values.splitlines() if line.strip().startswith("- ")]
    assert listed.index(SKELETON) == listed.index("import_planning") - 1
    said = _flat(block).split(f"`{SKELETON}` dit d'avance", 1)[1]
    at = [said.find(f"`{each}`") for each in ORDER]
    assert -1 not in at
    assert at == sorted(at)
    for told in ("`planning.write`", "`createRevision`", "`generatePlanningSkeleton`"):
        assert told in said, told
    assert "`ProjectCommand.generate_skeleton`" in _schema("revisions.yaml", "RevisionCommand")
    paths = _flat((API / "paths" / "revisions.yaml").read_text(encoding="utf-8"))
    for operation in ("generatePlanningSkeleton", "createRevision"):
        block = paths.split(f"operationId: {operation} ", 1)[1].split("operationId:", 1)[0]
        assert "`ProjectCommand.generate_skeleton`" in block, operation
    conditions = _schema("projects.yaml", "CommandCondition")
    assert "(`ProjectCommand.generate_skeleton`, WF-PRJ-0030, WF-REV-0010" in conditions
    decisions = (API / "DECISIONS.md").read_text(encoding="utf-8")
    assert "## L'encart « Démarrer le projet » sur un projet sans révision" in decisions


def test_the_opening_refused_says_the_revision_in_progress_by_its_code() -> None:
    # A second opening on the project created today, asked from a screen read before its revision
    # 103 opened, is refused by the code of the catalogue, without parameter: the screen reads the
    # project again (WF-REV-0010).
    refused = fixture("current_revision_exists")
    assert refused == {
        "code": "CURRENT_REVISION_EXISTS",
        "status": 409,
        "correlation_id": universe(1308),
    }
    summary = _summary("current_revision_exists")
    assert "WF-REV-0010" in summary
    assert "revision_created" in summary
    paths = (API / "paths" / "revisions.yaml").read_text(encoding="utf-8")
    block = paths.split("operationId: createRevision\n", 1)[1].split("operationId:", 1)[0]
    said = block.split("'409':", 1)[1].split("'422':", 1)[0]
    example = "../../../fixtures/api/current_revision_exists.json"
    assert f"current_revision_exists: {{ $ref: {example} }}" in said
    assert "`CURRENT_REVISION_EXISTS`" in _flat(said)


def test_the_project_without_a_revision_names_the_background_task_that_creates_one() -> None:
    # The application of an import and the processing of an occurrence create the revision in
    # progress (WF-INTF-0090, WF-RIS-0060): meanwhile the project names the condition to the
    # commands it bears that would create or open that revision, the skeleton among them.
    conditions = _schema("projects.yaml", "CommandCondition")
    said = conditions.split("Un projet sans révision en cours en a une qui naît", 1)[1]
    said = said.split("L'analyse d'un import", 1)[0]
    for command in ("`edit_risks`", "`declare_risk`", f"`{SKELETON}`"):
        assert command in said, command
    decisions = _flat((API / "DECISIONS.md").read_text(encoding="utf-8"))
    assert "**`no_background_task_running` sur un projet sans révision en cours**" in decisions
    assert "**L'ordre des conditions** (relecture 1 du lot)" in decisions
    assert "`current_revision_exists` (corrélation 1308, seconde suite)" in decisions
