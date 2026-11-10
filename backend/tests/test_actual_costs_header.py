# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The header of an extraction of the actual costs, read against the mapping.

Laid by US-1580/L1, the socle of EP-09, so that no two stories create the same file;
US-1610/L1 writes its tests here ("Les tests du back"): the opening of an import of the actual
costs through the service — the conditions of the project and of the mapping (409), the headers of
the first tab compared to the labels of the mapping (422), the period of the extraction —, each
answer checked against the contract.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from actual_costs_import_support import (
    CODE,
    DECLARED,
    HEADERS,
    STATE,
    UNREADABLE,
    analysed,
    declare,
    extraction,
    in_progress,
    line,
    opening,
    untouched,
)
from fastapi.testclient import TestClient
from imports_trial import PROJECTS, import_worker, refusal, stored
from projects_support import Person, Scene, put_in_state
from projects_support import scene as make_scene
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.costs.extraction import Kept, Reading
from waterfall.core.costs.interface import ACTUAL_COSTS_FORMAT
from waterfall.core.exchanges.interface import ImportTarget
from waterfall.core.projects.commands import Running, commands_of
from waterfall.platform.errors import ConflictError
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context
from waterfall.platform.tasks import submit

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket
    from waterfall.worker.runner import Worker

FOUR = ["wbs_element", "document_number", "document_date", "amount"]
COMMAND = "import_actual_costs"


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
    """Give a platform installed — its mapping empty —, its sessions, a project In progress."""
    made = make_scene(api, owner, database, realm)
    in_progress(made)
    return made


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports."""
    return import_worker(database, queue, backups_bucket)


@pytest.mark.requirement("WF-REF-0190-A")
def test_on_a_new_installation_an_import_of_actual_costs_is_refused_naming_the_mapping(
    api: ContractClient, stage: Scene
) -> None:
    # « Sur une installation neuve, l'import d'un fichier de coûts réels est refusé et nomme la
    # correspondance à régler. » : the four required columns without a label, in the order of the
    # mapping; nothing is analysed.
    response = opening(api, stage, extraction([line()]))
    assert refusal(response) == (
        409,
        STATE,
        {"missing_condition": "actual_cost_mapping_complete", "columns": FOUR},
    )
    assert untouched(stage.database) == (0, 0)


@pytest.mark.requirement("WF-REF-0190-A")
def test_a_mapping_lacking_one_label_names_that_column_alone(
    api: ContractClient, stage: Scene
) -> None:
    declare(stage.database, {**DECLARED, "document_date": []})
    response = opening(api, stage, extraction([line()]))
    assert refusal(response)[2] == {
        "missing_condition": "actual_cost_mapping_complete",
        "columns": ["document_date"],
    }


@pytest.mark.requirement("WF-REF-0190-A")
@pytest.mark.parametrize(
    ("state", "condition"),
    [
        pytest.param("pricing", "project_in_progress", id="pricing"),
        pytest.param("completed", "project_not_terminal", id="terminal"),
    ],
)
def test_the_state_of_the_project_is_judged_before_the_mapping(
    api: ContractClient, stage: Scene, state: str, condition: str
) -> None:
    # « … après les conditions de l'état du projet » : the mapping, empty, is named after them.
    put_in_state(stage.owner, stage.project["project_id"], state)
    response = opening(api, stage, extraction([line()]))
    assert refusal(response) == (409, STATE, {"missing_condition": condition})
    assert untouched(stage.database) == (0, 0)


@pytest.mark.requirement("WF-REF-0190-A")
def test_a_task_of_the_background_writing_in_the_project_is_judged_before_the_mapping(
    api: ContractClient, stage: Scene, queue: TaskQueue
) -> None:
    # A marking queued around the service: the import waits for it, as its command says.
    payload = {"project_id": stage.project["project_id"]}
    with logging_context(correlation_id="queued-around"), stage.database.transaction() as session:
        submit(session, queue, "revision_mark", stage.manager.user_id, payload)
    response = opening(api, stage, extraction([line()]))
    assert refusal(response) == (409, STATE, {"missing_condition": "no_background_task_running"})


@pytest.mark.requirement("WF-REF-0190-A")
def test_the_mapping_is_judged_at_the_opening_after_the_project_and_before_the_header(
    api: ContractClient, stage: Scene
) -> None:
    # « … un import déjà analysé est appliqué tel qu'il a été analysé » (setActualCostMapping) : the
    # opening refuses an incomplete mapping, in ``read_header`` and before the header is read;
    # ``judge``, which the application replays, no longer judges the mapping.
    declare(stage.database, {**DECLARED, "document_date": []})
    target = ImportTarget(UUID(stage.project["project_id"]), None, None)
    with stage.database.transaction() as session:
        ACTUAL_COSTS_FORMAT.judge(session, target)
        with pytest.raises(ConflictError) as incomplete:
            ACTUAL_COSTS_FORMAT.read_header(session, b"no workbook")
    assert incomplete.value.params == {
        "missing_condition": "actual_cost_mapping_complete",
        "columns": ["document_date"],
    }
    response = opening(api, stage, b"no workbook")
    assert refusal(response)[2]["missing_condition"] == "actual_cost_mapping_complete"
    declare(stage.database)
    assert refusal(opening(api, stage, b"no workbook"))[:2] == (422, UNREADABLE)


@pytest.mark.requirement("WF-REF-0190-A")
def test_an_import_analysed_is_judged_as_analysed_when_a_label_of_the_mapping_is_then_emptied(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # The report keeps the reading of the header the analysis made; the mapping emptied after it
    # changes neither it nor the judgment the application replays.
    declare(stage.database)
    found = analysed(api, stage, worker, extraction([line()]))
    kept = stored(stage.database, found["import_id"]).report
    assert kept is not None
    declare(stage.database, {**DECLARED, "amount": []})
    target = ImportTarget(UUID(stage.project["project_id"]), None, None)
    with stage.database.transaction() as session:
        ACTUAL_COSTS_FORMAT.judge(session, target)
    assert stored(stage.database, found["import_id"]).report == kept
    assert kept["actual_cost_reading"]["columns"]["amount"] == 4


@pytest.mark.requirement("WF-REF-0190-A")
def test_once_the_four_columns_are_declared_an_extraction_headed_with_an_accent_is_imported(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Après déclaration de « Elément d'OTP », « Nº pièce référence », « Date de la pièce » et
    # « Val./Devise objet », une extraction dont l'en-tête est « Élément d'OTP » s'importe. » : the
    # headers compared without case, accents nor spaces at their ends; the item is not declared.
    declare(stage.database, {**DECLARED, "document_item": []}, kept=())
    headers = ("  ÉLÉMENT D'OTP ", "nº pièce RÉFÉRENCE", "Date de la pièce", "Val./Devise objet")
    found = analysed(
        api,
        stage,
        worker,
        extraction([(f"{CODE}/10001", 5100001234, "2026-04-02", 1250)], headers=headers),
    )
    report = found["report"]
    assert (report["read_count"], report["rejected"]) == (1, [])
    assert report["differences"] == [
        {
            "change": "added",
            "target": "actual_cost_line",
            "lineage_id": None,
            "label": "5100001234",
            "document_item": None,
            "fields": [],
        }
    ]


@pytest.mark.requirement("WF-REF-0190-A")
@pytest.mark.requirement("WF-INTF-0070-A")
def test_an_extraction_lacking_a_required_column_is_refused_naming_it_and_the_project_is_unchanged(
    api: ContractClient, stage: Scene
) -> None:
    # « Une extraction à laquelle manque une colonne exigée est refusée, et le message nomme la
    # colonne attendue. » — « un fichier de coûts réels auquel manque une colonne exigée par la
    # correspondance est refusé avec un message qui la nomme. » — « Le projet est inchangé. »
    declare(stage.database, {**DECLARED, "amount": ["Val./Devise objet", "Montant"]})
    lacking = {"Date de la pièce", "Val./Devise objet"}
    headers = [header for header in HEADERS if header not in lacking]
    response = opening(api, stage, extraction([], headers=headers))
    assert refusal(response) == (
        422,
        UNREADABLE,
        {
            "expected_format": "actual_costs",
            "missing_columns": [
                {"column": "document_date", "labels": ["Date de la pièce"]},
                {"column": "amount", "labels": ["Val./Devise objet", "Montant"]},
            ],
        },
    )
    assert untouched(stage.database) == (0, 0)


@pytest.mark.requirement("WF-INTF-0070-A")
def test_the_item_is_not_required_and_the_headers_are_those_of_the_first_tab(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # The item may be absent from the file; the headers of another tab are not read.
    declare(stage.database)
    headers = [header for header in HEADERS if header != "Poste"]
    row = [cell for rank, cell in enumerate(line(item="10")) if rank != 2]
    found = analysed(api, stage, worker, extraction([row], headers=headers))
    assert found["report"]["differences"][0]["document_item"] is None
    response = opening(api, stage, extraction([], headers=["Notes", "Élément d'OTP"]))
    assert refusal(response)[2]["missing_columns"][0]["column"] == "document_number"


@pytest.mark.requirement("WF-INTF-0070-A")
def test_a_file_that_is_no_workbook_is_refused_naming_the_format_without_a_version(
    api: ContractClient, stage: Scene
) -> None:
    declare(stage.database)
    response = opening(api, stage, "Elément d'OTP;Nº pièce\nA.ABC.26001;1\n".encode())
    assert refusal(response) == (422, UNREADABLE, {"expected_format": "actual_costs"})
    assert untouched(stage.database) == (0, 0)


@pytest.mark.requirement("WF-INTF-0140-A")
def test_the_period_of_the_extraction_is_kept_by_the_import_and_an_inverted_one_refused(
    api: ContractClient, stage: Scene
) -> None:
    # « … extrait de l'ERP sur une période donnée » : the period the opening gives, kept; an end
    # before the start refused, nothing opened.
    declare(stage.database)
    response = opening(
        api, stage, extraction([line()]), period_from="2026-04-01", period_to="2026-04-30"
    )
    assert response.status_code == 202, response.text
    found: dict[str, Any] = response.json()
    assert (found["period_from"], found["period_to"]) == ("2026-04-01", "2026-04-30")
    assert (found["structure_id"], found["revision_id"]) == (None, None)
    inverted = opening(
        api, stage, extraction([line()]), period_from="2026-04-30", period_to="2026-04-01"
    )
    assert refusal(inverted)[:2] == (422, "VALIDATION_FAILED")
    assert inverted.json()["fields"] == [
        {"pointer": "/period_to", "code": "VALUE_OUT_OF_RANGE", "params": {"minimum": "2026-04-30"}}
    ]


@pytest.mark.requirement("WF-REF-0190-A")
def test_the_reading_of_the_header_is_kept_with_the_report_and_not_returned(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Sa modification vaut pour les imports suivants » : the analysis keeps the ranks of the
    # columns read and kept, which the application reads the file by, whatever the mapping then.
    declare(stage.database)
    found = analysed(api, stage, worker, extraction([line()]))
    assert "actual_cost_reading" not in found["report"]
    kept = stored(stage.database, found["import_id"]).report
    assert kept is not None
    assert kept["actual_cost_reading"] == {
        "columns": {
            "wbs_element": 0,
            "document_number": 1,
            "document_item": 2,
            "document_date": 3,
            "amount": 4,
        },
        "kept": [{"rank": 5, "label": "Fournisseur"}],
    }


@pytest.mark.requirement("WF-REF-0190-A")
def test_a_second_header_naming_a_column_already_named_is_ignored_and_named(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Une colonne de l'extraction qui n'est ni lue ni déclarée conservée est ignorée, et le compte
    # rendu de l'import la nomme. » : the first of two headers of a column is read, or kept; the
    # second is neither. A column without a header is no column.
    declare(stage.database)
    headers = (*HEADERS, "élément d'otp", None, "FOURNISSEUR")
    row = (*line(), "A.ABC.26002/1", "sans en-tête", "Usinage Martin")
    found = analysed(api, stage, worker, extraction([row], headers=headers))
    report = found["report"]
    assert report["ignored"] == [
        {"kind": "columns", "count": 3, "labels": ["Nom Matricule", "élément d'otp", "FOURNISSEUR"]}
    ]
    assert (report["rejected"], len(report["differences"])) == ([], 1)
    kept = stored(stage.database, found["import_id"]).report
    assert kept is not None
    reading = Reading.from_report(kept["actual_cost_reading"])
    assert (reading.columns["wbs_element"], reading.kept) == (0, (Kept(5, "Fournisseur"),))


def lacking(api: ContractClient, stage: Scene, who: Person | None = None) -> list[str] | None:
    """Give the conditions the import of the actual costs lacks on the project, or none unlisted."""
    response = api.get(
        f"{PROJECTS}/{stage.project['project_id']}", headers=(who or stage.manager).headers
    )
    assert response.status_code == 200, response.text
    commands = response.json()["available_commands"]
    return next(
        (each["missing_conditions"] for each in commands if each["command"] == COMMAND), None
    )


@pytest.mark.requirement("WF-REF-0190-A")
def test_the_command_of_the_project_states_in_advance_what_the_opening_refuses_by(
    api: ContractClient, stage: Scene, queue: TaskQueue
) -> None:
    # « … la commande `import_actual_costs` du projet le dit d'avance » : listed under
    # `actual_costs.write`, unavailable out of In progress, then while a task of the background
    # writes in the project, then while the mapping lacks a label — in the order of the opening.
    assert lacking(api, stage) == ["actual_cost_mapping_complete"]
    declare(stage.database)
    assert lacking(api, stage) == []
    assert lacking(api, stage, stage.reader) is None
    put_in_state(stage.owner, stage.project["project_id"], "pricing")
    declare(stage.database, {**DECLARED, "amount": []})
    payload = {"project_id": stage.project["project_id"]}
    with logging_context(correlation_id="queued-around"), stage.database.transaction() as session:
        submit(session, queue, "revision_mark", stage.manager.user_id, payload)
    assert lacking(api, stage) == [
        "project_in_progress",
        "no_background_task_running",
        "actual_cost_mapping_complete",
    ]


@pytest.mark.requirement("WF-IHM-0090-A")
def test_the_commands_of_the_actual_costs_and_of_the_remaining_name_their_conditions() -> None:
    # Each listed under its permission, the quality of contributor first, then the conditions of
    # the state in the order of the contract: the exclusion of a line asks In progress alone; the
    # import of the remaining to commit, as the other imports of a revision, asks besides that no
    # task writes and that who imports may create the revision it would create.
    held = {"actual_costs.write", "cost_line_exclude", "remaining.write"}
    idle = Running(no_task_running=True)
    busy = Running(no_task_running=False, mapping_complete=False)
    assert dict(commands_of(held, "contributor", "pricing", None, running=busy)) == {
        "import_actual_costs": (
            "project_in_progress",
            "no_background_task_running",
            "actual_cost_mapping_complete",
        ),
        "exclude_cost_lines": ("project_in_progress",),
        "import_remaining": (
            "project_in_progress",
            "no_background_task_running",
            "may_create_revision",
        ),
    }
    assert dict(commands_of(held, None, "in_progress", UUID(int=1), running=idle)) == {
        "import_actual_costs": ("is_contributor",),
        "exclude_cost_lines": ("is_contributor",),
        "import_remaining": ("is_contributor",),
    }
    assert commands_of({"remaining.write"}, "contributor", "completed", None, running=idle) == []
