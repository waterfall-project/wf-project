# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The application of the workbook of an estimate (US-1550/L3).

Its report applied by the worker into the main structure of the current revision, judged again
under the lock of the structure: the lines written under their tasks and those absent removed, the
budget and the lineage of a line kept, the hours of the tasks judged on the structure the import
leaves; through the service and its worker, each answer checked against the contract. Its opening
and its analysis are ``test_estimate_import``'s.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from estimate_import_support import (
    STATE,
    analysed_import,
    as_exported,
    entry_of,
    project_of,
    row,
    two_tasks,
    workbook,
)
from estimate_support import YEAR, Costing, Lines, add_role, costing
from fastapi.testclient import TestClient
from imports_trial import (
    Stopped,
    apply,
    import_worker,
    nodes,
    path,
    read,
    refusal,
    run,
    stored,
)
from nodes_support import Tree, entries, mark, opened, set_progress
from projects_support import PROJECTS, Scene, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import select, update
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.estimate.entries import LineEntry
from waterfall.core.estimate.interface.excel import EstimateFormat
from waterfall.core.estimate.tables import RevisionRate
from waterfall.core.planning.interface import LinesWrite, Place, Writer, write_lines
from waterfall.core.projects.tables import Project
from waterfall.core.resource_settings.tables import ResourceRole
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import ConflictError, NotFoundError, UnprocessableError
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


@pytest.fixture
def held(tree: Tree, costs: Costing, stage: Scene) -> dict[str, Any]:
    """Give a structure of two tasks, a labour line and a line of material under the first."""
    return two_tasks(tree, costs, stage)


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


EARLY = (8, 8, 8, 0, 0, 0, 0)
LATE = (0, 0, 0, 8, 8, 0, 0)


def labour_lines(tree: Tree, task: dict[str, Any], roles: list[UUID]) -> list[dict[str, Any]]:
    """Create a labour line of each role under a task; give their nodes."""
    lines = Lines(tree)
    return [
        lines.made(task, quantity="1", resource_role_id=str(role), hours="4")["nodes"][0]
        for role in roles
    ]


def imported(stage: Scene, task: str, line: dict[str, Any], role: UUID) -> list[Any]:
    """Give the row of an exported labour line, under a task and of a role the file gives it."""
    cells = {"Quantité": 1, "Heures": 4, "ID ligne": line["lineage_id"]}
    return row(task, entry_of(stage.database, ResourceRole, role), cells)


@pytest.mark.requirement("WF-INTF-0100-A")
@pytest.mark.requirement("WF-PLA-0010-A")
def test_two_lines_of_a_task_that_exchange_their_calendars_are_applied_as_the_report_says(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    # « Chaque ligne se retrouve sous la tâche désignée, avec […] son rôle » : two lines of the
    # beginning of the week given roles of its end leave their task its Thursday and its Friday;
    # written a line at a time, the task would have had no hour between the two (WF-PLA-0010).
    tree = held["tree"]
    early = [add_role(stage.database, code, EARLY) for code in ("LM1", "LM2")]
    late = [add_role(stage.database, code, LATE) for code in ("JV1", "JV2")]
    made = labour_lines(tree, held["second"], early)
    rows = [
        *as_exported(held),
        *(imported(stage, "2 Essais", line, role) for line, role in zip(made, late, strict=True)),
    ]
    import_id = analysed_import(api, stage, worker, workbook(rows, held["tasks"]))
    report = read(api, stage, import_id)["report"]
    assert report["rejected"] == []
    assert [(each["change"], each["fields"]) for each in report["differences"]] == [
        ("updated", ["resource_role"]),
        ("updated", ["resource_role"]),
    ]
    applied_now(api, stage, worker, import_id)
    found = estimate_lines(tree.items())
    second = held["second"]["lineage_id"]
    assert [found[line["lineage_id"]][0] for line in made] == [second, second]
    assert [found[line["lineage_id"]][1]["resource_role_id"] for line in made] == [
        str(role) for role in late
    ]


@pytest.mark.requirement("WF-INTF-0100-A")
@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_line_moved_under_a_task_whose_other_line_changes_its_role_is_applied(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    # « Chaque ligne se retrouve sous la tâche désignée, avec […] son rôle » : a line of the end of
    # the week moved under a task, and a line moved there given a role of the end of the week,
    # while the line of the beginning of the week of that task passes to one of its end. Moved
    # before that change, they would have found the task without an hour (WF-PLA-0010).
    tree = held["tree"]
    third = tree.made("Recette")
    early = add_role(stage.database, "LM1", EARLY)
    late = [add_role(stage.database, code, LATE) for code in ("JV1", "JV2")]
    [kept] = labour_lines(tree, held["first"], [late[0]])
    [moved] = labour_lines(tree, third, [early])
    [staying] = labour_lines(tree, held["second"], [early])
    rows = [
        *as_exported(held),
        imported(stage, "2 Essais", kept, late[0]),
        imported(stage, "2 Essais", moved, late[1]),
        imported(stage, "2 Essais", staying, late[1]),
    ]
    tasks = {**held["tasks"], "3 Recette": third["lineage_id"]}
    import_id = analysed_import(api, stage, worker, workbook(rows, tasks))
    report = read(api, stage, import_id)["report"]
    assert report["rejected"] == []
    assert [(each["change"], each["fields"]) for each in report["differences"]] == [
        ("updated", ["parent"]),
        ("updated", ["resource_role", "parent"]),
        ("updated", ["resource_role"]),
    ]
    applied_now(api, stage, worker, import_id)
    found = estimate_lines(tree.items())
    second = held["second"]["lineage_id"]
    assert [
        (found[line["lineage_id"]][0], found[line["lineage_id"]][1]["resource_role_id"])
        for line in (kept, moved, staying)
    ] == [(second, str(late[0])), (second, str(late[1])), (second, str(late[1]))]


@pytest.mark.requirement("WF-INTF-0100-A")
@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_line_rejected_for_the_hours_of_its_task_keeps_its_role_which_rejects_another(
    api: ContractClient, stage: Scene, worker: Worker, held: dict[str, Any]
) -> None:
    # « est rejetée » : the second line of the task given a role of the week-end is rejected, and
    # keeps its role of the beginning of the week, which the role of the end of the week the first
    # is given no longer meets: rejected too, the task is left as it is, and the application
    # writes what the report says (WF-PLA-0010).
    tree = held["tree"]
    early = [add_role(stage.database, code, EARLY) for code in ("LM1", "LM2")]
    late = add_role(stage.database, "JV1", LATE)
    weekend = add_role(stage.database, "WE", (0, 0, 0, 0, 0, 8, 8))
    made = labour_lines(tree, held["second"], early)
    rows = [
        *as_exported(held),
        imported(stage, "2 Essais", made[0], late),
        imported(stage, "2 Essais", made[1], weekend),
    ]
    import_id = analysed_import(api, stage, worker, workbook(rows, held["tasks"]))
    # Read as the database keeps it, as the analysis reads a rejection of the hours.
    report = dict(stored(stage.database, import_id).report or {})
    assert [(each["row"], each["code"]) for each in report["rejected"]] == [
        (4, "TASK_WITHOUT_WORKING_HOURS"),
        (5, "TASK_WITHOUT_WORKING_HOURS"),
    ]
    assert report["differences"] == []
    before = estimate_lines(tree.items())
    assert apply(api, stage, import_id).status_code == 202
    run(worker)
    assert stored(stage.database, import_id).status == "applied"
    assert estimate_lines(tree.items()) == before


@pytest.mark.requirement("WF-INTF-0080-A")
@pytest.mark.parametrize("completed", ["second", "first"], ids=["arrival", "origin"])
def test_a_line_moved_to_or_from_a_task_completed_since_the_analysis_fails_the_application(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    held: dict[str, Any],
    completed: str,
) -> None:
    # « Si l'import est interrompu pendant son application, le projet revient à son état
    # antérieur. » : the report moves the labour line from the first task to the second, a move the
    # structure accepted; the task it comes from, or the one it goes to, is completed before the
    # application (#1767): the import fails, and nothing of the file is written (#2640).
    tree = held["tree"]
    moving = as_exported(held, {"Heures": 12})
    moving[0][0] = "2 Essais"
    import_id = analysed_import(api, stage, worker, workbook(moving, held["tasks"]))
    report = read(api, stage, import_id)["report"]
    assert report["rejected"] == []
    assert [(each["change"], each["fields"]) for each in report["differences"]] == [
        ("updated", ["hours", "parent"])
    ]
    set_progress(stage, held[completed]["node_id"], "completed", date(2026, 1, 5))
    before = (nodes(stage.database), tree.items())
    assert apply(api, stage, import_id).status_code == 202
    run(worker)
    assert stored(stage.database, import_id).status == "failed"
    assert (nodes(stage.database), tree.items()) == before


def written_directly(stage: Scene, tree: Tree, lines: LinesWrite) -> None:
    """Write lines by the interface of the planning, as the application of an import does."""
    place = Place(
        UUID(stage.project["project_id"]),
        UUID(tree.revision["revision_id"]),
        UUID(tree.structure_id),
    )
    with stage.database.transaction() as session:
        write_lines(session, place, lines, Writer(Act(None, utc_now()), None))


@pytest.mark.requirement("WF-INTF-0080-A")
@pytest.mark.parametrize("completed", ["second", "first"], ids=["arrival", "origin"])
def test_the_write_of_the_lines_refuses_a_task_completed_it_moves_to_or_from_and_writes_nothing(
    stage: Scene, tree: Tree, held: dict[str, Any], completed: str
) -> None:
    # « task_not_completed » (#1767), judged by the write itself under the lock of the structure,
    # whatever the caller judged: a line moved under a completed task of the main structure, or
    # out of one, is refused (409), and the transaction leaves the structure as it was (#2640).
    set_progress(stage, held[completed]["node_id"], "completed", date(2026, 1, 5))
    before = (nodes(stage.database), tree.items())
    task, line = UUID(held["second"]["node_id"]), UUID(held["labour"]["node_id"])
    with pytest.raises(ConflictError) as raised:
        written_directly(stage, tree, LinesWrite({task: (line,)}, {}, ()))
    assert (raised.value.status, raised.value.code) == (409, STATE)
    assert raised.value.params == {"missing_condition": "task_not_completed"}
    assert (nodes(stage.database), tree.items()) == before


@pytest.mark.requirement("WF-INTF-0080-A")
def test_the_write_of_the_lines_refuses_a_line_created_under_a_task_completed(
    stage: Scene, tree: Tree, held: dict[str, Any]
) -> None:
    # The same refusal for a line created: under a completed task of the main structure (#1767).
    set_progress(stage, held["second"]["node_id"], "completed", date(2026, 1, 5))
    before = (nodes(stage.database), tree.items())
    created = LinesWrite({}, {}, ((UUID(held["second"]["node_id"]), LineEntry(label="Ajout")),))
    with pytest.raises(ConflictError) as raised:
        written_directly(stage, tree, created)
    assert (raised.value.status, raised.value.code) == (409, STATE)
    assert raised.value.params == {"missing_condition": "task_not_completed"}
    assert (nodes(stage.database), tree.items()) == before


@pytest.mark.requirement("WF-INTF-0080-A")
def test_the_write_of_the_lines_refuses_an_unknown_task_and_an_unknown_line_writing_nothing(
    stage: Scene, tree: Tree, held: dict[str, Any]
) -> None:
    # A task the structure does not hold is refused (422 ``VALIDATION_FAILED`` on ``/parent_id``,
    # ``UNKNOWN_TASK``), a line it does not hold is not found (404): nothing is written (#2640).
    before = (nodes(stage.database), tree.items())
    labour = UUID(held["labour"]["node_id"])
    with pytest.raises(UnprocessableError) as raised:
        written_directly(stage, tree, LinesWrite({uuid4(): (labour,)}, {}, ()))
    assert (raised.value.status, raised.value.code) == (422, "VALIDATION_FAILED")
    assert [(each.pointer, each.code) for each in raised.value.fields] == [
        ("/parent_id", "UNKNOWN_TASK")
    ]
    lost = LinesWrite({UUID(held["second"]["node_id"]): (uuid4(),)}, {}, ())
    with pytest.raises(NotFoundError) as missing:
        written_directly(stage, tree, lost)
    assert (missing.value.status, missing.value.code) == (404, "NOT_FOUND")
    assert (nodes(stage.database), tree.items()) == before
