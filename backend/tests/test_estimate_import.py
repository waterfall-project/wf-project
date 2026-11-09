# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The import of the workbook of an estimate.

Laid by US-1490/L1, the socle of EP-07, so that no two stories create the same file;
US-1550 writes its tests here ("Les tests du back"). US-1550/L3: the format ``estimate`` — its
header read at the opening, its condition on the main structure of a project In progress, at the
opening and at the application, the analysis of a workbook against the main structure of the
current revision, and its application by the worker —, through the service and its worker, each
answer checked against the contract; and the command of the project that states the import.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import YEAR, Costing, Lines, add_role, costing
from fastapi.testclient import TestClient
from imports_trial import (
    Stopped,
    apply,
    deposited,
    import_worker,
    nodes,
    path,
    read,
    refusal,
    run,
    stored,
    withdraw,
)
from nodes_support import Tree, entries, mark, opened, set_progress
from openpyxl import Workbook
from projects_support import PROJECTS, Scene, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import select, update
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.cost_settings.tables import CostCategory
from waterfall.core.estimate.interface.excel import EstimateFormat
from waterfall.core.estimate.tables import RevisionRate
from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.projects.tables import Project
from waterfall.core.resource_settings.tables import ResourceRole
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
    notes: list[list[Any]] | None = None,
) -> bytes:
    """Write a workbook of the format: its header, « Tâches », a tab of lines, maybe notes."""
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
    if notes is not None:
        written = book.create_sheet("Notes")
        for each in notes:
            written.append(each)
    out = BytesIO()
    book.save(out)
    return out.getvalue()


def row(task: str | None, entry: str | None, cells: dict[str, Any] | None = None) -> list[Any]:
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


def analysed_import(api: ContractClient, stage: Scene, worker: Worker, content: bytes) -> str:
    """Open the import of a workbook and run its analysis; give the import."""
    response = opening(api, stage, content)
    assert response.status_code == 202, response.text
    run(worker)
    return response.json()["import_id"]


def analysed(
    api: ContractClient, stage: Scene, worker: Worker, content: bytes, *, kept: bool = False
) -> dict[str, Any]:
    """Open the import of a workbook, run its analysis; give its report, read by ``getImport``.

    ``kept`` reads it as the database keeps it.
    """
    import_id = analysed_import(api, stage, worker, content)
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
    """Give a structure of two tasks, a labour line and a line of material under the first.

    ``tree`` and ``costs`` are the structure and the categories it is written with.
    """
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
        "tree": tree,
        "costs": costs,
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
def test_a_workbook_without_a_version_or_of_an_unknown_one_is_refused_at_the_opening(
    api: ContractClient, stage: Scene, tree: Tree, held: dict[str, Any], header: tuple[Any, ...]
) -> None:
    # "Un fichier de devis sans version, ou d'une version non reconnue, est refusé avec un message
    # qui nomme le format et la version attendus." — "Le projet est inchangé." : its tasks and its
    # lines, amounts included.
    before = (nodes(stage.database), tree.items())
    changed = workbook(as_exported(held, {"Heures": 12}), held["tasks"], header=header)
    response = opening(api, stage, changed)
    assert refusal(response) == (
        422,
        "FILE_FORMAT_UNREADABLE",
        {"expected_format": "estimate", "expected_version": "1"},
    )
    assert (nodes(stage.database), tree.items()) == before
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
    notes = [["Remarque", "Quantité"], ["à revoir", "beaucoup"]]
    content = workbook(rows, held["tasks"], sheet=HEADERS[:-1], notes=notes)
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


@pytest.mark.requirement("WF-INTF-0080-A")
def test_a_line_without_its_task_or_its_role_or_with_too_long_a_label_is_rejected(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    rows = [
        *as_exported(held),
        row(None, held["stuff"], {"Débours unitaire": 2}),
        row("2 Essais", None, {"Heures": 2}),
        row("2 Essais", held["stuff"], {"Désignation": "x" * 301}),
    ]
    report = analysed(api, stage, worker, workbook(rows, held["tasks"]))
    assert [(each["row"], each["code"], each["params"]) for each in report["rejected"]] == [
        (4, "VALUE_REQUIRED", {"header": "Tâche"}),
        (5, "VALUE_REQUIRED", {"header": "Rôle ou catégorie"}),
        (6, "VALUE_TOO_LONG", {"max_length": 300, "header": "Désignation"}),
    ]


@pytest.mark.requirement("WF-INTF-0100-A")
def test_a_line_moved_to_another_task_is_updated_and_a_repeated_lineage_is_a_new_line(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    # A row copied in Excel keeps the hidden lineage: the first row updates the line, the copy is
    # created; a lineage the structure does not hold is a new line too.
    labour, stuff = as_exported(held, {"Tâche": "2 Essais"})
    unknown = row("2 Essais", held["stuff"], {"Débours unitaire": 5, "ID ligne": "not-a-lineage"})
    rows = [labour, stuff, list(stuff), unknown]
    report = analysed(api, stage, worker, workbook(rows, held["tasks"]))
    assert [(each["change"], each["fields"]) for each in report["differences"]] == [
        ("updated", ["parent"]),
        ("added", []),
        ("added", []),
    ]
    assert (report["read_count"], report["unchanged_count"]) == (4, 1)
    # From a completed task of the main structure, the line does not move: rejected as its entry.
    set_progress(stage, held["first"]["node_id"], "completed", date(2026, 1, 5))
    report = analysed(api, stage, worker, workbook([labour, stuff], held["tasks"]), kept=True)
    assert [(each["row"], each["params"]["missing_condition"]) for each in report["rejected"]] == [
        (2, "task_not_completed")
    ]


# --- The application ---------------------------------------------------------------------------

# An instant of the year after the one the revisions of the tests are priced at.
LATER = datetime(YEAR + 1, 1, 12, 10, tzinfo=UTC)


def applied_now(api: ContractClient, stage: Scene, worker: Worker, import_id: str) -> None:
    """Confirm the application of an import analysed and run it by the worker; it is applied."""
    answer = apply(api, stage, import_id)
    assert answer.status_code == 202, answer.text
    run(worker)
    assert read(api, stage, import_id)["status"] == "applied"


def applied(api: ContractClient, stage: Scene, worker: Worker, content: bytes) -> str:
    """Open, analyse and apply the import of a workbook; give the import applied."""
    import_id = analysed_import(api, stage, worker, content)
    applied_now(api, stage, worker, import_id)
    return import_id


def estimate_lines(items: list[dict[str, Any]]) -> dict[str, tuple[str, dict[str, Any]]]:
    """Give the lines of a structure read by lineage: the lineage of their task, their facet."""
    tasks = {item["node_id"]: item["lineage_id"] for item in items if item["kind"] == "task"}
    return {
        item["lineage_id"]: (tasks[item["parent_id"]], item["estimate_line"])
        for item in items
        if item["kind"] == "estimate_line"
    }


def figure(facet: dict[str, Any], name: str) -> Decimal | None:
    """Read a figure of a line as a number, none when the line has none."""
    value = facet[name]
    return None if value is None else Decimal(value)


def project_of(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Read the project of the stage as its manager does."""
    answer = api.get(f"{PROJECTS}/{stage.project['project_id']}", headers=stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def current_items(api: ContractClient, stage: Scene) -> list[dict[str, Any]]:
    """Read the nodes of the main structure of the current revision, writing nothing."""
    revision = project_of(api, stage)["current_revision_id"]
    base = f"{PROJECTS}/{stage.project['project_id']}/revisions/{revision}/structures"
    listed = api.get(base, headers=stage.manager.headers)
    assert listed.status_code == 200, listed.text
    structure = listed.json()[0]["structure_id"]
    answer = api.get(f"{base}/{structure}/nodes", headers=stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()["items"]


def designate(api: ContractClient, stage: Scene, revision: dict[str, Any]) -> None:
    """Designate a marked revision the reference, as the manager does, confirmed."""
    counter = project_of(api, stage)["lock_version"]
    sent = {"revision_id": revision["revision_id"], "confirmed": True, "lock_version": counter}
    answer = api.put(
        f"{PROJECTS}/{stage.project['project_id']}/reference-revision",
        headers=stage.manager.headers,
        json=sent,
    )
    assert answer.status_code == 200, answer.text


@pytest.mark.requirement("WF-DAT-0110-A")
@pytest.mark.requirement("WF-INTF-0100-A")
@pytest.mark.requirement("WF-INTF-0110-A")
def test_two_imports_of_one_workbook_give_the_same_estimate_the_second_without_difference(
    api: ContractClient, stage: Scene, worker: Worker, tree: Tree, held: dict[str, Any]
) -> None:
    # « Deux imports successifs du même fichier de devis donnent une révision en cours au contenu
    # identique. » ; « Un second import du même fichier donne un devis identique. » ; « Le compte
    # rendu […] ne signale aucun écart, et les lignes obtenues sont identiques. »
    content = workbook(as_exported(held, {"Heures": 12, "Quantité": 3}), held["tasks"])
    applied(api, stage, worker, content)
    first = tree.items()
    line = estimate_lines(first)[held["labour"]["lineage_id"]][1]
    assert (figure(line, "hours"), figure(line, "quantity")) == (12, 3)
    again = analysed_import(api, stage, worker, content)
    report = read(api, stage, again)["report"]
    assert (report["differences"], report["rejected"]) == ([], [])
    assert report["unchanged_count"] == report["read_count"] == 2
    applied_now(api, stage, worker, again)
    assert tree.items() == first


@pytest.mark.requirement("WF-INTF-0100-A")
def test_lines_of_labour_and_of_material_are_written_under_their_tasks_and_absent_ones_removed(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    # « On importe un fichier qui comporte des lignes de main-d'œuvre et des lignes hors
    # main-d'œuvre. » ; « Chaque ligne se retrouve sous la tâche désignée, avec sa quantité, ses
    # heures ou son débours, son rôle et, le cas échéant, son sous-projet. » The import enters
    # nothing in the undo history.
    tree, costs = held["tree"], held["costs"]
    answer = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/subprojects",
        headers=stage.manager.headers,
        json={"code": "SP-CMD", "label": "Poste de commande"},
    )
    assert answer.status_code == 201, answer.text
    subproject = answer.json()["subproject_id"]
    history = len(entries(stage))
    material = {"Désignation": "Câbles", "Quantité": 3, "Débours unitaire": 20}
    rows = [
        as_exported(held, {"Heures": 12})[0],
        row("2 Essais", held["role"], {"Quantité": 2, "Heures": 4, "Sous-projet": "SP-CMD"}),
        row("Essais", held["stuff"], material),
    ]
    applied(api, stage, worker, workbook(rows, held["tasks"]))
    lines = estimate_lines(tree.items())
    first, second = held["first"]["lineage_id"], held["second"]["lineage_id"]
    task, kept = lines.pop(held["labour"]["lineage_id"])
    assert (task, figure(kept, "hours")) == (first, 12)
    assert held["material"]["lineage_id"] not in lines
    created = {
        facet["label"]: (
            task,
            facet["resource_role_id"],
            facet["cost_category_id"],
            figure(facet, "quantity"),
            figure(facet, "hours") if facet["resource_role_id"] else None,
            None if facet["resource_role_id"] else figure(facet, "unit_disbursement"),
            facet["subproject_id"],
        )
        for task, facet in lines.values()
    }
    role = held["role"].split(" (")[0]
    assert created == {
        f"Essais — {role}": (second, str(costs.role), str(costs.labour), 2, 4, None, subproject),
        "Câbles": (second, None, str(costs.material), 3, None, 20, None),
    }
    assert len(entries(stage)) == history


@pytest.mark.requirement("WF-INTF-0100-A")
def test_on_a_project_with_a_reference_a_line_keeps_its_budget_and_lineage_a_new_one_has_none(
    api: ContractClient, stage: Scene, worker: Worker, tree: Tree, held: dict[str, Any]
) -> None:
    # « Un fichier exporté, dont une charge a été modifiée, réimporté sur un projet qui porte une
    # révision de référence sans être encore En cours met à jour cette ligne sans changer son
    # montant budgété ni sa lignée. » A line created has a budgeted amount of nought (WF-DEV-0020).
    mark(stage, tree.revision)
    designate(api, stage, tree.revision)
    current = Tree(api, stage, opened(api, stage))
    before = estimate_lines(current.items())
    rows = [
        *as_exported(held, {"Heures": 12}),
        row("2 Essais", held["stuff"], {"Quantité": 1, "Débours unitaire": 20}),
    ]
    applied(api, stage, worker, workbook(rows, held["tasks"]))
    assert project_of(api, stage)["state"] == "pricing"
    after = estimate_lines(current.items())
    lineage = held["labour"]["lineage_id"]
    was, now = before[lineage][1], after[lineage][1]
    assert figure(now, "hours") == 12
    assert now["budgeted_amount"] == was["budgeted_amount"] != "0.00"
    assert now["reestimated_amount"] != was["reestimated_amount"]
    [added] = [facet for key, (_, facet) in after.items() if key not in before]
    assert (added["budgeted_amount"], added["reestimated_amount"]) == ("0.00", "20.00")


@pytest.mark.requirement("WF-INTF-0080-A")
def test_a_worker_stopped_during_the_application_leaves_the_estimate_as_it_was(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    held: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # « Si l'import est interrompu pendant son application, le projet revient à son état
    # antérieur. » : the worker is stopped once the format has written; nothing is kept, and the
    # task runs again from the start.
    tree = held["tree"]
    rows = [as_exported(held, {"Heures": 12})[0], row("2 Essais", held["stuff"], {"Quantité": 1})]
    import_id = analysed_import(api, stage, worker, workbook(rows, held["tasks"]))
    before = (nodes(stage.database), tree.items())
    written = EstimateFormat.apply

    def stopped(self: EstimateFormat, *arguments: Any) -> None:
        written(self, *arguments)
        raise Stopped

    monkeypatch.setattr(EstimateFormat, "apply", stopped)
    assert apply(api, stage, import_id).status_code == 202
    with pytest.raises(Stopped):
        run(worker)
    assert (nodes(stage.database), tree.items()) == before
    assert read(api, stage, import_id)["status"] == "applying"
    monkeypatch.undo()
    run(worker)
    assert read(api, stage, import_id)["status"] == "applied"
    lines = estimate_lines(tree.items())
    assert held["material"]["lineage_id"] not in lines
    assert len(lines) == 2


@pytest.mark.requirement("WF-INTF-0080-A")
def test_an_estimate_import_abandoned_at_its_report_leaves_the_project_unchanged(
    api: ContractClient, stage: Scene, worker: Worker, tree: Tree, held: dict[str, Any]
) -> None:
    # « Si l'utilisateur abandonne à cette étape, le projet reste inchangé. »
    import_id = analysed_import(api, stage, worker, workbook([], held["tasks"]))
    assert len(read(api, stage, import_id)["report"]["differences"]) == 2
    before = (nodes(stage.database), tree.items())
    abandoned = api.delete(path(stage, import_id), headers=stage.manager.headers)
    assert abandoned.status_code == 204, abandoned.text
    run(worker)
    assert (nodes(stage.database), tree.items()) == before


@pytest.mark.requirement("WF-INTF-0090-A")
def test_an_estimate_on_a_project_whose_revisions_are_all_marked_creates_one_at_projected_rates(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    held: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # « Un import sur un projet dont toutes les révisions sont marquées crée une révision en cours
    # d'élaboration et s'y applique ; les révisions marquées sont inchangées. » ; « Seule la
    # révision en cours est modifiée : […] les montants de la révision marquée sont identiques
    # avant et après chaque import. » The revision is created the next year: it keeps the rate of
    # its source projected by the inflation of the project, 65.00 times 1.03 (US-1500).
    tree, costs = held["tree"], held["costs"]
    mark(stage, tree.revision)
    with stage.owner.begin() as connection:
        connection.execute(
            update(Project)
            .where(Project.id == UUID(stage.project["project_id"]))
            .values(inflation_rate=Decimal("0.03"))
        )
    marked = tree.items()
    content = workbook(as_exported(held, {"Heures": 12}), held["tasks"])
    import_id = analysed_import(api, stage, worker, content)
    monkeypatch.setattr("waterfall.core.exchanges.running.utc_now", lambda: LATER)
    applied_now(api, stage, worker, import_id)
    assert tree.items() == marked
    created = project_of(api, stage)["current_revision_id"]
    assert created not in {None, tree.revision["revision_id"]}
    assert read(api, stage, import_id)["revision_id"] == created
    with stage.database.transaction() as session:
        kept = session.execute(
            select(RevisionRate.cost_category_id, RevisionRate.amount, RevisionRate.origin).where(
                RevisionRate.revision_id == UUID(created)
            )
        ).all()
    assert [tuple(each) for each in kept] == [(costs.labour, Decimal("66.95"), "projected")]
    line = estimate_lines(current_items(api, stage))[held["labour"]["lineage_id"]][1]
    assert figure(line, "hours") == 12


@pytest.mark.requirement("WF-INTF-0100-A")
def test_an_estimate_analysed_before_the_project_is_in_progress_is_refused_at_its_application(
    api: ContractClient, stage: Scene, worker: Worker, tree: Tree, held: dict[str, Any]
) -> None:
    # « Sur un projet En cours, l'import d'un devis sur la structure principale est refusé et nomme
    # la condition » (C-358), at the application as at the opening: the import is refused for good.
    content = workbook(as_exported(held, {"Heures": 12}), held["tasks"])
    import_id = analysed_import(api, stage, worker, content)
    put_in_state(stage.owner, stage.project["project_id"], "in_progress")
    before = tree.items()
    answer = apply(api, stage, import_id)
    assert refusal(answer) == (409, STATE, {"missing_condition": "project_before_in_progress"})
    assert stored(stage.database, import_id).status == "refused"
    run(worker)
    assert tree.items() == before


@pytest.mark.requirement("WF-INTF-0080-A")
def test_a_line_the_structure_refuses_since_the_analysis_fails_the_application_writing_nothing(
    api: ContractClient, stage: Scene, worker: Worker, tree: Tree, held: dict[str, Any]
) -> None:
    # The report the user confirmed is judged again: a line it accepted under a task completed
    # since is refused, and nothing of the file is written (#1767).
    rows = [
        *as_exported(held, {"Heures": 12}),
        row("2 Essais", held["stuff"], {"Débours unitaire": 9}),
    ]
    import_id = analysed_import(api, stage, worker, workbook(rows, held["tasks"]))
    assert read(api, stage, import_id)["report"]["rejected"] == []
    set_progress(stage, held["second"]["node_id"], "completed", date(2026, 1, 5))
    before = tree.items()
    assert apply(api, stage, import_id).status_code == 202
    run(worker)
    assert stored(stage.database, import_id).status == "failed"
    assert tree.items() == before


@pytest.mark.requirement("WF-INTF-0080-A")
def test_a_line_entered_since_the_analysis_is_not_removed_by_the_application(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    # What is applied is the report the user read before confirming: a line entered since, absent
    # from the file, was not announced removed, and stays.
    tree, costs = held["tree"], held["costs"]
    import_id = analysed_import(api, stage, worker, workbook(as_exported(held), held["tasks"]))
    assert read(api, stage, import_id)["report"]["differences"] == []
    entered = Lines(tree).made(
        held["second"], quantity="1", cost_category_id=str(costs.material), unit_disbursement="5"
    )
    applied_now(api, stage, worker, import_id)
    assert entered["nodes"][0]["lineage_id"] in estimate_lines(tree.items())


@pytest.mark.requirement("WF-INTF-0080-A")
def test_a_line_the_report_rejected_is_not_written_though_accepted_since(
    api: ContractClient, stage: Scene, worker: Worker, tree: Tree, held: dict[str, Any]
) -> None:
    # « le compte rendu les liste avec leur motif avant la confirmation » : the user confirmed the
    # file without the line rejected, whose subproject is created since; it is not written.
    rows = [*as_exported(held), row("2 Essais", held["role"], {"Heures": 2, "Sous-projet": "SP"})]
    import_id = analysed_import(api, stage, worker, workbook(rows, held["tasks"]))
    rejected = read(api, stage, import_id)["report"]["rejected"]
    assert [each["code"] for each in rejected] == ["UNKNOWN_SUBPROJECT"]
    answer = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/subprojects",
        headers=stage.manager.headers,
        json={"code": "SP", "label": "Poste"},
    )
    assert answer.status_code == 201, answer.text
    applied_now(api, stage, worker, import_id)
    assert set(estimate_lines(tree.items())) == {
        held["labour"]["lineage_id"],
        held["material"]["lineage_id"],
    }


@pytest.mark.requirement("WF-INTF-0100-A")
def test_the_import_of_an_estimate_is_a_command_of_the_project_that_stays_in_progress(
    api: ContractClient, stage: Scene, queue: TaskQueue
) -> None:
    # « Sur un projet En cours, l'import d'un devis sur la structure principale est refusé » : the
    # import, not the command, which stays available for a differential (C-358); it names what a
    # task of the background, and the revision it would create, ask.
    def lacking() -> list[str]:
        commands = project_of(api, stage)["available_commands"]
        return next(
            each["missing_conditions"] for each in commands if each["command"] == "import_estimate"
        )

    assert lacking() == []
    put_in_state(stage.owner, stage.project["project_id"], "in_progress")
    assert lacking() == []
    withdraw(stage.database, stage.manager, "revisions.write")
    assert lacking() == ["may_create_revision"]
    payload = {
        "project_id": stage.project["project_id"],
        "revision_id": str(UUID(int=1)),
        "version_name": "v1.0",
        "description": None,
    }
    with logging_context(correlation_id="queued-around"), stage.database.transaction() as session:
        submit(session, queue, "revision_mark", stage.manager.user_id, payload)
    assert lacking() == ["no_background_task_running", "may_create_revision"]
