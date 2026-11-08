# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The named timelines of a project (US-1400/L1, WF-PLA-0140), through the service.

``listTimelines``, ``createTimeline`` and ``deleteTimeline`` on projects created through the
service, every answer checked against the contract: the label that is not unique, the physical
deletion that takes the inscriptions with it and leaves the other timeline's, the refusals of a
terminal project, the quality and the permissions of the writer, the command ``manage_timelines``
of the project, and the two timelines the witness loads under the identifiers it imposes.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from project_rows import STAMP
from projects_support import PROJECTS, Person, Scene, contribute, person, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import func, insert, select
from support import WITNESS

from waterfall.core.planning.tables import Timeline, TrackingEntry

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

NOT_TERMINAL = "project_not_terminal"
CONSULT = "planning.read"
CHANGE = "planning.write"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


def path(stage: Scene, *more: str) -> str:
    """Give the path of the timelines of the project of the scene, or of one of them."""
    return "/".join([f"{PROJECTS}/{stage.project['project_id']}/timelines", *more])


def refusal(response: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("params", {})


def add(api: ContractClient, stage: Scene, label: str, who: Person | None = None) -> Any:
    """Create a timeline as the manager of the project does, and give the answer."""
    headers = (who or stage.manager).headers
    return api.post(path(stage), headers=headers, json={"label": label})


def made(api: ContractClient, stage: Scene, label: str) -> dict[str, Any]:
    """Create a timeline that must be created, and give what is answered."""
    answer = add(api, stage, label)
    assert answer.status_code == 201, answer.text
    return answer.json()


def listed(api: ContractClient, stage: Scene) -> list[dict[str, Any]]:
    """Read the timelines of the project of the scene, as its manager does."""
    answer = api.get(path(stage), headers=stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def inscribe(stage: Scene, timeline_id: str, lineage_id: UUID | None = None) -> UUID:
    """Inscribe a task, by its lineage, to a timeline, around the service (L2 serves them)."""
    lineage = lineage_id or uuid4()
    with stage.database.transaction() as session:
        session.execute(
            insert(TrackingEntry).values(
                id=uuid4(),
                project_id=UUID(stage.project["project_id"]),
                lineage_id=lineage,
                kind="timeline",
                timeline_id=UUID(timeline_id),
                **STAMP,
            )
        )
    return lineage


def inscriptions(stage: Scene) -> list[UUID]:
    """Give the timelines the base holds inscriptions to, one per inscription."""
    with stage.database.transaction() as session:
        found = session.scalars(select(TrackingEntry.timeline_id))
        return [item for item in found if item is not None]


@pytest.mark.requirement("WF-PLA-0140-A")
def test_a_project_without_timeline_lists_none(api: ContractClient, stage: Scene) -> None:
    assert listed(api, stage) == []


@pytest.mark.requirement("WF-PLA-0140-A")
def test_a_timeline_is_created_named_and_listed_in_the_order_of_its_creation(
    api: ContractClient, stage: Scene
) -> None:
    first = made(api, stage, "Comité de pilotage")
    second = made(api, stage, "Revue client")
    assert set(first) == {"timeline_id", "label"}
    assert first["label"] == "Comité de pilotage"
    assert listed(api, stage) == [first, second]
    with stage.database.transaction() as session:
        row = session.get_one(Timeline, UUID(first["timeline_id"]))
        assert row.created_by == stage.manager.user_id
        assert (row.created_at, row.updated_by) == (row.updated_at, stage.manager.user_id)


@pytest.mark.requirement("WF-PLA-0140-A")
def test_the_label_of_a_timeline_is_not_unique(api: ContractClient, stage: Scene) -> None:
    first = made(api, stage, "Réunion de chantier")
    second = made(api, stage, "Réunion de chantier")
    assert first["timeline_id"] != second["timeline_id"]
    assert [item["label"] for item in listed(api, stage)] == ["Réunion de chantier"] * 2


@pytest.mark.requirement("WF-PLA-0140-A")
def test_two_creations_at_once_of_the_same_label_both_succeed(
    api: ContractClient, stage: Scene
) -> None:
    with ThreadPoolExecutor(2) as pool:
        pending = [pool.submit(add, api, stage, "Réunion de chantier") for _ in range(2)]
        answers = [each.result() for each in pending]
    assert [answer.status_code for answer in answers] == [201, 201]
    assert len({answer.json()["timeline_id"] for answer in answers}) == 2
    assert len(listed(api, stage)) == 2


@pytest.mark.requirement("WF-PLA-0140-A")
@pytest.mark.parametrize(
    ("label", "code"),
    [("", "VALUE_REQUIRED"), ("x" * 201, "VALUE_TOO_LONG"), ("   ", "VALIDATION_FAILED")],
)
def test_a_label_that_is_empty_too_long_or_blank_is_refused_and_nothing_is_written(
    api: ContractClient, stage: Scene, label: str, code: str
) -> None:
    answer = add(api, stage, label)
    assert (answer.status_code, answer.json()["code"]) == (422, "VALIDATION_FAILED")
    assert [(field["pointer"], field["code"]) for field in answer.json()["fields"]] == [
        ("/label", code)
    ]
    assert listed(api, stage) == []


@pytest.mark.requirement("WF-PLA-0140-A")
def test_a_label_of_200_characters_is_accepted(api: ContractClient, stage: Scene) -> None:
    assert made(api, stage, "x" * 200)["label"] == "x" * 200


@pytest.mark.requirement("WF-PLA-0140-A")
def test_two_timelines_keep_their_own_selection_and_a_deletion_leaves_the_other_untouched(
    api: ContractClient, stage: Scene
) -> None:
    committee = made(api, stage, "Comité de pilotage")["timeline_id"]
    client = made(api, stage, "Revue client")["timeline_id"]
    shared, alone = uuid4(), uuid4()
    inscribe(stage, committee, shared)
    inscribe(stage, committee, alone)
    inscribe(stage, client, shared)
    assert sorted(map(str, inscriptions(stage))) == sorted([committee, committee, client])
    deleted = api.delete(path(stage, committee), headers=stage.manager.headers)
    assert deleted.status_code == 204
    assert deleted.content == b""
    # The inscriptions of the timeline go with it, those of the other stay, and the list says so
    # at the next reading.
    assert [str(item) for item in inscriptions(stage)] == [client]
    assert [item["timeline_id"] for item in listed(api, stage)] == [client]
    with stage.database.transaction() as session:
        assert session.scalar(select(func.count()).select_from(Timeline)) == 1


@pytest.mark.requirement("WF-PLA-0140-A")
def test_a_timeline_already_deleted_or_of_another_project_is_not_found(
    api: ContractClient, stage: Scene
) -> None:
    created = made(api, stage, "Comité de pilotage")["timeline_id"]
    other = api.post(PROJECTS, headers=stage.manager.headers, json={"label": "Autre projet"})
    other_path = f"{PROJECTS}/{other.json()['project_id']}/timelines/{created}"
    # Another project's path does not reach it, and a second deletion finds nothing (#1733).
    assert refusal(api.delete(other_path, headers=stage.manager.headers))[:2] == (404, "NOT_FOUND")
    assert api.delete(path(stage, created), headers=stage.manager.headers).status_code == 204
    again = api.delete(path(stage, created), headers=stage.manager.headers)
    assert refusal(again)[:2] == (404, "NOT_FOUND")
    unknown = api.delete(path(stage, str(uuid4())), headers=stage.manager.headers)
    assert refusal(unknown)[:2] == (404, "NOT_FOUND")


@pytest.mark.requirement("WF-CYC-0100-A")
def test_a_terminal_project_lists_no_manage_timelines_and_refuses_both_writes(
    api: ContractClient, stage: Scene
) -> None:
    created = made(api, stage, "Revue client")["timeline_id"]
    inscribe(stage, created)
    put_in_state(stage.owner, stage.project["project_id"], "completed")
    project = api.get(f"{PROJECTS}/{stage.project['project_id']}", headers=stage.manager.headers)
    assert project.json()["available_commands"] == []
    refused = (
        add(api, stage, "Réunion de chantier"),
        api.delete(path(stage, created), headers=stage.manager.headers),
    )
    for answer in refused:
        assert refusal(answer) == (
            409,
            "STATE_FORBIDS_OPERATION",
            {"missing_condition": NOT_TERMINAL},
        )
    # Nothing is created, nothing deleted, no inscription lost; the reading stays open.
    assert [item["label"] for item in listed(api, stage)] == ["Revue client"]
    assert len(inscriptions(stage)) == 1


@pytest.mark.requirement("WF-PLA-0140-A")
def test_manage_timelines_is_listed_to_who_holds_planning_write_and_to_no_one_else(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    def commands(who: Person) -> dict[str, list[str]]:
        answer = api.get(f"{PROJECTS}/{stage.project['project_id']}", headers=who.headers)
        assert answer.status_code == 200, answer.text
        return {
            each["command"]: each["missing_conditions"]
            for each in answer.json()["available_commands"]
        }

    assert commands(stage.manager)["manage_timelines"] == []
    reading = person(stage.database, realm, "project_settings.read", CONSULT)
    contribute(stage.database, stage.project["project_id"], reading, "contributor")
    assert "manage_timelines" not in commands(reading)
    assert "manage_timelines" not in commands(stage.reader)


@pytest.mark.requirement("WF-PLA-0140-A")
def test_a_contributor_without_planning_write_an_outsider_and_a_reader_do_not_write(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    created = made(api, stage, "Revue client")["timeline_id"]
    reading = person(stage.database, realm, "project_settings.read", CONSULT)
    contribute(stage.database, stage.project["project_id"], reading, "contributor")
    body = {"label": "Autre"}
    # 403 to who consults without the permission; 404 to who may not consult the project at all;
    # the reader holds ``all_projects_read`` and still is no contributor (403).
    answers = {
        "reading": api.post(path(stage), headers=reading.headers, json=body),
        "outsider": api.post(path(stage), headers=stage.outsider.headers, json=body),
        "reader": api.post(path(stage), headers=stage.reader.headers, json=body),
    }
    assert {name: answer.status_code for name, answer in answers.items()} == {
        "reading": 403,
        "outsider": 404,
        "reader": 403,
    }
    assert refusal(answers["reading"])[1:] == ("PERMISSION_MISSING", {"missing_permission": CHANGE})
    for who in (reading, stage.outsider, stage.reader):
        assert api.delete(path(stage, created), headers=who.headers).status_code in (403, 404)
    assert len(listed(api, stage)) == 1


@pytest.mark.requirement("WF-PLA-0140-A")
def test_a_participant_who_contributes_creates_and_the_outsider_does_not_read(
    api: ContractClient, stage: Scene
) -> None:
    assert add(api, stage, "Revue client", stage.participant).status_code == 201
    assert api.get(path(stage), headers=stage.reader.headers).status_code == 200
    assert api.get(path(stage), headers=stage.outsider.headers).status_code == 404


@pytest.mark.requirement("WF-PLA-0140-A")
def test_the_timelines_of_a_project_that_does_not_exist_are_not_found(
    api: ContractClient, stage: Scene
) -> None:
    missing = f"{PROJECTS}/{uuid4()}/timelines"
    assert api.get(missing, headers=stage.manager.headers).status_code == 404
    assert api.post(missing, headers=stage.manager.headers, json={"label": "A"}).status_code == 404


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_witness_loads_the_two_timelines_of_its_project_under_the_identifiers_it_imposes(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    reader = person(witness, realm, CONSULT, "all_projects_read")
    value = json.loads((WITNESS / "timelines.json").read_text(encoding="utf-8"))["value"]
    project = json.loads((WITNESS / "project.json").read_text(encoding="utf-8"))["value"]
    answer = api.get(f"{PROJECTS}/{project['project_id']}/timelines", headers=reader.headers)
    assert answer.status_code == 200, answer.text
    # The order of the list is not what is judged here: compare the identifiers and labels.
    assert {(item["timeline_id"], item["label"]) for item in answer.json()} == {
        (item["timeline_id"], item["label"]) for item in value
    }
    assert len(answer.json()) == len(value) == 2
    with witness.transaction() as session:
        rows = session.scalars(select(Timeline)).all()
        assert {row.created_by for row in rows} == {None}
        assert len({row.created_at for row in rows}) == 1
