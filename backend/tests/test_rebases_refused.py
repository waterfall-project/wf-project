# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What refuses the update of a differential, and writes nothing (US-3050/L4).

A counter changed since the report — the main structure's or the differential's — is refused
(412, the counter of the differential named, the object the path names); a reason of the report,
judged on the differential the update would leave, is refused with its code and its parameters
(422), and the faulty link removed from the differential, the update goes through; a structure
that has no update is refused by the first condition its command lacks (409), in the order of the
contract; the update is guarded by the permission of the opening of a differential. In every case
the structures, their counters, the base and the links are as they were. Every answer is checked
against the contract (``ContractClient``).
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import (
    MAIN_RENAMED,
    OWN_RENAMED,
    OutOfDate,
    contributor_with,
    listed,
    node_labelled,
    opened_amendment,
    out_of_date,
    started_marking,
)
from estimate_support import Costing, Lines, add_role, costing
from history_support import link
from nodes_support import mark, put_facts
from projects_support import Scene, put_in_state
from projects_support import scene as make_scene
from rebases_support import (
    base_of,
    confirmation,
    lineages,
    links_of,
    read_report,
    rebase_path,
    rebased,
    state_of,
)
from risks_support import MAKING, STUDY, Costed, costed, declared
from sqlalchemy import update

from waterfall.core.revisions.tables import CostStructure

if TYPE_CHECKING:
    from collections.abc import Callable

    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

REFUSED = "STATE_FORBIDS_OPERATION"
FORMATION = "Formation"


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
def late(api: ContractClient, project: Costed) -> OutOfDate:
    """Give a differential out of date: the main structure moved on, the differential too."""
    return out_of_date(api, project)


def written(api: ContractClient, late: OutOfDate) -> dict[str, Any]:
    """Read everything an update may write: the structures, their nodes, the base, the links."""
    project, main, own = late.project, late.project.tree, late.amendment
    base = base_of(project, late.structure_id)
    return {
        "structures": [
            (each["structure_id"], each["lock_version"], each["is_up_to_date"])
            for each in listed(api, project)
        ],
        "main": main.read().json(),
        "own": own.read().json(),
        "base": lineages(project, base.id),
        "links": links_of(project, late.structure_id),
    }


def sent(project: Costed, structure_id: object, body: dict[str, Any]) -> Any:
    """Send a confirmation for a structure, as the manager does."""
    return project.tree.api.post(
        rebase_path(project, structure_id), headers=project.stage.manager.headers, json=body
    )


def refusal(answer: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = answer.json()
    return answer.status_code, body["code"], body.get("params", {})


# --- The counters ---------------------------------------------------------------------------------


@pytest.mark.parametrize("who", ["main", "differential"])
@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_counter_changed_since_the_report_is_refused_and_nothing_is_written(
    api: ContractClient, late: OutOfDate, who: str
) -> None:
    # « un compteur changé depuis la lecture, 412 STALE_LOCK_VERSION, rien n'est écrit »: the main
    # structure written since the report, or the differential; the counter named is the
    # differential's, the object the path names, even when only the main structure moved.
    project = late.project
    found = read_report(api, late)
    (project.tree if who == "main" else late.amendment).made("Livraison")
    held = written(api, late)
    current = state_of(api, project, late.structure_id)
    answer = sent(project, late.structure_id, confirmation(found))
    assert refusal(answer) == (
        412,
        "STALE_LOCK_VERSION",
        {"expected_lock_version": current["lock_version"]},
    )
    assert written(api, late) == held
    assert current["is_up_to_date"] is False
    # Read again, the report is confirmed.
    assert rebased(api, late).status_code == 200


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_body_that_is_no_confirmation_is_refused_and_nothing_is_written(
    api: ContractClient, late: OutOfDate
) -> None:
    # « Or a body that is not a confirmation (VALIDATION_FAILED) »: a confirmation that is not
    # true, a counter missing.
    found = read_report(api, late)
    held = written(api, late)
    declined = sent(late.project, late.structure_id, {**confirmation(found), "confirmed": False})
    assert declined.status_code == 422
    assert declined.json()["code"] == "VALIDATION_FAILED"
    partial = {
        key: value for key, value in confirmation(found).items() if key != "structure_lock_version"
    }
    assert sent(late.project, late.structure_id, partial).status_code == 422
    assert written(api, late) == held


# --- The reasons ----------------------------------------------------------------------------------


def a_loop(late: OutOfDate) -> None:
    """Make the update close a loop of links: Étude follows Réalisation there, and the reverse."""
    project, main, own = late.project, late.project.tree, late.amendment
    manager = project.stage.manager
    making = node_labelled(main, MAKING)
    assert link(main, making, manager, node_labelled(main, MAIN_RENAMED[1])).status_code == 200
    study = node_labelled(own, STUDY)
    assert link(own, study, manager, node_labelled(own, MAKING)).status_code == 200


def a_link_across_the_hierarchy(late: OutOfDate) -> None:
    """Make the update put a link between a summary and its subordinate: Réalisation under Étude."""
    project, main, own = late.project, late.project.tree, late.amendment
    manager = project.stage.manager
    held = state_of(main.api, project, main.structure_id)
    moving = {
        "node_ids": [node_labelled(main, MAKING)["node_id"]],
        "parent_id": node_labelled(main, MAIN_RENAMED[1])["node_id"],
        "lock_version": held["lock_version"],
    }
    moved = main.api.post(f"{main.path}/nodes/move", headers=manager.headers, json=moving)
    assert moved.status_code == 200, moved.text
    making = node_labelled(own, MAKING)
    assert link(own, making, manager, node_labelled(own, STUDY)).status_code == 200


def beyond_the_horizon(late: OutOfDate) -> None:
    """Make a task of the differential end beyond fifteen years, around the service."""
    making = node_labelled(late.amendment, MAKING)
    put_facts(late.project.stage, making["node_id"], duration_value=Decimal(6000))


def without_hours(late: OutOfDate) -> None:
    """Make a task bear two roles that share no hour of the week: one there, one in the main."""
    project, main, own = late.project, late.project.tree, late.amendment
    welder = add_role(project.stage.database, "SOUD", (8, 8, 8, 8, 8, 0, 0))
    fitter = add_role(project.stage.database, "MONT", (0, 0, 0, 0, 0, 8, 8))
    for tree, role, label in ((main, welder, "Soudure"), (own, fitter, "Montage week-end")):
        task = node_labelled(tree, OWN_RENAMED[1] if tree is own else FORMATION)
        line = {"label": label, "quantity": "1", "resource_role_id": str(role), "hours": "4"}
        Lines(tree).made(task, **line)


@pytest.mark.parametrize(
    ("make", "code"),
    [
        (a_loop, "LINK_CYCLE"),
        (a_link_across_the_hierarchy, "LINK_FORBIDDEN"),
        (beyond_the_horizon, "PROJECT_HORIZON_EXCEEDED"),
        (without_hours, "TASK_WITHOUT_WORKING_HOURS"),
    ],
)
@pytest.mark.requirement("WF-REV-0100-A")
def test_a_reason_of_the_report_refuses_the_update_by_its_code_and_nothing_is_written(
    api: ContractClient, late: OutOfDate, make: Callable[[OutOfDate], None], code: str
) -> None:
    # « une mise à jour qui laisserait dans le différentiel une boucle de liaisons, une liaison
    # interdite, une date au-delà de l'horizon ou une tâche sans heure travaillée est refusée, le
    # motif et la tâche nommés au compte rendu (ReportRefusal), et rien n'est écrit »: the first
    # reason of the report, its code and its parameters, 422.
    make(late)
    found = read_report(api, late)
    assert found["refusals"]
    held = written(api, late)
    answer = sent(late.project, late.structure_id, confirmation(found))
    assert refusal(answer) == (422, code, found["refusals"][0]["params"])
    assert written(api, late) == held


@pytest.mark.parametrize("make", [a_loop, a_link_across_the_hierarchy])
@pytest.mark.requirement("WF-REV-0100-A")
def test_the_faulty_link_removed_from_the_differential_the_update_goes_through(
    api: ContractClient, late: OutOfDate, make: Callable[[OutOfDate], None]
) -> None:
    # [US-3050]: a reason that is a link of the differential is lifted by an entry of the
    # differential, then the update is sent again, and goes through.
    make(late)
    assert rebased(api, late).status_code == 422
    own = late.amendment
    held = node_labelled(own, STUDY if make is a_loop else MAKING)
    assert link(own, held, late.project.stage.manager).status_code == 200
    answer = rebased(api, late)
    assert answer.status_code == 200, answer.text
    assert answer.json()["is_up_to_date"] is True


# --- The conditions of the command ----------------------------------------------------------------


def merged(late: OutOfDate) -> str:
    """Open a second differential and mark it merged, around the service; give it."""
    project = late.project
    structure_id = opened_amendment(project.tree.api, project, "Avenant fusionné")
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(CostStructure)
            .where(CostStructure.id == UUID(structure_id))
            .values(is_merged=True)
        )
    return structure_id


def up_to_date(late: OutOfDate) -> str:
    """Open a second differential, up to date: the main structure has not moved since."""
    return opened_amendment(late.project.tree.api, late.project, "Avenant à jour")


# What a confirmation sends of the counters, when the report of the structure is not given.
ANY = {"confirmed": True, "main_structure_lock_version": 1, "structure_lock_version": 1}


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_structure_that_is_no_differential_out_of_date_is_refused_by_its_first_condition(
    api: ContractClient, late: OutOfDate
) -> None:
    # « rebaseCostStructure est refusé par 409 sur la structure principale, sur un devis propre, sur
    # un différentiel fusionné, sur une révision marquée, pendant un traitement de fond et sur un
    # différentiel à jour, la première condition qui manque nommée dans l'ordre du contrat »: the
    # main structure, the own estimate of a risk and a merged differential lack
    # unmerged_amendment_exists; a differential up to date, structure_out_of_date; nothing is
    # written.
    project = late.project
    risk = declared(project)
    lacking = {"missing_condition": "unmerged_amendment_exists"}
    held = written(api, late)
    for structure_id in (project.tree.structure_id, str(risk.structure_id), merged(late)):
        assert refusal(sent(project, structure_id, ANY)) == (409, REFUSED, lacking)
    current = {"missing_condition": "structure_out_of_date"}
    assert refusal(sent(project, up_to_date(late), ANY)) == (409, REFUSED, current)
    after = written(api, late)
    assert {key: value for key, value in after.items() if key != "structures"} == {
        key: value for key, value in held.items() if key != "structures"
    }


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_background_task_is_named_before_the_conditions_of_the_structure(
    api: ContractClient, late: OutOfDate
) -> None:
    # « la première condition qui manque nommée dans l'ordre du contrat »: during a marking, the
    # task is named — before the structure that has no update, the main structure and a
    # differential up to date alike —, and nothing is written.
    project = late.project
    older = up_to_date(late)
    held = written(api, late)
    started_marking(api, project)
    running = {"missing_condition": "no_background_task_running"}
    for structure_id in (late.structure_id, project.tree.structure_id, older):
        assert refusal(sent(project, structure_id, ANY)) == (409, REFUSED, running)
    assert written(api, late) == held


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_update_is_refused_on_a_marked_revision_and_on_a_terminal_project(
    api: ContractClient, project: Costed
) -> None:
    # « sur une révision marquée »: the last marked revision of a project without a current one
    # waits for the revision to be created; a terminal project is judged before it.
    late = out_of_date(api, project)
    found = read_report(api, late)
    mark(project.stage, project.tree.revision)
    draft = {"missing_condition": "revision_draft"}
    answer = sent(project, late.structure_id, confirmation(found))
    assert refusal(answer) == (409, REFUSED, draft)
    put_in_state(project.stage.owner, str(project.project_id), "completed")
    terminal = {"missing_condition": "project_not_terminal"}
    answer = sent(project, late.structure_id, confirmation(found))
    assert refusal(answer) == (409, REFUSED, terminal)


@pytest.mark.requirement("WF-REV-0100-A")
def test_an_unknown_structure_and_a_base_are_not_found_and_the_conditions_come_before_the_counters(
    api: ContractClient, late: OutOfDate
) -> None:
    # « 404 »: a structure of no revision and a base, which no operation serves; the 409 comes
    # before the 412: a differential up to date is refused by its condition, whatever counters it
    # is sent.
    project = late.project
    base = base_of(project, late.structure_id)
    found = confirmation(read_report(api, late))
    assert sent(project, project.project_id, found).status_code == 404
    assert sent(project, base.id, found).status_code == 404
    assert rebased(api, late).status_code == 200
    stale = {**found, "structure_lock_version": 1}
    current = {"missing_condition": "structure_out_of_date"}
    assert refusal(sent(project, late.structure_id, stale)) == (409, REFUSED, current)


# --- The permission -------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_update_is_guarded_by_the_permission_of_the_opening_of_a_differential(
    api: ContractClient, late: OutOfDate, realm: TestRealm
) -> None:
    # « il est gardé par la permission de create_structure »: a contributor who reads the
    # revisions without managing them is refused (403), one who does not read them is not told the
    # structure exists (404); one who manages them updates it.
    project = late.project
    found = read_report(api, late)
    path = rebase_path(project, late.structure_id)
    held = written(api, late)
    reader = contributor_with(project, realm, "revisions.read")
    assert api.post(path, headers=reader.headers, json=confirmation(found)).status_code == 403
    stranger = contributor_with(project, realm)
    assert api.post(path, headers=stranger.headers, json=confirmation(found)).status_code == 404
    assert written(api, late) == held
    writer = contributor_with(project, realm, "revisions.read", "revisions.write")
    assert rebased(api, late, writer).status_code == 200
