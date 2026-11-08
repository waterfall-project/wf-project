# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The current revision, its abandonment, the history, the structures (US-0960), by the service.

``createRevision``, ``getRevision``, ``listRevisions``, ``abandonRevision`` and
``listCostStructures`` on a project its manager created (``projects_support``), every answer
checked against the contract. A revision is marked by the transaction of the worker
(``mark_revision``, US-0970), without its task; the witness opens its revisions by the same rules.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from planning_support import give_a_task
from projects_support import MANAGING, PROJECTS, READING, Scene, person, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session
from support import wait_for_a_lock

from waterfall.core.projects.tables import Project
from waterfall.core.revisions.interface import (
    RevisionCopy,
    compute_indicators,
    mark_revision,
    register_copy,
    register_indicators,
    register_tasks_and_lines,
    revision_draft,
)
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.platform.audit import Act, AuditEntry
from waterfall.platform.database import utc_now
from waterfall.platform.errors import ConflictError, NotFoundError
from waterfall.platform.logs import logging_context
from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

PRJ_001 = UUID("01926f3a-7c00-7000-8000-000000000001")
PRJ_002 = UUID("01926f3a-7c00-7000-8000-000000000002")
OFFER = UUID("01926f3a-7c00-7000-8000-000000000100")
REFERENCE = UUID("01926f3a-7c00-7000-8000-000000000101")
CURRENT = UUID("01926f3a-7c00-7000-8000-000000000102")
MARKED_AT = datetime(2026, 2, 1, 9, 0, tzinfo=UTC)
EVENTS = "/api/v1/audit-events"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


def revisions_of(project_id: str) -> str:
    """Give the path of the revisions of a project."""
    return f"{PROJECTS}/{project_id}/revisions"


def open_revision(api: ContractClient, stage: Scene, **body: Any) -> dict[str, Any]:
    """Open the current revision of the project of the stage, as its manager does."""
    path = revisions_of(stage.project["project_id"])
    response = api.post(path, headers=stage.manager.headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def abandon(api: ContractClient, stage: Scene, revision: dict[str, Any]) -> Any:
    """Abandon a revision of the project of the stage at the counter read, as its manager does."""
    path = f"{revisions_of(stage.project['project_id'])}/{revision['revision_id']}"
    return api.delete(
        f"{path}?lock_version={revision['lock_version']}", headers=stage.manager.headers
    )


def mark_as_the_worker(
    owner: Engine,
    revision: dict[str, Any],
    name: str,
    *,
    description: str | None = None,
    **columns: object,
) -> None:
    """Mark a revision by the transaction of the worker (US-0970), at ``MARKED_AT``.

    ``columns`` are written on the current revision before, by the owner: what it was opened with.
    """
    revision_id = UUID(revision["revision_id"])
    if columns:
        with owner.begin() as connection:
            connection.execute(update(Revision).where(Revision.id == revision_id).values(**columns))
    with logging_context(correlation_id="marking"), Session(owner) as session, session.begin():
        mark_revision(session, revision_id, name, description, Act(None, MARKED_AT))


def structures(api: ContractClient, stage: Scene, revision_id: str) -> list[dict[str, Any]]:
    """Read the structures of a revision of the project of the stage, as its manager does."""
    path = f"{revisions_of(stage.project['project_id'])}/{revision_id}/structures"
    response = api.get(path, headers=stage.manager.headers)
    assert response.status_code == 200, response.text
    return response.json()


def rows_of(database: Database, revision_id: str) -> list[tuple[object, ...]]:
    """Read the structures that bear the identifier of a revision, every column of each."""
    with database.transaction() as session:
        found = session.scalars(
            select(CostStructure)
            .where(CostStructure.revision_id == UUID(revision_id))
            .order_by(CostStructure.id)
        ).all()
        return [
            (row.id, row.kind, row.label, row.is_merged, row.lineage_id, row.lock_version)
            for row in found
        ]


def project_of(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Read the project of the stage, as its manager does."""
    response = api.get(f"{PROJECTS}/{stage.project['project_id']}", headers=stage.manager.headers)
    assert response.status_code == 200
    return response.json()


def missing(listed: dict[str, Any]) -> dict[str, list[str]]:
    """Give the conditions each command of an object lacks, by command."""
    return {each["command"]: each["missing_conditions"] for each in listed["available_commands"]}


def refusal(response: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("params", {})


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_first_revision_is_born_current_with_its_main_structure_alone(
    api: ContractClient, stage: Scene
) -> None:
    # « La première révision d'un projet comporte, à sa création, une structure principale et
    # aucune autre » : current, of the year of today, copying nothing, the project naming it.
    revision = open_revision(api, stage)
    assert (revision["status"], revision["version_name"], revision["marked_at"]) == (
        "draft",
        None,
        None,
    )
    assert revision["reference_year"] == utc_now().year
    assert (revision["source_revision_id"], revision["source_version_name"]) == (None, None)
    assert revision["is_reference"] is False
    assert project_of(api, stage)["current_revision_id"] == revision["revision_id"]
    # Its manager may enter, mark and abandon it; the designation asks it marked, with tasks.
    assert missing(revision) == {
        "edit_planning": [],
        "edit_estimate": [],
        "edit_remaining": [],
        "mark": [],
        "designate_reference": ["revision_marked", "revision_has_tasks_and_lines"],
        "abandon": [],
    }
    [main] = structures(api, stage, revision["revision_id"])
    assert (main["kind"], main["label"], main["is_merged"]) == (
        "main",
        "Structure principale",
        False,
    )
    assert main["planning_start_on"] == revision["audit"]["created_at"][:10]
    # Before In progress, the main structure is estimated, its remaining not yet entered.
    assert missing(main) == {
        "edit_planning": [],
        "edit_estimate": [],
        "edit_remaining": ["project_in_progress"],
    }
    read = api.get(
        f"{revisions_of(stage.project['project_id'])}/{revision['revision_id']}",
        headers=stage.manager.headers,
    )
    assert (read.status_code, read.json()) == (200, revision)


def test_the_description_given_at_the_opening_is_kept_on_the_current_revision(
    api: ContractClient, stage: Scene
) -> None:
    # ``RevisionCreate.description`` is kept on the current revision, read with it, for its marking
    # to take up (#2171); none given, it has none. The Vérif of WF-REV-0090 is the marking's, which
    # ``test_revision_mark.py`` holds, in
    # ``test_the_description_of_the_marking_follows_the_rule_of_the_update_of_a_project``: this
    # test cites no requirement.
    revision = open_revision(api, stage, description="Chiffrage de l'appel d'offres")
    assert revision["description"] == "Chiffrage de l'appel d'offres"
    path = f"{revisions_of(stage.project['project_id'])}/{revision['revision_id']}"
    read = api.get(path, headers=stage.manager.headers)
    assert read.json()["description"] == "Chiffrage de l'appel d'offres"
    listed = api.get(revisions_of(stage.project["project_id"]), headers=stage.manager.headers)
    assert [item["description"] for item in listed.json()["items"]] == [
        "Chiffrage de l'appel d'offres"
    ]
    assert abandon(api, stage, revision).status_code == 204
    assert open_revision(api, stage)["description"] is None


@pytest.mark.requirement("WF-REV-0010-A")
def test_a_second_current_revision_is_refused_while_the_first_is_not_marked(
    api: ContractClient, stage: Scene
) -> None:
    # « La création d'une seconde révision en cours est refusée tant que la première n'est pas
    # marquée. » : the command says so beforehand, the call is refused by it, nothing written.
    open_revision(api, stage)
    assert missing(project_of(api, stage))["create_revision"] == ["no_current_revision"]
    second = api.post(
        revisions_of(stage.project["project_id"]), headers=stage.manager.headers, json={}
    )
    assert refusal(second) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "no_current_revision"},
    )
    with stage.database.transaction() as session:
        assert session.scalar(select(func.count()).select_from(Revision)) == 1


@pytest.mark.requirement("WF-REV-0010-A")
def test_two_openings_at_once_open_one_revision(api: ContractClient, stage: Scene) -> None:
    # Under the lock of the project: the second opening waits for the first, then reads the
    # current revision it wrote.
    path = revisions_of(stage.project["project_id"])
    with ThreadPoolExecutor(2) as others, Session(stage.database.engine) as holding:
        holding.execute(
            select(Project.id)
            .where(Project.id == UUID(stage.project["project_id"]))
            .with_for_update()
        )
        openings = [
            others.submit(api.post, path, headers=stage.manager.headers, json={}) for _ in range(2)
        ]
        wait_for_a_lock(stage.database)
        holding.commit()
        answers = sorted(opening.result(timeout=10).status_code for opening in openings)
    assert answers == [201, 409]
    with stage.database.transaction() as session:
        assert session.scalar(select(func.count()).select_from(Revision)) == 1


@pytest.mark.requirement("WF-REV-0010-A")
def test_the_unique_index_refuses_a_current_revision_the_lock_did_not_see(
    api: ContractClient, stage: Scene
) -> None:
    # « l'unicité est aussi une contrainte de la base » : a draft written around the lock, the
    # project not naming it, is still the one current revision; the opening is refused by it.
    project_id = UUID(stage.project["project_id"])
    with stage.owner.begin() as connection:
        written = uuid4()
        connection.execute(
            insert(Revision).values(
                id=written,
                project_id=project_id,
                status="draft",
                reference_year=2026,
                is_reference=False,
                lineage_id=written,
                created_at=MARKED_AT,
                updated_at=MARKED_AT,
            )
        )
    answer = api.post(revisions_of(str(project_id)), headers=stage.manager.headers, json={})
    assert refusal(answer) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "no_current_revision"},
    )
    with stage.database.transaction() as session:
        assert session.scalars(select(Revision.id)).all() == [written]
        assert session.scalar(select(CostStructure.id)) is None


@pytest.mark.requirement("WF-REV-0010-A")
@pytest.mark.requirement("WF-DAT-0010-A")
def test_abandoning_the_only_revision_leaves_the_project_in_pricing_without_one(
    api: ContractClient, stage: Scene
) -> None:
    # « L'abandon de l'unique révision d'un projet en chiffrage le laisse sans révision, à l'état
    # Chiffrage, et la création d'une révision y est de nouveau proposée. » ; « L'abandon d'une
    # révision en cours ne laisse aucune ligne portant son identifiant. » The passage to Pricing
    # is US-0980/L1's: the project is put there around the service.
    revision = open_revision(api, stage)
    put_in_state(stage.owner, stage.project["project_id"], "pricing")
    assert len(rows_of(stage.database, revision["revision_id"])) == 1
    answer = abandon(api, stage, revision)
    assert answer.status_code == 204
    project = project_of(api, stage)
    assert (project["state"], project["current_revision_id"]) == ("pricing", None)
    assert missing(project)["create_revision"] == []
    assert rows_of(stage.database, revision["revision_id"]) == []
    with stage.database.transaction() as session:
        assert session.get(Revision, UUID(revision["revision_id"])) is None
        journal = session.scalars(
            select(AuditEntry).where(AuditEntry.action == "revision_abandon")
        ).one()
        assert (journal.object_kind, journal.object_id, journal.object_label) == (
            "revision",
            UUID(revision["revision_id"]),
            None,
        )
        # The project, without code, is named all the same (#2166).
        assert (journal.actor_user_id, journal.project_id, journal.project_code) == (
            stage.manager.user_id,
            UUID(stage.project["project_id"]),
            None,
        )
    listed = api.get(revisions_of(stage.project["project_id"]), headers=stage.manager.headers)
    assert listed.json() == {"items": [], "meta": {"limit": 50, "offset": 0, "total": 0}}
    assert open_revision(api, stage)["source_revision_id"] is None


@pytest.mark.requirement("WF-REV-0010-A")
def test_after_an_abandonment_the_last_marked_revision_stands_and_another_opens(
    api: ContractClient, stage: Scene
) -> None:
    # « Après abandon d'une révision en cours, le projet présente les données de la dernière
    # révision marquée, et une nouvelle révision peut être créée. »
    offer = open_revision(api, stage)
    mark_as_the_worker(stage.owner, offer, "v1.0")
    current = open_revision(api, stage)
    assert (current["source_revision_id"], current["source_version_name"]) == (
        offer["revision_id"],
        "v1.0",
    )
    assert abandon(api, stage, current).status_code == 204
    assert project_of(api, stage)["current_revision_id"] is None
    path = revisions_of(stage.project["project_id"])
    read = api.get(f"{path}/{offer['revision_id']}", headers=stage.manager.headers)
    assert (read.status_code, read.json()["status"], read.json()["version_name"]) == (
        200,
        "marked",
        "v1.0",
    )
    reopened = open_revision(api, stage)
    assert reopened["source_revision_id"] == offer["revision_id"]


@pytest.mark.requirement("WF-DAT-0010-A")
@pytest.mark.requirement("WF-DAT-0030-A")
@pytest.mark.requirement("WF-REV-0100-A")
def test_a_revision_opened_from_a_marked_one_copies_its_structures_keeping_their_lineage(
    api: ContractClient, stage: Scene
) -> None:
    # « Après marquage d'une révision puis création de la suivante, le nombre de lignes de chaque
    # table portant l'identifiant de la nouvelle révision égale celui de la révision marquée » :
    # for ``cost_structure``, each copy its own row, of the lineage of the one it copies. A revision
    # holds one structure until EP-08: ``ck_cost_structure_kind_known`` admits the kind ``main``
    # alone, and ``uq_cost_structure_main`` one of it by revision; the owner writes no second one.
    offer = open_revision(api, stage)
    mark_as_the_worker(stage.owner, offer, "v1.0")
    current = open_revision(api, stage)
    marked, copied = (
        rows_of(stage.database, offer["revision_id"]),
        rows_of(stage.database, current["revision_id"]),
    )
    assert len(copied) == len(marked) == 1
    assert copied[0][0] != marked[0][0]
    assert copied[0][1:5] == marked[0][1:5]
    # The planning of a structure taken up starts on the day its lineage was born.
    [main] = structures(api, stage, current["revision_id"])
    assert main["planning_start_on"] == offer["audit"]["created_at"][:10]


@pytest.mark.requirement("WF-DAT-0010-A")
def test_the_copy_does_not_take_up_a_merged_structure(api: ContractClient, stage: Scene) -> None:
    # « … hors les lignes des structures différentielles fusionnées et des structures propres des
    # risques survenus » (#1759): a merged structure is consumed, and the copy leaves it. Its kinds
    # are EP-08's: the main one, said merged around the service, stands for them. No second
    # structure stays beside it, unmerged: the base admits one structure by revision, of the kind
    # ``main``, until EP-08 adds its kinds.
    offer = open_revision(api, stage)
    with stage.owner.begin() as connection:
        connection.execute(
            update(CostStructure)
            .where(CostStructure.revision_id == UUID(offer["revision_id"]))
            .values(is_merged=True)
        )
    mark_as_the_worker(stage.owner, offer, "v1.0")
    current = open_revision(api, stage)
    assert len(rows_of(stage.database, offer["revision_id"])) == 1
    assert rows_of(stage.database, current["revision_id"]) == []


@pytest.mark.requirement("WF-DAT-0010-A")
def test_a_change_in_the_current_revision_changes_no_row_of_a_marked_one(
    api: ContractClient, stage: Scene
) -> None:
    # « Une modification dans la révision en cours ne change aucune ligne portant l'identifiant
    # d'une révision marquée. » : the copy is rows of its own, and its abandonment deletes them
    # alone.
    offer = open_revision(api, stage)
    mark_as_the_worker(stage.owner, offer, "v1.0")
    before = rows_of(stage.database, offer["revision_id"])
    current = open_revision(api, stage)
    with stage.database.transaction() as session:
        session.execute(
            update(CostStructure)
            .where(CostStructure.revision_id == UUID(current["revision_id"]))
            .values(label="Principale reprise", lock_version=CostStructure.lock_version + 1)
        )
    assert rows_of(stage.database, offer["revision_id"]) == before
    assert abandon(api, stage, current).status_code == 204
    assert rows_of(stage.database, offer["revision_id"]) == before


@pytest.mark.requirement("WF-REV-0070-A")
@pytest.mark.requirement("WF-REV-0090-A")
def test_the_history_lists_the_marked_revisions_with_each_of_their_attributes(
    api: ContractClient, stage: Scene
) -> None:
    # « La liste des révisions marquées est accessible depuis le projet » ; « Chacun de ces
    # attributs est présent dans l'historique des révisions. » : name of version, description,
    # status, moment of the marking, year of reference, reference.
    offer = open_revision(api, stage)
    mark_as_the_worker(stage.owner, offer, "Offre v1.0", description="Remise au client")
    current = open_revision(api, stage)
    path = revisions_of(stage.project["project_id"])
    history = api.get(path, headers=stage.manager.headers).json()
    assert [item["revision_id"] for item in history["items"]] == [
        current["revision_id"],
        offer["revision_id"],
    ]
    assert history["meta"] == {"limit": 50, "offset": 0, "total": 2}
    marked = api.get(f"{path}?status=marked", headers=stage.manager.headers).json()
    [item] = marked["items"]
    assert {
        name: item[name]
        for name in (
            "version_name",
            "description",
            "status",
            "marked_at",
            "reference_year",
            "is_reference",
        )
    } == {
        "version_name": "Offre v1.0",
        "description": "Remise au client",
        "status": "marked",
        "marked_at": "2026-02-01T09:00:00Z",
        "reference_year": offer["reference_year"],
        "is_reference": False,
    }
    # A marked revision is modified no more: what would write in it lacks ``revision_draft``.
    assert missing(item)["mark"] == ["revision_draft"]
    assert missing(item)["designate_reference"] == ["revision_has_tasks_and_lines"]
    searched = api.get(f"{path}?search=remise", headers=stage.manager.headers).json()
    assert [each["revision_id"] for each in searched["items"]] == [offer["revision_id"]]
    page = api.get(f"{path}?limit=1&offset=1", headers=stage.manager.headers).json()
    assert [each["revision_id"] for each in page["items"]] == [offer["revision_id"]]
    assert page["meta"] == {"limit": 1, "offset": 1, "total": 2}
    wrong = api.get(f"{path}?status=lost", headers=stage.manager.headers)
    assert wrong.status_code == 422


@pytest.mark.requirement("WF-REV-0030-A")
@pytest.mark.requirement("WF-REV-0070-A")
def test_a_marked_revision_keeps_its_year_of_reference_and_the_next_takes_the_current_one(
    api: ContractClient, stage: Scene
) -> None:
    # A revision keeps what it was marked with: its year of reference, here; its rates are those
    # EP-07 keeps. The next one retains the current year.
    offer = open_revision(api, stage)
    mark_as_the_worker(stage.owner, offer, "v1.0", reference_year=2025)
    current = open_revision(api, stage)
    assert current["reference_year"] == utc_now().year
    path = f"{revisions_of(stage.project['project_id'])}/{offer['revision_id']}"
    assert api.get(path, headers=stage.manager.headers).json()["reference_year"] == 2025


def test_a_marked_revision_is_not_abandoned(api: ContractClient, stage: Scene) -> None:
    # « abandonRevision refuse une révision marquée (409, revision_draft) »; nothing is deleted. A
    # criterion of the story's own, which reprises no Vérif: it cites no requirement.
    offer = open_revision(api, stage)
    mark_as_the_worker(stage.owner, offer, "v1.0")
    path = f"{revisions_of(stage.project['project_id'])}/{offer['revision_id']}"
    read = api.get(path, headers=stage.manager.headers).json()
    assert refusal(abandon(api, stage, read)) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "revision_draft"},
    )
    assert len(rows_of(stage.database, offer["revision_id"])) == 1


@pytest.mark.requirement("WF-IHM-0110-A")
def test_an_abandonment_at_a_stale_counter_is_refused(api: ContractClient, stage: Scene) -> None:
    # A change another made since is not undone blindly: the counter read names the conflict.
    revision = open_revision(api, stage)
    stale = {**revision, "lock_version": revision["lock_version"] + 1}
    assert refusal(abandon(api, stage, stale)) == (
        412,
        "STALE_LOCK_VERSION",
        {"expected_lock_version": revision["lock_version"]},
    )
    assert project_of(api, stage)["current_revision_id"] == revision["revision_id"]


@pytest.mark.requirement("WF-CYC-0100-A")
def test_a_terminal_project_opens_no_revision(api: ContractClient, stage: Scene) -> None:
    # « Toute modification d'un projet terminal est refusée » : a revision opened is one.
    put_in_state(stage.owner, stage.project["project_id"], "lost")
    answer = api.post(
        revisions_of(stage.project["project_id"]), headers=stage.manager.headers, json={}
    )
    assert refusal(answer) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "project_not_terminal"},
    )
    with stage.database.transaction() as session:
        assert session.scalar(select(func.count()).select_from(Revision)) == 0


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_a_participant_opens_a_revision_and_does_not_abandon_it(
    api: ContractClient, stage: Scene
) -> None:
    # « Inscrit comme participant, il l'ouvre et saisit le devis, mais ne marque pas de révision » :
    # the abandonment is structuring as the marking is (WF-ADM-0100), reserved to the managers.
    path = revisions_of(stage.project["project_id"])
    opened = api.post(path, headers=stage.participant.headers, json={})
    assert opened.status_code == 201
    revision = opened.json()
    # Marking, designating and abandoning are structuring: a participant reads them unavailable.
    assert missing(revision)["abandon"] == ["is_project_manager"]
    answer = api.delete(
        f"{path}/{revision['revision_id']}?lock_version={revision['lock_version']}",
        headers=stage.participant.headers,
    )
    assert refusal(answer) == (
        403,
        "NOT_PROJECT_MANAGER",
        {"missing_condition": "is_project_manager"},
    )


@pytest.mark.requirement("WF-ADM-0110-A")
def test_a_revision_is_read_only_through_its_own_project(
    api: ContractClient, stage: Scene, database: Database, realm: TestRealm
) -> None:
    # « Une adresse d'objet inexistant et une adresse d'objet non consultable mènent au même
    # écran. » : a revision of a project its reader does not consult, addressed through his own,
    # is refused as a revision that does not exist.
    revision = open_revision(api, stage)
    manager = person(database, realm, *MANAGING)
    other = api.post(PROJECTS, headers=manager.headers, json={"label": "Autre"}).json()
    elsewhere = f"{revisions_of(other['project_id'])}/{revision['revision_id']}"
    unknown = f"{revisions_of(other['project_id'])}/{uuid4()}"
    for path in (elsewhere, f"{elsewhere}/structures", unknown, f"{unknown}/structures"):
        assert refusal(api.get(path, headers=manager.headers)) == (404, "NOT_FOUND", {})


def test_a_write_in_a_marked_revision_is_refused(api: ContractClient, stage: Scene) -> None:
    # What the later epics write in a revision asks it current first (``revision_draft``). The
    # rule of the design (EP-04, "Modules"), which reprises no Vérif: it cites no requirement.
    offer = open_revision(api, stage)
    with stage.database.transaction() as session:
        revision_draft(session, UUID(offer["revision_id"]))
    mark_as_the_worker(stage.owner, offer, "v1.0")
    with stage.database.transaction() as session:
        with pytest.raises(ConflictError) as refused:
            revision_draft(session, UUID(offer["revision_id"]))
        assert refused.value.params == {"missing_condition": "revision_draft"}
        with pytest.raises(NotFoundError):
            revision_draft(session, uuid4())


@pytest.mark.requirement("WF-SEC-0030-A")
def test_the_abandonment_in_a_coded_project_is_read_in_the_journal_naming_its_project(
    api: ContractClient, stage: Scene, database: Database, realm: TestRealm
) -> None:
    # « L'abandon d'une révision en cours […] produi[t] une inscription qui nomme l'action et
    # l'objet » : the revision, deleted, by its identifier and without a label; its project by its
    # code and its label (#927), read by ``listAuditEvents``.
    project = project_of(api, stage)
    coded = api.patch(
        f"{PROJECTS}/{project['project_id']}",
        headers=stage.manager.headers,
        json={"code": "PRJ-077", "lock_version": project["lock_version"]},
    )
    assert coded.status_code == 200, coded.text
    revision = open_revision(api, stage)
    assert abandon(api, stage, revision).status_code == 204
    auditor = person(database, realm, "audit_log.read", name="Ada")
    journal = api.get(f"{EVENTS}?actions=revision_abandon", headers=auditor.headers)
    assert journal.status_code == 200
    [event] = journal.json()["items"]
    assert (event["action"], event["object"], event["project"]) == (
        "revision_abandon",
        {"kind": "revision", "object_id": revision["revision_id"], "label": None, "revision": None},
        {
            "project_id": project["project_id"],
            "code": "PRJ-077",
            "label": project["label"],
            "can_open": False,
        },
    )
    assert (event["actor"]["kind"], event["actor"]["user_id"]) == (
        "user",
        str(stage.manager.user_id),
    )


@pytest.mark.requirement("WF-SEC-0030-A")
def test_the_abandonment_in_a_project_without_code_names_its_project_by_its_label(
    api: ContractClient, stage: Scene, database: Database, realm: TestRealm
) -> None:
    # A project is born without code (WF-PRJ-0010): the abandonment of its revision names it by
    # its label all the same, its code null (#2166).
    project = project_of(api, stage)
    assert project["code"] is None
    revision = open_revision(api, stage)
    assert abandon(api, stage, revision).status_code == 204
    auditor = person(database, realm, "audit_log.read", name="Ada")
    journal = api.get(f"{EVENTS}?actions=revision_abandon", headers=auditor.headers)
    assert journal.status_code == 200
    [event] = journal.json()["items"]
    assert event["project"] == {
        "project_id": project["project_id"],
        "code": None,
        "label": project["label"],
        "can_open": False,
    }


def test_an_abandonment_waits_for_the_write_that_judged_the_revision_current(
    api: ContractClient, stage: Scene
) -> None:
    # The locks of the design (EP-04, "Modules"), which reprise no Vérif: a write holds the revision
    # under ``FOR SHARE`` (``revision_draft``), and the abandonment, which locks it, waits for the
    # write to end before it deletes the revision.
    revision = open_revision(api, stage)
    with ThreadPoolExecutor(1) as others, Session(stage.database.engine) as writing:
        revision_draft(writing, UUID(revision["revision_id"]))
        abandoning = others.submit(abandon, api, stage, revision)
        wait_for_a_lock(stage.database)
        assert not abandoning.done()
        writing.commit()
        assert abandoning.result(timeout=10).status_code == 204
    assert project_of(api, stage)["current_revision_id"] is None


@pytest.mark.requirement("WF-IHM-0110-A")
def test_opening_a_revision_changes_the_counter_of_its_project(
    api: ContractClient, stage: Scene
) -> None:
    # The project names its current revision: a change made at the counter read before is refused,
    # naming the counter the opening left.
    before = project_of(api, stage)
    open_revision(api, stage)
    after = project_of(api, stage)
    assert after["lock_version"] > before["lock_version"]
    stale = api.patch(
        f"{PROJECTS}/{before['project_id']}",
        headers=stage.manager.headers,
        json={"label": "Autre", "lock_version": before["lock_version"]},
    )
    assert refusal(stale) == (
        412,
        "STALE_LOCK_VERSION",
        {"expected_lock_version": after["lock_version"]},
    )
    assert project_of(api, stage)["label"] == before["label"]


def test_a_structure_whose_lineage_lost_its_origin_is_listed_starting_on_its_own_creation(
    api: ContractClient, stage: Scene
) -> None:
    # An invariant of the realization, which reprises no Vérif: the origin of a lineage is always
    # there; were it not, the structure would still be listed, its planning started on its birth.
    # The case is written by giving the structure a lineage no row bears, which only holds because
    # ``lineage_id`` bears no foreign key: a lineage is an identifier the copies share, not a
    # reference (EP-04, "Tables et migrations"; #2179). A key added there makes the case impossible,
    # this ``UPDATE`` refused, and the test is withdrawn with the fallback it proves. The date is
    # read so from a row that the migration ``0023`` did not fill, its column null (#2170).
    revision = open_revision(api, stage)
    with stage.owner.begin() as connection:
        connection.execute(
            update(CostStructure)
            .where(CostStructure.revision_id == UUID(revision["revision_id"]))
            .values(
                lineage_id=uuid4(),
                created_at=datetime(2026, 3, 4, 8, 0, tzinfo=UTC),
                planning_start_on=None,
            )
        )
    [main] = structures(api, stage, revision["revision_id"])
    assert (main["kind"], main["planning_start_on"]) == ("main", "2026-03-04")


def test_a_copy_registered_by_a_later_module_comes_after_the_structures_and_reads_their_copies(
    api: ContractClient, stage: Scene
) -> None:
    # How EP-06, EP-07 and EP-08 extend the copy (``register_copy``), a detail of the realization
    # which reprises no Vérif: a copy registered receives the copies of the structures, once.
    received: list[tuple[UUID, UUID, dict[UUID, UUID]]] = []

    def copy_tasks(copy: RevisionCopy) -> None:
        received.append((copy.source, copy.target, dict(copy.identifiers)))

    with ExitStack() as registered:
        registered.callback(register_copy(copy_tasks))
        with pytest.raises(ValueError, match="registered already"):
            register_copy(copy_tasks)
        offer = open_revision(api, stage)
        assert received == []
        mark_as_the_worker(stage.owner, offer, "v1.0")
        current = open_revision(api, stage)
    [marked] = rows_of(stage.database, offer["revision_id"])
    [copied] = rows_of(stage.database, current["revision_id"])
    assert received == [
        (UUID(offer["revision_id"]), UUID(current["revision_id"]), {marked[0]: copied[0]})
    ]
    # Withdrawn, it copies no more.
    assert abandon(api, stage, current).status_code == 204
    open_revision(api, stage)
    assert len(received) == 1


def test_a_revision_bears_tasks_and_lines_when_every_question_registered_says_so(
    api: ContractClient, stage: Scene
) -> None:
    # How EP-06 and EP-07 answer ``revision_has_tasks_and_lines`` (``register_tasks_and_lines``),
    # a detail of the realization which reprises no Vérif: the planning answers whether the revision
    # bears a task (``revision_has_tasks``, US-1380/L1), EP-07 whether it bears a line; each part
    # needs its question, and every question registered must say yes.
    offer = open_revision(api, stage)
    path = f"{revisions_of(stage.project['project_id'])}/{offer['revision_id']}"

    def designation() -> list[str]:
        return missing(api.get(path, headers=stage.manager.headers).json())["designate_reference"]

    with ExitStack() as registered:
        registered.callback(register_tasks_and_lines("lines", lambda _session, _revision: True))
        mark_as_the_worker(stage.owner, offer, "v1.0")
        assert designation() == ["revision_has_tasks_and_lines"]
    offer = open_revision(api, stage)
    path = f"{revisions_of(stage.project['project_id'])}/{offer['revision_id']}"
    with stage.owner.begin() as connection:
        give_a_task(connection, UUID(offer["revision_id"]))
    mark_as_the_worker(stage.owner, offer, "v2.0")
    # Its tasks alone: no question of the lines, no designation.
    assert designation() == ["revision_has_tasks_and_lines"]
    with ExitStack() as registered:
        registered.callback(register_tasks_and_lines("lines", lambda _session, _revision: True))
        assert designation() == []
        lines = register_tasks_and_lines("lines", lambda _session, _revision: False)
        registered.callback(lines)
        assert designation() == ["revision_has_tasks_and_lines"]


def test_the_indicators_of_a_marking_are_those_of_every_computation_registered(
    database: Database,
) -> None:
    # How EP-10 keeps its indicators (``register_indicators``), a detail of the realization which
    # reprises no Vérif: each computation registered, in its order; none once withdrawn.
    computed: list[tuple[str, UUID]] = []
    revision_id = uuid4()
    with ExitStack() as registered, database.transaction() as session:
        registered.callback(
            register_indicators(lambda _session, revision: computed.append(("cpi", revision)))
        )
        registered.callback(
            register_indicators(lambda _session, revision: computed.append(("spi", revision)))
        )
        compute_indicators(session, revision_id)
    with database.transaction() as session:
        compute_indicators(session, revision_id)
    assert computed == [("cpi", revision_id), ("spi", revision_id)]


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_witness_opens_and_marks_its_revisions_as_the_service_and_the_worker_do(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The chronology opens the offer 100 of PRJ-001, marks it, opens the 101, marks it
    # « Référence », opens the 102: the names and the description of ``revisions.json``, each copy
    # of the last marked one. PRJ-002 has none.
    with witness.transaction() as session:
        revisions = {
            row.id: (row.status, row.version_name, row.description, row.source_revision_id)
            for row in session.scalars(select(Revision).where(Revision.project_id == PRJ_001))
        }
        projects = {row.id: row.current_revision_id for row in session.scalars(select(Project))}
        structures_of = {
            row.revision_id: row.lineage_id for row in session.scalars(select(CostStructure))
        }
    assert revisions == {
        OFFER: ("marked", "Offre v1.0", "Offre remise au client avant la commande.", None),
        REFERENCE: ("marked", "Référence", None, OFFER),
        CURRENT: ("draft", None, None, REFERENCE),
    }
    assert projects == {PRJ_001: CURRENT, PRJ_002: None}
    # One lineage, born with the main structure of the offer, kept by each copy (WF-DAT-0030).
    assert set(structures_of) == {OFFER, REFERENCE, CURRENT}
    assert len(set(structures_of.values())) == 1
    reader = person(witness, realm, *READING)
    listed = api.get(revisions_of(str(PRJ_001)), headers=reader.headers)
    assert [item["revision_id"] for item in listed.json()["items"]] == [
        str(CURRENT),
        str(REFERENCE),
        str(OFFER),
    ]


def test_a_withdrawal_withdraws_its_registration_once() -> None:
    # A detail of the realization which reprises no Vérif (#2179): called again, the withdrawal
    # does nothing, and never withdraws the same entry registered anew since.
    registry: Registry[str] = Registry()
    withdraw = registry.register("tasks")
    withdraw()
    withdraw()
    assert registry.entries() == ()
    again = registry.register("tasks")
    withdraw()
    assert registry.entries() == ("tasks",)
    again()
    assert registry.entries() == ()
