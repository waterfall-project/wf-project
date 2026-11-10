# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The export of the workbook of an estimate, and its round trips (US-1550/L4).

Against the service, with a worker of the imports and the exports: ``requestExport`` asks for the
workbook of a revision, the worker writes it from the current reference or from the images of a
marked revision, ``getBackgroundTaskResult`` serves it; the workbook is read back by openpyxl,
imported again — the round trip of the estimate, by a user in French and in English — or, for the
planning, exported to MS Project and imported again with lines of roles of other calendars. Every
answer is checked against the contract, the download of the file excepted (see ``download``). The
writer without a database is ``test_estimate_excel_write``, the reader ``test_estimate_excel_read``.
"""

from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_import_support import analysed, analysed_import, two_tasks
from estimate_support import YEAR, Costing, Lines, add_role, costing
from fastapi.testclient import TestClient
from imports_trial import apply, deposited, path, read, run
from nodes_support import Tree, mark, opened, put_facts, work_breakdown
from openpyxl import load_workbook
from projects_support import PROJECTS, Scene, contribute, person
from projects_support import scene as make_scene
from sqlalchemy import select, update
from support import ContractClient
from test_msproject_export import exported as exported_planning
from test_msproject_export import import_file, nodes, the_planning

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.access_roles.predefined import PROJECT_MANAGER
from waterfall.core.cost_settings.interface import CostCategoryDraft, create_cost_category
from waterfall.core.cost_settings.tables import (
    CostCategory,
    CostType,
    HourlyRate,
    ReferenceSetting,
)
from waterfall.core.estimate.exporting import file_name
from waterfall.core.planning.msproject import read_project
from waterfall.core.projects.tables import OrderItem, Project, WorkPackage
from waterfall.core.resource_settings.tables import ResourceRole
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.worker.exchanges import ExportTask, ImportTasks
from waterfall.worker.marking import mark as marking
from waterfall.worker.runner import Timing as WorkerTiming
from waterfall.worker.runner import Worker

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from openpyxl import Workbook
    from openpyxl.worksheet.worksheet import Worksheet
    from projects_support import Person
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket

KIND = "estimate"
TASKS = "/api/v1/tasks"
AT_ONCE = WorkerTiming(claim_after=0, block=0.01, redeposit_every=0)
SPREADSHEET = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
IN_ENGLISH = "en-GB,en;q=0.9"
IN_FRENCH = "fr-FR,fr;q=0.9"
LINES_HEADER = 20
FIXED = ["Présentation", "Devis"]
NOW = datetime(2026, 1, 5, tzinfo=UTC)
TAIL = ["Tâches", "Paramètres"]


@pytest.fixture
def services(
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
def api(contract: OpenAPI, services: Services) -> ContractClient:
    """Give a client of the service that deposits in the queue and the bucket of the test."""
    app = create_app(services)
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker that runs the imports, the markings and the exports, into the test's bucket."""
    queue.prepare()
    imports = ImportTasks(backups_bucket)
    handlers = {
        "import_analysis": imports.analyse,
        "import_apply": imports.apply,
        "revision_mark": marking,
        "export": ExportTask(backups_bucket),
    }
    return Worker(database, queue, handlers, "worker", AT_ONCE)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name, rated for the year."""
    return costing(stage.database)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the current revision of the project of the stage."""
    return Tree(api, stage, opened(api, stage))


@pytest.fixture
def held(tree: Tree, costs: Costing, stage: Scene) -> dict[str, Any]:
    """Give a structure of two tasks, a labour line and a line of material under the first."""
    return two_tasks(tree, costs, stage)


def download(
    api: ContractClient, stage: Scene, worker: Worker, revision_id: str, who: Person | None = None
) -> Any:
    """Ask for the export of the estimate of a revision, run it and download its file.

    The contract declares the file a binary string, and the validator of the answers refuses the
    bytes of a workbook as no string: the answer of the download is read here by the client of the
    application itself, its type and its name checked by the tests; the request is validated.
    """
    headers = (who or stage.manager).headers
    asked = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/exports",
        headers=headers,
        json={"kind": KIND, "revision_id": revision_id},
    )
    assert asked.status_code == 202, asked.text
    assert worker.step()
    answer = api.client.get(f"{TASKS}/{asked.json()['task_id']}/result", headers=headers)
    assert answer.status_code == 200, answer.text
    return answer


def exported(api: ContractClient, stage: Scene, worker: Worker, revision_id: str) -> bytes:
    """Export the estimate of a revision as the manager does; give the content of the workbook."""
    return bytes(download(api, stage, worker, revision_id).content)


def book_of(content: bytes) -> Workbook:
    """Read a workbook as Excel would show its formulas, not its values."""
    return load_workbook(BytesIO(content))


def presentation(content: bytes) -> dict[str, Any]:
    """Read the presentation of a workbook: what it says of the project, by its label."""
    sheet = book_of(content)["Présentation"]
    return {str(row[0].value): row[1].value for row in sheet.iter_rows(min_row=1, max_col=2)}


def footer_of(sheet: Worksheet) -> str:
    """Read the left part of the footer of a tab, where the copyright of the company stands."""
    footer = sheet.oddFooter
    assert footer is not None
    assert footer.left is not None
    return footer.left.text or ""


def lines_of(content: bytes, name: str) -> list[dict[str, Any]]:
    """Read the lines of a tab of lines by their headers: those that carry a lineage."""
    sheet = book_of(content)[name]
    rows = sheet.iter_rows(values_only=True)
    headers = [str(each) for each in next(rows)]
    found = [dict(zip(headers, row, strict=False)) for row in rows]
    return [each for each in found if each["ID ligne"]]


def items_of(tree: Tree) -> list[dict[str, Any]]:
    """Read the nodes of the structure, as they are served."""
    return tree.items()


def imported(
    api: ContractClient, stage: Scene, worker: Worker, content: bytes, who: Person | None = None
) -> dict[str, Any]:
    """Open the import of a workbook as someone does, run its analysis; give the import read."""
    who = who or stage.manager
    headers = {
        **who.headers,
        "Accept-Language": IN_ENGLISH if who is not stage.manager else IN_FRENCH,
    }
    upload_id = deposited(api, who, content)
    opening = api.post(path(stage), headers=headers, json={"kind": KIND, "upload_id": upload_id})
    assert opening.status_code == 202, opening.text
    run(worker)
    found = api.get(path(stage, opening.json()["import_id"]), headers=headers)
    assert found.status_code == 200, found.text
    return found.json()


def an_english_manager(stage: Scene, realm: TestRealm) -> Person:
    """Give a manager of the project whose language is English."""
    who = person(stage.database, realm, *PROJECT_MANAGER, name="Ava")
    contribute(stage.database, stage.project["project_id"], who, "project_manager")
    with stage.database.transaction() as session:
        session.execute(
            update(UserAccount)
            .where(UserAccount.id == who.user_id)
            .values(display_preferences={"language": "en"})
        )
    return who


@pytest.mark.requirement("WF-INTF-0110-A")
def test_the_estimate_of_a_current_revision_is_exported_in_a_workbook_under_the_name_of_its_project(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    # « Un utilisateur habilité peut exporter le devis d'une structure de coûts d'une révision, en
    # cours ou marquée, […] dans un fichier Excel au format « Devis ». » : the file is a workbook
    # of the spreadsheet type, named after the project and the version of its revision — none for
    # a revision in progress —, and carries the lines of the structure by their lineage.
    revision = held["tree"].revision
    answer = download(api, stage, worker, revision["revision_id"])
    assert answer.headers["content-type"].startswith(SPREADSHEET)
    assert answer.headers["content-disposition"].startswith(
        'attachment; filename="Modernisation_du_poste_de_commande-en-cours-devis.xlsx"'
    )
    book = book_of(answer.content)
    assert book.sheetnames == [*FIXED, "Hors lot", *TAIL]
    head = book["Présentation"]
    assert [head["A1"].value, head["B1"].value, head["A2"].value, head["B2"].value] == [
        "Format",
        "Devis",
        "Version",
        1,
    ]
    lines = lines_of(answer.content, "Hors lot")
    assert [(each["Tâche"], each["ID ligne"]) for each in lines] == [
        ("1 Câblage", held["labour"]["lineage_id"]),
        ("1 Câblage", held["material"]["lineage_id"]),
    ]
    labour, material = lines
    assert (labour["Rôle ou catégorie"], labour["Quantité"], labour["Heures"]) == (
        held["role"],
        2,
        10,
    )
    assert (material["Rôle ou catégorie"], material["Débours unitaire"]) == (held["stuff"], 350)
    tasks = list(book["Tâches"].iter_rows(min_row=4, values_only=True))
    assert [(each[0], each[1], each[4]) for each in tasks] == [
        ("1 Câblage", held["first"]["lineage_id"], "Hors lot"),
        ("2 Essais", held["second"]["lineage_id"], "Hors lot"),
    ]


@pytest.mark.requirement("WF-INTF-0110-A")
def test_the_amount_waterfall_of_a_line_is_the_amount_the_service_computed_inflation_included(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any], owner: Engine
) -> None:
    # « Montant Waterfall, inflation comprise » : the re-estimated amount of the line, as the
    # service serves it (WF-DEV-0050); the project inflates by 3 % a year.
    with owner.begin() as connection:
        connection.execute(
            update(Project)
            .where(Project.id == UUID(stage.project["project_id"]))
            .values(inflation_rate=Decimal("0.03"))
        )
    served = {
        item["lineage_id"]: item["estimate_line"]["reestimated_amount"]
        for item in held["tree"].items()
        if item["kind"] == "estimate_line"
    }
    content = exported(api, stage, worker, held["tree"].revision["revision_id"])
    written = {
        each["ID ligne"]: each["Montant Waterfall"] for each in lines_of(content, "Hors lot")
    }
    assert {key: Decimal(str(value)) for key, value in written.items()} == {
        key: Decimal(value) for key, value in served.items()
    }
    assert len(written) == 2


@pytest.mark.requirement("WF-EXP-0020-A")
@pytest.mark.requirement("WF-PRJ-0080-A")
@pytest.mark.requirement("WF-REF-0140-A")
def test_the_company_the_client_and_the_currency_figure_on_the_workbook_and_follow_their_changes(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any], owner: Engine
) -> None:
    # « Le nom de l'entreprise saisi à l'installation figure sur un devis exporté ; modifié, il
    # figure sur le suivant. » ; « Le nom du client est saisissable à tout moment […] et figure sur
    # la présentation d'un devis exporté. » ; « La devise apparaît partout où un montant est
    # affiché ou exporté » : the presentation and the footer of every tab.
    revision_id = held["tree"].revision["revision_id"]
    first = exported(api, stage, worker, revision_id)
    said = presentation(first)
    assert (said["Entreprise"], said["Client"], said["Devise"]) == (
        "Delmas Automatismes",
        None,
        "EUR",
    )
    with owner.begin() as connection:
        connection.execute(update(ReferenceSetting).values(company_name="Atelier Nord"))
        connection.execute(update(ReferenceSetting).values(currency_code="CHF"))
        connection.execute(
            update(Project)
            .where(Project.id == UUID(stage.project["project_id"]))
            .values(client="Ville de Lille")
        )
    second = exported(api, stage, worker, revision_id)
    said = presentation(second)
    assert (said["Entreprise"], said["Client"], said["Devise"]) == (
        "Atelier Nord",
        "Ville de Lille",
        "CHF",
    )
    assert said["Révision"] == "En cours"
    assert said["Structure"] == "Structure principale"
    assert said["Année de référence"] == YEAR
    for sheet in book_of(second).worksheets:
        footer = footer_of(sheet)
        assert "© " in footer
        assert "Atelier Nord" in footer
        assert "Delmas Automatismes" not in footer
    assert "Delmas Automatismes" in footer_of(book_of(first)["Présentation"])


@pytest.mark.requirement("WF-INTF-0110-A")
@pytest.mark.requirement("WF-DAT-0110-A")
def test_an_estimate_exported_then_imported_again_presents_no_difference_and_changes_no_line(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    # « On exporte un devis, puis on le réimporte sans modification dans la révision en cours. Le
    # compte rendu (WF-INTF-0080) ne signale aucun écart, et les lignes obtenues sont identiques. »
    tree = held["tree"]
    before = items_of(tree)
    content = exported(api, stage, worker, tree.revision["revision_id"])
    import_id = analysed_import(api, stage, worker, content)
    report = read(api, stage, import_id)["report"]
    assert (report["differences"], report["rejected"], report["refusals"]) == ([], [], [])
    assert (report["signals"], report["ignored"]) == ([], [])
    assert report["unchanged_count"] == report["read_count"] == 2
    assert apply(api, stage, import_id).status_code == 202
    run(worker)
    assert read(api, stage, import_id)["status"] == "applied"
    assert items_of(tree) == before


@pytest.mark.requirement("WF-INTF-0180-A")
def test_an_estimate_exported_by_a_user_in_french_and_imported_by_one_in_english_is_identical(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    held: dict[str, Any],
    realm: TestRealm,
) -> None:
    # « Un devis exporté par un utilisateur en français et réimporté par un utilisateur en anglais
    # donne un devis identique, sans avertissement de format. »
    tree = held["tree"]
    before = items_of(tree)
    in_french = download(api, stage, worker, tree.revision["revision_id"])
    english = an_english_manager(stage, realm)
    found = imported(api, stage, worker, bytes(in_french.content), english)
    assert found["status"] == "analysed"
    report = found["report"]
    assert (report["differences"], report["rejected"], report["refusals"]) == ([], [], [])
    assert (report["signals"], report["ignored"]) == ([], [])
    assert report["unchanged_count"] == report["read_count"] == 2
    applied = api.post(
        f"{path(stage, found['import_id'])}/apply",
        headers={**english.headers, "Accept-Language": IN_ENGLISH},
        json={"confirmed": True},
    )
    assert applied.status_code == 202, applied.text
    run(worker)
    assert read(api, stage, found["import_id"])["status"] == "applied"
    assert items_of(tree) == before


@pytest.mark.requirement("WF-INTF-0180-A")
def test_the_workbook_carries_the_same_headers_whatever_the_language_of_who_exports_it(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    held: dict[str, Any],
    realm: TestRealm,
) -> None:
    # « Le fichier Excel exporté porte les mêmes en-têtes quelle que soit la langue de celui qui
    # l'exporte. » : the headers of annex B, in French, fixed — every tab, every cell of a header.
    revision_id = held["tree"].revision["revision_id"]
    english = an_english_manager(stage, realm)
    by_french = book_of(bytes(download(api, stage, worker, revision_id).content))
    by_english = book_of(bytes(download(api, stage, worker, revision_id, english).content))
    assert by_english.sheetnames == by_french.sheetnames == [*FIXED, "Hors lot", *TAIL]
    headers = {"Hors lot": 1, "Tâches": 3, "Paramètres": 3, "Devis": 5}
    for name, row in headers.items():
        assert [cell.value for cell in by_english[name][row]] == [
            cell.value for cell in by_french[name][row]
        ]
    lines = [cell.value for cell in by_english["Hors lot"][1]]
    assert lines[:3] == ["Tâche", "Description de la tâche", "Rôle ou catégorie"]
    assert "ID ligne" in lines
    assert [cell.value for cell in by_english["Devis"][5]][:4] == [
        "N°",
        "Lot ou poste",
        "Inclus",
        "Niveau",
    ]
    assert (
        presentation(bytes(download(api, stage, worker, revision_id, english).content))[
            "Entreprise"
        ]
        == presentation(bytes(download(api, stage, worker, revision_id).content))["Entreprise"]
    )


@pytest.mark.requirement("WF-REV-0030-A")
@pytest.mark.requirement("WF-REF-0130-A")
def test_a_marked_revision_is_exported_on_its_images_a_current_one_on_the_reference(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    held: dict[str, Any],
    costs: Costing,
) -> None:
    # « Une révision marquée se lit sur ses images » : the label of a role and the rate of its
    # category as the revision kept them at its marking, whatever the reference says since; the
    # revision opened after it follows the reference for its labels. The file is named after the
    # version of the revision and the code of the project.
    marked = held["tree"].revision
    mark(stage, marked)
    with stage.owner.begin() as connection:
        connection.execute(
            update(Project)
            .where(Project.id == UUID(stage.project["project_id"]))
            .values(code="PRJ-042")
        )
        connection.execute(
            update(ResourceRole)
            .where(ResourceRole.id == costs.role)
            .values(label="Ingénieur senior")
        )
        connection.execute(
            update(HourlyRate)
            .where(HourlyRate.cost_category_id == costs.labour, HourlyRate.year == YEAR)
            .values(amount=Decimal("70.00"))
        )
    answer = download(api, stage, worker, marked["revision_id"])
    assert 'filename="PRJ-042-v1.0-devis.xlsx"' in answer.headers["content-disposition"]
    parameters = book_of(answer.content)["Paramètres"]
    roles = [row for row in parameters.iter_rows(min_row=4, values_only=True) if row[1] == "Rôle"]
    assert [(row[0], row[3], row[8]) for row in roles] == [
        ("Ingénieur (ING)", "Ingénieur", 65.0),
    ]
    assert presentation(answer.content)["Révision"] == "v1.0"
    first = next(iter(lines_of(answer.content, "Hors lot")))
    assert first["Rôle ou catégorie"] == "Ingénieur (ING)"
    current = opened(api, stage)
    follows = download(api, stage, worker, current["revision_id"])
    rows = book_of(follows.content)["Paramètres"].iter_rows(min_row=4, values_only=True)
    assert [(row[0], row[8]) for row in rows if row[1] == "Rôle"] == [
        ("Ingénieur senior (ING)", 65.0)
    ]
    assert 'filename="PRJ-042-en-cours-devis.xlsx"' in follows.headers["content-disposition"]


def attach(tree: Tree, stage: Scene) -> dict[str, Any]:
    """Give a structure of a poste, a lot outside its postes and a task outside any lot."""
    package, item = work_breakdown(stage)
    first, second, third = tree.made("Câblage"), tree.made("Essais"), tree.made("Recette")
    put_facts(stage, first["node_id"], order_item_id=item)
    put_facts(stage, second["node_id"], work_package_id=package)
    return {"first": first, "second": second, "third": third}


@pytest.mark.requirement("WF-INTF-0100-A")
def test_the_lines_are_exported_by_poste_by_lot_outside_its_postes_and_outside_any_lot(
    api: ContractClient, stage: Scene, worker: Worker, tree: Tree, costs: Costing
) -> None:
    # « un onglet par poste du lotissement […] nommé par sa numérotation dans le lotissement
    # — « 1.1 » — suivie de son libellé ; un onglet par lot pour les lignes du sous-arbre de sa
    # tâche hors de ceux de ses postes ; et « Hors lot » pour les lignes hors de tout sous-arbre
    # d'une tâche rattachée à un lot (WF-PLA-0170). » : and what is exported is imported without
    # a difference, each line under its task, whatever its tab.
    tasks = attach(tree, stage)
    lines = Lines(tree)
    made = {
        name: lines.made(
            tasks[name], quantity="1", resource_role_id=str(costs.role), hours=str(hours)
        )["nodes"][0]
        for name, hours in (("first", 3), ("second", 4), ("third", 5))
    }
    before = items_of(tree)
    content = exported(api, stage, worker, tree.revision["revision_id"])
    book = book_of(content)
    # The project holds a work package of its own at the first place: the lot added is the second.
    assert book.sheetnames == [*FIXED, "2.1 Poste", "2 Lot", "Hors lot", *TAIL]
    assert {
        name: [each["ID ligne"] for each in lines_of(content, name)]
        for name in book.sheetnames[2:5]
    } == {
        "2.1 Poste": [made["first"]["lineage_id"]],
        "2 Lot": [made["second"]["lineage_id"]],
        "Hors lot": [made["third"]["lineage_id"]],
    }
    listed = list(book["Tâches"].iter_rows(min_row=4, values_only=True))
    assert [(each[0], each[4]) for each in listed] == [
        ("1 Câblage", "2.1 Poste"),
        ("2 Essais", "2 Lot"),
        ("3 Recette", "Hors lot"),
    ]
    summary = [row[:4] for row in book["Devis"].iter_rows(min_row=6, max_row=10, values_only=True)]
    assert summary == [
        ("2", "Lot", None, "lot"),
        ("2.1", "Poste", "Oui", "onglet"),
        ("2", "Lot, hors postes", "Oui", "onglet"),
        ("", "Hors lot", "Oui", "onglet"),
        (None, "Total", None, None),
    ]
    import_id = analysed_import(api, stage, worker, content)
    report = read(api, stage, import_id)["report"]
    assert (report["differences"], report["rejected"]) == ([], [])
    assert report["unchanged_count"] == report["read_count"] == 3
    assert items_of(tree) == before


@pytest.mark.requirement("WF-INTF-0100-A")
def test_the_blank_model_of_a_structure_without_a_line_is_exported_and_imports_nothing(
    api: ContractClient, stage: Scene, worker: Worker, tree: Tree
) -> None:
    # « L'export d'une structure sans ligne donne le modèle vierge » : one tab of lines, empty,
    # which the import reads without a line and without a difference.
    content = exported(api, stage, worker, tree.revision["revision_id"])
    assert book_of(content).sheetnames == [*FIXED, "Hors lot", *TAIL]
    assert lines_of(content, "Hors lot") == []
    report = read(api, stage, analysed_import(api, stage, worker, content))["report"]
    assert (report["differences"], report["rejected"], report["read_count"]) == ([], [], 0)


@pytest.mark.requirement("WF-CYC-0110-A")
def test_the_export_of_the_estimate_is_a_command_of_the_revision_which_lacks_no_condition(
    api: ContractClient, stage: Scene, held: dict[str, Any]
) -> None:
    # « les exports restent »: listed with the other commands of the revision, after the planning's
    # (the order of ``RevisionCommand``), none of its conditions missing, marked or not.
    revision = held["tree"].revision
    address = f"{PROJECTS}/{stage.project['project_id']}/revisions/{revision['revision_id']}"

    def exports() -> list[tuple[str, list[str]]]:
        listed = api.get(address, headers=stage.manager.headers).json()["available_commands"]
        return [
            (each["command"], each["missing_conditions"])
            for each in listed
            if each["command"].startswith("export_")
        ]

    expected: list[tuple[str, list[str]]] = [
        ("export_planning", []),
        ("export_estimate", []),
        ("export_task_tree_image", []),
    ]
    assert exports() == expected
    mark(stage, revision)
    assert exports() == expected


@pytest.mark.requirement("WF-INTF-0040-A")
@pytest.mark.requirement("WF-INTF-0050-A")
@pytest.mark.requirement("WF-INTF-0060-A")
def test_a_planning_with_lines_of_roles_of_different_calendars_is_exported_to_ms_project_and_back(
    api: ContractClient, stage: Scene, worker: Worker, costs: Costing
) -> None:
    # « Un planning exporté, retravaillé dans MS Project puis réimporté conserve les lignes de
    # devis » ; « Les calendriers Waterfall y figurent et sont affectés aux tâches » ; « Un planning
    # […] des tâches portant des rôles de ressources aux calendriers différents, est exporté,
    # ouvert dans MS Project sans y être modifié, puis réimporté. Le compte rendu ne présente aucun
    # écart de dates ni de durées, et le planning obtenu est identique à celui relevé avant
    # l'export. » : three tasks, three calendars (the default one, a role of four days of ten hours,
    # a role of six days of six); the lines stay under their tasks, with their lineages.
    revision = opened(api, stage)
    import_file(api, stage, worker, the_planning(), apply=True)
    workshop = add_role(stage.database, "ATEL", (10, 10, 10, 10, 0, 0, 0))
    long_days = add_role(stage.database, "SIX", (6, 6, 6, 6, 6, 6, 0))
    lines = Lines(Tree(api, stage, revision))
    found = {task.label: node.id for node, task in nodes(stage)}
    for label, role in (("Pose", workshop), ("Câblage", long_days), ("Plans", costs.role)):
        lines.made(str(found[label]), quantity="1", resource_role_id=str(role), hours="8")
    snapshot = [
        (
            node.id,
            node.lineage_id,
            node.parent_id,
            (task.start_date, task.start_hours, task.finish_date, task.finish_hours),
            (task.duration_value, task.duration_unit),
        )
        for node, task in nodes(stage)
    ]
    before = items_of(lines.tree)
    assert len([each for each in before if each["kind"] == "estimate_line"]) == 3

    content = exported_planning(api, stage, worker, revision["revision_id"])
    project = read_project(content).project
    # The calendar of the project, and one calendar of a task for each distinct week of a role.
    assert [(each.uid, each.name) for each in project.calendars] == [
        (1, "Waterfall"),
        (2, "Waterfall 2"),
        (3, "Waterfall 3"),
    ]
    by_task = {each.name: each.calendar_uid for each in project.tasks}
    assert by_task["Pose"] != by_task["Câblage"]
    assert {by_task["Pose"], by_task["Câblage"]} == {2, 3}
    assert by_task["Plans"] == by_task["Études"] == 1

    report = import_file(api, stage, worker, content, apply=False)["report"]
    assert (report["differences"], report["date_mismatches"]) == ([], [])
    assert (report["refusals"], report["rejected"], report["signals"]) == ([], [], [])
    assert report["unchanged_count"] == report["read_count"] == 8
    import_file(api, stage, worker, content, apply=True)
    assert [
        (
            node.id,
            node.lineage_id,
            node.parent_id,
            (task.start_date, task.start_hours, task.finish_date, task.finish_hours),
            (task.duration_value, task.duration_unit),
        )
        for node, task in nodes(stage)
    ] == snapshot
    assert items_of(lines.tree) == before


@pytest.mark.requirement("WF-REF-0130-A")
def test_the_roles_offered_are_the_active_ones_and_those_a_line_employs(
    api: ContractClient, stage: Scene, worker: Worker, tree: Tree, costs: Costing
) -> None:
    # Les rôles de la liste de validation sont ceux du référentiel actifs : un rôle désactivé et
    # inemployé n'est plus offert (sa catégorie, active, n'y change rien), un rôle désactivé
    # qu'une ligne emploie reste listé pour que le devis se relise.
    unused = add_role(stage.database, "ARC", (8, 8, 8, 8, 8, 0, 0))
    task = tree.made("Câblage")
    Lines(tree).made(task, quantity="1", resource_role_id=str(costs.role), hours="3")
    with stage.owner.begin() as connection:
        connection.execute(update(ResourceRole).values(is_active=False))
    content = exported(api, stage, worker, tree.revision["revision_id"])
    rows = book_of(content)["Paramètres"].iter_rows(min_row=4, values_only=True)
    offered = [row[0] for row in rows if row[1] == "Rôle"]
    assert offered == ["Ingénieur (ING)"]
    assert unused != costs.role


def lot_of_a_poste(stage: Scene, tree: Tree, role: UUID, *, poste_only: bool) -> None:
    """Put a task with a line on a poste, mark, then delete the poste, or the poste and its lot."""
    package, item = work_breakdown(stage)
    task = tree.made("Câblage")
    put_facts(stage, task["node_id"], order_item_id=item)
    Lines(tree).made(task, quantity="1", resource_role_id=str(role), hours="3")
    mark(stage, tree.revision)
    with stage.owner.begin() as connection:
        connection.execute(update(OrderItem).where(OrderItem.id == item).values(deleted_at=NOW))
        if not poste_only:
            connection.execute(
                update(WorkPackage).where(WorkPackage.id == package).values(deleted_at=NOW)
            )


@pytest.mark.requirement("WF-INTF-0100-A")
def test_a_poste_deleted_with_its_lot_after_the_marking_keeps_its_numbers_and_its_names(
    api: ContractClient, stage: Scene, worker: Worker, tree: Tree, costs: Costing
) -> None:
    # Un poste porté par une tâche de la révision marquée, supprimé avec son lot : le lot garde
    # son numéro et son libellé (« 2 Lot »), le poste « 2.1 » en dépend ; ni l'un ni l'autre ne
    # prend « 1 », que le lot vivant du projet porte.
    lot_of_a_poste(stage, tree, costs.role, poste_only=False)
    content = exported(api, stage, worker, tree.revision["revision_id"])
    book = book_of(content)
    assert book.sheetnames == [*FIXED, "2.1 Poste", *TAIL]
    listed = list(book["Tâches"].iter_rows(min_row=4, values_only=True))
    assert [(each[0], each[4]) for each in listed] == [("1 Câblage", "2.1 Poste")]
    summary = [row[:4] for row in book["Devis"].iter_rows(min_row=6, max_row=8, values_only=True)]
    assert summary[:2] == [("2", "Lot", None, "lot"), ("2.1", "Poste", "Oui", "onglet")]


@pytest.mark.requirement("WF-INTF-0100-A")
def test_a_poste_deleted_after_the_marking_while_its_lot_lives_is_numbered_under_its_lot(
    api: ContractClient, stage: Scene, worker: Worker, tree: Tree, costs: Costing
) -> None:
    # Le poste supprimé, son lot vivant : il garde son rang sous le lot.
    lot_of_a_poste(stage, tree, costs.role, poste_only=True)
    content = exported(api, stage, worker, tree.revision["revision_id"])
    book = book_of(content)
    assert book.sheetnames == [*FIXED, "2.1 Poste", *TAIL]
    listed = list(book["Tâches"].iter_rows(min_row=4, values_only=True))
    assert [(each[0], each[4]) for each in listed] == [("1 Câblage", "2.1 Poste")]


@pytest.mark.requirement("WF-INTF-0100-A")
def test_a_version_named_like_the_current_revision_or_nothing_is_named_by_its_identifier() -> None:
    # Le nom du fichier ne confond pas une version avec la révision en cours.
    revision = UUID(int=7)
    assert file_name("P", "Projet", (None, revision)) == "P-en-cours-devis.xlsx"
    assert file_name("P", "Projet", ("En-cours", revision)) == f"P-{revision}-devis.xlsx"
    assert file_name("P", "Projet", ("§§", revision)) == f"P-{revision}-devis.xlsx"
    assert file_name("P", "Projet", ("v1.0", revision)) == "P-v1.0-devis.xlsx"


def with_quantity(content: bytes, lineage: str, quantity: int) -> bytes:
    """Change the quantity of a line of « Hors lot », found by its lineage, as a user does."""
    book = book_of(content)
    sheet = book["Hors lot"]
    headers = [cell.value for cell in sheet[1]]
    column = headers.index("Quantité") + 1
    for number, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        if row[headers.index("ID ligne")] == lineage:
            sheet.cell(number, column, quantity)
    out = BytesIO()
    book.save(out)
    return out.getvalue()


def no_difference(report: dict[str, Any], count: int) -> None:
    """Affirm that an analysis finds no difference, no rejection, and reads ``count`` lines."""
    assert (report["differences"], report["rejected"], report["refusals"]) == ([], [], [])
    assert report["unchanged_count"] == report["read_count"] == count


@pytest.mark.requirement("WF-INTF-0110-A")
def test_a_category_is_written_by_its_accounting_code_and_imported_back_by_it(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    # Annex B: « une catégorie est désignée par son code comptable (WF-REF-0040) », and « Devis »
    # gives « les heures par code comptable de main-d'œuvre » (#2688). The category of material is
    # MAT-001 for the reference, 606001 for the accounting; the one of labour ING and 641001: the
    # workbook says 606001 and 641001, never their technical codes, and imported again presents
    # no difference and changes no line.
    tree = held["tree"]
    before = items_of(tree)
    content = exported(api, stage, worker, tree.revision["revision_id"])
    material = lines_of(content, "Hors lot")[1]
    assert material["Rôle ou catégorie"] == "Matériel électrique (606001)"
    book = book_of(content)
    rows = list(book["Paramètres"].iter_rows(min_row=4, max_col=9, values_only=True))
    assert [(row[2], row[7]) for row in rows if row[1] == "Rôle"] == [("ING", "641001")]
    assert ("Matériel électrique (606001)", "Catégorie", "606001") in [
        (row[0], row[1], row[7]) for row in rows
    ]
    assert all("MAT-001" not in str(cell) for row in rows for cell in row)
    summary = [cell.value for cell in book["Devis"][5]]
    assert "Heures 641001" in summary
    assert "Heures ING" not in summary
    hours = str(book["Devis"].cell(6, summary.index("Heures 641001") + 1).value)
    assert '[[Code comptable]],"641001")' in hours
    import_id = analysed_import(api, stage, worker, content)
    no_difference(read(api, stage, import_id)["report"], 2)
    assert apply(api, stage, import_id).status_code == 202
    run(worker)
    assert read(api, stage, import_id)["status"] == "applied"
    assert items_of(tree) == before


@pytest.mark.requirement("WF-INTF-0110-A")
def test_a_role_and_a_category_renamed_after_the_export_are_imported_back_by_their_code(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any], costs: Costing
) -> None:
    # « Libellé (code) » is read by its code, the label being only indicative (#2689): the role
    # and the category renamed in the reference since the export, the file imported again presents
    # no difference and rejects no line.
    content = exported(api, stage, worker, held["tree"].revision["revision_id"])
    with stage.owner.begin() as connection:
        connection.execute(
            update(ResourceRole)
            .where(ResourceRole.id == costs.role)
            .values(label="Ingénieur senior")
        )
        connection.execute(
            update(CostCategory)
            .where(CostCategory.id == costs.material)
            .values(label="Matériel courant")
        )
    assert [each["Rôle ou catégorie"] for each in lines_of(content, "Hors lot")] == [
        "Ingénieur (ING)",
        "Matériel électrique (606001)",
    ]
    no_difference(analysed(api, stage, worker, content), 2)


@pytest.mark.requirement("WF-INTF-0110-A")
def test_a_code_shared_by_a_role_and_a_category_keeps_each_line_of_its_kind(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    # A code of a role is unique among the roles, an accounting code among the categories, not
    # between them (#2690): the category « Outillage », accounted under ING as the role is coded,
    # keeps its label in the workbook, and its line comes back a line of that category.
    with stage.database.transaction() as session:
        nature = session.scalars(select(CostType.id).where(CostType.code == "MAT")).one()
        draft = CostCategoryDraft("OUT-001", "Outillage", "ING", nature)
        tools = create_cost_category(session, draft, Act(None, utc_now())).cost_category_id
    tree = held["tree"]
    Lines(tree).made(
        held["first"], quantity="1", cost_category_id=str(tools), unit_disbursement="12.00"
    )
    before = items_of(tree)
    content = exported(api, stage, worker, tree.revision["revision_id"])
    assert [each["Rôle ou catégorie"] for each in lines_of(content, "Hors lot")] == [
        "Ingénieur (ING)",
        "Matériel électrique (606001)",
        "Outillage (ING)",
    ]
    import_id = analysed_import(api, stage, worker, content)
    no_difference(read(api, stage, import_id)["report"], 3)
    assert apply(api, stage, import_id).status_code == 202
    run(worker)
    assert items_of(tree) == before


def with_entry(content: bytes, lineage: str, text: str, *, lineage_kept: bool = True) -> bytes:
    """Change the « Rôle ou catégorie » cell of a line of « Hors lot », found by its lineage.

    With ``lineage_kept`` false the line loses its lineage, so that the file gives a new line.
    """
    book = book_of(content)
    sheet = book["Hors lot"]
    headers = [cell.value for cell in sheet[1]]
    for number, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        if row[headers.index("ID ligne")] == lineage:
            sheet.cell(number, headers.index("Rôle ou catégorie") + 1, text)
            if not lineage_kept:
                sheet.cell(number, headers.index("ID ligne") + 1).value = None
    out = BytesIO()
    book.save(out)
    return out.getvalue()


def a_tools_line(stage: Scene, held: dict[str, Any]) -> str:
    """Add a line of the category « Outillage », accounted ING as the role is coded; its lineage."""
    with stage.database.transaction() as session:
        nature = session.scalars(select(CostType.id).where(CostType.code == "MAT")).one()
        draft = CostCategoryDraft("OUT-001", "Outillage", "ING", nature)
        tools = create_cost_category(session, draft, Act(None, utc_now())).cost_category_id
    made = Lines(held["tree"]).made(
        held["first"], quantity="1", cost_category_id=str(tools), unit_disbursement="12.00"
    )
    return str(made["nodes"][0]["lineage_id"])


@pytest.mark.requirement("WF-INTF-0110-A")
@pytest.mark.parametrize("text", ["Outillage (ING)", "ING"], ids=["renamed", "code-alone"])
def test_a_shared_code_of_no_label_keeps_the_kind_of_the_line_it_replaces_or_rejects_a_new_one(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any], text: str
) -> None:
    # A code the role ING and the category « Outillage » share, whose label is neither the role's
    # nor, since the category was renamed « Outils » after the export, the category's: or no label
    # at all. The line that exists keeps its kind, a category, and is never turned into a labour
    # line; a new line is rejected, for it gives no way to tell (#2690).
    tools = a_tools_line(stage, held)
    content = exported(api, stage, worker, held["tree"].revision["revision_id"])
    with stage.owner.begin() as connection:
        connection.execute(
            update(CostCategory).where(CostCategory.code == "OUT-001").values(label="Outils")
        )
    no_difference(analysed(api, stage, worker, with_entry(content, tools, text)), 3)
    report = analysed(api, stage, worker, with_entry(content, tools, text, lineage_kept=False))
    assert [(each["code"], each["params"]) for each in report["rejected"]] == [
        ("UNKNOWN_RESOURCE_ROLE", {"value": text})
    ]


@pytest.mark.requirement("WF-INTF-0110-A")
def test_a_code_that_holds_parentheses_is_imported_back_by_the_export_that_wrote_it(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    # The accounting code takes any character that is not blank: « 606(1) » for a category, and a
    # role may be coded « R(1) ». The export writes « Rôle R(1) (R(1)) » and « Pièces (606(1)) »;
    # the import finds their codes by the end of the text, and presents no difference.
    role = add_role(stage.database, "R(1)", (8, 8, 8, 8, 8, 0, 0))
    with stage.database.transaction() as session:
        nature = session.scalars(select(CostType.id).where(CostType.code == "MAT")).one()
        draft = CostCategoryDraft("PIE-001", "Pièces", "606(1)", nature)
        parts = create_cost_category(session, draft, Act(None, utc_now())).cost_category_id
    tree, lines = held["tree"], Lines(held["tree"])
    lines.made(held["first"], quantity="1", resource_role_id=str(role), hours="3")
    lines.made(held["first"], quantity="2", cost_category_id=str(parts), unit_disbursement="9.00")
    before = items_of(tree)
    content = exported(api, stage, worker, tree.revision["revision_id"])
    assert [each["Rôle ou catégorie"] for each in lines_of(content, "Hors lot")][2:] == [
        "Rôle R(1) (R(1))",
        "Pièces (606(1))",
    ]
    import_id = analysed_import(api, stage, worker, content)
    no_difference(read(api, stage, import_id)["report"], 4)
    assert apply(api, stage, import_id).status_code == 202
    run(worker)
    assert items_of(tree) == before


@pytest.mark.requirement("WF-INTF-0100-A")
def test_an_estimate_exported_from_a_marked_revision_updates_the_current_one_creating_no_line(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any], costs: Costing
) -> None:
    # « Un devis exporté d'une révision marquée puis réimporté dans la révision en cours met à jour
    # les lignes de même lignée sans en créer aucune. » The marked revision is exported on its
    # images, « Ingénieur (ING) », after the role was renamed « Ingénieur senior » (#2689); the
    # quantity of its labour line changed, the file updates that line of the current revision,
    # rejects none, creates none.
    marked = held["tree"].revision
    mark(stage, marked)
    with stage.owner.begin() as connection:
        connection.execute(
            update(ResourceRole)
            .where(ResourceRole.id == costs.role)
            .values(label="Ingénieur senior")
        )
    current = Tree(api, stage, opened(api, stage))
    lineages = sorted(each["lineage_id"] for each in items_of(current))
    content = exported(api, stage, worker, marked["revision_id"])
    assert lines_of(content, "Hors lot")[0]["Rôle ou catégorie"] == "Ingénieur (ING)"
    labour = held["labour"]["lineage_id"]
    import_id = analysed_import(api, stage, worker, with_quantity(content, labour, 3))
    report = read(api, stage, import_id)["report"]
    assert (report["rejected"], report["refusals"]) == ([], [])
    changes = [(each["change"], each["lineage_id"]) for each in report["differences"]]
    assert changes == [("updated", labour)]
    assert report["differences"][0]["fields"] == ["quantity"]
    assert apply(api, stage, import_id).status_code == 202
    run(worker)
    assert read(api, stage, import_id)["status"] == "applied"
    after = {each["lineage_id"]: each for each in items_of(current)}
    assert sorted(after) == lineages
    assert after[labour]["estimate_line"]["quantity"] == "3"
