# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reimport of a planning of MS Project exported, then reworked there (US-3170, #3337).

Against the service, with the worker of the imports and of the exports: the lineages of the export
match the tasks first, and a task added in MS Project is never matched by the ``UID`` of another.
"""

from datetime import date
from typing import TYPE_CHECKING

import pytest
from estimate_support import Lines, costing
from fastapi.testclient import TestClient
from nodes_support import Tree, opened, put_facts, set_progress, work_breakdown
from projects_support import Scene
from projects_support import scene as make_scene
from support import ContractClient
from test_msproject_export import exported
from test_msproject_import import analysed, applied, by_label, imported, planning, task

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.worker.exchanges import ExportTask, ImportTasks
from waterfall.worker.marking import mark as marking
from waterfall.worker.runner import Timing as WorkerTiming
from waterfall.worker.runner import Worker

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket

AT_ONCE = WorkerTiming(claim_after=0, block=0.01, redeposit_every=0)


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


@pytest.mark.requirement("WF-INTF-0040-A")
def test_a_task_added_in_ms_project_with_the_uid_of_another_is_added_not_matched_to_it(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Un planning exporté, retravaillé dans MS Project puis réimporté conserve les lignes de
    # devis et les lignées de ses tâches, et ses tâches démarrées. » The scenario of #3337: a
    # structure of UID 1, 2, 3, 5, 8, 9 and 12, T1 to T7 by rank, lines under T5 (the task of UID
    # 8, the one the inserted UID collides with), its export, a task of UID 8 without lineage
    # inserted after the row 2, the reimport.
    revision = opened(api, stage)
    names = {1: "T1", 2: "T2", 3: "T3", 5: "T4", 8: "T5", 9: "T6", 12: "T7"}
    imported(api, stage, worker, planning(*(task(uid, name) for uid, name in names.items())))
    found = by_label(stage)
    five = str(found["T5"][0].id)
    assert found["T5"][1].external_id == "8"
    package, _ = work_breakdown(stage)
    put_facts(stage, five, work_package_id=package)
    set_progress(stage, five, "started", date(2026, 11, 2))
    tree = Tree(api, stage, revision)
    lines = Lines(tree)
    role = costing(stage.database).role
    for hours in ("4", "6"):
        lines.made({"node_id": five}, quantity="1", resource_role_id=str(role), hours=hours)

    def kept_lines() -> list[tuple[str, str]]:
        return sorted(
            (each["lineage_id"], each["parent_id"])
            for each in tree.items()
            if each["kind"] == "estimate_line"
        )

    lines_before = kept_lines()
    assert len(lines_before) == 2
    content = exported(api, stage, worker, revision["revision_id"])
    assert b"<UID>8</UID>" not in content
    cut = content.index(b"</Task>", content.index(b"<UID>2</UID>")) + len(b"</Task>")
    inserted = task(8, "NEW TASK").encode()
    reworked = content[:cut] + inserted + content[cut:]
    report = analysed(api, stage, worker, reworked)["report"]
    named = [(each["change"], each["label"]) for each in report["differences"]]
    assert named == [("added", "NEW TASK")]
    applied(api, stage, worker, analysed(api, stage, worker, reworked))
    after = by_label(stage)
    assert set(after) == {*names.values(), "NEW TASK"}
    assert after["T5"][0].id == found["T5"][0].id
    assert after["T5"][0].lineage_id == found["T5"][0].lineage_id
    assert (after["T5"][1].progress, after["T5"][1].work_package_id) == ("started", package)
    assert after["NEW TASK"][0].lineage_id not in {each[0].lineage_id for each in found.values()}
    assert (after["NEW TASK"][1].progress, after["NEW TASK"][1].work_package_id) == (
        "not_started",
        None,
    )
    assert kept_lines() == lines_before


@pytest.mark.requirement("WF-INTF-0040-A")
def test_a_lineage_twice_in_the_file_matches_the_first_row_and_adds_the_second(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # [US-3170] A task copied and pasted in MS Project carries its lineage twice: the first row in
    # the order of the file is the task, the second is one the file creates.
    opened(api, stage)
    imported(api, stage, worker, planning(task(1, "A"), task(2, "B")))
    lineage = by_label(stage)["A"][0].lineage_id
    field = (
        f"<ExtendedAttribute><FieldID>188743731</FieldID><Value>{lineage}</Value>"
        "</ExtendedAttribute>"
    )
    declared = (
        "<ExtendedAttributes><ExtendedAttribute><FieldID>188743731</FieldID>"
        "<Alias>Waterfall.lineage</Alias></ExtendedAttribute></ExtendedAttributes>"
    )
    reworked = planning(
        task(1, "A", besides=field), task(2, "A copie", besides=field), besides=declared
    )
    named = [
        (each["change"], each["label"])
        for each in analysed(api, stage, worker, reworked)["report"]["differences"]
    ]
    assert sorted(named) == [("added", "A copie"), ("removed", "B")]


@pytest.mark.requirement("WF-INTF-0040-A")
def test_an_external_id_twice_in_the_structure_is_matched_by_the_first_task_only(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # [US-3170] Two tasks of the structure that keep the same identifier of MS Project: a row of
    # that UID takes the first in the order of the plan, never both.
    opened(api, stage)
    imported(api, stage, worker, planning(task(1, "A"), task(2, "B")))
    put_facts(stage, str(by_label(stage)["B"][0].id), external_id="1")
    reworked = planning(task(1, "A revue"))
    named = [
        (each["change"], each["label"])
        for each in analysed(api, stage, worker, reworked)["report"]["differences"]
    ]
    assert sorted(named) == [("removed", "B"), ("updated", "A revue")]
