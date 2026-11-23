# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lines an estimate removes, in the one write of the tree that writes the others (US-3220).

The application of an import of an estimate removes the lines its report announced removed in the
write that moves, changes and creates the others (``write_lines``), its engine replayed once,
rather than one deletion each (#4422): a file without « ID ligne » imported again removes every
line of the first import and creates every line of the file. What the deletion of a line did stays
done: the lines under a task started or completed kept, the write refused under a completed task
of the main structure. Through the service and its worker, and through the interface of the
planning for the refusals of the write itself.
"""

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from estimate_import_support import analysed_import, row, two_tasks, workbook
from estimate_support import Costing, Lines, costing
from fastapi.testclient import TestClient
from imports_trial import apply, import_worker, nodes, read, run
from nodes_support import Tree, opened, set_progress
from projects_support import Scene
from projects_support import scene as make_scene
from risks_support import Risks, costed
from support import ContractClient
from test_inert_writes import counting, trees_read

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.estimate.entries import LineEntry
from waterfall.core.planning import rescheduling
from waterfall.core.planning.interface import LinesWrite, Place, Writer, write_lines
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import ConflictError, NotFoundError
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

STATE = "STATE_FORBIDS_OPERATION"
# What a line is besides its node and its lineage, which a line created anew does not keep.
OWN = ("node_id", "lineage_id", "lock_version", "created_at", "updated_at")


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
    """Give a worker on the queue of the test, which runs the imports."""
    return import_worker(database, queue, backups_bucket)


@pytest.fixture
def held(tree: Tree, costs: Costing, stage: Scene) -> dict[str, Any]:
    """Give a structure of two tasks, a labour line and a line of material under the first."""
    return two_tasks(tree, costs, stage)


def without_ids(held: dict[str, Any]) -> list[list[Any]]:
    """Give the rows of an estimate built in a spreadsheet: four lines, none with « ID ligne »."""
    labour, stuff = held["role"], held["stuff"]
    return [
        row("1 Câblage", labour, {"Désignation": "Pose", "Quantité": 2, "Heures": 10}),
        row("1 Câblage", stuff, {"Désignation": "Câbles", "Quantité": 3, "Débours unitaire": 20}),
        row("2 Essais", labour, {"Désignation": "Recette", "Quantité": 1, "Heures": 6}),
        row("2 Essais", stuff, {"Désignation": "Bancs", "Quantité": 1, "Débours unitaire": 400}),
    ]


def estimate(tree: Tree) -> list[tuple[str, dict[str, Any]]]:
    """Give the lines of a structure as an estimate reads them: under their task, by their facet.

    Neither the node nor the lineage of a line, which an import that creates it anew changes.
    """
    items = tree.items()
    tasks = {item["node_id"]: item["lineage_id"] for item in items if item["kind"] == "task"}
    return sorted(
        (
            (
                tasks[item["parent_id"]],
                {k: v for k, v in item["estimate_line"].items() if k not in OWN},
            )
            for item in items
            if item["kind"] == "estimate_line"
        ),
        key=lambda each: (each[0], each[1]["label"]),
    )


@dataclass(frozen=True, slots=True)
class Trial:
    """The service, its stage and its worker, and the structure of two tasks the imports write."""

    api: ContractClient
    stage: Scene
    worker: Worker
    tree: Tree
    held: dict[str, Any]

    def analysed(self, rows: list[list[Any]]) -> str:
        """Open the import of a workbook of these rows and run its analysis; give the import."""
        content = workbook(rows, self.held["tasks"])
        return analysed_import(self.api, self.stage, self.worker, content)

    def report(self, import_id: str) -> dict[str, Any]:
        """Read the report of an import as its manager does."""
        return read(self.api, self.stage, import_id)["report"]

    def applied(self, import_id: str, monkeypatch: pytest.MonkeyPatch) -> tuple[int, int]:
        """Confirm and run the application of an import; give the engines run and trees read."""
        engines = counting(monkeypatch, (rescheduling,), "dated")
        trees = trees_read(monkeypatch)
        answer = apply(self.api, self.stage, import_id)
        assert answer.status_code == 202, answer.text
        run(self.worker)
        assert read(self.api, self.stage, import_id)["status"] == "applied"
        monkeypatch.undo()
        return engines.count, trees.count


@pytest.fixture
def trial(
    api: ContractClient, stage: Scene, worker: Worker, tree: Tree, held: dict[str, Any]
) -> Trial:
    """Give the service, its stage, its worker and the structure of two tasks of the test."""
    return Trial(api, stage, worker, tree, held)


@pytest.mark.requirement("WF-INTF-0100-A")
def test_an_estimate_without_line_ids_imported_again_is_applied_in_one_write_and_one_replay(
    trial: Trial, monkeypatch: pytest.MonkeyPatch
) -> None:
    # « Un second import du même fichier donne un devis identique. », for a file without « ID
    # ligne »: the second import removes the N lines of the first and creates the N of the file in
    # one write of the tree, the engine replayed once, and the estimate is the first one.
    rows = without_ids(trial.held)
    trial.applied(trial.analysed(rows), monkeypatch)
    first = estimate(trial.tree)
    assert [facet["label"] for _, facet in first] == ["Câbles", "Pose", "Bancs", "Recette"]
    again = trial.analysed(rows)
    confirmed = trial.report(again)
    changes = [each["change"] for each in confirmed["differences"]]
    assert sorted(changes) == ["added"] * 4 + ["removed"] * 4
    assert confirmed["rejected"] == []
    assert trial.applied(again, monkeypatch) == (1, 1)
    assert estimate(trial.tree) == first
    # The report applied is the report confirmed, as before the write was one.
    assert trial.report(again) == confirmed


@pytest.mark.requirement("WF-INTF-0100-A")
@pytest.mark.story("US-3220")
@pytest.mark.parametrize("progress", ["started", "completed"])
def test_lines_under_a_started_or_completed_task_stay_when_the_others_are_replaced_in_one_write(
    trial: Trial, monkeypatch: pytest.MonkeyPatch, progress: str
) -> None:
    # What the deletion of a line did a line at a time stays done: the lines of a task started or
    # completed, which the file no longer carries, are kept; the line of the other task the file
    # no longer carries goes, in the write that creates the line it gives, one replay.
    held, tree = trial.held, trial.tree
    second, role = held["second"], str(held["costs"].role)
    old = Lines(tree).made(second, quantity="1", resource_role_id=role, hours="8")
    set_progress(trial.stage, held["first"]["node_id"], progress, date(2026, 1, 5))
    kept = [each for each in estimate(tree) if each[0] == held["first"]["lineage_id"]]
    import_id = trial.analysed([without_ids(held)[2]])
    report = trial.report(import_id)
    changes = sorted((each["change"], each.get("lineage_id")) for each in report["differences"])
    assert changes == [
        ("added", None),
        ("kept", held["labour"]["lineage_id"]),
        ("kept", held["material"]["lineage_id"]),
        ("removed", old["nodes"][0]["lineage_id"]),
    ]
    assert trial.applied(import_id, monkeypatch) == (1, 1)
    after = estimate(tree)
    assert [each for each in after if each[0] == held["first"]["lineage_id"]] == kept
    assert [facet["label"] for task, facet in after if task == second["lineage_id"]] == ["Recette"]
    assert old["nodes"][0]["node_id"] not in {item["node_id"] for item in tree.items()}


def written_directly(stage: Scene, tree: Tree, lines: LinesWrite) -> None:
    """Write lines by the interface of the planning, as the application of an import does."""
    place = Place(
        UUID(stage.project["project_id"]),
        UUID(tree.revision["revision_id"]),
        UUID(tree.structure_id),
    )
    with stage.database.transaction() as session:
        write_lines(session, place, lines, Writer(Act(None, utc_now()), None))


@pytest.mark.story("US-3220")
def test_the_write_of_the_lines_refuses_a_line_removed_from_a_completed_task_writing_nothing(
    stage: Scene, tree: Tree, held: dict[str, Any]
) -> None:
    # As the deletion of a line (``task_not_completed``, #1767): a line removed from a completed
    # task of the main structure is refused (409), with the line created beside it; nothing goes.
    set_progress(stage, held["first"]["node_id"], "completed", date(2026, 1, 5))
    before = (nodes(stage.database), tree.items())
    created = ((UUID(held["second"]["node_id"]), LineEntry(label="Ajout")),)
    labour = UUID(held["labour"]["node_id"])
    with pytest.raises(ConflictError) as raised:
        written_directly(stage, tree, LinesWrite({}, {}, created, (labour,)))
    assert (raised.value.status, raised.value.code) == (409, STATE)
    assert raised.value.params == {"missing_condition": "task_not_completed"}
    assert (nodes(stage.database), tree.items()) == before


@pytest.mark.story("US-3220")
def test_the_write_of_the_lines_refuses_to_remove_a_task_or_an_unknown_line_writing_nothing(
    stage: Scene, tree: Tree, held: dict[str, Any]
) -> None:
    # The entry of the removals takes lines of the structure: a task, or a line it does not hold,
    # is not found (404), and a line both removed and moved is a mistake of the caller.
    before = (nodes(stage.database), tree.items())
    for gone in (UUID(held["first"]["node_id"]), uuid4()):
        with pytest.raises(NotFoundError) as missing:
            written_directly(stage, tree, LinesWrite({}, {}, (), (gone,)))
        assert (missing.value.status, missing.value.code) == (404, "NOT_FOUND")
    labour = UUID(held["labour"]["node_id"])
    both = LinesWrite({UUID(held["second"]["node_id"]): (labour,)}, {}, (), (labour,))
    with pytest.raises(ValueError, match="neither moved nor changed"):
        written_directly(stage, tree, both)
    assert (nodes(stage.database), tree.items()) == before


@pytest.mark.story("US-3220")
def test_the_write_of_the_lines_refuses_a_provision_line_removed_writing_nothing(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # As the deletion of a line (``line_not_provision``, #4007): the provision line of a risk of
    # the main structure is written by its risk alone, so removing it is refused (409), with the
    # line created beside it; nothing goes.
    project = costed(api, stage, costs)
    risk = Risks(api, project).declared_costed()
    provision = UUID(risk["provision_node_id"])
    before = (nodes(stage.database), project.tree.items())
    created = ((project.tasks["Étude"], LineEntry(label="Ajout")),)
    with pytest.raises(ConflictError) as raised:
        written_directly(stage, project.tree, LinesWrite({}, {}, created, (provision,)))
    assert (raised.value.status, raised.value.code) == (409, STATE)
    assert raised.value.params["missing_condition"] == "line_not_provision"
    assert (nodes(stage.database), project.tree.items()) == before
