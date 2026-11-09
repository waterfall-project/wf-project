# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The import of the workbook of an estimate.

Laid by US-1490/L1, the socle of EP-07, so that no two stories create the same file;
US-1550 writes its tests here ("Les tests du back"). US-1550/L3: the format ``estimate`` — its
header read at the opening, its condition on the main structure of a project In progress, and the
analysis of a workbook against the main structure of the current revision, through the service
and its worker, each report read through ``getImport`` and checked against the contract.
"""

from datetime import date
from io import BytesIO
from typing import TYPE_CHECKING, Any

import pytest
from estimate_support import Costing, Lines, add_role, costing
from fastapi.testclient import TestClient
from imports_trial import (
    deposited,
    import_worker,
    nodes,
    read,
    refusal,
    run,
    stored,
)
from nodes_support import Tree, mark, opened, set_progress
from openpyxl import Workbook
from projects_support import PROJECTS, Scene, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import select
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.cost_settings.tables import CostCategory
from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.resource_settings.tables import ResourceRole
from waterfall.platform.keycloak_admin import KeycloakAdmin

if TYPE_CHECKING:
    from uuid import UUID

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket
    from waterfall.worker.runner import Worker

HEADERS = [
    "Tâche",
    "Description de la tâche",
    "Rôle ou catégorie",
    "Désignation",
    "Quantité",
    "Heures",
    "Débours unitaire",
    "Délai de paiement (j)",
    "Sous-projet",
    "Montant Waterfall",
    "ID ligne",
]
SHEET = "1 Études"
STATE = "STATE_FORBIDS_OPERATION"


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
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name, rated for the year."""
    return costing(stage.database)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the current revision of the project of the stage."""
    return Tree(api, stage, opened(api, stage))


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports and the markings."""
    return import_worker(database, queue, backups_bucket)


def entry_of(database: Database, model: type[ResourceRole | CostCategory], key: UUID) -> str:
    """Give the entry « label (code) » the list of « Paramètres » shows of a role or a category."""
    with database.transaction() as session:
        label, code = session.execute(select(model.label, model.code).where(model.id == key)).one()
    return f"{label} ({code})"


def workbook(
    rows: list[list[Any]],
    tasks: dict[str, str] | None = None,
    header: tuple[Any, ...] = ("Format", "Devis", "Version", 1),
    sheet: list[Any] | None = None,
) -> bytes:
    """Write a workbook of the format: its header, « Tâches », and a tab of lines."""
    book = Workbook()
    first = book.active
    assert first is not None
    first.title = "Présentation"
    first.append(list(header[:2]))
    first.append(list(header[2:]))
    listed = book.create_sheet("Tâches")
    listed.append(["Tâches de la structure"])
    listed.append(["Entrée", "ID tâche", "N°", "Libellé"])
    for entry, lineage in (tasks or {}).items():
        listed.append([entry, lineage, entry.split(" ")[0], entry])
    lines = book.create_sheet(SHEET)
    lines.append(sheet or HEADERS)
    for row in rows:
        lines.append(row)
    out = BytesIO()
    book.save(out)
    return out.getvalue()


def row(task: str, entry: str, cells: dict[str, Any] | None = None) -> list[Any]:
    """Give a row of a tab of lines, by the headers of ``HEADERS``."""
    named = {"Tâche": task, "Rôle ou catégorie": entry, **(cells or {})}
    return [named.get(header) for header in HEADERS]


def opening(api: ContractClient, stage: Scene, content: bytes) -> Any:
    """Deposit a workbook and open its import as the manager does; give the answer."""
    upload_id = deposited(api, stage.manager, content)
    return api.post(
        f"{PROJECTS}/{stage.project['project_id']}/imports",
        headers=stage.manager.headers,
        json={"kind": "estimate", "upload_id": upload_id},
    )


def analysed(
    api: ContractClient, stage: Scene, worker: Worker, content: bytes, *, kept: bool = False
) -> dict[str, Any]:
    """Open the import of a workbook, run its analysis; give its report, read by ``getImport``.

    ``kept`` reads it as the database keeps it: ``ContractClient`` refuses a report whose
    rejections name tasks, ``ProblemParams.tasks`` composing two shapes of object (``anyOf``),
    which its check of the properties declared does not tell apart.
    """
    response = opening(api, stage, content)
    assert response.status_code == 202, response.text
    run(worker)
    import_id = response.json()["import_id"]
    if kept:
        row = stored(stage.database, import_id)
        assert row.status == "analysed"
        return dict(row.report or {})
    found = read(api, stage, import_id)
    assert found["status"] == "analysed", found
    return found["report"]


def by_lineage(tree: Tree) -> dict[str, dict[str, Any]]:
    """Give the nodes of the structure by their lineage."""
    return {item["lineage_id"]: item for item in tree.items()}


@pytest.fixture
def held(tree: Tree, costs: Costing, stage: Scene) -> dict[str, Any]:
    """Give a structure of two tasks, a labour line and a line of material under the first."""
    first, second = tree.made("Câblage"), tree.made("Essais")
    lines = Lines(tree)
    labour = lines.made(first, quantity="2", resource_role_id=str(costs.role), hours="10")
    stuff = lines.made(
        first, quantity="1", cost_category_id=str(costs.material), unit_disbursement="350.00"
    )
    return {
        "first": first,
        "second": second,
        "labour": labour["nodes"][0],
        "material": stuff["nodes"][0],
        "role": entry_of(stage.database, ResourceRole, costs.role),
        "stuff": entry_of(stage.database, CostCategory, costs.material),
        "tasks": {"1 Câblage": first["lineage_id"], "2 Essais": second["lineage_id"]},
    }


def as_exported(held: dict[str, Any], changes: dict[str, Any] | None = None) -> list[list[Any]]:
    """Give the rows the export writes of the two lines of ``held``, the labour line changed."""
    labour, stuff = held["labour"], held["material"]
    return [
        row(
            "1 Câblage",
            held["role"],
            {
                "Désignation": labour["estimate_line"]["label"],
                "Quantité": 2,
                "Heures": 10,
                "Délai de paiement (j)": 0,
                "ID ligne": labour["lineage_id"],
                **(changes or {}),
            },
        ),
        row(
            "1 Câblage",
            held["stuff"],
            {
                "Désignation": stuff["estimate_line"]["label"],
                "Quantité": 1,
                "Débours unitaire": 350,
                "Délai de paiement (j)": 0,
                "ID ligne": stuff["lineage_id"],
            },
        ),
    ]


@pytest.mark.requirement("WF-INTF-0070-A")
@pytest.mark.parametrize(
    "header",
    [
        pytest.param(("Format", "Devis", "Version", None), id="without-version"),
        pytest.param(("Format", "Devis", "Version", 7), id="unknown-version"),
        pytest.param(("Format", "Reste", "Version", 1), id="another-format"),
    ],
)
@pytest.mark.usefixtures("tree")
def test_a_workbook_without_a_version_or_of_an_unknown_one_is_refused_at_the_opening(
    api: ContractClient, stage: Scene, header: tuple[Any, ...]
) -> None:
    # "Un fichier de devis sans version, ou d'une version non reconnue, est refusé avec un message
    # qui nomme le format et la version attendus." — "Le projet est inchangé."
    before = nodes(stage.database)
    response = opening(api, stage, workbook([], header=header))
    assert refusal(response) == (
        422,
        "FILE_FORMAT_UNREADABLE",
        {"expected_format": "estimate", "expected_version": "1"},
    )
    assert nodes(stage.database) == before
    with stage.database.transaction() as session:
        assert session.scalars(select(ImportReport)).all() == []


@pytest.mark.requirement("WF-INTF-0070-A")
def test_a_file_that_is_no_workbook_is_refused_at_the_opening(
    api: ContractClient, stage: Scene
) -> None:
    response = opening(api, stage, b"Format;Devis\nVersion;1\n")
    assert refusal(response)[:2] == (422, "FILE_FORMAT_UNREADABLE")


@pytest.mark.requirement("WF-INTF-0100-A")
@pytest.mark.usefixtures("tree")
def test_an_estimate_on_the_main_structure_of_a_project_in_progress_is_refused(
    api: ContractClient, stage: Scene
) -> None:
    # "Sur un projet En cours, l'import d'un devis sur la structure principale est refusé et nomme
    # la condition" (C-358): nothing is analysed.
    put_in_state(stage.owner, stage.project["project_id"], "in_progress")
    response = opening(api, stage, workbook([]))
    assert refusal(response) == (409, STATE, {"missing_condition": "project_before_in_progress"})
    with stage.database.transaction() as session:
        assert session.scalars(select(ImportReport)).all() == []


@pytest.mark.requirement("WF-INTF-0100-A")
@pytest.mark.requirement("WF-INTF-0110-A")
def test_a_file_as_exported_presents_no_difference_and_leaves_every_line_unchanged(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    report = analysed(api, stage, worker, workbook(as_exported(held), held["tasks"]))
    assert (report["differences"], report["rejected"]) == ([], [])
    assert (report["read_count"], report["unchanged_count"]) == (2, 2)
    assert report["format_version"] == "1"


@pytest.mark.requirement("WF-INTF-0100-A")
def test_a_changed_hour_updates_its_line_by_its_lineage_and_new_lines_are_added(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    # "On importe un fichier qui comporte des lignes de main-d'œuvre et des lignes hors
    # main-d'œuvre" ; "Chaque ligne se retrouve sous la tâche désignée".
    rows = as_exported(held, {"Heures": 12})
    rows.append(row("2 Essais", held["role"], {"Quantité": 1, "Heures": 4}))
    rows.append(row("Essais", held["stuff"], {"Quantité": 3, "Débours unitaire": 20}))
    report = analysed(api, stage, worker, workbook(rows, held["tasks"]))
    labour = held["labour"]
    assert report["differences"] == [
        {
            "change": "updated",
            "target": "estimate_line",
            "lineage_id": labour["lineage_id"],
            "label": labour["estimate_line"]["label"],
            "fields": ["hours"],
        },
        {
            "change": "added",
            "target": "estimate_line",
            "lineage_id": None,
            "label": f"Essais — {held['role'].split(' (')[0]}",
            "fields": [],
        },
        {
            "change": "added",
            "target": "estimate_line",
            "lineage_id": None,
            "label": "Essais",
            "fields": [],
        },
    ]
    assert (report["read_count"], report["unchanged_count"], report["rejected"]) == (4, 1, [])


@pytest.mark.requirement("WF-INTF-0100-A")
@pytest.mark.requirement("WF-INTF-0080-A")
def test_a_line_citing_an_unknown_task_role_or_subproject_is_rejected_naming_the_cell(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    # "Une ligne qui cite une tâche, un rôle ou un sous-projet inconnu […] est rejetée et figure au
    # compte rendu" ; "le compte rendu les liste avec leur motif avant la confirmation".
    rows = as_exported(held)
    rows.append(row("Recette", held["role"], {"Quantité": 1, "Heures": 2}))
    rows.append(row("2 Essais", "Plombier (PLB)", {"Quantité": 1, "Heures": 2}))
    rows.append(row("2 Essais", held["role"], {"Heures": 2, "Sous-projet": "ZZ"}))
    report = analysed(api, stage, worker, workbook(rows, held["tasks"]))
    assert report["rejected"] == [
        {"sheet": SHEET, "row": 4, "code": "UNKNOWN_TASK", "params": {"value": "Recette"}},
        {
            "sheet": SHEET,
            "row": 5,
            "code": "UNKNOWN_RESOURCE_ROLE",
            "params": {"value": "Plombier (PLB)"},
        },
        {"sheet": SHEET, "row": 6, "code": "UNKNOWN_SUBPROJECT", "params": {"value": "ZZ"}},
    ]
    assert (report["read_count"], report["unchanged_count"], report["differences"]) == (5, 2, [])


@pytest.mark.requirement("WF-INTF-0080-A")
def test_a_number_written_as_text_is_rejected_naming_its_value_and_its_header(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    rows = as_exported(held, {"Heures": "12"})
    rows.append(row("2 Essais", held["role"], {"Heures": 2, "Délai de paiement (j)": 1.5}))
    report = analysed(api, stage, worker, workbook(rows, held["tasks"]))
    assert report["rejected"] == [
        {
            "sheet": SHEET,
            "row": 2,
            "code": "NUMBER_INVALID",
            "params": {"header": "Heures", "value": "12"},
        },
        {
            "sheet": SHEET,
            "row": 4,
            "code": "NUMBER_INVALID",
            "params": {"value": "1.5", "header": "Délai de paiement (j)"},
        },
    ]
    # The line rejected keeps its lineage: it is not absent, and is left as it is.
    assert report["differences"] == []


@pytest.mark.requirement("WF-INTF-0080-A")
def test_a_line_its_entry_would_refuse_is_rejected_by_the_reason_of_its_field(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    rows = [row("2 Essais", held["stuff"], {"Quantité": -1, "Débours unitaire": 2})]
    report = analysed(api, stage, worker, workbook([*as_exported(held), *rows], held["tasks"]))
    assert report["rejected"] == [
        {
            "sheet": SHEET,
            "row": 4,
            "code": "VALUE_OUT_OF_RANGE",
            "params": {"minimum": 0, "header": "Quantité"},
        }
    ]


@pytest.mark.requirement("WF-INTF-0080-A")
def test_a_task_designated_by_a_label_several_tasks_carry_is_rejected_naming_them(
    api: ContractClient, stage: Scene, worker: Worker, tree: Tree, held: dict[str, Any]
) -> None:
    twin = tree.made("Essais")
    rows = [*as_exported(held), row("Essais", held["stuff"], {"Débours unitaire": 2})]
    report = analysed(api, stage, worker, workbook(rows, held["tasks"]), kept=True)
    second = held["second"]
    assert report["rejected"] == [
        {
            "sheet": SHEET,
            "row": 4,
            "code": "AMBIGUOUS_TASK_LABEL",
            "params": {
                "label": "Essais",
                "tasks": [
                    {"lineage_id": second["lineage_id"], "label": "Essais"},
                    {"lineage_id": twin["lineage_id"], "label": "Essais"},
                ],
            },
        }
    ]


@pytest.mark.requirement("WF-INTF-0100-A")
@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_line_that_would_leave_its_task_without_hours_is_rejected_naming_roles_and_task(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any], costs: Costing
) -> None:
    # "ou qui laisserait une tâche sans aucune heure travaillée dans la semaine (WF-PLA-0010), est
    # rejetée" — the role of the week-end beside the role of the week.
    weekend = add_role(stage.database, "WE", (0, 0, 0, 0, 0, 8, 8))
    entry = entry_of(stage.database, ResourceRole, weekend)
    rows = [*as_exported(held), row("1 Câblage", entry, {"Quantité": 1, "Heures": 2})]
    report = analysed(api, stage, worker, workbook(rows, held["tasks"]), kept=True)
    [rejected] = report["rejected"]
    assert (rejected["row"], rejected["code"]) == (4, "TASK_WITHOUT_WORKING_HOURS")
    params = rejected["params"]
    assert {role["resource_role_id"] for role in params["resource_roles"]} == {
        str(costs.role),
        str(weekend),
    }
    assert params["tasks"] == [{"lineage_id": held["first"]["lineage_id"], "label": "Câblage"}]
    # Alone under a task, the role of the week-end has its hours.
    alone = [*as_exported(held), row("2 Essais", entry, {"Quantité": 1, "Heures": 2})]
    assert analysed(api, stage, worker, workbook(alone, held["tasks"]))["rejected"] == []


@pytest.mark.requirement("WF-INTF-0100-A")
def test_a_line_of_a_category_of_provision_is_rejected(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any], costs: Costing
) -> None:
    # "une ligne de catégorie de provision sans identifiant est rejetée au compte rendu."
    entry = entry_of(stage.database, CostCategory, costs.provision)
    rows = [*as_exported(held), row("2 Essais", entry, {"Débours unitaire": 100})]
    report = analysed(api, stage, worker, workbook(rows, held["tasks"]))
    assert [(each["row"], each["code"]) for each in report["rejected"]] == [
        (4, "PROVISION_CATEGORY_RESERVED")
    ]


@pytest.mark.requirement("WF-INTF-0100-A")
def test_a_new_line_under_a_completed_task_of_the_main_structure_is_rejected(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    # #1767: rejected as its entry is refused, the task named (I-05).
    second = held["second"]
    set_progress(stage, second["node_id"], "completed", date(2026, 1, 5))
    rows = [*as_exported(held), row("2 Essais", held["stuff"], {"Débours unitaire": 9})]
    report = analysed(api, stage, worker, workbook(rows, held["tasks"]), kept=True)
    assert report["rejected"] == [
        {
            "sheet": SHEET,
            "row": 4,
            "code": STATE,
            "params": {
                "missing_condition": "task_not_completed",
                "tasks": [{"lineage_id": second["lineage_id"], "label": "Essais"}],
            },
        }
    ]


@pytest.mark.requirement("WF-INTF-0100-A")
def test_lines_absent_from_the_file_are_removed_but_kept_under_a_started_task(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    labour, stuff = held["labour"], held["material"]
    report = analysed(api, stage, worker, workbook([], held["tasks"]))
    assert [(each["change"], each["lineage_id"]) for each in report["differences"]] == [
        ("removed", labour["lineage_id"]),
        ("removed", stuff["lineage_id"]),
    ]
    set_progress(stage, held["first"]["node_id"], "started", date(2026, 1, 5))
    report = analysed(api, stage, worker, workbook([], held["tasks"]))
    assert [(each["change"], each["fields"]) for each in report["differences"]] == [
        ("kept", []),
        ("kept", []),
    ]
    assert report["read_count"] == report["unchanged_count"] == 0


@pytest.mark.requirement("WF-INTF-0100-A")
def test_a_missing_header_reads_its_cells_empty_and_an_unknown_tab_is_ignored(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    # Without « ID ligne », each line is new and those of the structure are absent; nothing refuses
    # the file: the user reads it before confirming (WF-INTF-0080).
    rows = [each[:-1] for each in as_exported(held)]
    content = workbook(rows, held["tasks"], sheet=HEADERS[:-1])
    report = analysed(api, stage, worker, content)
    assert [each["change"] for each in report["differences"]] == [
        "added",
        "added",
        "removed",
        "removed",
    ]
    assert report["rejected"] == []


@pytest.mark.requirement("WF-INTF-0090-A")
def test_a_project_whose_revisions_are_all_marked_is_analysed_on_the_last_marked_one(
    api: ContractClient, stage: Scene, worker: Worker, tree: Tree, held: dict[str, Any]
) -> None:
    # The application creates the current revision, a copy of the last marked one, whose lines keep
    # their lineages: the analysis reads that revision, nothing of which it changes.
    mark(stage, tree.revision)
    before = nodes(stage.database)
    report = analysed(api, stage, worker, workbook(as_exported(held), held["tasks"]))
    assert (report["differences"], report["rejected"]) == ([], [])
    assert nodes(stage.database) == before
