# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The current revision, its abandonment, the history, the structures (US-0960), by the service.

``createRevision``, ``getRevision``, ``listRevisions``, ``abandonRevision`` and
``listCostStructures`` on a project its manager created (``projects_support``), every answer
checked against the contract. A revision is marked around the service, by the owner of the
tables, until the worker marks it (US-0970); the witness opens its revisions by the same rules.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from projects_support import MANAGING, PROJECTS, READING, Scene, person, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session
from support import wait_for_a_lock

from waterfall.core.projects.tables import Project
from waterfall.core.revisions.interface import revision_draft
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.platform.audit import AuditEntry
from waterfall.platform.database import utc_now
from waterfall.platform.errors import ConflictError, NotFoundError

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

PRJ_001 = UUID("01926f3a-7c00-7000-8000-000000000001")
PRJ_002 = UUID("01926f3a-7c00-7000-8000-000000000002")
OFFER = UUID("01926f3a-7c00-7000-8000-000000000100")
MARKED_AT = datetime(2026, 2, 1, 9, 0, tzinfo=UTC)


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


def mark_around(owner: Engine, revision: dict[str, Any], name: str, **columns: object) -> None:
    """Mark a revision as the worker will (US-0970), by the owner: the project without a current."""
    with owner.begin() as connection:
        connection.execute(
            update(Revision)
            .where(Revision.id == UUID(revision["revision_id"]))
            .values(status="marked", version_name=name, marked_at=MARKED_AT, **columns)
        )
        connection.execute(
            update(Project)
            .where(Project.id == UUID(revision["project_id"]))
            .values(current_revision_id=None)
        )


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
        assert (journal.actor_user_id, journal.project_id) == (stage.manager.user_id, None)
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
    mark_around(stage.owner, offer, "v1.0")
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
@pytest.mark.requirement("WF-REV-0100-A")
def test_a_revision_opened_from_a_marked_one_copies_its_structures_keeping_their_lineage(
    api: ContractClient, stage: Scene
) -> None:
    # « Après marquage d'une révision puis création de la suivante, le nombre de lignes de chaque
    # table portant l'identifiant de la nouvelle révision égale celui de la révision marquée » :
    # for ``cost_structure``, each copy its own row, of the lineage of the one it copies.
    offer = open_revision(api, stage)
    mark_around(stage.owner, offer, "v1.0")
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
    # are EP-08's: the main one, said merged around the service, stands for them.
    offer = open_revision(api, stage)
    with stage.owner.begin() as connection:
        connection.execute(
            update(CostStructure)
            .where(CostStructure.revision_id == UUID(offer["revision_id"]))
            .values(is_merged=True)
        )
    mark_around(stage.owner, offer, "v1.0")
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
    mark_around(stage.owner, offer, "v1.0")
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
    mark_around(stage.owner, offer, "Offre v1.0", description="Remise au client")
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
    mark_around(stage.owner, offer, "v1.0", reference_year=2025)
    current = open_revision(api, stage)
    assert current["reference_year"] == utc_now().year
    path = f"{revisions_of(stage.project['project_id'])}/{offer['revision_id']}"
    assert api.get(path, headers=stage.manager.headers).json()["reference_year"] == 2025


def test_a_marked_revision_is_not_abandoned(api: ContractClient, stage: Scene) -> None:
    # « abandonRevision refuse une révision marquée (409, revision_draft) »; nothing is deleted.
    offer = open_revision(api, stage)
    mark_around(stage.owner, offer, "v1.0")
    path = f"{revisions_of(stage.project['project_id'])}/{offer['revision_id']}"
    read = api.get(path, headers=stage.manager.headers).json()
    assert refusal(abandon(api, stage, read)) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "revision_draft"},
    )
    assert len(rows_of(stage.database, offer["revision_id"])) == 1


def test_an_abandonment_at_a_stale_counter_is_refused(api: ContractClient, stage: Scene) -> None:
    revision = open_revision(api, stage)
    stale = {**revision, "lock_version": revision["lock_version"] + 1}
    assert refusal(abandon(api, stage, stale)) == (
        412,
        "STALE_LOCK_VERSION",
        {"expected_lock_version": revision["lock_version"]},
    )
    assert project_of(api, stage)["current_revision_id"] == revision["revision_id"]


def test_a_terminal_project_opens_no_revision(api: ContractClient, stage: Scene) -> None:
    put_in_state(stage.owner, stage.project["project_id"], "lost")
    answer = api.post(
        revisions_of(stage.project["project_id"]), headers=stage.manager.headers, json={}
    )
    assert refusal(answer) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "project_not_terminal"},
    )


def test_a_participant_opens_a_revision_and_does_not_abandon_it(
    api: ContractClient, stage: Scene
) -> None:
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


def test_a_revision_is_read_only_through_its_own_project(
    api: ContractClient, stage: Scene, database: Database, realm: TestRealm
) -> None:
    revision = open_revision(api, stage)
    manager = person(database, realm, *MANAGING)
    other = api.post(PROJECTS, headers=manager.headers, json={"label": "Autre"}).json()
    elsewhere = f"{revisions_of(other['project_id'])}/{revision['revision_id']}"
    for path in (elsewhere, f"{elsewhere}/structures"):
        assert refusal(api.get(path, headers=manager.headers))[:2] == (404, "NOT_FOUND")


def test_a_write_in_a_marked_revision_is_refused(api: ContractClient, stage: Scene) -> None:
    # What the later epics write in a revision asks it current first (``revision_draft``).
    offer = open_revision(api, stage)
    with stage.database.transaction() as session:
        revision_draft(session, UUID(offer["revision_id"]))
    mark_around(stage.owner, offer, "v1.0")
    with stage.database.transaction() as session:
        with pytest.raises(ConflictError) as refused:
            revision_draft(session, UUID(offer["revision_id"]))
        assert refused.value.params == {"missing_condition": "revision_draft"}
        with pytest.raises(NotFoundError):
            revision_draft(session, uuid4())


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_witness_opens_its_first_revision_by_the_rules_of_the_opening(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The chronology opens the revision 100 of PRJ-001 first; the 101 waits for its marking
    # (US-0970). PRJ-002 has none.
    with witness.transaction() as session:
        revisions = session.scalars(select(Revision)).all()
        projects = {row.id: row.current_revision_id for row in session.scalars(select(Project))}
        [structure] = session.scalars(select(CostStructure)).all()
    assert [(row.id, row.project_id, row.status) for row in revisions] == [
        (OFFER, PRJ_001, "draft")
    ]
    assert projects == {PRJ_001: OFFER, PRJ_002: None}
    assert (structure.revision_id, structure.kind) == (OFFER, "main")
    reader = person(witness, realm, *READING)
    listed = api.get(revisions_of(str(PRJ_001)), headers=reader.headers)
    assert [item["revision_id"] for item in listed.json()["items"]] == [str(OFFER)]
