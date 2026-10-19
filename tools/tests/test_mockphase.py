# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of what the examples say the grids may enter, by the phase of the project (EP-15/US-0460).

The commands of each structure, written by hand, against the revision and the project they belong
to; the fields each node of the witness accepts, generated, against the subprojects and the
progress of its task (C-358, C-359, #1065, #1066). They try the examples against the universe and
the contract, not the Vérif of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre
aucune exigence »).
"""

from pathlib import Path
from typing import Any, cast

import pytest

from wftools import REPOSITORY, mockcore, mockwitness
from wftools.mockwitness import fixture

type Entry = dict[str, Any]

EDIT = ("edit_planning", "edit_estimate", "edit_remaining")
"""The commands of a structure, in the order of `StructureCommand`, one by grid that enters it."""

PHASE = {"edit_estimate": "project_before_in_progress", "edit_remaining": "project_in_progress"}
"""The condition of phase of a command of the main structure, and the state it misses it in."""

READ = {
    "structures": ("revision", "project"),
    "structures_amendments": ("revision_marked", "project"),
    "structures_without_tasks": ("revision_without_tasks", "project_revision_opened"),
}
"""Each example of listCostStructures, the revision it lists the structures of, and its project."""


def _commands(entry: Entry) -> list[tuple[str, bool, list[str]]]:
    return [
        (each["command"], each["is_available"], each["missing_conditions"])
        for each in cast("list[Entry]", entry["available_commands"])
    ]


def _phase(command: str, state: str) -> list[str]:
    """Return the condition of phase a command of the main structure misses in a state."""
    if command == "edit_estimate" and state not in ("created", "pricing"):
        return [PHASE[command]]
    if command == "edit_remaining" and state != "in_progress":
        return [PHASE[command]]
    return []


@pytest.mark.parametrize("name", sorted(READ))
def test_each_structure_says_its_commands_by_the_phase_and_the_state_of_its_revision(
    name: str,
) -> None:
    # The main structure is entered in the estimate before the project is in progress, in the
    # remaining to commit then; an amendment and the estimate of a risk in the planning and the
    # estimate whatever the phase, never in the remaining (WF-DEV-0050, WF-RAE-0040, C-358). The
    # condition of phase first, then the conditions of state of the revision, as its command of
    # the same name lists them: the structures do not repeat what the revision does not say.
    revision_name, project_name = READ[name]
    revision, project = fixture(revision_name), fixture(project_name)
    assert revision["project_id"] == project["project_id"]
    of_revision = {command: missing for command, _, missing in _commands(revision)}
    structures = fixture(name)
    assert {each["revision_id"] for each in structures} == {revision["revision_id"]}
    for structure in structures:
        main = structure["kind"] == "main"
        expected: list[tuple[str, bool, list[str]]] = []
        for command in EDIT if main else EDIT[:2]:
            missing = (_phase(command, project["state"]) if main else []) + of_revision[command]
            expected.append((command, not missing, missing))
        assert _commands(structure) == expected, (name, structure["structure_id"])


def test_the_witness_enters_its_main_structure_in_the_remaining_to_commit_alone() -> None:
    # The project in progress: its estimate is read only, its remaining to commit is entered; the
    # project created today enters its estimate, not yet a remaining to commit.
    [main] = [each for each in fixture("structures") if each["kind"] == "main"]
    assert _commands(main) == [
        ("edit_planning", True, []),
        ("edit_estimate", False, ["project_before_in_progress"]),
        ("edit_remaining", True, []),
    ]
    [opened] = fixture("structures_without_tasks")
    assert _commands(opened)[2] == ("edit_remaining", False, ["project_in_progress"])


def test_the_conditions_of_the_commands_of_a_structure_are_those_of_the_contract() -> None:
    schemas = REPOSITORY / "docs" / "api" / "components" / "schemas"
    assert _enumeration(schemas / "revisions.yaml", "StructureCommand") == list(EDIT)
    conditions = _enumeration(schemas / "projects.yaml", "CommandCondition")
    assert set(PHASE.values()) <= set(conditions)


def _enumeration(path: Path, schema: str) -> list[str]:
    """Return the values of an enumeration of the contract written one a line, in its order."""
    block = path.read_text(encoding="utf-8").split(f"\n{schema}:\n", 1)[1].split("\n\n", 1)[0]
    listed = block.split("enum:\n", 1)[1]
    return [line.strip()[2:] for line in listed.splitlines() if line.strip().startswith("- ")]


def test_every_task_of_the_main_structure_names_its_inscriptions_to_the_timelines() -> None:
    # The grid of planning offers the submenu of the timelines from the node alone (#1065):
    # every task of the main structure names `task.tracking`, last, summary, leaf or milestone;
    # no line does.
    for name in ("nodes_core", "nodes_estimate", "nodes_timeline", "skeleton_generated"):
        reading = fixture(name)
        for node in reading.get("items", reading.get("nodes", [])):
            fields = node["editable_fields"]
            if node["kind"] == mockcore.TASK:
                assert fields[-1] == "task.tracking", (name, node["node_id"])
            else:
                assert "task.tracking" not in fields, (name, node["node_id"])


def test_a_line_of_a_started_task_does_not_offer_to_leave_a_charged_subproject() -> None:
    # Both subprojects of the witness received actual costs (WF-PRJ-0050, #1066): a line borne by
    # a task started or completed does not name its subproject among the fields it accepts, nor
    # computes it; a line of a task not started does, as does one without a subproject.
    charged = {each["subproject_id"] for each in fixture("subprojects") if each["has_actual_costs"]}
    assert charged == {mockwitness.SUBPROJECT_CONTROL, mockwitness.SUBPROJECT_TESTS}
    read = {node["node_id"]: node for node in fixture("nodes_core")["items"]}
    held: list[int] = []
    for node in read.values():
        if node["kind"] != mockcore.ESTIMATE_LINE or node["estimate_line"]["is_computed"]:
            continue
        progress = read[node["parent_id"]]["task"]["progress"]
        if progress != "not_started" and node["estimate_line"]["subproject_id"] in charged:
            held.append(int(node["node_id"][-3:]))
            assert "estimate_line.subproject_id" not in node["editable_fields"]
        else:
            assert node["editable_fields"][-1] == "estimate_line.subproject_id"
        assert "estimate_line.subproject_id" not in node["computed_fields"]
    # The labour and the terminal blocks of the wiring, started, alone.
    assert held == [mockwitness.N.LABOUR, mockwitness.N.BLOCKS]
