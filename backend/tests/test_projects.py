# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The projects (US-0920; WF-PRJ-0010, WF-PRJ-0080, WF-CYC-0120), through the service.

``createProject``, ``getProject`` and ``updateProject`` on a platform whose reference is complete
(``projects_support``) or not, every answer checked against the contract. The list is tried in
``test_projects_list.py``, the witness in ``test_witness_projects.py``.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from installed_reference import install
from project_rows import insert_project, partition_of
from projects_support import (
    PROJECTS,
    Person,
    Scene,
    complete_reference,
    contribute,
    create,
    person,
    put_in_state,
)
from projects_support import scene as make_scene
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session
from support import wait_for_a_lock

from waterfall.api.contract.models import MissingEnum, ProjectCreate, ProjectUpdate
from waterfall.api.projects import ProjectCreateBody, ProjectUpdateBody
from waterfall.core.access_roles.predefined import PROJECT_MANAGER
from waterfall.core.cost_settings.interface import PREREQUISITES
from waterfall.core.cost_settings.tables import CostCategory, CostType
from waterfall.core.projects.interface import ProjectChange, project_code, project_label
from waterfall.core.projects.interface.projects import MODIFIABLE
from waterfall.core.projects.tables import (
    Contributor,
    OrderItem,
    Project,
    ProjectStateTransition,
    WorkPackage,
)
from waterfall.core.resource_settings.tables import DAYS, Calendar
from waterfall.platform.audit import AuditEntry

if TYPE_CHECKING:
    from decimal import Decimal

    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


def refusal(response: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("params", {})


def faults(response: Any) -> list[tuple[str, str, dict[str, Any]]]:
    """Give, by field, the pointer, the code and the parameters of a refusal."""
    return [
        (field["pointer"], field["code"], field.get("params", {}))
        for field in response.json()["fields"]
    ]


def missing(project: dict[str, Any]) -> dict[str, list[str]]:
    """Give the conditions each command of a project lacks, by command."""
    return {each["command"]: each["missing_conditions"] for each in project["available_commands"]}


def one(session: Session, project_id: str) -> Project:
    """Read a project as the service reads it."""
    return session.scalars(select(Project).where(Project.id == UUID(project_id))).one()


@pytest.mark.requirement("WF-CYC-0010-A")
@pytest.mark.requirement("WF-PRJ-0010-A")
def test_a_project_is_born_created_without_a_code_and_its_creator_manages_it(
    api: ContractClient, stage: Scene
) -> None:
    # « Un projet se crée et se chiffre sans code projet. » ; « L'API ne renvoie que ces six
    # codes. » : the project is born ``created``, its code null, its rates and its counter zero.
    project = stage.project
    assert project["label"] == "Modernisation du poste de commande"
    assert (project["state"], project["code"], project["client"]) == ("created", None, None)
    assert (project["inflation_rate"], project["win_probability"]) == ("0", "0")
    assert (project["reference_revision_id"], project["current_revision_id"]) == (None, None)
    assert project["lock_version"] == 0
    assert project["audit"]["created_by"]["user_id"] == str(stage.manager.user_id)
    # Its creator reads the commands of a project manager; the state-bound ones say what lacks.
    assert missing(project) == {
        "update": [],
        "update_win_probability": [],
        "update_work_breakdown": [],
        "manage_contributors": [],
        "manage_timelines": [],
        "create_revision": [],
        "complete": ["project_in_progress"],
        "lose": ["project_in_pricing"],
        "abandon": [],
        "generate_skeleton": [],
        "import_estimate": [],
    }
    read = api.get(f"{PROJECTS}/{project['project_id']}", headers=stage.manager.headers)
    assert (read.status_code, read.json()) == (200, project)


@pytest.mark.requirement("WF-CYC-0010-A")
def test_a_creation_writes_what_is_born_with_the_project_in_one_transaction(
    stage: Scene,
) -> None:
    # The creator inscribed project manager, the work package and the order item by default at the
    # label of the project, the transition from no state, the partitions of the revised tables and
    # the inscription in the journal.
    project_id = UUID(stage.project["project_id"])
    with stage.database.transaction() as session:
        kinds = dict(session.execute(select(Contributor.user_account_id, Contributor.kind)).all())
        package = session.scalars(select(WorkPackage).where(WorkPackage.project_id == project_id))
        item = session.scalars(select(OrderItem).where(OrderItem.project_id == project_id))
        packages, items = package.one(), item.one()
        transitions = session.scalars(
            select(ProjectStateTransition).where(ProjectStateTransition.project_id == project_id)
        ).all()
        partition = session.scalar(
            text("SELECT to_regclass(:name)"), {"name": partition_of(project_id)}
        )
        journal = session.scalars(
            select(AuditEntry).where(AuditEntry.object_id == project_id)
        ).one()
    assert kinds[stage.manager.user_id] == "project_manager"
    assert (packages.label, packages.position) == (stage.project["label"], 0)
    assert (items.label, items.position, items.work_package_id) == (
        stage.project["label"],
        0,
        packages.id,
    )
    [transition] = transitions
    assert (transition.from_state, transition.to_state) == (None, "created")
    assert transition.actor_user_id == stage.manager.user_id
    assert transition.reason is None
    assert partition is not None
    assert (journal.action, journal.object_kind, journal.actor_user_id) == (
        "project_create",
        "project",
        stage.manager.user_id,
    )
    assert journal.object_label == stage.project["label"]
    # Born without code, the project is named in the journal all the same, its code null (#2166).
    assert stage.project["code"] is None
    assert (journal.project_id, journal.project_code, journal.project_label) == (
        project_id,
        None,
        stage.project["label"],
    )


@pytest.mark.requirement("WF-PRJ-0080-A")
def test_a_project_is_created_with_the_attributes_the_creator_gives(
    api: ContractClient, stage: Scene
) -> None:
    sent = {"label": "Ligne 4", "description": "Reprise", "client": "Papeteries", "code": "PRJ-9.1"}
    project = create(api, stage.manager, **sent)
    assert {name: project[name] for name in sent} == sent
    assert project["state"] == "created"


@pytest.mark.requirement("WF-PRJ-0080-A")
def test_a_creation_without_a_label_is_refused(api: ContractClient, stage: Scene) -> None:
    # « La création d'un projet sans libellé est refusée. »
    headers = stage.manager.headers
    absent = api.post(PROJECTS, headers=headers, json={})
    assert (absent.status_code, faults(absent)) == (
        422,
        [("/label", "VALUE_REQUIRED", {})],
    )
    empty = api.post(PROJECTS, headers=headers, json={"label": ""})
    assert faults(empty) == [("/label", "VALUE_REQUIRED", {})]
    blank = api.post(PROJECTS, headers=headers, json={"label": "   "})
    assert faults(blank) == [("/label", "VALIDATION_FAILED", {})]
    long = api.post(PROJECTS, headers=headers, json={"label": "x" * 301})
    assert faults(long) == [("/label", "VALUE_TOO_LONG", {"max_length": 300})]
    with stage.database.transaction() as session:
        assert session.scalar(select(func.count()).select_from(Project)) == 1


@pytest.mark.requirement("WF-PRJ-0010-A")
@pytest.mark.parametrize("code", ["/  ", "/", "PRJ/001", "  /", "a/ "])
def test_a_code_that_holds_a_slash_is_refused_whatever_else_it_holds(
    api: ContractClient, stage: Scene, code: str
) -> None:
    # #1658: « /  » is both blank and a bearer of the barre oblique, and receives the one refusal
    # the contract gives it, the barre oblique first; on the creation and on the modification.
    expected = [("/code", "PROJECT_CODE_INVALID", {"forbidden_characters": ["/"]})]
    created = api.post(PROJECTS, headers=stage.manager.headers, json={"label": "A", "code": code})
    assert (created.status_code, faults(created)) == (422, expected)
    changed = api.patch(
        f"{PROJECTS}/{stage.project['project_id']}",
        headers=stage.manager.headers,
        json={"code": code, "lock_version": 0},
    )
    assert (changed.status_code, faults(changed)) == (422, expected)
    assert changed.json()["code"] == "VALIDATION_FAILED"


@pytest.mark.requirement("WF-PRJ-0010-A")
def test_a_code_empty_blank_or_too_long_is_refused_by_its_own_reason(
    api: ContractClient, stage: Scene
) -> None:
    headers = stage.manager.headers

    def reason(code: str) -> list[tuple[str, str, dict[str, Any]]]:
        answer = api.post(PROJECTS, headers=headers, json={"label": "A", "code": code})
        assert answer.status_code == 422
        return faults(answer)

    assert reason("") == [("/code", "VALUE_REQUIRED", {})]
    assert reason("   ") == [("/code", "VALIDATION_FAILED", {})]
    assert reason("x" * 51) == [("/code", "VALUE_TOO_LONG", {"max_length": 50})]
    assert create(api, stage.manager, code="x" * 50)["code"] == "x" * 50


@pytest.mark.requirement("WF-PRJ-0080-A")
def test_a_client_is_judged_as_the_contract_says(api: ContractClient, stage: Scene) -> None:
    headers = stage.manager.headers

    def reason(client: str) -> list[tuple[str, str, dict[str, Any]]]:
        answer = api.post(PROJECTS, headers=headers, json={"label": "A", "client": client})
        assert answer.status_code == 422
        return faults(answer)

    assert reason("") == [("/client", "VALUE_REQUIRED", {})]
    assert reason("  ") == [("/client", "VALIDATION_FAILED", {})]
    assert reason("c" * 301) == [("/client", "VALUE_TOO_LONG", {"max_length": 300})]
    assert create(api, stage.manager, client=None)["client"] is None


@pytest.mark.requirement("WF-PRJ-0010-A")
def test_a_code_borne_by_another_project_is_refused_naming_it(
    api: ContractClient, stage: Scene
) -> None:
    # « La saisie d'un code déjà porté par un autre projet est refusée. » : on the creation, and
    # on the modification, which leaves the project as it was.
    held = create(api, stage.manager, label="Porteur", code="PRJ-001")
    named = [
        (
            "/code",
            "ALREADY_EXISTS",
            {"conflicting_object_id": held["project_id"], "conflicting_object_label": "Porteur"},
        )
    ]
    again = api.post(
        PROJECTS, headers=stage.manager.headers, json={"label": "B", "code": "PRJ-001"}
    )
    assert (again.status_code, again.json()["code"], faults(again)) == (
        409,
        "ALREADY_EXISTS",
        named,
    )
    path = f"{PROJECTS}/{stage.project['project_id']}"
    changed = api.patch(
        path, headers=stage.manager.headers, json={"code": "PRJ-001", "lock_version": 0}
    )
    assert (changed.status_code, faults(changed)) == (409, named)
    with stage.database.transaction() as session:
        assert session.scalar(select(func.count()).select_from(Project)) == 2
        assert one(session, stage.project["project_id"]).code is None
    # A project may keep its own code, sent again.
    kept = api.patch(
        f"{PROJECTS}/{held['project_id']}",
        headers=stage.manager.headers,
        json={"code": "PRJ-001", "lock_version": 0},
    )
    assert (kept.status_code, kept.json()["lock_version"]) == (200, 0)


@pytest.mark.requirement("WF-PRJ-0010-A")
def test_a_creation_that_meets_a_code_being_written_waits_for_it_and_is_refused_naming_it(
    api: ContractClient, stage: Scene
) -> None:
    # The unique index decides when two writes meet: the second waits for the first to commit,
    # then is refused by the project the first wrote, which it could not read before.
    holder = uuid4()
    with ThreadPoolExecutor(1) as other, Session(stage.database.engine) as writing:
        writing.execute(insert_project(id=holder, label="Écrit", code="RACE"))
        creating = other.submit(
            api.post,
            PROJECTS,
            headers=stage.manager.headers,
            json={"label": "Course", "code": "RACE"},
        )
        wait_for_a_lock(stage.database)
        writing.commit()
        answer = creating.result(timeout=10)
    assert answer.status_code == 409
    assert faults(answer) == [
        (
            "/code",
            "ALREADY_EXISTS",
            {"conflicting_object_id": str(holder), "conflicting_object_label": "Écrit"},
        )
    ]


@pytest.mark.requirement("WF-PRJ-0010-A")
def test_two_simultaneous_creations_of_one_code_leave_one_project_and_one_refusal(
    api: ContractClient, stage: Scene
) -> None:
    sent = {"label": "Jumeau", "code": "TWIN"}

    def send(_: int) -> Any:
        return api.post(PROJECTS, headers=stage.manager.headers, json=sent)

    with ThreadPoolExecutor(2) as pool:
        answers = list(pool.map(send, range(2)))
    created = [answer for answer in answers if answer.status_code == 201]
    refused = [answer for answer in answers if answer.status_code == 409]
    assert (len(created), len(refused)) == (1, 1)
    params = {
        "conflicting_object_id": created[0].json()["project_id"],
        "conflicting_object_label": "Jumeau",
    }
    assert faults(refused[0]) == [("/code", "ALREADY_EXISTS", params)]
    with stage.database.transaction() as session:
        assert session.scalar(select(func.count()).select_from(Project)) == 2


@pytest.mark.requirement("WF-ADM-0110-A")
def test_a_creation_is_refused_to_a_session_without_the_permission_to_create(
    api: ContractClient, stage: Scene
) -> None:
    refused = api.post(PROJECTS, headers=stage.reader.headers, json={"label": "A"})
    assert refusal(refused) == (403, "PERMISSION_MISSING", {"missing_permission": "project_create"})


# The reference a new installation holds — its provision category alone — lacks a category of
# labour and a role of resources.
PRIMED = ["active_cost_category", "active_resource_role"]


def incomplete(owner: Engine, database: Database, realm: TestRealm) -> Person:
    """Give the session of a manager on an installation whose reference is not complete."""
    install(owner)
    return person(database, realm, *PROJECT_MANAGER)


def refused_creation(api: ContractClient, headers: dict[str, str]) -> list[str]:
    """Create a project, refused for the prerequisites that miss; give them, in their order."""
    answer = api.post(PROJECTS, headers=headers, json={"label": "A"})
    status, code, params = refusal(answer)
    assert (status, code) == (409, "REFERENCE_INCOMPLETE")
    assert list(params) == ["missing_prerequisites"]
    return params["missing_prerequisites"]


@pytest.mark.requirement("WF-CYC-0120-A")
@pytest.mark.requirement("WF-EXP-0020-A")
def test_a_new_installation_refuses_the_creation_naming_the_labour_category_and_the_role(
    api: ContractClient, owner: Engine, database: Database, realm: TestRealm
) -> None:
    # « Sur une installation neuve, dont la seule catégorie est celle des provisions pour risques,
    # la création est refusée en nommant la catégorie de main-d'œuvre et le rôle manquants. » ;
    # « La création d'un projet est refusée et nomme les prérequis manquants, jusqu'à ce qu'une
    # catégorie de coût de main-d'œuvre et un rôle de ressource aient été saisis. »
    manager = incomplete(owner, database, realm)
    assert refused_creation(api, manager.headers) == PRIMED
    with database.transaction() as session:
        assert session.scalar(select(func.count()).select_from(Project)) == 0
    complete_reference(database)
    created = api.post(PROJECTS, headers=manager.headers, json={"label": "A"})
    assert created.status_code == 201


@pytest.mark.requirement("WF-CYC-0120-A")
def test_the_refusal_names_every_prerequisite_that_misses_in_the_order_of_the_contract(
    api: ContractClient, owner: Engine, database: Database, realm: TestRealm
) -> None:
    # « Sur une plateforme dont le référentiel est incomplet, la création d'un projet est refusée,
    # et le refus nomme chaque prérequis manquant. » : a calendar without an hour, no category
    # active, no role. One day of work is enough for the calendar.
    manager = incomplete(owner, database, realm)
    with database.transaction() as session:
        session.execute(update(Calendar).values(dict.fromkeys(DAYS, 0)))
        session.execute(update(CostCategory).values(is_active=False))
    assert refused_creation(api, manager.headers) == [
        "default_calendar_with_hours",
        "active_cost_category",
        "active_provision_category",
        "active_resource_role",
    ]
    with database.transaction() as session:
        session.execute(update(Calendar).values(sunday=1))
    assert "default_calendar_with_hours" not in refused_creation(api, manager.headers)


@pytest.mark.requirement("WF-CYC-0120-A")
def test_a_reference_without_an_active_category_of_provision_refuses_naming_it(
    api: ContractClient, stage: Scene
) -> None:
    # « Sur un référentiel dont aucune catégorie de type provision pour risques n'est active, la
    # création est refusée en nommant ce prérequis. » ; « La création aboutit dès que tous les
    # prérequis sont satisfaits. »
    provision = select(CostType.id).where(CostType.kind == "provision")
    with stage.database.transaction() as session:
        session.execute(
            update(CostCategory)
            .where(CostCategory.cost_type_id.in_(provision))
            .values(is_active=False)
        )
    assert refused_creation(api, stage.manager.headers) == ["active_provision_category"]
    with stage.database.transaction() as session:
        session.execute(update(CostCategory).values(is_active=True))
    assert api.post(PROJECTS, headers=stage.manager.headers, json={"label": "A"}).status_code == 201


@pytest.mark.requirement("WF-PRJ-0080-A")
def test_a_manager_changes_the_attributes_and_each_change_counts_once(
    api: ContractClient, stage: Scene
) -> None:
    # « Le nom du client est saisissable à tout moment » (#1337) : it is entered, and emptied by
    # null; « La date de réception de la commande est saisissable à tout moment ».
    path = f"{PROJECTS}/{stage.project['project_id']}"
    headers = stage.manager.headers
    sent = {
        "label": "Modernisation",
        "description": "Poste de commande",
        "client": "Papeteries de la Vienne",
        "code": "PRJ-001",
        "inflation_rate": "0.03",
        "win_probability": "0.4",
        "order_received_on": "2026-01-15",
        "lock_version": 0,
    }
    changed = api.patch(path, headers=headers, json=sent)
    assert changed.status_code == 200
    body = changed.json()
    assert {name: body[name] for name in sent if name != "lock_version"} == {
        name: value for name, value in sent.items() if name != "lock_version"
    }
    assert (body["lock_version"], body["audit"]["updated_by"]["user_id"]) == (
        1,
        str(stage.manager.user_id),
    )
    emptied = api.patch(
        path,
        headers=headers,
        json={"client": None, "order_received_on": None, "description": None, "lock_version": 1},
    )
    assert emptied.status_code == 200
    body = emptied.json()
    assert (body["client"], body["order_received_on"], body["description"]) == (None, None, None)
    assert (body["label"], body["code"], body["lock_version"]) == ("Modernisation", "PRJ-001", 2)
    assert api.get(path, headers=headers).json() == body


@pytest.mark.requirement("WF-DAT-0070-A")
def test_a_change_that_changes_nothing_writes_nothing(api: ContractClient, stage: Scene) -> None:
    path = f"{PROJECTS}/{stage.project['project_id']}"
    same = api.patch(
        path,
        headers=stage.manager.headers,
        json={"label": stage.project["label"], "win_probability": "0.0", "lock_version": 0},
    )
    assert (same.status_code, same.json()) == (200, stage.project)


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_change_at_a_stale_version_is_refused_and_writes_nothing(
    api: ContractClient, stage: Scene
) -> None:
    path = f"{PROJECTS}/{stage.project['project_id']}"
    first = api.patch(path, headers=stage.manager.headers, json={"label": "Un", "lock_version": 0})
    assert first.status_code == 200
    stale = api.patch(
        path, headers=stage.manager.headers, json={"label": "Deux", "lock_version": 0}
    )
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 1})
    assert api.get(path, headers=stage.manager.headers).json()["label"] == "Un"


@pytest.mark.requirement("WF-PRJ-0040-A")
@pytest.mark.requirement("WF-PRJ-0090-A")
def test_a_rate_or_a_probability_out_of_zero_to_one_is_refused_field_by_field(
    api: ContractClient, stage: Scene
) -> None:
    path = f"{PROJECTS}/{stage.project['project_id']}"
    headers = stage.manager.headers
    out = api.patch(
        path,
        headers=headers,
        json={"win_probability": "1.5", "inflation_rate": "-0.1", "lock_version": 0},
    )
    assert (out.status_code, out.json()["code"]) == (422, "VALIDATION_FAILED")
    assert faults(out) == [
        ("/win_probability", "VALUE_OUT_OF_RANGE", {"maximum": "1"}),
        ("/inflation_rate", "VALUE_OUT_OF_RANGE", {"minimum": "0"}),
    ]
    edge = api.patch(
        path,
        headers=headers,
        json={"win_probability": "1", "inflation_rate": "0", "lock_version": 0},
    )
    assert (edge.status_code, edge.json()["win_probability"]) == (200, "1")
    # The values are judged before the counter, as the contract orders them.
    stale = api.patch(path, headers=headers, json={"inflation_rate": "2", "lock_version": 9})
    assert stale.status_code == 422


@pytest.mark.requirement("WF-PRJ-0080-A")
def test_a_field_that_is_never_null_refuses_a_null(api: ContractClient, stage: Scene) -> None:
    path = f"{PROJECTS}/{stage.project['project_id']}"
    sent = {"label": None, "win_probability": None, "lock_version": 0}
    answer = api.patch(path, headers=stage.manager.headers, json=sent)
    assert (answer.status_code, faults(answer)) == (
        422,
        [("/label", "VALIDATION_FAILED", {}), ("/win_probability", "VALIDATION_FAILED", {})],
    )


@pytest.mark.requirement("WF-PRJ-0090-A")
def test_the_probability_is_refused_from_in_progress_and_its_command_said_so_beforehand(
    api: ContractClient, stage: Scene
) -> None:
    # « La modification de la probabilité est refusée à partir de l'état En cours. » : the state
    # In progress is put around the service, as no reference may bear a task before EP-07.
    project_id = stage.project["project_id"]
    path = f"{PROJECTS}/{project_id}"
    headers = stage.manager.headers
    assert missing(stage.project)["update_win_probability"] == []
    pricing = api.patch(path, headers=headers, json={"win_probability": "0.4", "lock_version": 0})
    assert pricing.status_code == 200
    put_in_state(stage.owner, project_id, "in_progress")
    read = api.get(path, headers=headers).json()
    assert missing(read)["update_win_probability"] == ["project_before_in_progress"]
    assert "lose" not in missing(read)
    frozen = api.patch(path, headers=headers, json={"win_probability": "0.9", "lock_version": 1})
    assert refusal(frozen) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "project_before_in_progress"},
    )
    # The rate of inflation remains modifiable at any time (WF-PRJ-0040).
    inflation = api.patch(path, headers=headers, json={"inflation_rate": "0.05", "lock_version": 1})
    assert (inflation.status_code, inflation.json()["win_probability"]) == (200, "0.4")


@pytest.mark.requirement("WF-ARC-0070-A")
@pytest.mark.parametrize("state", ["completed", "lost", "abandoned"])
def test_a_terminal_project_is_read_without_commands_and_refuses_every_change(
    api: ContractClient, stage: Scene, state: str
) -> None:
    project_id = stage.project["project_id"]
    put_in_state(stage.owner, project_id, state)
    path = f"{PROJECTS}/{project_id}"
    read = api.get(path, headers=stage.manager.headers)
    assert (read.status_code, read.json()["state"], read.json()["available_commands"]) == (
        200,
        state,
        [],
    )
    refused = api.patch(path, headers=stage.manager.headers, json={"label": "X", "lock_version": 0})
    assert refusal(refused) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "project_not_terminal"},
    )
    # The probability's own condition comes first (a terminal project has reached In progress),
    # although its commands, none being listed, do not say it beforehand.
    both = api.patch(
        path, headers=stage.manager.headers, json={"win_probability": "0.2", "lock_version": 0}
    )
    assert refusal(both)[2] == {"missing_condition": "project_before_in_progress"}


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_the_parameters_are_reserved_to_the_managers_of_the_project(
    api: ContractClient, stage: Scene
) -> None:
    path = f"{PROJECTS}/{stage.project['project_id']}"
    sent = {"label": "Autre", "lock_version": 0}
    participant = api.patch(path, headers=stage.participant.headers, json=sent)
    assert refusal(participant) == (
        403,
        "NOT_PROJECT_MANAGER",
        {"missing_condition": "is_project_manager"},
    )
    # What the participant reads of its commands says it before it asks, quality first.
    read = api.get(path, headers=stage.participant.headers).json()
    assert missing(read)["update"] == ["is_project_manager"]
    assert missing(read)["update_win_probability"] == ["is_project_manager"]
    assert missing(read)["create_revision"] == []
    outsider = api.patch(path, headers=stage.outsider.headers, json=sent)
    assert refusal(outsider) == (404, "NOT_FOUND", {})
    reader = api.patch(path, headers=stage.reader.headers, json=sent)
    assert refusal(reader) == (
        403,
        "PERMISSION_MISSING",
        {"missing_permission": "project_settings.write"},
    )
    with stage.database.transaction() as session:
        assert one(session, stage.project["project_id"]).label == stage.project["label"]


@pytest.mark.requirement("WF-ADM-0110-A")
def test_a_project_a_session_may_not_consult_does_not_exist_for_it(
    api: ContractClient, stage: Scene
) -> None:
    # A project its caller does not contribute to, one that does not exist and an address that
    # names none are refused alike; a session that holds ``all_projects_read`` reads it.
    path = f"{PROJECTS}/{stage.project['project_id']}"
    seen = [
        refusal(api.get(path, headers=stage.outsider.headers)),
        refusal(api.get(f"{PROJECTS}/{uuid4()}", headers=stage.manager.headers)),
        refusal(api.get(f"{PROJECTS}/not-an-identifier", headers=stage.manager.headers)),
    ]
    assert seen == [(404, "NOT_FOUND", {})] * 3
    contributed = api.get(path, headers=stage.reader.headers)
    assert contributed.status_code == 200
    # It is not a contributor: every command that its permissions would give is said unavailable
    # by the quality it lacks, but for none, its permission being only to consult.
    assert contributed.json()["available_commands"] == []
    contribute(stage.database, stage.project["project_id"], stage.outsider, "contributor")
    assert api.get(path, headers=stage.outsider.headers).status_code == 200


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_a_holder_of_the_permissions_who_is_no_contributor_reads_what_it_lacks(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    holder = person(
        stage.database,
        realm,
        "all_projects_read",
        "project_settings.read",
        "project_settings.write",
    )
    read = api.get(f"{PROJECTS}/{stage.project['project_id']}", headers=holder.headers).json()
    assert missing(read) == {
        "update": ["is_contributor", "is_project_manager"],
        "update_win_probability": ["is_contributor", "is_project_manager"],
        "update_work_breakdown": ["is_contributor", "is_project_manager"],
        "manage_contributors": ["is_contributor", "is_project_manager"],
    }
    refused = api.patch(
        f"{PROJECTS}/{stage.project['project_id']}",
        headers=holder.headers,
        json={"label": "Autre", "lock_version": 0},
    )
    assert refusal(refused) == (403, "NOT_CONTRIBUTOR", {"missing_condition": "is_contributor"})


@pytest.mark.requirement("WF-PRJ-0010-A")
def test_a_project_renamed_is_named_by_its_label_of_the_day_and_the_journal_keeps_the_old_one(
    api: ContractClient, stage: Scene
) -> None:
    project_id = stage.project["project_id"]
    path = f"{PROJECTS}/{project_id}"
    renamed = api.patch(
        path,
        headers=stage.manager.headers,
        json={"label": "Renommé", "code": "PRJ-7", "lock_version": 0},
    )
    assert renamed.status_code == 200
    with stage.database.transaction() as session:
        assert project_label(session, UUID(project_id)) == "Renommé"
        assert project_code(session, UUID(project_id)) == "PRJ-7"
        assert project_label(session, uuid4()) is None
        journal = session.scalars(
            select(AuditEntry).where(AuditEntry.object_id == UUID(project_id))
        ).one()
    assert journal.object_label == stage.project["label"]
    assert api.get(path, headers=stage.manager.headers).json()["label"] == "Renommé"


@pytest.mark.requirement("WF-DAT-0100-A")
def test_the_rates_are_exact_decimals_written_without_a_useless_zero(
    api: ContractClient, stage: Scene
) -> None:
    path = f"{PROJECTS}/{stage.project['project_id']}"
    sent = {"inflation_rate": "0.0350", "win_probability": "0.1", "lock_version": 0}
    answer = api.patch(path, headers=stage.manager.headers, json=sent)
    assert (answer.json()["inflation_rate"], answer.json()["win_probability"]) == ("0.035", "0.1")
    with stage.database.transaction() as session:
        rate: Decimal = one(session, stage.project["project_id"]).inflation_rate
    assert str(rate) == "0.0350"


@pytest.mark.requirement("WF-DAT-0100-A")
def test_a_rate_with_more_decimals_than_the_base_keeps_is_refused_and_one_that_fits_is_exact(
    api: ContractClient, stage: Scene
) -> None:
    # The base keeps four decimals: a fifth would be rounded, which « non arrondi » forbids.
    path = f"{PROJECTS}/{stage.project['project_id']}"
    headers = stage.manager.headers
    for name in ("inflation_rate", "win_probability"):
        refused = api.patch(path, headers=headers, json={name: "0.03125", "lock_version": 0})
        assert (refused.status_code, refused.json()["code"]) == (422, "VALIDATION_FAILED")
        assert faults(refused) == [(f"/{name}", "VALIDATION_FAILED", {})]
    assert api.get(path, headers=headers).json() == stage.project
    sent = {"inflation_rate": "0.0313", "win_probability": "0.12340", "lock_version": 0}
    changed = api.patch(path, headers=headers, json=sent)
    assert changed.status_code == 200
    assert changed.json() == api.get(path, headers=headers).json()
    assert (changed.json()["inflation_rate"], changed.json()["win_probability"]) == (
        "0.0313",
        "0.1234",
    )
    again = api.patch(path, headers=headers, json={**sent, "lock_version": 1})
    assert (again.status_code, again.json()["lock_version"]) == (200, 1)


@pytest.mark.requirement("WF-CYC-0120-A")
def test_the_prerequisites_the_creation_asks_for_are_those_the_readiness_route_names(
    api: ContractClient, owner: Engine, database: Database, realm: TestRealm
) -> None:
    # Both ask ``missing_prerequisites``, whose names are the enumeration of the contract, in its
    # order: a name the contract does not enumerate would fail the route.
    assert [name for name, _ in PREREQUISITES] == [each.value for each in MissingEnum]
    manager = incomplete(owner, database, realm)
    route = api.get("/api/v1/reference/readiness", headers=manager.headers)
    assert route.json()["missing"] == PRIMED
    assert refused_creation(api, manager.headers) == PRIMED


def test_a_change_writes_the_attributes_of_a_project_and_no_other_column() -> None:
    assert ProjectChange(dict.fromkeys(MODIFIABLE), 0).lock_version == 0
    for name in ("state", "lock_version", "id", "no_such_column"):
        with pytest.raises(ValueError, match=name):
            ProjectChange({name: "x"}, 0)


def _bounds(model: type[Any]) -> dict[str, tuple[Any, ...]]:
    """Read, by field, whether it is required, its default and the bounds the model declares."""
    read: dict[str, tuple[Any, ...]] = {}
    for name, field in model.model_fields.items():
        constraints = sorted(
            (key, value)
            for each in field.metadata
            for key in ("min_length", "max_length", "pattern", "ge", "le", "gt", "lt")
            if (value := getattr(each, key, None)) is not None
        )
        read[name] = (field.is_required(), field.default, tuple(constraints))
    return read


@pytest.mark.parametrize(
    ("body", "generated"),
    [(ProjectCreateBody, ProjectCreate), (ProjectUpdateBody, ProjectUpdate)],
)
def test_the_bodies_of_the_routes_redeclare_the_fields_and_bounds_of_the_contract(
    body: type[Any], generated: type[Any]
) -> None:
    assert _bounds(body) == _bounds(generated)
    assert _bounds(body)["label"][2], "the label carries its bounds"
