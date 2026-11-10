# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The analysis of an extraction of the actual costs against the lines of the project.

Laid by US-1580/L1, the socle of EP-09, so that no two stories create the same file;
US-1610/L1 writes its tests here ("Les tests du back"): the reading of the lines of an extraction —
the WBS element, the document and its item, the date, the amount, the columns kept —, without a
database; then the report of an analysis through the service and its worker — the lines rejected,
doubled, added, updated and unchanged, the columns ignored, the reasons to confirm —, each answer
checked against the contract.
"""

from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from actual_costs_import_support import (
    CODE,
    SUBPROJECT,
    analysed,
    declare,
    extraction,
    in_progress,
    line,
    subproject,
)
from costs_support import insert_cost_line, write_import
from fastapi.testclient import TestClient
from imports_trial import import_worker
from projects_support import Scene
from projects_support import scene as make_scene
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.costs.extraction import Kept, Reading, read_lines
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

# The reading of the header of ``HEADERS`` as the mapping of the support declares it.
READING = Reading(
    {"wbs_element": 0, "document_number": 1, "document_item": 2, "document_date": 3, "amount": 4},
    (Kept(5, "Fournisseur"),),
    ("Nom Matricule",),
)
ELEMENT = f"{CODE}/{SUBPROJECT}"


def lines_of(*rows: Sequence[Any]) -> list[tuple[Any, ...]]:
    """Read rows below the headers; give each line accepted or rejected, by its row, in order."""
    read = read_lines(rows, READING, CODE)
    accepted: list[tuple[Any, ...]] = [
        (
            each.row,
            each.subproject_code,
            each.document_number,
            each.document_item,
            each.document_date,
            each.amount,
            dict(each.passthrough),
        )
        for each in read.lines
    ]
    rejected: list[tuple[Any, ...]] = [
        (each.row, each.code, dict(each.params)) for each in read.rejected
    ]
    return sorted([*accepted, *rejected], key=lambda each: each[0])


def rejection(**named: Any) -> tuple[str, dict[str, Any]]:
    """Read one row, valid but for the cells named; give the reason it is rejected for."""
    (only,) = lines_of(line(**named))
    assert len(only) == 3, only
    return only[1], only[2]


@pytest.mark.requirement("WF-CRE-0020-A")
@pytest.mark.parametrize(
    ("element", "expected"),
    [
        pytest.param(None, ("WBS_ELEMENT_INVALID", {"wbs_element": ""}), id="empty"),
        pytest.param("   ", ("WBS_ELEMENT_INVALID", {"wbs_element": "   "}), id="blank"),
        pytest.param("/10001", ("WBS_ELEMENT_INVALID", {"wbs_element": "/10001"}), id="slash"),
        pytest.param(f"{CODE}/", ("WBS_ELEMENT_INVALID", {"wbs_element": f"{CODE}/"}), id="no-sub"),
        pytest.param(
            "A.ABC.26002/10001",
            (
                "WBS_ELEMENT_OUTSIDE_PROJECT",
                {"wbs_element": "A.ABC.26002/10001", "project_code": "A.ABC.26002"},
            ),
            id="other-project",
        ),
        pytest.param(
            "A.ABC/26001",
            (
                "WBS_ELEMENT_OUTSIDE_PROJECT",
                {"wbs_element": "A.ABC/26001", "project_code": "A.ABC"},
            ),
            id="slash-inside-the-code",
        ),
        pytest.param(
            f"{CODE}/{'9' * 51}",
            ("VALUE_TOO_LONG", {"column": "wbs_element", "max_length": 50}),
            id="subproject-too-long",
        ),
    ],
)
def test_a_wbs_element_without_the_expected_form_or_of_another_project_is_rejected(
    element: str | None, expected: tuple[str, dict[str, Any]]
) -> None:
    # « Une ligne dont l'élément d'OTP ne respecte pas la forme attendue — vide, ou sans rien avant
    # la barre oblique — est signalée au compte rendu et n'est pas importée » ; « Une ligne d'un
    # autre projet est rejetée et signalée. » ; « une ligne d'élément A.ABC.26002/10001 est rejetée
    # comme d'un autre projet. »
    assert rejection(element=element) == expected


@pytest.mark.requirement("WF-CRE-0020-A")
def test_the_code_of_the_project_holds_dots_and_only_the_slash_separates_the_subproject() -> None:
    # « Sur le projet de code A.ABC.26001, une ligne d'élément A.ABC.26001/10001 est imputée au
    # sous-projet 10001 » ; « une ligne qui ne porte que le code projet, sans sous-projet, est
    # importée et imputée au seul projet. » ; the part after the first slash is the subproject's.
    read = lines_of(
        line(element=ELEMENT, number="1"),
        line(element=f" {CODE} ", number="2"),
        line(element=f"{CODE}/10/01", number="3"),
    )
    assert [(each[0], each[1]) for each in read] == [(2, "10001"), (3, None), (4, "10/01")]


@pytest.mark.requirement("WF-INTF-0140-A")
def test_the_document_its_item_and_the_columns_kept_are_read_as_texts() -> None:
    # The document a text or a whole number; the item a text, a number, or none; the columns kept
    # in text, an empty one left out; an empty row is not read.
    read = read_lines(
        [
            line(number=5100001234, item=10, supplier=None),
            (None, "", "   ", None, None, None, None),
            line(number=" 51-A ", item="0010", supplier=4711.0),
            line(number=5100001235.0, item=None, supplier=" Atelier Durand "),
        ],
        READING,
        CODE,
    )
    assert read.read_count == 3
    assert [(each.row, each.key, dict(each.passthrough)) for each in read.lines] == [
        (2, ("5100001234", "10"), {}),
        (4, ("51-A", "0010"), {"Fournisseur": "4711"}),
        (5, ("5100001235", None), {"Fournisseur": "Atelier Durand"}),
    ]


@pytest.mark.requirement("WF-INTF-0140-A")
@pytest.mark.parametrize(
    ("cells", "expected"),
    [
        pytest.param(
            {"number": None}, ("VALUE_REQUIRED", {"column": "document_number"}), id="no-doc"
        ),
        pytest.param(
            {"number": "9" * 201},
            ("VALUE_TOO_LONG", {"column": "document_number", "max_length": 200}),
            id="long-doc",
        ),
        pytest.param({"on": None}, ("VALUE_REQUIRED", {"column": "document_date"}), id="no-date"),
        pytest.param(
            {"on": "02/04/2026"},
            ("DATE_INVALID", {"column": "document_date", "value": "02/04/2026"}),
            id="french-date",
        ),
        pytest.param(
            {"on": "2026-02-30"},
            ("DATE_INVALID", {"column": "document_date", "value": "2026-02-30"}),
            id="no-such-day",
        ),
        pytest.param(
            {"on": 46114},
            ("DATE_INVALID", {"column": "document_date", "value": "46114"}),
            id="number-as-date",
        ),
        pytest.param({"amount": None}, ("VALUE_REQUIRED", {"column": "amount"}), id="no-amount"),
        pytest.param(
            {"amount": "1250"},
            ("NUMBER_INVALID", {"column": "amount", "value": "1250"}),
            id="number-as-text",
        ),
        pytest.param(
            {"amount": "12,50"},
            ("NUMBER_INVALID", {"column": "amount", "value": "12,50"}),
            id="french-number",
        ),
        pytest.param(
            {"amount": True},
            ("NUMBER_INVALID", {"column": "amount", "value": "True"}),
            id="boolean",
        ),
        pytest.param(
            {"amount": 1e13},
            (
                "VALUE_OUT_OF_RANGE",
                {
                    "column": "amount",
                    "minimum": "-999999999999.99",
                    "maximum": "999999999999.99",
                },
            ),
            id="too-large",
        ),
    ],
)
def test_a_line_is_rejected_for_the_first_fault_of_its_cells(
    cells: dict[str, Any], expected: tuple[str, dict[str, Any]]
) -> None:
    assert rejection(**cells) == expected


@pytest.mark.requirement("WF-CRE-0010-A")
@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        pytest.param(0.005, "0.01", id="half-cent"),
        pytest.param(-0.005, "-0.01", id="negative-half-cent-away-from-zero"),
        pytest.param(2.675, "2.68", id="written-as-seen"),
        pytest.param(-2.675, "-2.68", id="negative-written-as-seen"),
        pytest.param(0.004, "0.00", id="below-half"),
        pytest.param(-0.004, "0.00", id="negative-below-half"),
    ],
)
def test_an_amount_is_rounded_half_a_cent_away_from_zero(amount: float, expected: str) -> None:
    # ROUND_HALF_UP of ``decimal``: away from zero, not toward plus infinity; the rule is left to
    # settle by the spec (#2721).
    (only,) = lines_of(line(amount=amount))
    assert only[5] == Decimal(expected)


@pytest.mark.requirement("WF-CRE-0010-A")
@pytest.mark.parametrize("amount", [1e30, -1e30, 1e300, 1e28])
def test_an_amount_far_beyond_the_column_is_rejected_out_of_range(amount: float) -> None:
    code, params = rejection(amount=amount)
    assert code == "VALUE_OUT_OF_RANGE"
    assert params["column"] == "amount"


@pytest.mark.requirement("WF-CRE-0020-A")
def test_the_wbs_element_is_reported_as_the_file_carries_it() -> None:
    # « tel que le fichier le porte » : spaces at its ends kept; a slash with nothing after it is
    # rejected as invalid (#2721).
    carried = f"  {CODE}/ "
    assert rejection(element=carried) == ("WBS_ELEMENT_INVALID", {"wbs_element": carried})
    code, params = rejection(element=" A.ABC.26002/1 ")
    assert (code, params["wbs_element"]) == ("WBS_ELEMENT_OUTSIDE_PROJECT", " A.ABC.26002/1 ")


@pytest.mark.requirement("WF-CRE-0010-A")
def test_a_date_is_a_cell_of_date_or_a_text_and_an_amount_is_signed_to_the_cent() -> None:
    # « Une ligne de montant négatif est acceptée et diminue le coût réel. » : an amount signed,
    # in a numeric cell, kept to the cent.
    read = lines_of(
        line(number="1", on=datetime.combine(date(2026, 4, 2), time.min), amount=-300.5),
        line(number="2", on=date(2026, 4, 3), amount=0.1 + 0.2),
        line(number="3", on=" 2026-04-04 ", amount=1250),
    )
    assert [(each[4], each[5]) for each in read] == [
        (date(2026, 4, 2), Decimal("-300.50")),
        (date(2026, 4, 3), Decimal("0.30")),
        (date(2026, 4, 4), Decimal("1250.00")),
    ]


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


def added(number: str, item: str | None = None) -> dict[str, Any]:
    return {
        "change": "added",
        "target": "actual_cost_line",
        "lineage_id": None,
        "label": number,
        "document_item": item,
        "fields": [],
    }


def updated(number: str, *fields: str, item: str | None = None) -> dict[str, Any]:
    return {**added(number, item), "change": "updated", "fields": list(fields)}


@pytest.mark.requirement("WF-CRE-0020-A")
@pytest.mark.usefixtures("lot")
def test_the_report_rejects_the_lines_of_another_project_and_keeps_an_unknown_subproject(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Une ligne d'un autre projet est rejetée et signalée. » : `lines_outside_project` among the
    # reasons to confirm. « Une ligne dont le sous-projet est inconnu est importée, imputée au
    # projet » : accepted, `unknown_subproject`.
    content = extraction(
        [
            line(element=None, number="1"),
            line(element=CODE, number="2"),
            line(element=ELEMENT, number="3"),
            line(element="A.ABC.26002/10001", number="4"),
            line(element=f"{CODE}/99999", number="5"),
        ]
    )
    report = analysed(api, stage, worker, content)["report"]
    assert [(each["row"], each["code"]) for each in report["rejected"]] == [
        (2, "WBS_ELEMENT_INVALID"),
        (5, "WBS_ELEMENT_OUTSIDE_PROJECT"),
    ]
    assert report["differences"] == [added("2"), added("3"), added("5")]
    assert report["requires_confirmation_reasons"] == [
        "lines_outside_project",
        "unknown_subproject",
    ]
    assert (report["read_count"], report["unchanged_count"], report["format_version"]) == (
        5,
        0,
        None,
    )


@pytest.mark.requirement("WF-INTF-0140-A")
@pytest.mark.usefixtures("lot")
def test_two_lines_of_the_same_document_and_item_are_doubled_whatever_else_they_lack(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « … une ligne pour laquelle une autre ligne du fichier porte la même pièce et le même poste »
    # (ImportRejection), without condition: the amount of one in text, both are rejected doubled; a
    # line of another project doubled likewise; a document unreadable doubles nothing.
    content = extraction(
        [
            line(number="9100", amount="12,50"),
            line(number="9100"),
            line(number="9200", element="A.ABC.26002/1"),
            line(number="9200"),
            line(number=None),
            line(number=None),
        ]
    )
    report = analysed(api, stage, worker, content)["report"]
    assert report["differences"] == []
    required = {"column": "document_number"}
    assert report["rejected"] == [
        {"sheet": None, "row": 2, "code": "DUPLICATE_COST_LINE", "params": {"rows": [3]}},
        {"sheet": None, "row": 3, "code": "DUPLICATE_COST_LINE", "params": {"rows": [2]}},
        {"sheet": None, "row": 4, "code": "DUPLICATE_COST_LINE", "params": {"rows": [5]}},
        {"sheet": None, "row": 5, "code": "DUPLICATE_COST_LINE", "params": {"rows": [4]}},
        {"sheet": None, "row": 6, "code": "VALUE_REQUIRED", "params": required},
        {"sheet": None, "row": 7, "code": "VALUE_REQUIRED", "params": required},
    ]
    assert report["requires_confirmation_reasons"] == []


@pytest.mark.requirement("WF-INTF-0140-A")
@pytest.mark.usefixtures("lot")
def test_an_invoice_split_in_two_items_gives_two_lines_and_doubled_lines_are_rejected_each(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Une facture ventilée sur deux éléments d'OTP, en deux postes de la même pièce, donne deux
    # lignes de coût ; deux lignes de la même pièce sans poste sont rejetées au compte rendu. » :
    # each, `params.rows` the rows of the others; an item read as text, 10 and "10" alike.
    content = extraction(
        [
            line(element=ELEMENT, number="9000", item="1"),
            line(element=CODE, number="9000", item="2"),
            line(number="9100"),
            line(number="9100", amount=-40),
            line(number="9100", element=CODE),
            (None, None, None, None, None, None, None),
            line(number="9200", item="10"),
            line(number="9200", item=10),
            line(number="9300", element="A.ABC.26002/1"),
            line(number="9301"),
        ]
    )
    report = analysed(api, stage, worker, content)["report"]
    assert report["differences"] == [added("9000", "1"), added("9000", "2"), added("9301")]
    assert report["rejected"] == [
        {"sheet": None, "row": row, "code": "DUPLICATE_COST_LINE", "params": {"rows": rows}}
        for row, rows in ((4, [5, 6]), (5, [4, 6]), (6, [4, 5]), (8, [9]), (9, [8]))
    ] + [
        {
            "sheet": None,
            "row": 10,
            "code": "WBS_ELEMENT_OUTSIDE_PROJECT",
            "params": {"wbs_element": "A.ABC.26002/1", "project_code": "A.ABC.26002"},
        }
    ]
    assert (report["read_count"], report["unchanged_count"]) == (9, 0)
    assert report["requires_confirmation_reasons"] == ["lines_outside_project"]


def _held(stage: Scene, subproject_id: str) -> None:
    """Write three lines of the project, as an earlier import would have."""
    project_id = UUID(stage.project["project_id"])
    supplier = {"Fournisseur": "Atelier Durand"}
    with stage.owner.begin() as connection:
        imported = write_import(connection, project_id)
        insert_cost_line(connection, imported, document_number="1", passthrough=supplier)
        insert_cost_line(
            connection,
            imported,
            document_number="2",
            document_item="1",
            amount=Decimal("500.00"),
            subproject_code=SUBPROJECT,
            subproject_id=UUID(subproject_id),
            passthrough=supplier,
            is_in_tracked_scope=False,
            excluded_reason="Hors périmètre",
        )
        insert_cost_line(
            connection,
            imported,
            document_number="3",
            document_date=date(2026, 4, 3),
            subproject_code="99999",
            passthrough={**supplier, "Libellé": "Usinage"},
        )


@pytest.mark.requirement("WF-INTF-0140-A")
@pytest.mark.requirement("WF-REF-0190-A")
@pytest.mark.requirement("WF-CRE-0010-A")
def test_the_report_presents_the_lines_added_updated_unchanged_and_rejected_before_confirming(
    api: ContractClient, stage: Scene, worker: Worker, lot: str
) -> None:
    # « Le compte rendu (WF-INTF-0080) présente les lignes ajoutées, mises à jour, inchangées et
    # rejetées avant confirmation. » — « Une colonne « Nom Matricule » non déclarée n'est pas
    # conservée, et le compte rendu la nomme » ; the exclusion of a line is no column of the file.
    _held(stage, lot)
    content = extraction(
        [
            line(element=CODE, number="1", on="2026-04-02", amount=1250),
            line(element=ELEMENT, number="2", item="1", amount=650),
            line(element=ELEMENT, number="3", on="2026-04-05", supplier="Usinage Martin"),
            line(number="4"),
            line(number="5", amount="12,50"),
        ]
    )
    report = analysed(api, stage, worker, content)["report"]
    assert report["differences"] == [
        updated("2", "amount", item="1"),
        updated(
            "3",
            "document_date",
            "subproject",
            "passthrough.Fournisseur",
            "passthrough.Libellé",
        ),
        added("4"),
    ]
    assert report["rejected"] == [
        {
            "sheet": None,
            "row": 6,
            "code": "NUMBER_INVALID",
            "params": {"column": "amount", "value": "12,50"},
        }
    ]
    assert (report["read_count"], report["unchanged_count"]) == (5, 1)
    assert report["ignored"] == [{"kind": "columns", "count": 1, "labels": ["Nom Matricule"]}]
    assert report["requires_confirmation_reasons"] == []


@pytest.mark.requirement("WF-REF-0190-A")
def test_a_column_declared_kept_enters_the_lines_of_the_next_import(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « … déclarée conservée, elle est restituée à la consultation des lignes importées ensuite. » :
    # no longer ignored, it is a column of the line, a difference of a line already imported.
    declare(stage.database, kept=("Fournisseur", "nom matricule"))
    with stage.owner.begin() as connection:
        imported = write_import(connection, UUID(stage.project["project_id"]))
        insert_cost_line(
            connection,
            imported,
            document_number="1",
            subproject_code=None,
            passthrough={"Fournisseur": "Atelier Durand"},
        )
    content = extraction([line(element=CODE, number="1", on="2026-04-02", amount=1250)])
    report = analysed(api, stage, worker, content)["report"]
    assert report["ignored"] == []
    assert report["differences"] == [updated("1", "passthrough.Nom Matricule")]
