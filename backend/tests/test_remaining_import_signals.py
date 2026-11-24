# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The import of a remaining completes a task by the spec 1.0.7, and signals an amount rounded.

A task started is completed by the import only when none of its lines keeps a remaining, the lines
the file does not carry included (#3978); a line other than labour whose amount the import writes
is not the amount typed is signalled to the report, ``AMOUNT_ROUNDED`` (#4428). Both are US-3230.
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from estimate_support import YEAR, Costing, Lines, costing
from fastapi.testclient import TestClient
from imports_trial import import_worker, read
from nodes_support import Tree, put_facts, set_progress
from projects_support import Scene
from projects_support import scene as make_scene
from remaining_import_support import (
    REVIEW,
    Rows,
    analysed,
    applied,
    labour,
    material,
    report,
    row_of,
    task_row,
    workbook,
)
from remaining_support import in_progress, line_named, task_named
from sqlalchemy import update
from support import ContractClient
from test_inert_writes import counting

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.estimate.remaining import applying as remaining_applying
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.projects.tables import Project
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.keycloak_admin import KeycloakAdmin

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

OUTSIDE = "Hors sous-projet"
STARTED_ON = date(YEAR, 1, 1)


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
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports."""
    return import_worker(database, queue, backups_bucket)


@pytest.fixture
def scene(api: ContractClient, stage: Scene) -> Rows:
    """Give the project In progress, its tasks and their lines, as a workbook names them."""
    costs: Costing = costing(stage.database)

    def build(tree: Tree, lines: Lines) -> None:
        wiring = tree.made("Câblage")
        lines.made(wiring, **labour(costs, "Raccordement", "2", "10"))
        lines.made(wiring, **material(costs, "Fournitures", "1", "100"))
        tests = tree.made("Essais")
        lines.made(tests, **material(costs, "Banc", "1", "50"))
        lines.made(tests, **material(costs, "Câbles", "0", "20"))
        acceptance = tree.made("Réception")
        lines.made(acceptance, **material(costs, "Procès-verbal", "1", "10"))
        tree.made("Clôture")

    return Rows(stage, in_progress(api, stage, build), costs)


def zeroed(stage: Scene, tree: Tree, label: str) -> None:
    """Bring a line of the structure to a remaining of nought, as a re-estimate would."""
    with stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.node_id == UUID(line_named(tree, label)["node_id"]))
            .values(reestimated_amount=0, **({"hours": 0} if label == "Raccordement" else {}))
        )


@pytest.mark.story("US-3230")
@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_started_task_keeping_a_remaining_on_a_line_absent_from_the_file_is_not_completed(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # « toutes les lignes, celles absentes du fichier comprises » : the wiring started holds two
    # lines; the file carries one, set to nought, and the other, absent, keeps its remaining.
    wiring = task_named(scene.tree, "Câblage")
    set_progress(stage, wiring["node_id"], "started", STARTED_ON)
    rows = scene.exported()
    rows[0][3] = 0
    del rows[1]
    import_id = analysed(api, stage, worker, workbook({OUTSIDE: rows}, scene.tasks()))
    found = report(api, stage, import_id)
    assert [each["label"] for each in found["differences"]] == ["Raccordement"]
    assert found["completed_tasks"] == []
    applied(api, stage, worker, import_id)
    assert task_row(stage, wiring["node_id"]).progress == "started"
    assert row_of(stage, line_named(scene.tree, "Fournitures")["node_id"]).reestimated_amount == 100


@pytest.mark.story("US-3230")
@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_started_task_whose_absent_line_is_at_nought_is_completed_when_the_file_zeroes_the_other(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # The line absent already at nought, the other set to nought by the file: completed at the
    # date of the review.
    wiring = task_named(scene.tree, "Câblage")
    set_progress(stage, wiring["node_id"], "started", STARTED_ON)
    zeroed(stage, scene.tree, "Fournitures")
    rows = scene.exported()
    rows[0][3] = 0
    del rows[1]
    import_id = analysed(api, stage, worker, workbook({OUTSIDE: rows}, scene.tasks()))
    found = report(api, stage, import_id)
    assert found["completed_tasks"] == [
        {"lineage_id": wiring["lineage_id"], "label": "Câblage", "completed_on": str(REVIEW)}
    ]
    applied(api, stage, worker, import_id)
    done = task_row(stage, wiring["node_id"])
    assert (done.progress, done.completed_on) == ("completed", REVIEW)


@pytest.mark.story("US-3230")
@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_started_task_whose_two_lines_are_at_nought_and_left_as_they_are_is_not_completed(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # Both lines already at nought, the file leaving them as exported: the import writes nothing
    # of them, and completes nothing.
    wiring = task_named(scene.tree, "Câblage")
    set_progress(stage, wiring["node_id"], "started", STARTED_ON)
    zeroed(stage, scene.tree, "Raccordement")
    zeroed(stage, scene.tree, "Fournitures")
    rows = scene.exported()
    rows[0][3], rows[1][4] = 0, 0
    import_id = analysed(api, stage, worker, workbook({OUTSIDE: rows}, scene.tasks()))
    found = report(api, stage, import_id)
    assert (found["completed_tasks"], found["differences"]) == ([], [])
    applied(api, stage, worker, import_id)
    assert task_row(stage, wiring["node_id"]).progress == "started"


# --- The amount written, announced when it is not the amount typed --------------------------------


@pytest.mark.story("US-3230")
@pytest.mark.requirement("WF-INTF-0120-A")
def test_an_amount_that_does_not_divide_by_the_quantity_is_signalled_with_both_amounts(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # [US-3230] #4428: 1,234.56 typed on a quantity of 1,000 write a unit disbursement of 1.23,
    # 1,230.00 in all; the bench, at 1,000.00 over a quantity of 1,000, divides exactly and is not
    # signalled; the cables, of a quantity of nought in the base
    # brought to one at the writing, give 77.77 back.
    supplies = line_named(scene.tree, "Fournitures")
    with stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(
                EstimateLine.node_id.in_(
                    [
                        UUID(supplies["node_id"]),
                        UUID(line_named(scene.tree, "Banc")["node_id"]),
                    ]
                )
            )
            .values(quantity=1000)
        )
    rows = scene.exported()
    rows[1][4], rows[2][4], rows[3][4] = 1234.56, 1000, 77.77
    import_id = analysed(api, stage, worker, workbook({OUTSIDE: rows}, scene.tasks()))
    found = report(api, stage, import_id)
    assert found["signals"] == [
        {
            "lineage_id": supplies["lineage_id"],
            "label": "Fournitures",
            "column": "unit_disbursement",
            "code": "AMOUNT_ROUNDED",
            "params": {"typed_amount": "1234.56", "written_amount": "1230.00"},
        }
    ]
    assert len(found["differences"]) == 3
    applied(api, stage, worker, import_id)
    written = row_of(stage, supplies["node_id"])
    assert (written.unit_disbursement, written.reestimated_amount) == (
        Decimal("1.23"),
        Decimal("1230.00"),
    )
    assert read(api, stage, import_id)["report"]["signals"] == found["signals"]


@pytest.mark.story("US-3230")
@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_workbook_reimported_as_exported_signals_nothing(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # [US-3230] No line changes, so no amount is written and none signalled.
    import_id = analysed(api, stage, worker, workbook({OUTSIDE: scene.exported()}, scene.tasks()))
    assert report(api, stage, import_id)["signals"] == []


@pytest.mark.story("US-3230")
@pytest.mark.requirement("WF-INTF-0120-A")
def test_an_amount_typed_to_the_cent_it_writes_is_not_signalled(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # 1,230.004 typed on a quantity of 1,000 are 1,230.00 to the cent: the amount written is the
    # amount typed, as the report would show it; no signal with two identical amounts.
    supplies = line_named(scene.tree, "Fournitures")
    with stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.node_id == UUID(supplies["node_id"]))
            .values(quantity=1000)
        )
    rows = scene.exported()
    rows[1][4] = Decimal("1230.004")
    import_id = analysed(api, stage, worker, workbook({OUTSIDE: rows}, scene.tasks()))
    found = report(api, stage, import_id)
    assert [each["label"] for each in found["differences"]] == ["Fournitures"]
    assert found["signals"] == []


@pytest.mark.story("US-3230")
@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_labour_line_changed_is_not_signalled(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # Only the amounts of lines other than labour are signalled: the days of the labour line, whose
    # hours are written to 0.01 h, change it without a signal.
    rows = scene.exported()
    rows[0][3] = Decimal("1.2345")
    import_id = analysed(api, stage, worker, workbook({OUTSIDE: rows}, scene.tasks()))
    found = report(api, stage, import_id)
    assert [each["label"] for each in found["differences"]] == ["Raccordement"]
    assert found["signals"] == []


@pytest.mark.story("US-3230")
@pytest.mark.requirement("WF-INTF-0120-A")
def test_the_amount_signalled_is_the_amount_the_projection_re_estimates(
    api: ContractClient, stage: Scene, worker: Worker, scene: Rows
) -> None:
    # At 3 % over a task of two years (the last four days of the year, then six), the amount
    # written is the one the projection re-estimates — the shares projected one by one, the sum
    # rounded: the signal gives it, and gives none for an amount that divides exactly at the mean
    # coefficient of the task (103 typed, 103.00 written).
    december = [date(YEAR, 12, day) for day in range(1, 32) if date(YEAR, 12, day).weekday() < 5]
    january = [
        date(YEAR + 1, 1, day) for day in range(1, 32) if date(YEAR + 1, 1, day).weekday() < 5
    ]
    with stage.owner.begin() as connection:
        connection.execute(
            update(Project)
            .where(Project.id == UUID(stage.project["project_id"]))
            .values(inflation_rate=Decimal("0.03"))
        )
        connection.execute(
            update(CostStructure)
            .where(CostStructure.id == UUID(scene.tree.structure_id))
            .values(planning_start_on=december[-4])
        )
    tests = task_named(scene.tree, "Essais")
    put_facts(
        stage,
        tests["node_id"],
        start_date=december[-4],
        finish_date=january[5],
        duration_value=Decimal(10),
    )
    rows = scene.exported()
    rows[2][4], rows[3][4] = 103, Decimal("56.27")
    import_id = analysed(api, stage, worker, workbook({OUTSIDE: rows}, scene.tasks()))
    found = report(api, stage, import_id)
    applied(api, stage, worker, import_id)
    bench = row_of(stage, line_named(scene.tree, "Banc")["node_id"])
    cables = line_named(scene.tree, "Câbles")
    written = row_of(stage, cables["node_id"]).reestimated_amount
    assert bench.reestimated_amount == Decimal("103.00")
    assert [each["label"] for each in found["signals"]] == ["Câbles"]
    assert found["signals"][0]["params"] == {
        "typed_amount": "56.27",
        "written_amount": format(written, "f"),
    }
    assert written != Decimal("56.27")


@pytest.mark.story("US-3230")
@pytest.mark.requirement("WF-RAE-0040-A")
def test_the_counters_of_the_lines_that_complete_their_tasks_are_read_in_one_query(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    scene: Rows,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # [US-3230b] (#4849): the application read the counter of each closing line, one query a task;
    # two tasks completed by the file read them once, and are completed as before.
    tree = scene.tree
    set_progress(stage, task_named(tree, "Câblage")["node_id"], "started", STARTED_ON)
    rows = scene.exported()
    rows[0][3], rows[1][4], rows[2][4] = 0, 0, 0
    import_id = analysed(api, stage, worker, workbook({OUTSIDE: rows}, scene.tasks()))
    assert len(report(api, stage, import_id)["completed_tasks"]) == 2
    reads = counting(monkeypatch, (remaining_applying,), "node_versions")
    applied(api, stage, worker, import_id)
    monkeypatch.undo()
    assert reads.count == 1
    for name in ("Câblage", "Essais"):
        assert task_row(stage, task_named(tree, name)["node_id"]).progress == "completed"
