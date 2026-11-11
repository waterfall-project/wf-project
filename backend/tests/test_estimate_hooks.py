# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The facet estimate line in the planning: creation, history, paste and redating (US-1490/L3).

What the planning asks of the facet the estimate registers (``FacetHooks``): the calendar of a task
intersected from the roles of its lines and the line refused that would leave it without an hour
(``calendar_of``), its lines priced again once the task is redated (``reinflate``), their snapshot
and their restoration by the history (``snapshot``, ``restore``), the question of the designation
(``revision_has_lines``). Every answer is checked against the contract; US-1560 writes here those
of the paste.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import YEAR, Costing, Lines, add_role, costing
from history_support import delete, redone, undo, undone
from nodes_support import Tree, entries, faults, opened, refusal, signed_in
from projects_support import PROJECTS, Person, Scene
from projects_support import scene as make_scene
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from waterfall.core.estimate import writing
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.interface import facets
from waterfall.core.revisions.interface import mark_revision
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines of the scene name, rated for the year."""
    return costing(stage.database)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


@pytest.fixture
def lines(tree: Tree) -> Lines:
    """Give the lines of the main structure."""
    return Lines(tree)


@pytest.fixture
def who(stage: Scene, realm: TestRealm) -> Person:
    """Give a contributor of the project whose token carries a session of sign-in."""
    return signed_in(stage, realm)


def worked(role: UUID, **line: Any) -> dict[str, Any]:
    """Give a labour line of a role: one person for ten hours, unless said."""
    return {"quantity": "1", "resource_role_id": str(role), "hours": "10", **line}


def marked(stage: Scene, revision: dict[str, Any], name: str) -> None:
    """Mark a revision under a name by the transaction of the worker (US-0970)."""
    with (
        logging_context(correlation_id="marking"),
        Session(stage.owner) as session,
        session.begin(),
    ):
        mark_revision(session, UUID(revision["revision_id"]), name, None, Act(None, utc_now()))


def stored(stage: Scene) -> int:
    """Count the lines the base keeps."""
    with stage.database.transaction() as session:
        return session.scalar(select(func.count()).select_from(EstimateLine)) or 0


def test_the_estimate_registers_the_facet_of_its_lines_in_the_planning() -> None:
    # How EP-07 extends the planning (``register_facet``), a detail of the realization which
    # reprises no Vérif: the hooks of the kind ``estimate_line``, registered at the import of the
    # interface of the estimate; no other module registers a facet.
    assert list(facets()) == ["estimate_line"]


# --- The calendar of a task --------------------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_task_is_planned_on_the_fewest_hours_its_roles_work_each_day(
    stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Une tâche dont les deux rôles travaillent huit et six heures le lundi est planifiée sur six
    # heures ce jour-là. » The task is redated at the creation of the second line.
    task = tree.made("Câblage")
    short = add_role(stage.database, "MONT", (6, 8, 8, 8, 8, 0, 0))
    first = lines.made(task, **worked(costs.role))
    [above] = first["ancestors"]
    assert above["task"]["calendar_hours"]["monday"] == "8"
    second = lines.made(task, **worked(short))
    [bearer] = second["ancestors"]
    assert bearer["task"]["calendar_hours"]["monday"] == "6"
    assert bearer["task"]["calendar_id"] is None
    assert bearer["task"]["finish"] == {"date": "2026-11-03", "hours": "2"}
    assert [each["node_id"] for each in second["rescheduled"]] == [task["node_id"]]


@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_role_that_would_leave_its_task_without_an_hour_is_refused_naming_the_roles(
    stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « L'ajout, à une tâche dont un rôle travaille du lundi au vendredi, d'une ligne d'un rôle qui
    # ne travaille que le week-end est refusé en nommant les deux rôles, et la tâche reste
    # inchangée. » At the creation and at the role changed.
    task = tree.made("Câblage")
    weekend = add_role(stage.database, "WE", (0, 0, 0, 0, 0, 8, 8))
    node = lines.made(task, **worked(costs.role))["nodes"][0]
    before = tree.node(task["node_id"])
    idle = (
        422,
        "TASK_WITHOUT_WORKING_HOURS",
        {
            "resource_roles": [
                {"resource_role_id": str(costs.role), "code": "ING", "label": "Ingénieur"},
                {"resource_role_id": str(weekend), "code": "WE", "label": "Rôle WE"},
            ],
            "tasks": [
                {
                    "project_id": stage.project["project_id"],
                    "node_id": task["node_id"],
                    "label": "Câblage",
                }
            ],
        },
    )
    created = {"kind": "estimate_line", "parent_id": task["node_id"]}
    sent = {**created, "estimate_line": worked(weekend)}
    headers = tree.stage.manager.headers
    assert refusal(tree.api.post(f"{tree.path}/nodes", headers=headers, json=sent)) == idle
    second = lines.made(task, **worked(costs.role, label="Second"))["nodes"][0]
    path = f"{tree.path}/nodes/{second['node_id']}/estimate-line"
    changed = {"lock_version": second["lock_version"], "resource_role_id": str(weekend)}
    assert refusal(tree.api.patch(path, headers=headers, json=changed)) == idle
    after = tree.node(task["node_id"])
    kept = ("start", "finish", "calendar_id", "calendar_hours")
    assert [after["task"][name] for name in kept] == [before["task"][name] for name in kept]
    assert after["lock_version"] == before["lock_version"]
    assert tree.node(node["node_id"])["estimate_line"]["resource_role_id"] == str(costs.role)


@pytest.mark.requirement("WF-PLA-0010-A")
def test_the_hours_of_a_task_are_judged_when_the_role_of_its_line_changes_only(
    stage: Scene, tree: Tree, lines: Lines, costs: Costing, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A modification that keeps the role of its line does not judge the hours of the task again: a
    # calendar changed since cannot make the judgment refuse it. Counted where the line is written.
    task = tree.made("Câblage")
    node = lines.made(task, **worked(costs.role))["nodes"][0]
    short = add_role(stage.database, "MONT", (4, 4, 4, 4, 4, 0, 0))
    judged: list[UUID] = []
    real = writing.judge_working_hours

    def counting(session: Session, held: Any, role_id: UUID, earlier: Any = None) -> None:
        judged.append(role_id)
        real(session, held, role_id, earlier)

    monkeypatch.setattr(writing, "judge_working_hours", counting)
    kept = lines.changed(node, quantity="2")
    assert judged == []
    lines.changed(kept["nodes"][0], resource_role_id=str(short))
    assert judged == [short]


@pytest.mark.requirement("WF-PLA-0010-A")
@pytest.mark.usefixtures("costs")
def test_a_task_whose_last_labour_line_goes_is_back_on_the_default_calendar(
    stage: Scene, tree: Tree, lines: Lines
) -> None:
    # « Une tâche sans ligne de main-d'œuvre est planifiée sur le calendrier par défaut. »
    task = tree.made("Câblage")
    default = tree.node(task["node_id"])["task"]["calendar_id"]
    short = add_role(stage.database, "MONT", (4, 4, 4, 4, 4, 0, 0))
    node = lines.made(task, **worked(short))["nodes"][0]
    assert tree.node(task["node_id"])["task"]["calendar_id"] != default
    gone = tree.api.delete(
        f"{tree.path}/nodes/{node['node_id']}?lock_version={node['lock_version']}",
        headers=stage.manager.headers,
    )
    assert gone.status_code == 200, gone.text
    assert tree.node(task["node_id"])["task"]["calendar_id"] == default
    assert stored(stage) == 0


# --- The redating ------------------------------------------------------------------------------


@pytest.mark.requirement("WF-DEV-0040-A")
def test_the_lines_of_a_task_redated_are_priced_again_and_given_back(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # A task moved from one year to the next takes its lines with it: their re-estimated amount
    # and their year of consumption follow, given back in ``reinflated`` with the task that bears
    # them, which is not written.
    path = f"{PROJECTS}/{stage.project['project_id']}"
    counter = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    changed = api.patch(
        path,
        headers=stage.manager.headers,
        json={"inflation_rate": "0.03", "lock_version": counter},
    )
    assert changed.status_code == 200, changed.text
    first = tree.made("Études")
    second = tree.made(
        "Exploitation",
        task={
            "scheduling_mode": "manual",
            "start": {"date": f"{YEAR}-12-07"},
            "finish": {"date": f"{YEAR}-12-08"},
        },
    )
    line = lines.made(second, **worked(costs.role))["nodes"][0]
    assert line["estimate_line"]["consumption_year"] == YEAR
    moved = tree.changed(
        tree.node(second["node_id"]),
        start={"date": f"{YEAR + 1}-12-06"},
        finish={"date": f"{YEAR + 1}-12-07"},
    )
    assert [each["node_id"] for each in moved["nodes"]] == [second["node_id"]]
    assert moved["reinflated"] == [
        {
            "node_id": line["node_id"],
            "budgeted_amount": "669.50",
            "reestimated_amount": "669.50",
            "consumption_year": YEAR + 1,
        }
    ]
    assert moved["nodes"][0]["task"]["reestimated_amount"] == "669.50"
    assert first["node_id"] not in {each["node_id"] for each in moved["reinflated"]}
    assert tree.node(line["node_id"])["estimate_line"]["reestimated_amount"] == "669.50"


# --- The history -------------------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_deletion_of_a_task_then_its_undoing_give_back_the_task_and_its_lines(
    tree: Tree, stage: Scene, lines: Lines, costs: Costing, who: Person
) -> None:
    # « La suppression d'une tâche puis son annulation restituent la tâche, ses lignes et ses
    # liaisons. » The lines, by the snapshot of their facet; the links are EP-06's.
    task = tree.made("Câblage", who=who)
    labour = lines.made(task, who, **worked(costs.role))["nodes"][0]
    before = tree.node(labour["node_id"])
    deleted = delete(tree, tree.node(task["node_id"]), who)
    assert deleted.status_code == 200, deleted.text
    assert (tree.items(), stored(stage)) == ([], 0)
    body = undone(tree, who)
    assert body["undone"]["kind"] == "node_delete"
    back = tree.node(labour["node_id"])
    assert back["estimate_line"] == before["estimate_line"]
    assert back["lock_version"] == before["lock_version"] + 1
    assert tree.node(task["node_id"])["task"]["base_amount"] == "650.00"
    assert redone(tree, who)["undone"]["kind"] == "node_delete"
    assert stored(stage) == 0


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_line_changed_is_kept_by_the_history_and_brought_back_by_the_undoing(
    tree: Tree, stage: Scene, lines: Lines, costs: Costing, who: Person
) -> None:
    task = tree.made("Câblage", who=who)
    node = lines.made(task, who, **worked(costs.role))["nodes"][0]
    assert lines.change(node, who, hours="20").status_code == 200
    *_, cell = entries(stage)
    assert (cell.kind, cell.node_ids) == ("cell", [UUID(node["node_id"])])
    assert cell.before[0]["label"] == "Câblage — Ingénieur"
    assert cell.before[0]["rows"]["facet"]["hours"] == "10.00"
    assert cell.after[0]["rows"]["facet"]["hours"] == "20.00"
    body = undone(tree, who)
    assert body["undone"] == {"kind": "cell", "node_ids": [node["node_id"]], "risk_ids": []}
    back = tree.node(node["node_id"])["estimate_line"]
    assert (back["hours"], back["base_amount"]) == ("10", "650.00")
    assert redone(tree, who)["written"]["nodes"][0]["estimate_line"]["hours"] == "20"


@pytest.mark.requirement("WF-IHM-0110-A")
def test_an_undoing_of_a_line_another_contributor_took_up_since_names_it_by_its_label(
    tree: Tree, lines: Lines, costs: Costing, who: Person
) -> None:
    # « L'annulation d'une modification qu'un autre contributeur a depuis reprise est refusée en
    # nommant l'objet en conflit. » Here a line, named by its label.
    task = tree.made("Câblage", who=who)
    node = lines.made(task, who, **worked(costs.role))["nodes"][0]
    assert lines.change(tree.node(node["node_id"]), who, hours="20").status_code == 200
    taken = lines.changed(tree.node(node["node_id"]), label="Câblage repris")
    assert taken["nodes"][0]["estimate_line"]["label"] == "Câblage repris"
    assert refusal(undo(tree, who)) == (
        409,
        "UNDO_CONFLICT",
        {"conflicting_object_id": node["node_id"], "conflicting_object_label": "Câblage repris"},
    )


# --- The designation ---------------------------------------------------------------------------


@pytest.mark.requirement("WF-CYC-0030-A")
def test_a_revision_is_designated_the_reference_once_it_bears_a_line(
    api: ContractClient, stage: Scene, tree: Tree, costs: Costing
) -> None:
    # The estimate answers the question of the lines (``revision_has_lines``): tasks alone do not
    # make a revision designable.
    path = f"{PROJECTS}/{stage.project['project_id']}"

    def designated(revision: dict[str, Any]) -> Any:
        counter = api.get(path, headers=stage.manager.headers).json()["lock_version"]
        sent = {"revision_id": revision["revision_id"], "confirmed": True, "lock_version": counter}
        return api.put(f"{path}/reference-revision", headers=stage.manager.headers, json=sent)

    tree.made("Câblage")
    marked(stage, tree.revision, "v1.0")
    assert refusal(designated(tree.revision)) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "revision_has_tasks_and_lines"},
    )
    current = Tree(api, stage, opened(api, stage))
    task = next(item for item in current.items() if item["kind"] == "task")
    Lines(current).made(task, **worked(costs.role))
    marked(stage, current.revision, "v2.0")
    assert designated(current.revision).status_code == 200


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_write_of_a_line_refused_keeps_no_entry_of_the_history(
    tree: Tree, stage: Scene, lines: Lines, costs: Costing, who: Person
) -> None:
    task = tree.made("Câblage", who=who)
    lines.made(task, who, **worked(costs.role))
    held = len(entries(stage))
    assert faults(lines.create(task, who, quantity="1")) == [
        ("/estimate_line/cost_category_id", "VALUE_REQUIRED", {})
    ]
    assert len(entries(stage)) == held
