# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The abandonment of a differential (``deleteCostStructure``; US-2550/L4).

A differential not merged of the current revision is abandoned at the counter read: its nodes, its
lines and its entries of the history are gone, the other structures are as they were, the next
revision does not know it, and the journal says so. It is refused on the main structure, on the own
estimate of a risk and on a merged differential (409 ``unmerged_amendment_exists``), on a marked
revision, a terminal project and while a background task writes, at another counter (412); the
command ``delete`` says it in advance. Every answer is checked against the contract
(``ContractClient``).
"""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import (
    commands_of,
    listed,
    on,
    open_amendment,
    opened_amendment,
    started_marking,
    structures_path,
)
from estimate_support import Costing, Lines, costing
from history_support import plans
from nodes_support import Tree, entries, mark, opened, signed_in
from paste_support import applied, planned
from projects_support import PROJECTS, Person, Scene, put_in_state
from projects_support import scene as make_scene
from risks_support import Costed, costed, declared, material
from sqlalchemy import func, select, update
from support import wait_for_a_lock

from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import Node, Task
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.audit import AuditEntry

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

FIXTURES = Path(__file__).parents[2] / "fixtures" / "api"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a fresh platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories the lines name."""
    return costing(stage.database)


@pytest.fixture
def project(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed(api, stage, costs)


@pytest.fixture
def who(stage: Scene, realm: TestRealm) -> Person:
    """Give a contributor of the project whose token carries a session of sign-in."""
    return signed_in(stage, realm)


def abandon(
    api: ContractClient,
    project: Costed,
    structure_id: str | UUID,
    lock_version: int | str,
    who: Person | None = None,
) -> Any:
    """Abandon a structure at the counter given, as the manager does by default."""
    headers = (who or project.stage.manager).headers
    path = f"{structures_path(project)}/{structure_id}?lock_version={lock_version}"
    return api.delete(path, headers=headers)


def counter_of(api: ContractClient, project: Costed, structure_id: str) -> int:
    """Read the counter of a structure, as the list of the structures gives it."""
    found = next(each for each in listed(api, project) if each["structure_id"] == structure_id)
    return found["lock_version"]


def abandoned(api: ContractClient, project: Costed, structure_id: str) -> Any:
    """Abandon a structure at the counter it holds now."""
    return abandon(api, project, structure_id, counter_of(api, project, structure_id))


def held_by(project: Costed, structure_id: str) -> dict[str, int]:
    """Count what a structure holds: its row, its nodes, its tasks, its lines."""
    key = UUID(structure_id)
    with project.stage.database.transaction() as session:
        nodes = select(Node.id).where(Node.structure_id == key)
        return {
            "structure": session.scalar(
                select(func.count()).select_from(CostStructure).where(CostStructure.id == key)
            )
            or 0,
            "node": session.scalar(
                select(func.count()).select_from(Node).where(Node.structure_id == key)
            )
            or 0,
            "task": session.scalar(
                select(func.count()).select_from(Task).where(Task.structure_id == key)
            )
            or 0,
            "line": session.scalar(
                select(func.count())
                .select_from(EstimateLine)
                .where(EstimateLine.node_id.in_(nodes))
            )
            or 0,
        }


def with_a_task(project: Costed, structure_id: str, label: str = "Essais") -> Tree:
    """Write a task and its line in a differential, as its manager does; give its tree."""
    tree = on(project.tree, structure_id)
    Lines(tree).made(tree.made(label), **material(project.costs, "Banc d'essai", "50.00"))
    return tree


# --- The abandonment ------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_abandonment_deletes_the_differential_and_leaves_the_other_structures_intact(
    api: ContractClient, project: Costed
) -> None:
    # « Deux structures différentielles coexistent dans une même révision, et la fusion de l'une
    # laisse l'autre intacte », de même pour l'abandon : sa structure, ses tâches, ses lignes et ses
    # images disparaissent, la principale et l'autre différentiel sont lus comme avant.
    first, second = (opened_amendment(api, project, label) for label in ("Avenant 1", "Avenant 2"))
    with_a_task(project, first)
    other = with_a_task(project, second, "Recette")
    before = (project.tree.read().json(), other.read().json())
    counters = {
        each["structure_id"]: each["lock_version"]
        for each in listed(api, project)
        if each["structure_id"] != first
    }
    assert held_by(project, first)["node"] == 6
    answer = abandoned(api, project, first)
    assert answer.status_code == 204, answer.text
    assert answer.content == b""
    assert held_by(project, first) == {"structure": 0, "node": 0, "task": 0, "line": 0}
    assert (project.tree.read().json(), other.read().json()) == before
    assert {each["structure_id"]: each["lock_version"] for each in listed(api, project)} == counters
    assert on(project.tree, first).read().status_code == 404


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_entries_and_the_plans_of_the_differential_leave_the_stacks_the_others_stay(
    api: ContractClient, project: Costed, who: Person
) -> None:
    # « les saisies du différentiel quittant les piles d'annulation » : l'abandon est hors de
    # l'historique annulable, et rien de ce qui touchait la structure n'est plus défait ni refait ;
    # les entrées des autres structures, de la même pile, restent, et l'annulation les défait.
    first, second = (opened_amendment(api, project, label) for label in ("Avenant 1", "Avenant 2"))
    other = on(project.tree, second)
    kept = other.create("Recette", who)
    assert kept.status_code == 201, kept.text
    gone = on(project.tree, first)
    created = gone.create("Essais", who).json()["nodes"][0]
    assert gone.change(created, who, label="Essais 2").status_code == 200
    planned(gone, gone.node(created["node_id"]), "label", [["Un"], ["Deux"]], who)
    # The label of the structure is an entry of the history of its own (``structure_update``).
    patched = api.patch(
        f"{structures_path(project)}/{first}",
        headers=who.headers,
        json={"label": "Avenant renommé", "lock_version": counter_of(api, project, first)},
    )
    assert patched.status_code == 200, patched.text
    assert len(entries(project.stage)) == 4
    assert len(plans(project.stage)) == 1
    answer = abandoned(api, project, first)
    assert answer.status_code == 204, answer.text
    assert plans(project.stage) == []
    [remaining] = entries(project.stage)
    assert remaining.node_ids == [UUID(kept.json()["nodes"][0]["node_id"])]
    undone = api.post(
        f"{PROJECTS}/{project.project_id}/revisions/{project.revision_id}/undo", headers=who.headers
    )
    assert undone.status_code == 200, undone.text
    assert undone.json()["undone"]["node_ids"] == [kept.json()["nodes"][0]["node_id"]]
    again = api.post(
        f"{PROJECTS}/{project.project_id}/revisions/{project.revision_id}/undo", headers=who.headers
    )
    assert again.status_code == 409, again.text
    assert again.json()["params"] == {"missing_condition": "undo_history_not_empty"}


@pytest.mark.requirement("WF-SEC-0030-A")
def test_the_abandonment_is_inscribed_in_the_journal_with_its_structure_and_its_revision(
    api: ContractClient, project: Costed
) -> None:
    structure_id = opened_amendment(api, project, "Avenant « reprise des essais »")
    assert abandoned(api, project, structure_id).status_code == 204
    with project.stage.database.transaction() as session:
        found = session.scalars(
            select(AuditEntry).where(AuditEntry.action == "structure_abandon")
        ).all()
        [entry] = found
        assert (entry.object_kind, entry.object_id) == ("cost_structure", UUID(structure_id))
        assert entry.object_label == "Avenant « reprise des essais »"
        assert (entry.object_revision_id, entry.object_revision_label) == (
            project.revision_id,
            None,
        )
        assert entry.project_id == project.project_id
        assert entry.params == {}
        assert entry.actor_user_id == project.stage.manager.user_id
    # A refusal inscribes nothing.
    main = abandon(api, project, project.structure_id, 1)
    assert main.status_code == 409, main.text
    with project.stage.database.transaction() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuditEntry)
                .where(AuditEntry.action == "structure_abandon")
            )
            == 1
        )


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_revision_that_follows_does_not_know_the_differential_abandoned(
    api: ContractClient, project: Costed
) -> None:
    # « la révision suivante ne le connaît plus » : l'autre différentiel est repris, pas celui-là.
    stage = project.stage
    gone = opened_amendment(api, project, "Avenant abandonné")
    opened_amendment(api, project, "Avenant gardé")
    assert abandoned(api, project, gone).status_code == 204
    mark(stage, project.tree.revision)
    created = opened(api, stage)
    path = structures_path(project).replace(str(project.revision_id), created["revision_id"])
    structures = api.get(path, headers=stage.manager.headers).json()
    assert [(each["kind"], each["label"]) for each in structures] == [
        ("main", "Structure principale"),
        ("amendment", "Avenant gardé"),
    ]


# --- The refusals --------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_main_structure_is_not_abandoned_nor_the_own_estimate_of_a_risk_nor_a_merged_one(
    api: ContractClient, project: Costed
) -> None:
    risk = declared(project)
    merged = opened_amendment(api, project, "Avenant fusionné")
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(CostStructure).where(CostStructure.id == UUID(merged)).values(is_merged=True)
        )
    held = {each["structure_id"]: each for each in listed(api, project)}
    for structure_id in (project.tree.structure_id, str(risk.structure_id), merged):
        answer = abandon(api, project, structure_id, held[structure_id]["lock_version"])
        assert answer.status_code == 409, answer.text
        assert answer.json()["code"] == "STATE_FORBIDS_OPERATION"
        assert answer.json()["params"] == {"missing_condition": "unmerged_amendment_exists"}
        assert held_by(project, structure_id)["structure"] == 1
    assert project.tree.read().json()["items"]
    assert {each["structure_id"] for each in listed(api, project)} == set(held)


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_main_structure_example_of_the_contract_is_the_refusal_the_service_gives(
    api: ContractClient, project: Costed
) -> None:
    answer = abandon(api, project, project.tree.structure_id, 1)
    example = json.loads((FIXTURES / "structure_delete_main_refused.json").read_text())["value"]
    assert answer.status_code == example["status"] == 409
    assert {key: answer.json()[key] for key in ("code", "status", "params")} == {
        key: example[key] for key in ("code", "status", "params")
    }


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_marked_revision_refuses_the_abandonment_and_keeps_the_differential(
    api: ContractClient, project: Costed
) -> None:
    structure_id = opened_amendment(api, project)
    with_a_task(project, structure_id)
    counter = counter_of(api, project, structure_id)
    mark(project.stage, project.tree.revision)
    answer = abandon(api, project, structure_id, counter)
    assert answer.status_code == 409, answer.text
    assert answer.json()["params"] == {"missing_condition": "revision_draft"}
    assert held_by(project, structure_id)["node"] == 6
    example = json.loads((FIXTURES / "structure_delete_revision_marked.json").read_text())["value"]
    assert answer.json()["params"] == example["params"]
    # The main structure of a marked revision names the state of the revision first.
    main = abandon(api, project, project.tree.structure_id, 1)
    assert main.json()["params"] == {"missing_condition": "revision_draft"}


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_background_task_refuses_the_abandonment_and_the_command_says_it_in_advance(
    api: ContractClient, project: Costed
) -> None:
    structure_id = opened_amendment(api, project)
    counter = counter_of(api, project, structure_id)
    started_marking(api, project)
    answer = abandon(api, project, structure_id, counter)
    assert answer.status_code == 409, answer.text
    assert answer.json()["params"] == {"missing_condition": "no_background_task_running"}
    assert held_by(project, structure_id)["structure"] == 1
    found = next(each for each in listed(api, project) if each["structure_id"] == structure_id)
    assert commands_of(found)["delete"] == (False, ["no_background_task_running"])


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_terminal_project_names_that_the_project_is_not_terminal(
    api: ContractClient, project: Costed
) -> None:
    structure_id = opened_amendment(api, project)
    counter = counter_of(api, project, structure_id)
    mark(project.stage, project.tree.revision)
    for state in ("completed", "lost", "abandoned"):
        put_in_state(project.stage.owner, str(project.project_id), state)
        answer = abandon(api, project, structure_id, counter)
        assert answer.status_code == 409, answer.text
        assert answer.json()["params"] == {"missing_condition": "project_not_terminal"}
    assert held_by(project, structure_id)["structure"] == 1


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_structure_written_since_it_was_read_is_not_abandoned(
    api: ContractClient, project: Costed
) -> None:
    structure_id = opened_amendment(api, project)
    read = counter_of(api, project, structure_id)
    with_a_task(project, structure_id)
    now = counter_of(api, project, structure_id)
    assert now > read
    answer = abandon(api, project, structure_id, read)
    assert answer.status_code == 412, answer.text
    assert answer.json()["code"] == "STALE_LOCK_VERSION"
    assert answer.json()["params"] == {"expected_lock_version": now}
    assert held_by(project, structure_id)["node"] == 6
    assert abandon(api, project, structure_id, now).status_code == 204


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_abandonment_waits_for_a_write_in_flight_and_is_refused_at_the_counter_it_leaves(
    api: ContractClient, project: Costed
) -> None:
    # A write of the differential holds it ``FOR UPDATE``: the abandonment locks it before it judges
    # its counter, waits, then reads the counter the write left and is refused (412).
    structure_id = opened_amendment(api, project)
    read = counter_of(api, project, structure_id)
    with ThreadPoolExecutor(1) as others, project.stage.owner.begin() as writing:
        writing.execute(
            select(CostStructure.id).where(CostStructure.id == UUID(structure_id)).with_for_update()
        )
        asking = others.submit(abandon, api, project, structure_id, read)
        wait_for_a_lock(project.stage.database)
        assert not asking.done()
        writing.execute(
            update(CostStructure)
            .where(CostStructure.id == UUID(structure_id))
            .values(lock_version=read + 1)
        )
    answer = asking.result(timeout=10)
    assert answer.status_code == 412, answer.text
    assert answer.json()["params"] == {"expected_lock_version": read + 1}
    assert held_by(project, structure_id)["structure"] == 1


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_request_is_judged_before_the_state_unknown_structures_are_not_found(
    api: ContractClient, project: Costed
) -> None:
    structure_id = opened_amendment(api, project)
    unknown = abandon(api, project, UUID(int=9), 1)
    assert unknown.status_code == 404, unknown.text
    elsewhere = api.delete(
        f"{PROJECTS}/{project.project_id}/revisions/{UUID(int=7)}/structures/{structure_id}"
        "?lock_version=1",
        headers=project.stage.manager.headers,
    )
    assert elsewhere.status_code == 404, elsewhere.text
    for invalid in ("-1", "abc", ""):
        answer = abandon(api, project, structure_id, invalid)
        assert answer.status_code == 422, answer.text
    missing = api.delete(
        f"{structures_path(project)}/{structure_id}", headers=project.stage.manager.headers
    )
    assert missing.status_code == 422, missing.text
    assert held_by(project, structure_id)["structure"] == 1


# --- The command ---------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_command_delete_is_listed_on_a_differential_not_merged_alone(
    api: ContractClient, project: Costed
) -> None:
    risk = declared(project)
    first = opened_amendment(api, project, "Avenant 1")
    merged = opened_amendment(api, project, "Avenant fusionné")
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(CostStructure).where(CostStructure.id == UUID(merged)).values(is_merged=True)
        )
    held = {each["structure_id"]: commands_of(each) for each in listed(api, project)}
    assert held[first]["delete"] == (True, [])
    assert list(held[first]) == ["edit_planning", "edit_estimate", "delete"]
    for structure_id in (project.tree.structure_id, str(risk.structure_id), merged):
        assert "delete" not in held[structure_id]
    mark(project.stage, project.tree.revision)
    after = {each["structure_id"]: commands_of(each) for each in listed(api, project)}
    assert after[first]["delete"] == (False, ["revision_draft"])


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_command_delete_follows_the_permission_to_manage_the_revisions(
    api: ContractClient, project: Costed
) -> None:
    # The one that opens a differential abandons it (``create_structure``, ``revisions.write``): a
    # reader of the project is listed no such command and is refused by 403.
    stage = project.stage
    structure_id = opened_amendment(api, project)
    found = next(
        each for each in listed(api, project, stage.reader) if each["structure_id"] == structure_id
    )
    assert "delete" not in commands_of(found)
    answer = abandon(api, project, structure_id, 1, stage.reader)
    assert answer.status_code == 403, answer.text
    assert held_by(project, structure_id)["structure"] == 1


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_opening_answers_the_commands_of_the_example_of_the_contract(
    api: ContractClient, project: Costed
) -> None:
    # The example ``amendment_created``, « qui s'abandonne tant qu'il n'est pas fusionné » : the
    # commands the opening answers are its, ``delete`` included, in its order.
    example = json.loads((FIXTURES / "amendment_created.json").read_text())["value"]
    answer = open_amendment(api, project, example["label"])
    assert answer.status_code == 201, answer.text
    created = answer.json()
    assert created["available_commands"] == example["available_commands"]
    assert created["lock_version"] == example["lock_version"]
    assert abandoned(api, project, created["structure_id"]).status_code == 204


@pytest.mark.requirement("WF-IHM-0110-A")
def test_an_undoing_in_flight_while_the_differential_is_abandoned_ends_in_a_conflict(
    api: ContractClient, project: Costed, who: Person
) -> None:
    # The undoing of another stack has read its entry and waits for the lock of the structure the
    # abandonment holds first: when it has the lock, the structure and its nodes are gone, and it
    # ends in 409 ``UNDO_CONFLICT`` (``_judge``), not in a 404 or a failure.
    structure_id = opened_amendment(api, project)
    created = on(project.tree, structure_id).create("Essais", who)
    assert created.status_code == 201, created.text
    read = counter_of(api, project, structure_id)
    revision = f"{PROJECTS}/{project.project_id}/revisions/{project.revision_id}"
    with ThreadPoolExecutor(2) as others, project.stage.owner.begin() as writing:
        writing.execute(
            select(CostStructure.id).where(CostStructure.id == UUID(structure_id)).with_for_update()
        )
        abandoning = others.submit(abandon, api, project, structure_id, read)
        wait_for_a_lock(project.stage.database)
        undoing = others.submit(api.post, f"{revision}/undo", headers=who.headers)
        wait_for_a_lock(project.stage.database, 2)
        assert not abandoning.done()
        assert not undoing.done()
    assert abandoning.result(timeout=10).status_code == 204
    answer = undoing.result(timeout=10)
    assert answer.status_code == 409, answer.text
    assert answer.json()["code"] == "UNDO_CONFLICT"
    assert answer.json()["params"]["conflicting_object_id"] == created.json()["nodes"][0]["node_id"]
    assert held_by(project, structure_id)["structure"] == 0


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_entries_of_a_paste_applied_on_the_differential_leave_the_stack_with_it(
    api: ContractClient, project: Costed, who: Person
) -> None:
    # ``forget_structure`` keeps the entries that name no node by their snapshot alone, the label
    # of the structure: an entry of a paste, which names its nodes, leaves the stack as the others.
    structure_id = opened_amendment(api, project)
    other = on(project.tree, opened_amendment(api, project, "Avenant 2"))
    kept = other.create("Recette", who)
    assert kept.status_code == 201, kept.text
    tree = on(project.tree, structure_id)
    created = tree.create("Essais", who).json()["nodes"][0]
    plan = planned(tree, tree.node(created["node_id"]), "label", [["Un"], ["Deux"]], who)
    applied(tree, plan, who)
    assert len(entries(project.stage)) == 3
    assert abandoned(api, project, structure_id).status_code == 204
    [remaining] = entries(project.stage)
    assert remaining.node_ids == [UUID(kept.json()["nodes"][0]["node_id"])]
