# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The application of an extraction of the actual costs, and its idempotence.

Laid by US-1580/L1, the socle of EP-09, so that no two stories create the same file;
US-1610/L2 writes its tests here ("Les tests du back"): an extraction opened, analysed and confirmed
through the service, then applied by the worker in the transaction of its task — the lines inserted
or updated on their document and item, their imputation computed again, their exclusion kept, the
entry of the log and its four counts —, the same file imported twice, two periods that overlap, an
amount changed, a line imputed again, and an application that waits for the creation of a
subproject. Every answer of the service is checked against the contract.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from actual_costs_import_support import (
    CODE,
    SUBPROJECT,
    declare,
    extraction,
    in_progress,
    line,
    opening,
    subproject,
)
from fastapi.testclient import TestClient
from imports_trial import apply, import_worker, read, run
from projects_support import Scene
from projects_support import scene as make_scene
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from support import ContractClient, wait_for_a_lock

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.costs.interface import ACTUAL_COSTS_FORMAT, PROJECT, actual_costs_until
from waterfall.core.costs.tables import CostImport, CostLine
from waterfall.core.exchanges.interface import ImportTarget
from waterfall.core.history.tables import UndoEntry
from waterfall.core.projects.interface import (
    SubprojectWrite,
    Viewer,
    create_subproject,
    lock_project,
)
from waterfall.platform.audit import Act, AuditEntry
from waterfall.platform.database import utc_now
from waterfall.platform.keycloak_admin import KeycloakAdmin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket
    from waterfall.worker.runner import Worker

ELEMENT = f"{CODE}/{SUBPROJECT}"
# A day after every line of the tests: the sum of the lines tracked until it is their whole sum.
LATER = date(2099, 12, 31)


@pytest.fixture
def import_services(
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
    backups_bucket: Bucket,
) -> Services:
    """Give the services of the API on the database, the queue and the bucket of the test."""
    administration = KeycloakAdmin(keycloak, realm_settings)
    return Services(database, keycloak, administration, queue, backups_bucket)


@pytest.fixture
def api(contract: OpenAPI, import_services: Services) -> ContractClient:
    """Give a client of the service that deposits in the queue and the bucket of the test."""
    app = create_app(import_services)
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a project In progress, code A.ABC.26001, and the mapping declared."""
    made = make_scene(api, owner, database, realm)
    in_progress(made)
    declare(database)
    return made


@pytest.fixture
def lot(api: ContractClient, stage: Scene) -> str:
    """Give the subproject 10001 of the project of the stage."""
    return subproject(api, stage)


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports."""
    return import_worker(database, queue, backups_bucket)


def analysed(
    api: ContractClient, stage: Scene, worker: Worker, content: bytes, **body: Any
) -> dict[str, Any]:
    """Open the import of an extraction as the manager does, over a period if given; analyse it."""
    response = opening(api, stage, content, **body)
    assert response.status_code == 202, response.text
    run(worker)
    found = read(api, stage, response.json()["import_id"])
    assert found["status"] == "analysed", found
    return found


def confirmed(api: ContractClient, stage: Scene, worker: Worker, found: dict[str, Any]) -> None:
    """Confirm an import analysed, as the participant does, and run its application."""
    response = apply(api, stage, found["import_id"], stage.participant)
    assert response.status_code == 202, response.text
    run(worker)
    assert read(api, stage, found["import_id"])["status"] == "applied"


def imported(
    api: ContractClient, stage: Scene, worker: Worker, content: bytes, **body: Any
) -> dict[str, Any]:
    """Open, analyse and apply an extraction, confirmed by the participant; give its report."""
    found = analysed(api, stage, worker, content, **body)
    confirmed(api, stage, worker, found)
    return found["report"]


def project_of(stage: Scene) -> UUID:
    return UUID(stage.project["project_id"])


def lines(stage: Scene) -> list[CostLine]:
    """Read the lines of cost of the project of the stage, by document and item."""
    with stage.database.transaction() as session:
        found = session.scalars(
            select(CostLine)
            .where(CostLine.project_id == project_of(stage))
            .order_by(CostLine.document_number, CostLine.document_item)
        ).all()
        session.expunge_all()
        return list(found)


def log(api: ContractClient, stage: Scene, **query: Any) -> dict[str, Any]:
    """Read the log of the imports of the project of the stage, as its reader does."""
    response = api.get(
        f"/api/v1/projects/{stage.project['project_id']}/cost-imports",
        headers=stage.reader.headers,
        params=query,
    )
    assert response.status_code == 200, response.text
    return response.json()


def counts(entry: dict[str, Any]) -> tuple[int, int, int, int]:
    """Give the four counts of an entry of the log: created, updated, unchanged, rejected."""
    return (
        entry["created_count"],
        entry["updated_count"],
        entry["unchanged_count"],
        entry["rejected_count"],
    )


def total(stage: Scene) -> Decimal:
    """Sum the tracked lines of the project of the stage."""
    with stage.database.transaction() as session:
        return actual_costs_until(session, project_of(stage), LATER, PROJECT)


def exclude(stage: Scene, number: str, reason: str) -> None:
    """Exclude a line of the project from the scope tracked, around the service."""
    with stage.owner.begin() as connection:
        connection.execute(
            update(CostLine)
            .where(CostLine.project_id == project_of(stage), CostLine.document_number == number)
            .values(is_in_tracked_scope=False, excluded_reason=reason)
        )


def keyed(rows: Sequence[CostLine]) -> list[tuple[str, str | None, Decimal, bool]]:
    return [
        (row.document_number, row.document_item, row.amount, row.is_in_tracked_scope)
        for row in rows
    ]


# An extraction of April: a line of the subproject, a credit of the project alone in an item, a
# line of another project.
APRIL = extraction(
    [
        line(element=ELEMENT, number="5100001234", amount=1250),
        line(element=CODE, number="5100001300", item="10", amount=-300.5, on="2026-04-12"),
        line(element="A.ABC.26002/10001", number="5100001400"),
    ]
)


@pytest.mark.requirement("WF-INTF-0140-A")
@pytest.mark.requirement("WF-DAT-0110-A")
@pytest.mark.usefixtures("lot")
def test_two_imports_of_the_same_file_give_the_same_total_and_keep_an_exclusion(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Deux imports successifs du même fichier donnent le même total de coûts réels. » : the second
    # counts all its lines unchanged, none created. « Deux imports du même fichier de coûts réels
    # laissent le même nombre de lignes et les mêmes montants, et une ligne exclue le reste. »
    imported(api, stage, worker, APRIL)
    exclude(stage, "5100001300", "Avoir hors contrat")
    first, before = lines(stage), total(stage)
    assert before == Decimal("1250.00")

    report = imported(api, stage, worker, APRIL)

    assert (report["differences"], report["unchanged_count"]) == ([], 2)
    entries = log(api, stage)["items"]
    assert [counts(entry) for entry in entries] == [(0, 0, 2, 1), (2, 0, 0, 1)]
    again = lines(stage)
    assert keyed(again) == keyed(first)
    assert [row.id for row in again] == [row.id for row in first]
    assert (again[1].is_in_tracked_scope, again[1].excluded_reason) == (False, "Avoir hors contrat")
    assert total(stage) == before
    # A line the second import does not change is not written again: its last import is the first.
    assert {row.last_import_id for row in again} == {UUID(entries[1]["cost_import_id"])}
    assert all(row.updated_at == row.created_at for row in again)


@pytest.mark.requirement("WF-INTF-0140-A")
@pytest.mark.requirement("WF-CRE-0050-A")
def test_a_line_in_two_extractions_whose_periods_overlap_is_counted_once(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Si deux fichiers ont des périodes qui se recouvrent, une ligne présente dans les deux n'est
    # comptée qu'une fois. » : unchanged by the second; each import logs its period.
    march = extraction(
        [
            line(element=CODE, number="FA-1", on="2026-03-20", amount=400),
            line(element=CODE, number="FA-2", on="2026-04-02", amount=600),
        ]
    )
    april = extraction(
        [
            line(element=CODE, number="FA-2", on="2026-04-02", amount=600),
            line(element=CODE, number="FA-3", on="2026-04-20", amount=150),
        ]
    )
    imported(api, stage, worker, march, period_from="2026-03-01", period_to="2026-04-15")
    imported(api, stage, worker, april, period_from="2026-04-01", period_to="2026-04-30")

    assert [row.document_number for row in lines(stage)] == ["FA-1", "FA-2", "FA-3"]
    assert total(stage) == Decimal("1150.00")
    entries = log(api, stage)["items"]
    assert [(entry["period_from"], entry["period_to"], counts(entry)) for entry in entries] == [
        ("2026-04-01", "2026-04-30", (1, 0, 1, 0)),
        ("2026-03-01", "2026-04-15", (2, 0, 0, 0)),
    ]


@pytest.mark.requirement("WF-INTF-0140-A")
@pytest.mark.requirement("WF-DAT-0070-A")
def test_a_line_whose_amount_changed_is_updated_and_keeps_its_exclusion(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Une ligne déjà importée dont le montant a changé dans l'ERP est mise à jour, et son
    # exclusion est préservée. » — « Une ligne créée par un import porte le compte qui l'a
    # confirmé. » : the participant confirms, after the manager opened; mise à jour par un
    # réimport, `updated_by` the account that confirmed the second.
    imported(api, stage, worker, extraction([line(element=CODE, number="FA-7", amount=900)]))
    exclude(stage, "FA-7", "Refacturé au client")
    [held] = lines(stage)
    assert (held.created_by, held.updated_by) == (stage.participant.user_id,) * 2

    found = analysed(
        api, stage, worker, extraction([line(element=CODE, number="FA-7", amount=950)])
    )
    assert found["report"]["differences"] == [
        {
            "change": "updated",
            "target": "actual_cost_line",
            "lineage_id": None,
            "label": "FA-7",
            "document_item": None,
            "fields": ["amount"],
        }
    ]
    response = apply(api, stage, found["import_id"])
    assert response.status_code == 202, response.text
    run(worker)

    [again] = lines(stage)
    latest = log(api, stage)["items"][0]
    assert (again.id, again.amount) == (held.id, Decimal("950.00"))
    assert (again.is_in_tracked_scope, again.excluded_reason) == (False, "Refacturé au client")
    assert (again.created_by, again.created_at) == (stage.participant.user_id, held.created_at)
    assert (again.updated_by, again.last_import_id) == (
        stage.manager.user_id,
        UUID(latest["cost_import_id"]),
    )
    assert again.updated_at > held.updated_at
    assert counts(latest) == (0, 1, 0, 0)


@pytest.mark.requirement("WF-CRE-0020-A")
def test_a_line_imported_again_with_another_wbs_element_is_imputed_again(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Une ligne réimportée avec un autre élément d'OTP change d'imputation. » : by the real
    # application of an import, the line found by its document and its item, its subproject computed
    # again from its code — another subproject, a code no subproject bears, none —, compared as
    # stored, its exclusion kept.
    cabling = UUID(subproject(api, stage, "10001"))
    automation = UUID(subproject(api, stage, "10002"))
    imported(api, stage, worker, extraction([line(element=f"{CODE}/10001", number="FA-9")]))
    [first] = lines(stage)
    assert first.subproject_id == cabling
    exclude(stage, "FA-9", "Hors périmètre")

    imputations: list[tuple[UUID | None, str | None]] = []
    for element in (f"{CODE}/10002", f"{CODE}/99999", CODE):
        report = imported(api, stage, worker, extraction([line(element=element, number="FA-9")]))
        assert report["differences"][0]["fields"] == ["subproject"]
        [held] = lines(stage)
        assert (held.id, held.is_in_tracked_scope) == (first.id, False)
        imputations.append((held.subproject_id, held.subproject_code))

    assert imputations == [(automation, "10002"), (None, "99999"), (None, None)]
    assert counts(log(api, stage)["items"][0]) == (0, 1, 0, 0)


@pytest.mark.requirement("WF-CRE-0010-A")
@pytest.mark.requirement("WF-DAT-0070-A")
def test_each_line_imported_bears_its_four_attributes_and_its_columns_kept(
    api: ContractClient, stage: Scene, worker: Worker, lot: str
) -> None:
    # « Les quatre attributs significatifs sont renseignés pour chaque ligne importée. » : the
    # document, the date, the amount, the imputation; the item when the extraction gives it.
    # « Une ligne de montant négatif est acceptée et diminue le coût réel. » « Une colonne que la
    # correspondance ne déclare pas conservée ne l'est pas. » : « Nom Matricule », ignored.
    imported(api, stage, worker, APRIL)

    held = lines(stage)
    assert [
        (
            row.document_number,
            row.document_item,
            row.document_date,
            row.amount,
            row.subproject_id,
            row.subproject_code,
            row.passthrough,
        )
        for row in held
    ] == [
        (
            "5100001234",
            None,
            date(2026, 4, 2),
            Decimal("1250.00"),
            UUID(lot),
            SUBPROJECT,
            {"Fournisseur": "Atelier Durand"},
        ),
        (
            "5100001300",
            "10",
            date(2026, 4, 12),
            Decimal("-300.50"),
            None,
            None,
            {"Fournisseur": "Atelier Durand"},
        ),
    ]
    assert {(row.created_by, row.is_in_tracked_scope) for row in held} == {
        (stage.participant.user_id, True)
    }
    assert total(stage) == Decimal("949.50")
    with stage.database.transaction() as session:
        [entry] = session.scalars(select(CostImport)).all()
        assert (entry.requested_by, entry.passthrough_columns) == (
            stage.participant.user_id,
            ["Fournisseur"],
        )
        assert {row.last_import_id for row in held} == {entry.id}


@pytest.mark.requirement("WF-CRE-0050-A")
def test_the_log_presents_each_import_dated_with_its_author_and_its_counts_latest_first(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Après un import, le journal présente une entrée datée du jour avec ses comptes de lignes » :
    # `actor` the account that confirmed, the period, the four counts, the latest first, by pages.
    assert log(api, stage) == {"items": [], "meta": {"limit": 50, "offset": 0, "total": 0}}
    before = utc_now()
    imported(api, stage, worker, APRIL, period_from="2026-04-01", period_to="2026-04-30")
    imported(api, stage, worker, extraction([line(element=CODE, number="FA-1")]))

    page = log(api, stage, limit=1, offset=1)
    assert page["meta"] == {"limit": 1, "offset": 1, "total": 2}
    [oldest] = page["items"]
    assert oldest["actor"] == {
        "kind": "user",
        "user_id": str(stage.participant.user_id),
        "display_name": "Inès Martin",
    }
    assert (oldest["period_from"], oldest["period_to"], counts(oldest)) == (
        "2026-04-01",
        "2026-04-30",
        (2, 0, 0, 1),
    )
    latest = log(api, stage)["items"][0]
    assert (latest["period_from"], latest["period_to"], counts(latest)) == (
        None,
        None,
        (1, 0, 0, 0),
    )
    assert before.isoformat()[:10] == latest["imported_at"][:10]
    assert latest["imported_at"] >= oldest["imported_at"]


@pytest.mark.requirement("WF-CRE-0050-A")
def test_the_log_is_read_under_the_reading_of_the_actual_costs(
    api: ContractClient, stage: Scene
) -> None:
    # The log is the project's, read by whoever may read its actual costs; of an unknown project,
    # as of one the caller may not consult, 404.
    response = api.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/cost-imports",
        headers=stage.reader.headers,
    )
    assert response.status_code == 404
    response = api.get(
        f"/api/v1/projects/{stage.project['project_id']}/cost-imports",
        headers=stage.outsider.headers,
    )
    assert response.status_code == 404


@pytest.mark.requirement("WF-INTF-0140-A")
def test_an_application_is_inscribed_in_the_journal_with_its_kind_and_not_in_the_undo_history(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    found = analysed(api, stage, worker, APRIL)
    confirmed(api, stage, worker, found)
    with stage.database.transaction() as session:
        (entry,) = session.scalars(select(AuditEntry).where(AuditEntry.action == "import_apply"))
        assert (entry.object_kind, entry.object_id, entry.params) == (
            "import",
            UUID(found["import_id"]),
            {"import_kind": "actual_costs"},
        )
        assert entry.actor_user_id == stage.participant.user_id
        assert session.scalars(select(UndoEntry)).all() == []
    applied = read(api, stage, found["import_id"])
    assert (applied["revision_id"], applied["structure_id"]) == (None, None)


@pytest.mark.requirement("WF-CRE-0020-A")
def test_an_application_waits_for_the_creation_of_a_subproject_and_imputes_to_it(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    # The application reads the subprojects under the lock of the project: a subproject created
    # while it waits receives the line the analysis said of an unknown subproject.
    found = analysed(api, stage, worker, extraction([line(element=ELEMENT, number="FA-1")]))
    assert found["report"]["requires_confirmation_reasons"] == ["unknown_subproject"]
    response = apply(api, stage, found["import_id"])
    assert response.status_code == 202, response.text
    manager = Viewer(stage.manager.user_id, frozenset({"project_settings.write"}))
    with ThreadPoolExecutor(1) as others, Session(database.engine) as creating:
        lock_project(creating, project_of(stage))
        application = others.submit(run, worker)
        wait_for_a_lock(database, 1)
        assert not application.done()
        created = create_subproject(
            creating,
            project_of(stage),
            SubprojectWrite(SUBPROJECT, "Câblage"),
            Act(stage.manager.user_id, utc_now()),
            manager,
        )
        creating.commit()
        application.result(timeout=20)
    [held] = lines(stage)
    assert (held.subproject_id, held.subproject_code) == (created.subproject_id, SUBPROJECT)
    assert read(api, stage, found["import_id"])["status"] == "applied"


def test_an_application_without_its_import_or_its_account_is_a_defect(
    stage: Scene,
) -> None:
    # The exchanges give the application its import and the account that confirmed it: without
    # either, nothing is written, rather than an entry of the log without its import or author.
    target = ImportTarget(project_of(stage), None, None)
    with stage.database.transaction() as session, pytest.raises(ValueError, match="for an account"):
        ACTUAL_COSTS_FORMAT.apply(session, target, APRIL, {}, Act(stage.manager.user_id, utc_now()))
    with stage.database.transaction() as session, pytest.raises(ValueError, match="for an account"):
        ACTUAL_COSTS_FORMAT.apply(
            session,
            ImportTarget(project_of(stage), None, None, import_id=project_of(stage)),
            APRIL,
            {},
            Act(None, utc_now()),
        )
    assert lines(stage) == []
