# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The predecessors of a task, replaced, their loops and conflicts (US-1390/L2).

``setPredecessors`` on the main structure of a revision a project's manager opened, every answer
checked against the contract: the four types and their lags kept in their unit, the successors
redated and the manual ones left, a loop or a link across the hierarchy refused by name, a
predecessor named twice or unknown, the conflict of a manual task signalled on both its ends and
lifted, the horizon, the state, the counter and the history. The structure starts its planning on
Monday the 2nd of November 2026, on the default calendar of eight hours from Monday to Friday.

Laid by US-1380/L1, the socle of EP-06, so that no two stories create the same file.
"""

from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from nodes_support import (
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

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

TUESDAY = DAY + timedelta(days=1)
WEDNESDAY = DAY + timedelta(days=2)
THURSDAY = DAY + timedelta(days=3)
FRIDAY = DAY + timedelta(days=4)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


def after(
    predecessor: dict[str, Any],
    link_type: str = "finish_to_start",
    lag: tuple[str, str] = ("0", "d"),
) -> dict[str, Any]:
    """Write a predecessor as ``setPredecessors`` reads it."""
    value, unit = lag
    return {
        "predecessor_node_id": predecessor["node_id"],
        "link_type": link_type,
        "lag": {"value": value, "unit": unit},
    }


def link(tree: Tree, node: dict[str, Any], *predecessors: dict[str, Any], who: Any = None) -> Any:
    """Replace the predecessors of a task at its counter read; give the answer."""
    headers = (who or tree.stage.manager).headers
    sent = {"predecessors": list(predecessors), "lock_version": node["lock_version"]}
    path = f"{tree.path}/nodes/{node['node_id']}/predecessors"
    return tree.api.put(path, headers=headers, json=sent)


def linked(tree: Tree, node: dict[str, Any], *predecessors: dict[str, Any]) -> dict[str, Any]:
    """Replace the predecessors of a task, which must be replaced; give what is answered."""
    answer = link(tree, node, *predecessors)
    assert answer.status_code == 200, answer.text
    return answer.json()


def manual(day: Any, hours: tuple[str, str] = ("0", "8")) -> dict[str, Any]:
    """Give the facet of a manual task of a day."""
    start, finish = hours
    return {"scheduling_mode": "manual", "start": instant(day, start), "finish": instant(day, finish)}


def days(value: str) -> dict[str, str]:
    """Give a duration in days as the contract writes it."""
    return {"value": value, "unit": "d"}


def scheduled(written: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Give the tasks a write redated without writing them, by node."""
    return {each["node_id"]: each for each in written["rescheduled"]}


# --- The links kept --------------------------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0030-A")
def test_the_four_types_and_a_negative_lag_are_kept_with_their_unit_and_read_back(
    tree: Tree,
) -> None:
    # « Les quatre types et un décalage négatif sont importés, saisis et exportés sans perte. »
    # « Un décalage saisi en semaines ou en mois est conservé dans son unité. »
    first, second, third, fourth = (tree.made(label) for label in ("A", "B", "C", "D"))
    task = tree.made("E")
    sent = [
        after(first, "finish_to_start", ("-1", "d")),
        after(second, "start_to_start", ("1", "w")),
        after(third, "finish_to_finish", ("50", "percent")),
        after(fourth, "start_to_finish", ("2", "mo")),
    ]
    written = linked(tree, task, *sent)
    [node] = written["nodes"]
    expected = [
        {**each, "predecessor_row_number": number} for number, each in enumerate(sent, start=1)
    ]
    assert node["predecessors"] == expected
    assert node["lock_version"] == task["lock_version"] + 1
    assert tree.node(task["node_id"])["predecessors"] == expected
    # Replaced, not added to: the links sent again are the task's, and those left out are gone.
    again = linked(tree, tree.node(task["node_id"]), sent[1])
    assert again["nodes"][0]["predecessors"] == [{**sent[1], "predecessor_row_number": 2}]


@pytest.mark.requirement("WF-PLA-0020-A")
def test_a_predecessor_moved_moves_its_automatic_successors_and_leaves_the_manual_ones(
    tree: Tree,
) -> None:
    # « Le déplacement d'une tâche prédécesseur déplace ses successeurs en mode automatique et
    # laisse inchangés ceux en mode manuel. »
    studies = tree.made("Études", task={"duration": days("3")})
    predecessor = tree.made("Approvisionnement")
    follower = tree.made("Montage")
    fixed = tree.made("Réception", task=manual(DAY + timedelta(days=14)))
    linked(tree, follower, after(predecessor))
    linked(tree, fixed, after(predecessor))
    before = tree.node(fixed["node_id"])["task"]
    # The predecessor now follows the studies: from Thursday, its successor from Friday.
    written = linked(tree, tree.node(predecessor["node_id"]), after(studies))
    assert written["nodes"][0]["task"]["start"] == instant(THURSDAY, "0")
    moved = scheduled(written)
    assert moved[follower["node_id"]]["start"] == instant(FRIDAY, "0")
    assert moved[follower["node_id"]]["finish"] == instant(FRIDAY, "8")
    assert fixed["node_id"] not in moved
    kept = tree.node(fixed["node_id"])["task"]
    assert (kept["start"], kept["finish"]) == (before["start"], before["finish"])
    assert written["structure_lock_version"] > written["nodes"][0]["lock_version"]


@pytest.mark.requirement("WF-PLA-0020-A")
def test_the_summaries_above_a_task_linked_are_returned_whole_as_its_ancestors(
    tree: Tree,
) -> None:
    summary = tree.made("Installation sur site")
    first = tree.made("Câblage", parent_id=summary["node_id"])
    second = tree.made("Essais", parent_id=summary["node_id"])
    written = linked(tree, second, after(first))
    [above] = written["ancestors"]
    assert above["node_id"] == summary["node_id"]
    assert (above["task"]["start"], above["task"]["finish"]) == (
        instant(DAY, "0"),
        instant(TUESDAY, "8"),
    )


# --- The links refused -----------------------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0030-A")
def test_a_link_closing_a_loop_is_refused_naming_its_tasks_and_nothing_is_written(
    tree: Tree,
) -> None:
    # « La création d'une liaison fermant un cycle [...] est refusée, et la raison en est nommée
    # à l'utilisateur. » From the task entered to the predecessor sent that already follows it.
    reception = tree.made("Réception usine")
    assembly = tree.made("Montage des armoires sur site")
    commissioning = tree.made("Mise en service")
    linked(tree, assembly, after(reception))
    linked(tree, commissioning, after(tree.node(assembly["node_id"])))
    answer = link(tree, reception, after(tree.node(commissioning["node_id"])))
    assert refusal(answer) == (
        422,
        "LINK_CYCLE",
        {
            "cycle": [
                {"node_id": reception["node_id"], "label": "Réception usine"},
                {"node_id": assembly["node_id"], "label": "Montage des armoires sur site"},
                {"node_id": commissioning["node_id"], "label": "Mise en service"},
            ]
        },
    )
    read = tree.node(reception["node_id"])
    assert (read["predecessors"], read["lock_version"]) == ([], reception["lock_version"])


@pytest.mark.requirement("WF-PLA-0030-A")
def test_a_link_between_a_summary_and_its_subordinate_or_to_itself_is_refused(
    tree: Tree,
) -> None:
    # « [...] ou reliant une récapitulative à l'une de ses subordonnées, est refusée [...]. »
    summary = tree.made("Installation sur site")
    assembly = tree.made("Montage des armoires sur site", parent_id=summary["node_id"])
    assert refusal(link(tree, assembly, after(summary))) == (422, "LINK_FORBIDDEN", {})
    assert refusal(link(tree, tree.node(summary["node_id"]), after(assembly)))[:2] == (
        422,
        "LINK_FORBIDDEN",
    )
    assert refusal(link(tree, assembly, after(assembly))) == (
        422,
        "LINK_CYCLE",
        {"cycle": [{"node_id": assembly["node_id"], "label": "Montage des armoires sur site"}]},
    )
    assert tree.node(assembly["node_id"])["predecessors"] == []


@pytest.mark.requirement("WF-PLA-0030-A")
def test_a_predecessor_sent_twice_or_unknown_is_refused_at_its_rank(tree: Tree) -> None:
    # « Deux tâches ne sont reliées que par une liaison au plus » (DUPLICATE_PREDECESSOR).
    assembly = tree.made("Montage des armoires sur site")
    commissioning = tree.made("Mise en service")
    stranger = {"node_id": str(uuid4())}
    answer = link(
        tree,
        commissioning,
        after(assembly),
        after(assembly, "start_to_start"),
        after(stranger),
    )
    assert faults(answer) == [
        ("/predecessors/1/predecessor_node_id", "DUPLICATE_PREDECESSOR", {}),
        ("/predecessors/2/predecessor_node_id", "UNKNOWN_TASK", {}),
    ]
    assert tree.node(commissioning["node_id"])["predecessors"] == []


@pytest.mark.requirement("WF-PLA-0150-A")
def test_links_carrying_the_project_beyond_fifteen_years_are_refused_naming_the_task_entered(
    tree: Tree,
) -> None:
    assembly = tree.made("Montage des armoires sur site")
    commissioning = tree.made("Mise en service")
    answer = link(tree, commissioning, after(assembly, lag=("300", "mo")))
    assert refusal(answer) == (
        422,
        "PROJECT_HORIZON_EXCEEDED",
        {"task": {"node_id": commissioning["node_id"], "label": "Mise en service"}},
    )
    assert tree.node(commissioning["node_id"])["predecessors"] == []


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_stale_counter_an_unknown_task_or_a_marked_revision_refuse_the_links(
    tree: Tree, stage: Scene
) -> None:
    first = tree.made("Études")
    second = tree.made("Revue")
    stale = {**second, "lock_version": second["lock_version"] + 1}
    assert refusal(link(tree, stale, after(first))) == (
        412,
        "STALE_LOCK_VERSION",
        {"expected_lock_version": second["lock_version"]},
    )
    unknown = {"node_id": str(uuid4()), "lock_version": 1}
    assert refusal(link(tree, unknown, after(first)))[:2] == (404, "NOT_FOUND")
    mark(stage, tree.revision)
    assert refusal(link(tree, second, after(first))) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "revision_draft"},
    )


@pytest.mark.requirement("WF-IHM-0110-A")
def test_links_entered_keep_their_entry_of_the_history(
    tree: Tree, stage: Scene, realm: TestRealm
) -> None:
    writer = signed_in(stage, realm)
    first = tree.made("Études")
    second = tree.made("Revue")
    assert link(tree, second, after(first), who=writer).status_code == 200
    [entry] = entries(stage)
    assert (entry.kind, entry.node_ids) == ("link", [UUID(second["node_id"])])
    assert entry.before[0]["rows"]["links"] == []
    [kept] = entry.after[0]["rows"]["links"]
    assert (kept["predecessor_id"], kept["link_type"]) == (first["node_id"], "finish_to_start")


# --- The conflicts of a manual task --------------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0020-A")
def test_a_manual_task_before_the_finish_of_its_predecessor_is_signalled_until_delayed(
    tree: Tree,
) -> None:
    # « Une tâche manuelle datée avant la fin calculée de son prédécesseur est signalée dans la
    # grille et dans le Gantt, avec ce prédécesseur ; la retarder au-delà de cette fin [...] fait
    # disparaître le signalement. » The predecessor floats negative and is critical (WF-PLA-0100).
    predecessor = tree.made("Câblage", task={"duration": days("3")})
    fixed = tree.made("Essais", task=manual(TUESDAY))
    written = linked(tree, fixed, after(predecessor))
    conflict = {
        "predecessor_node_id": predecessor["node_id"],
        "successor_node_id": fixed["node_id"],
        "link_type": "finish_to_start",
    }
    assert written["nodes"][0]["task"]["link_conflicts"] == [conflict]
    signalled = scheduled(written)[predecessor["node_id"]]
    assert signalled["link_conflicts"] == [conflict]
    # Bound by the start of the manual task, the predecessor should finish on Monday: two days
    # of work late.
    assert signalled["total_float"] == {"value": "-2", "unit": "d"}
    assert signalled["is_critical"]
    read = tree.node(predecessor["node_id"])["task"]
    assert (read["link_conflicts"], read["total_float"], read["is_critical"]) == (
        [conflict],
        {"value": "-2", "unit": "d"},
        True,
    )
    delayed = tree.changed(
        tree.node(fixed["node_id"]),
        start=instant(THURSDAY, "0"),
        finish=instant(THURSDAY, "8"),
    )
    assert delayed["nodes"][0]["task"]["link_conflicts"] == []
    lifted = scheduled(delayed)[predecessor["node_id"]]
    assert lifted["link_conflicts"] == []
    assert lifted["total_float"] == {"value": "0", "unit": "d"}


@pytest.mark.requirement("WF-PLA-0020-A")
def test_shortening_the_predecessor_or_withdrawing_the_link_lifts_the_signal(
    tree: Tree,
) -> None:
    # « [...] ou raccourcir le prédécesseur, fait disparaître le signalement. »
    predecessor = tree.made("Câblage", task={"duration": days("3")})
    fixed = tree.made("Essais", task=manual(TUESDAY))
    linked(tree, fixed, after(predecessor))
    shortened = tree.changed(tree.node(predecessor["node_id"]), duration=days("1"))
    assert shortened["nodes"][0]["task"]["link_conflicts"] == []
    assert scheduled(shortened)[fixed["node_id"]]["link_conflicts"] == []
    # Back in conflict, then the link withdrawn: the predecessor is given back without it.
    tree.changed(tree.node(predecessor["node_id"]), duration=days("3"))
    assert tree.node(predecessor["node_id"])["task"]["link_conflicts"] != []
    withdrawn = linked(tree, tree.node(fixed["node_id"]))
    assert withdrawn["nodes"][0]["predecessors"] == []
    assert scheduled(withdrawn)[predecessor["node_id"]]["link_conflicts"] == []
    assert tree.node(predecessor["node_id"])["task"]["link_conflicts"] == []
