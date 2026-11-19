# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The confirmation of a merge and its task (``mergeCostStructure``; US-2560/L2).

The confirmation judged in the order of the contract — the conditions of the command
``merge_structure``, the counters the report read, the differential up to date, the name of
version —, nothing deposited when refused; the task, one operation, which writes nothing when it
fails, leaves no revision opened, and enters nothing in the history that can be undone; the merge
inscribed in the journal before the marking and the designation it produces; the command of the
revision. Every answer is checked against the contract (``ContractClient``).
"""

from contextlib import ExitStack
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import (
    OutOfDate,
    commands_of,
    node_labelled,
    on,
    opened_amendment,
    out_of_date,
    revision_commands,
)
from estimate_support import Lines
from history_support import delete, undo
from merges_support import (
    REFUSED,
    STALE,
    asked,
    client,
    confirmation,
    copy_of,
    costed_project,
    main_of,
    merge_path,
    merged,
    merging_worker,
    project_of,
    read_report,
    revision_of,
    shape_of,
    structure_row,
    tasks_of,
)
from nodes_support import mark, opened, refusal, signed_in
from planning_support import insert_link
from projects_support import PROJECTS, contribute, person, put_in_state
from rebases_support import rebased
from risks_support import MAKING, STUDY, Costed, material
from sqlalchemy import func, select

from waterfall.core.history.tables import UndoEntry
from waterfall.core.revisions.interface import (
    MergePart,
    register_indicators,
    register_marking,
    register_merge_end,
)
from waterfall.core.revisions.tables import Revision
from waterfall.platform.audit import AuditEntry
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from datetime import datetime

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.core.revisions.interface import RevisionMarking, StructureMerging
    from waterfall.platform.audit import Act
    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.worker.runner import Worker


@pytest.fixture
def api(
    contract: OpenAPI,
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
) -> ContractClient:
    """Give a client of the application that deposits its tasks in the queue of the test."""
    return client(contract, database, keycloak, realm_settings, queue)


@pytest.fixture
def worker(database: Database, queue: TaskQueue) -> Worker:
    """Give a worker on the queue of the test that runs the merges."""
    return merging_worker(database, queue)


@pytest.fixture
def project(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed_project(api, owner, database, realm)


def revisions_counted(project: Costed) -> int:
    """Count the revisions of the project, around the service."""
    with project.stage.database.transaction() as session:
        counted = session.scalar(
            select(func.count())
            .select_from(Revision)
            .where(Revision.project_id == project.project_id)
        )
    return counted or 0


# Why a computation refuses, as the indicators of EP-10 may: a category without its rate.
HOURLY_RATE_MISSING = "HOURLY_RATE_MISSING"
MISSING_RATES = {
    "missing_rates": [{"cost_category_id": "01926f3a-7c00-7000-8000-000000000201", "year": 2026}]
}


def entries_of(project: Costed) -> list[tuple[UUID, str]]:
    """Read the entries of the history of the revision of the project, around the service."""
    with project.stage.database.transaction() as session:
        rows = session.execute(
            select(UndoEntry.id, UndoEntry.kind).where(UndoEntry.revision_id == project.revision_id)
        ).all()
        return sorted((each, kind) for each, kind in rows)


def held_counters(project: Costed, late: OutOfDate, name: str = "v2.0") -> dict[str, Any]:
    """Give a confirmation of the merge of a differential at the counters its structures bear."""
    return {
        "confirmed": True,
        "version_name": name,
        "main_structure_lock_version": structure_row(project, project.structure_id).lock_version,
        "amendment_lock_version": structure_row(project, late.structure_id).lock_version,
    }


def opened_amendment_in(api: ContractClient, project: Costed, revision_id: object) -> str:
    """Open a differential in a revision of the project, as the manager does; give it."""
    path = f"{PROJECTS}/{project.project_id}/revisions/{revision_id}/structures"
    body = {"kind": "amendment", "label": "Avenant 1"}
    answer = api.post(path, headers=project.stage.manager.headers, json=body)
    assert answer.status_code == 201, answer.text
    return answer.json()["structure_id"]


# --- The confirmation ----------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_write_of_either_structure_since_the_report_is_a_412_and_nothing_is_merged(
    api: ContractClient, project: Costed
) -> None:
    # « mergeCostStructure exige les compteurs lus […] : l'un ou l'autre changé depuis, 412
    # STALE_LOCK_VERSION, rien n'est fusionné »; « une écriture de la structure principale entre le
    # compte rendu et la confirmation est un 412 » (US-3050): it makes the differential out of date
    # as well, and the counters are judged first. ``expected_lock_version`` is the counter of the
    # differential, the object the path names.
    amendment = opened_amendment(api, project)
    path = merge_path(project, amendment)
    headers = project.stage.manager.headers
    found = read_report(api, project, amendment)
    on(project.tree, amendment).made("Essais")
    answer = api.post(path, headers=headers, json=confirmation(found))
    held = structure_row(project, amendment).lock_version
    assert refusal(answer) == (412, STALE, {"expected_lock_version": held})
    found = read_report(api, project, amendment)
    project.tree.made("Recette")
    again = api.post(path, headers=headers, json=confirmation(found))
    assert refusal(again) == (412, STALE, {"expected_lock_version": held})
    assert revision_of(api, project, project.revision_id)["status"] == "draft"
    assert structure_row(project, amendment).is_merged is False


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_differential_out_of_date_has_neither_report_nor_merge_until_it_is_updated(
    api: ContractClient, project: Costed
) -> None:
    # « getStructureMergeReport et mergeCostStructure d'un différentiel en retard sont refusés
    # par 409 STATE_FORBIDS_OPERATION, la condition nouvelle que le contrat ajoute, nommée après
    # les autres ; sur un différentiel à jour, le compte rendu est celui d'US-2560/L1 »: confirmed
    # at its own counters, read from the list of the structures, it is refused all the same; once
    # updated, it has its report.
    late = out_of_date(api, project)
    up_to_date = (409, REFUSED, {"missing_condition": "structure_up_to_date"})
    path = merge_path(project, late.structure_id)
    headers = project.stage.manager.headers
    assert refusal(api.get(path, headers=headers)) == up_to_date
    sent = held_counters(project, late)
    assert refusal(api.post(path, headers=headers, json=sent)) == up_to_date
    assert rebased(api, late).status_code == 200
    assert read_report(api, project, late.structure_id)["refusals"] == []


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_differential_out_of_date_under_a_name_taken_is_refused_as_out_of_date(
    api: ContractClient, project: Costed
) -> None:
    # « un différentiel en retard dont le nom de version est déjà pris est refusé par
    # structure_up_to_date, non par ALREADY_EXISTS » (#4186): on the last marked revision, which
    # bears the name, the differential waiting for the current revision where it is updated.
    late = out_of_date(api, project)
    mark(project.stage, {"revision_id": str(project.revision_id)}, label="pris")
    path = merge_path(project, late.structure_id)
    sent = held_counters(project, late, "pris")
    answer = api.post(path, headers=project.stage.manager.headers, json=sent)
    assert refusal(answer) == (409, REFUSED, {"missing_condition": "structure_up_to_date"})


@pytest.mark.requirement("WF-REV-0050-A")
def test_the_conditions_of_the_merge_are_judged_in_the_order_of_its_command(
    api: ContractClient, project: Costed, realm: TestRealm
) -> None:
    # « les conditions de la commande merge_structure sont nommées dans l'ordre du contrat »: the
    # main structure is no differential to merge (unmerged_amendment_exists); on the last marked
    # revision, to a manager who may not create a revision, may_create_revision; once another
    # revision is opened, revision_draft; a terminal project, project_not_terminal.
    stage = project.stage
    amendment = opened_amendment(api, project)
    found = read_report(api, project, amendment)
    headers = stage.manager.headers
    main = api.post(
        merge_path(project, project.structure_id), headers=headers, json=confirmation(found)
    )
    assert refusal(main) == (409, REFUSED, {"missing_condition": "unmerged_amendment_exists"})
    mark(stage, {"revision_id": str(project.revision_id)})
    taker = person(stage.database, realm, "revisions.read", "structure_merge", name="Sam")
    contribute(stage.database, stage.project["project_id"], taker, "project_manager")
    sent = confirmation(read_report(api, project, amendment))
    without = api.post(merge_path(project, amendment), headers=taker.headers, json=sent)
    assert refusal(without) == (409, REFUSED, {"missing_condition": "may_create_revision"})
    opened(api, stage)
    later = api.post(merge_path(project, amendment), headers=headers, json=sent)
    assert refusal(later) == (409, REFUSED, {"missing_condition": "revision_draft"})
    put_in_state(stage.owner, str(project.project_id), "completed")
    ended = api.post(merge_path(project, amendment), headers=headers, json=sent)
    assert refusal(ended) == (409, REFUSED, {"missing_condition": "project_not_terminal"})


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_name_of_version_a_marked_revision_bears_is_refused_and_nothing_is_queued(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « StructureMerge.version_name est exigé, unique parmi les révisions marquées du projet »:
    # the name of the offer marked refused, the revision that bears it named; absent, a 422.
    stage = project.stage
    mark(stage, {"revision_id": str(project.revision_id)}, label="Offre")
    opened(api, stage)
    current = project_of(api, project)["current_revision_id"]
    amendment = opened_amendment_in(api, project, current)
    answer = asked(api, project, amendment, current, name="Offre")
    assert answer.status_code == 409, answer.text
    assert answer.json()["code"] == "ALREADY_EXISTS"
    assert answer.json()["fields"][0]["params"] == {
        "conflicting_object_id": str(project.revision_id)
    }
    found = read_report(api, project, amendment, current)
    sent = {key: value for key, value in confirmation(found).items() if key != "version_name"}
    path = merge_path(project, amendment, current)
    lacking = api.post(path, headers=stage.manager.headers, json=sent)
    assert (lacking.status_code, lacking.json()["code"]) == (422, "VALIDATION_FAILED")
    assert not worker.step()


# --- The task ------------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0050-A")
def test_while_the_merge_runs_the_writes_of_the_revision_name_the_task(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « pendant qu'elle court, les écritures de la révision nomment no_background_task_running »
    amendment = opened_amendment(api, project)
    on(project.tree, amendment).made("Essais")
    assert asked(api, project, amendment).status_code == 202
    commands = revision_commands(api, project)
    running = "no_background_task_running"
    assert commands["edit_planning"] == (False, [running])
    assert commands["merge_structure"] == (False, [running])
    refused = project.tree.create("Recette")
    assert refusal(refused)[2] == {"missing_condition": running}
    assert worker.step()
    assert revision_of(api, project, project.revision_id)["status"] == "marked"


@pytest.mark.requirement("WF-REV-0050-A")
def test_the_merge_is_offered_where_a_differential_is_to_merge(
    api: ContractClient, project: Costed
) -> None:
    # « sur la dernière révision marquée d'un projet sans révision en cours la fusion est
    # offerte »: on the current revision once a differential is open; on the last marked revision
    # without a current revision; lacking revision_draft once a revision is current.
    assert revision_commands(api, project)["merge_structure"] == (
        False,
        ["unmerged_amendment_exists"],
    )
    opened_amendment(api, project)
    assert revision_commands(api, project)["merge_structure"] == (True, [])
    mark(project.stage, {"revision_id": str(project.revision_id)})
    marked = revision_of(api, project, project.revision_id)
    assert commands_of(marked)["merge_structure"] == (True, [])
    opened(api, project.stage)
    marked = revision_of(api, project, project.revision_id)
    assert commands_of(marked)["merge_structure"] == (False, ["revision_draft"])


@pytest.mark.requirement("WF-REV-0050-A")
def test_without_a_current_revision_the_merge_creates_it_merges_and_marks_it(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « sur un projet sans révision en cours, elle en crée une par copie de la dernière révision
    # marquée […], y fusionne la copie du différentiel et la marque »: the revision marked is not
    # written; the revision created bears the name confirmed and is the reference.
    amendment = opened_amendment(api, project)
    on(project.tree, amendment).made("Essais")
    mark(project.stage, {"revision_id": str(project.revision_id)})
    source = tasks_of(project, project.structure_id)
    assert read_report(api, project, amendment)["creates_current_revision"] is True
    task = merged(api, project, worker, amendment, name="Avenant 1")
    assert task["status"] == "succeeded", task
    assert tasks_of(project, project.structure_id) == source
    read = project_of(api, project)
    assert read["current_revision_id"] is None
    created = revision_of(api, project, read["reference_revision_id"])
    assert (created["status"], created["version_name"]) == ("marked", "Avenant 1")
    assert created["source_revision_id"] == str(project.revision_id)
    main = main_of(project, created["revision_id"])
    assert set(tasks_of(project, main)) == {STUDY, MAKING, "Essais"}
    assert structure_row(project, copy_of(project, amendment, created["revision_id"])).is_merged
    assert structure_row(project, amendment).is_merged is False


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_merge_that_fails_without_a_current_revision_leaves_none(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « en échec, sur un motif de refus ou tout autre, elle ne laisse ni fusion, ni révision
    # marquée, ni révision créée »: a loop of links the differential closes, written around the
    # service, which its entry refuses.
    amendment = opened_amendment(api, project)
    tree = on(project.tree, amendment)
    with project.stage.owner.begin() as connection:
        for before, after in ((STUDY, MAKING), (MAKING, STUDY)):
            connection.execute(
                insert_link(
                    project.project_id,
                    project.revision_id,
                    UUID(amendment),
                    UUID(node_labelled(tree, before)["node_id"]),
                    UUID(node_labelled(tree, after)["node_id"]),
                )
            )
    mark(project.stage, {"revision_id": str(project.revision_id)})
    counted = revisions_counted(project)
    task = merged(api, project, worker, amendment)
    assert (task["status"], task["problem"]["code"]) == ("failed", "LINK_CYCLE")
    assert revisions_counted(project) == counted
    assert project_of(api, project)["current_revision_id"] is None
    assert structure_row(project, amendment).is_merged is False


def failing_once_written(merging: StructureMerging) -> MergePart:
    """End a merge by a failure once everything is written; give nothing to its report."""
    if merging.applying:
        raise UnprocessableError(HOURLY_RATE_MISSING, MISSING_RATES)
    return MergePart()


def failing_at_the_marking(_session: Session, _revision_id: UUID, _act: Act) -> None:
    """Fail the computation of the indicators of a revision being marked, as EP-10 may."""
    raise UnprocessableError(HOURLY_RATE_MISSING, MISSING_RATES)


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_merge_that_fails_once_it_has_written_leaves_nothing_of_it(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « la fusion est une tâche de fond et une seule opération […] en échec, sur un motif de refus
    # ou tout autre, elle ne laisse ni fusion, ni révision marquée, ni révision créée »: a failure
    # at the end of the merge, once its tasks, its lines and the end of the planning are written
    # (``place_lines``, ``finish``): the main structure, the revisions, the reference and the
    # differential are as they were.
    amendment = opened_amendment(api, project)
    tree = on(project.tree, amendment)
    tests = tree.made("Essais")
    Lines(tree).made(tests, **material(project.costs, "Banc d'essai", "50.00"))
    assert delete(tree, node_labelled(tree, MAKING), project.stage.manager).status_code == 200
    held = (shape_of(project, project.structure_id), revisions_counted(project))
    reference = project_of(api, project)["reference_revision_id"]
    with ExitStack() as registered:
        registered.callback(register_merge_end(failing_once_written))
        task = merged(api, project, worker, amendment)
    assert (task["status"], task["problem"]["code"]) == ("failed", HOURLY_RATE_MISSING)
    assert (shape_of(project, project.structure_id), revisions_counted(project)) == held
    read = project_of(api, project)
    assert (read["current_revision_id"], read["reference_revision_id"]) == (
        str(project.revision_id),
        reference,
    )
    assert revision_of(api, project, project.revision_id)["status"] == "draft"
    assert structure_row(project, amendment).is_merged is False


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_merge_that_fails_at_the_marking_without_a_current_revision_leaves_none(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « Sans révision en cours, la même tâche ouvre la révision par copie, y fusionne la copie du
    # différentiel […] et la marque ; en échec, la transaction ne laisse rien » (conception): the
    # failure comes at the marking, once the revision is opened and the copy merged into it.
    amendment = opened_amendment(api, project)
    on(project.tree, amendment).made("Essais")
    mark(project.stage, {"revision_id": str(project.revision_id)})
    held = (shape_of(project, project.structure_id), revisions_counted(project))
    reference = project_of(api, project)["reference_revision_id"]
    with ExitStack() as registered:
        registered.callback(register_indicators(failing_at_the_marking))
        task = merged(api, project, worker, amendment)
    assert (task["status"], task["problem"]["code"]) == ("failed", HOURLY_RATE_MISSING)
    assert (shape_of(project, project.structure_id), revisions_counted(project)) == held
    read = project_of(api, project)
    assert (read["current_revision_id"], read["reference_revision_id"]) == (None, reference)
    assert structure_row(project, amendment).is_merged is False


def journal(project: Costed) -> tuple[list[tuple[str, str, str | None, datetime]], set[object]]:
    """Read the journal of the project: each entry's action, object, revision named and instant.

    And the authors of the last three.
    """
    with project.stage.database.transaction() as session:
        rows = session.scalars(
            select(AuditEntry)
            .where(AuditEntry.project_id == project.project_id)
            .order_by(AuditEntry.id)
        ).all()
        found = [
            (row.action, str(row.object_id), row.object_revision_label, row.occurred_at)
            for row in rows
        ]
        return found, {row.actor_user_id for row in rows[-3:]}


@pytest.mark.requirement("WF-SEC-0030-A")
def test_the_merge_is_inscribed_before_the_marking_and_the_designation_it_produces(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « la fusion […] s'inscrit au journal »: structure_merge on the differential, its revision
    # named by the name confirmed, then revision_mark and reference_designate on the revision, at
    # one instant, by the requester.
    amendment = opened_amendment(api, project)
    merged(api, project, worker, amendment, name="Avenant 1")
    found, authors = journal(project)
    [merge, marking, reference] = found[-3:]
    assert merge[:3] == ("structure_merge", amendment, "Avenant 1")
    assert marking[:2] == ("revision_mark", str(project.revision_id))
    assert reference[:2] == ("reference_designate", str(project.revision_id))
    assert merge[3] == marking[3] == reference[3]
    assert authors == {project.stage.manager.user_id}


@pytest.mark.requirement("WF-SEC-0030-A")
def test_without_a_current_revision_the_journal_names_the_copy_of_the_differential_merged(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « Sans révision en cours, la même tâche ouvre la révision par copie, y fusionne la copie du
    # différentiel » (conception): the object of structure_merge is the copy, merged in the
    # revision the merge creates and marks — the differential of the marked revision is untouched.
    amendment = opened_amendment(api, project)
    mark(project.stage, {"revision_id": str(project.revision_id)})
    merged(api, project, worker, amendment, name="Avenant 1")
    created = project_of(api, project)["reference_revision_id"]
    copy = copy_of(project, amendment, created)
    found, authors = journal(project)
    [merge, marking, reference] = found[-3:]
    assert merge[:3] == ("structure_merge", str(copy), "Avenant 1")
    assert marking[:2] == ("revision_mark", created)
    assert reference[:2] == ("reference_designate", created)
    assert merge[3] == marking[3] == reference[3]
    assert authors == {project.stage.manager.user_id}
    assert all(each[1] != amendment for each in found)


@pytest.mark.requirement("WF-IHM-0110-A")
def test_no_undoing_takes_back_a_merge(
    api: ContractClient, project: Costed, worker: Worker, realm: TestRealm
) -> None:
    # « Aucune commande n'annule […] une fusion » (US-2590, #4211): a contributor's entry, the
    # last of their history, then the merge, which enters none — the entries of the revision, read
    # by the marking the merge calls, just before it finishes the history, are those it had —:
    # their undoing is refused, and the merge stays.
    who = signed_in(project.stage, realm)
    project.tree.made("Recette", who=who)
    amendment = opened_amendment(api, project)
    on(project.tree, amendment).made("Essais")
    before = entries_of(project)
    seen: list[list[tuple[UUID, str]]] = []

    def entries_at_the_marking(marking: RevisionMarking) -> None:
        seen.append(
            sorted(
                (each, kind)
                for each, kind in marking.session.execute(
                    select(UndoEntry.id, UndoEntry.kind).where(
                        UndoEntry.revision_id == marking.revision_id
                    )
                ).all()
            )
        )

    with ExitStack() as registered:
        registered.callback(register_marking(entries_at_the_marking))
        merged(api, project, worker, amendment)
    assert before
    assert seen == [before]
    assert entries_of(project) == []
    status, code, params = refusal(undo(project.tree, who))
    assert (status, code, params) == (409, REFUSED, {"missing_condition": "revision_draft"})
    assert set(tasks_of(project, project.structure_id)) == {STUDY, MAKING, "Recette", "Essais"}
