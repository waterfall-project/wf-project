# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The date a structure starts its planning on, and its label (US-1390/L2, #2170).

``updateCostStructure`` on the main structure of a revision a project's manager opened, every
answer checked against the contract: the automatic tasks without a predecessor and their
successors moved with the date, the manual ones left; a day without hours of the default calendar
refused naming the next, none when it has no hour at all; the label alone; a body without a field,
a stale counter, a marked revision; the horizon; the entry of the history; the date kept by the
copy of a marked revision.
The structure starts its planning on Monday the 2nd of November 2026, on the default calendar of
eight hours from Monday to Friday.

Laid by US-1380/L1, the socle of EP-06, so that no two stories create the same file.
"""

from datetime import date, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from nodes_support import (
    SATURDAY,
    Tree,
    entries,
    faults,
    instant,
    mark,
    opened,
    refusal,
    signed_in,
)
from planning_support import DAY
from projects_support import Scene
from projects_support import scene as make_scene
from sqlalchemy import update as update_rows

from waterfall.core.resource_settings.tables import DAYS, Calendar

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

WEEK_BEFORE = DAY - timedelta(days=7)
TUESDAY = DAY + timedelta(days=1)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


def structure(tree: Tree) -> dict[str, Any]:
    """Read the structure of the tree as the list of its revision gives it."""
    listed = tree.api.get(tree.path.rsplit("/", 1)[0], headers=tree.stage.manager.headers)
    assert listed.status_code == 200, listed.text
    return next(each for each in listed.json() if each["structure_id"] == tree.structure_id)


def update(tree: Tree, who: Any = None, **body: Any) -> Any:
    """Write the structure at the counter read unless the body sends one; give the answer."""
    sent = {"lock_version": structure(tree)["lock_version"], **body}
    return tree.api.patch(tree.path, headers=(who or tree.stage.manager).headers, json=sent)


def updated(tree: Tree, **body: Any) -> dict[str, Any]:
    """Write the structure, which must be written; give what is answered."""
    answer = update(tree, **body)
    assert answer.status_code == 200, answer.text
    return answer.json()


def link(tree: Tree, node: dict[str, Any], predecessor: dict[str, Any]) -> None:
    """Make a task follow another, finish to start, through the service."""
    sent = {
        "predecessors": [
            {
                "predecessor_node_id": predecessor["node_id"],
                "link_type": "finish_to_start",
                "lag": {"value": "0", "unit": "d"},
            }
        ],
        "lock_version": node["lock_version"],
    }
    path = f"{tree.path}/nodes/{node['node_id']}/predecessors"
    answer = tree.api.put(path, headers=tree.stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text


@pytest.mark.requirement("WF-PLA-0020-A")
def test_a_start_a_week_earlier_moves_the_automatic_tasks_and_their_successors_by_as_much(
    tree: Tree,
) -> None:
    # « Une tâche en mode automatique sans prédécesseur commence à la date de début de planning ;
    # avancer cette date d'une semaine l'avance d'autant, ainsi que ses successeurs
    # automatiques. » The manual tasks stay.
    first = tree.made("Études")
    second = tree.made("Revue")
    link(tree, second, first)
    fixed = tree.made(
        "Réception",
        task={
            "scheduling_mode": "manual",
            "start": instant(DAY + timedelta(days=3), "0"),
            "finish": instant(DAY + timedelta(days=3), "8"),
        },
    )
    assert tree.node(first["node_id"])["task"]["start"] == instant(DAY, "0")
    counter = structure(tree)["lock_version"]
    written = updated(tree, planning_start_on=WEEK_BEFORE.isoformat())
    assert (written["nodes"], written["ancestors"]) == ([], [])
    moved = {each["node_id"]: each for each in written["rescheduled"]}
    assert (moved[first["node_id"]]["start"], moved[first["node_id"]]["finish"]) == (
        instant(WEEK_BEFORE, "0"),
        instant(WEEK_BEFORE, "8"),
    )
    assert moved[second["node_id"]]["start"] == instant(WEEK_BEFORE + timedelta(days=1), "0")
    assert fixed["node_id"] not in moved
    assert tree.node(fixed["node_id"])["task"]["start"] == instant(DAY + timedelta(days=3), "0")
    assert written["structure_lock_version"] == counter + 1
    read = structure(tree)
    assert (read["planning_start_on"], read["lock_version"]) == (
        WEEK_BEFORE.isoformat(),
        counter + 1,
    )
    # A node's counter follows its own writes only.
    assert tree.node(first["node_id"])["lock_version"] == first["lock_version"]


@pytest.mark.requirement("WF-PLA-0020-A")
def test_the_summary_above_a_task_the_start_moves_is_returned_whole(tree: Tree) -> None:
    summary = tree.made("Études")
    tree.made("Études de détail", parent_id=summary["node_id"])
    written = updated(tree, planning_start_on=WEEK_BEFORE.isoformat())
    [above] = written["ancestors"]
    assert (above["node_id"], above["task"]["start"]) == (
        summary["node_id"],
        instant(WEEK_BEFORE, "0"),
    )


@pytest.mark.requirement("WF-PLA-0020-A")
def test_a_start_on_a_day_without_hours_of_the_default_calendar_names_the_next_working_day(
    tree: Tree,
) -> None:
    # The structure has no calendar of its own: its date is judged on the default calendar,
    # which grants no hour on a Saturday; the refusal names the Monday after (WF-PLA-0010).
    counter = structure(tree)["lock_version"]
    answer = update(tree, planning_start_on=SATURDAY.isoformat())
    assert faults(answer) == [
        (
            "/planning_start_on",
            "NON_WORKING_DAY",
            {
                "date": SATURDAY.isoformat(),
                "next_working_day": (SATURDAY + timedelta(days=2)).isoformat(),
            },
        )
    ]
    read = structure(tree)
    assert (read["planning_start_on"], read["lock_version"]) == (DAY.isoformat(), counter)


def test_a_start_on_a_default_calendar_without_any_hour_names_no_next_working_day(
    tree: Tree, stage: Scene
) -> None:
    # A default calendar left without an hour while no current task is on it: no day follows.
    with stage.owner.begin() as connection:
        connection.execute(
            update_rows(Calendar).where(Calendar.is_default).values(dict.fromkeys(DAYS, 0))
        )
    answer = update(tree, planning_start_on=TUESDAY.isoformat())
    assert faults(answer) == [
        (
            "/planning_start_on",
            "NON_WORKING_DAY",
            {"date": TUESDAY.isoformat(), "next_working_day": None},
        )
    ]
    assert structure(tree)["planning_start_on"] == DAY.isoformat()


def test_the_label_alone_redates_nothing_and_advances_the_counter(tree: Tree) -> None:
    tree.made("Études")
    counter = structure(tree)["lock_version"]
    written = updated(tree, label="Structure du chantier")
    assert (written["nodes"], written["ancestors"], written["rescheduled"]) == ([], [], [])
    assert written["structure_lock_version"] == counter + 1
    read = structure(tree)
    assert (read["label"], read["planning_start_on"]) == ("Structure du chantier", DAY.isoformat())


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_body_without_a_field_a_null_one_or_a_stale_counter_writes_nothing(tree: Tree) -> None:
    counter = structure(tree)["lock_version"]
    assert refusal(update(tree)) == (422, "VALIDATION_FAILED", {})
    assert faults(update(tree, label=None)) == [("/label", "VALIDATION_FAILED", {})]
    assert faults(update(tree, planning_start_on=None)) == [
        ("/planning_start_on", "VALIDATION_FAILED", {})
    ]
    assert refusal(update(tree, label="Autre", lock_version=counter + 1)) == (
        412,
        "STALE_LOCK_VERSION",
        {"expected_lock_version": counter},
    )
    read = structure(tree)
    assert (read["label"], read["lock_version"]) == ("Structure principale", counter)


@pytest.mark.requirement("WF-REV-0020-A")
def test_a_structure_of_a_marked_revision_is_not_written(tree: Tree, stage: Scene) -> None:
    mark(stage, tree.revision)
    assert refusal(update(tree, label="Autre")) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "revision_draft"},
    )


@pytest.mark.requirement("WF-PLA-0150-A")
def test_a_start_carrying_the_project_beyond_fifteen_years_names_the_task_finishing_last(
    tree: Tree,
) -> None:
    tree.made(
        "Réception",
        task={
            "scheduling_mode": "manual",
            "start": instant(DAY, "0"),
            "finish": instant(DAY, "8"),
        },
    )
    late = tree.made("Exploitation")
    answer = update(tree, planning_start_on=date(2042, 11, 3).isoformat())
    assert refusal(answer) == (
        422,
        "PROJECT_HORIZON_EXCEEDED",
        {"task": {"node_id": late["node_id"], "label": "Exploitation"}},
    )
    assert structure(tree)["planning_start_on"] == DAY.isoformat()


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_write_of_the_structure_keeps_its_start_and_label_in_the_history(
    tree: Tree, stage: Scene, realm: TestRealm
) -> None:
    writer = signed_in(stage, realm)
    counter = structure(tree)["lock_version"]
    answer = update(tree, writer, planning_start_on=WEEK_BEFORE.isoformat(), label="Chantier")
    assert answer.status_code == 200, answer.text
    [entry] = entries(stage)
    assert (entry.kind, entry.node_ids) == ("structure_update", [])
    [before], [after] = entry.before, entry.after
    assert (before["object_id"], before["lock_version"]) == (tree.structure_id, counter)
    assert before["rows"] == {
        "structure": {"planning_start_on": DAY.isoformat(), "label": "Structure principale"}
    }
    assert (after["lock_version"], after["rows"]["structure"]) == (
        counter + 1,
        {"planning_start_on": WEEK_BEFORE.isoformat(), "label": "Chantier"},
    )


@pytest.mark.requirement("WF-PLA-0020-A")
def test_a_structure_taken_from_a_marked_revision_keeps_its_start(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    # « [...] une structure reprise d'une révision marquée conserve la sienne » (#2170).
    updated(tree, planning_start_on=WEEK_BEFORE.isoformat())
    mark(stage, tree.revision)
    following = opened(api, stage)
    path = f"{tree.path.split('/revisions/')[0]}/revisions/{following['revision_id']}/structures"
    [copied] = api.get(path, headers=stage.manager.headers).json()
    assert UUID(copied["structure_id"]) != UUID(tree.structure_id)
    assert copied["planning_start_on"] == WEEK_BEFORE.isoformat()
