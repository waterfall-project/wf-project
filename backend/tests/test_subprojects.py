# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The subprojects of a project (US-0940, WF-PRJ-0050, WF-DAT-0080), through the service.

``listSubprojects``, ``createSubproject``, ``updateSubproject`` and ``deleteSubproject`` on projects
created through the service, every answer checked against the contract: the code unique in the
project, even under two creations at once, the codes a tab refuses and the reserved names under
their variants (#1502), the commands and the refusal that names the first condition lacking, the
deletion for good, and the subprojects the witness loads.
"""

import json
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

import pytest
from projects_support import PROJECTS, Person, Scene, contribute, person, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import func, select
from support import WITNESS

from waterfall.core.projects.tables import Subproject

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

NOT_TERMINAL = "project_not_terminal"
INTERFACE = "waterfall.core.projects.interface.subprojects"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


def path(stage: Scene, *more: str) -> str:
    """Give the path of the subprojects of the project of the scene, or of one of them."""
    return "/".join([f"{PROJECTS}/{stage.project['project_id']}/subprojects", *more])


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


def add(api: ContractClient, stage: Scene, code: str, label: str = "Poste de commande") -> Any:
    """Create a subproject as the manager of the project does, and give the answer."""
    return api.post(path(stage), headers=stage.manager.headers, json={"code": code, "label": label})


def made(api: ContractClient, stage: Scene, code: str, label: str = "Poste de commande") -> Any:
    """Create a subproject that must be created, and give what is answered."""
    answer = add(api, stage, code, label)
    assert answer.status_code == 201, answer.text
    return answer.json()


def stored(stage: Scene) -> int:
    """Count the subprojects the base holds."""
    with stage.database.transaction() as session:
        return session.scalars(select(func.count()).select_from(Subproject)).one()


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_a_subproject_is_created_listed_and_changed_by_the_manager_of_the_project(
    api: ContractClient, stage: Scene
) -> None:
    created = made(api, stage, "SP-CMD")
    assert (created["code"], created["has_actual_costs"], created["lock_version"]) == (
        "SP-CMD",
        False,
        0,
    )
    assert [(c["command"], c["is_available"]) for c in created["available_commands"]] == [
        ("update", True),
        ("delete", True),
    ]
    assert created["audit"]["created_by"]["user_id"] == str(stage.manager.user_id)
    changed = api.patch(
        path(stage, created["subproject_id"]),
        headers=stage.manager.headers,
        json={"code": "SP-CMD2", "label": "Commande", "lock_version": 0},
    )
    assert changed.status_code == 200, changed.text
    assert (changed.json()["code"], changed.json()["lock_version"]) == ("SP-CMD2", 1)
    listed = api.get(path(stage), headers=stage.manager.headers)
    assert [item["code"] for item in listed.json()] == ["SP-CMD2"]


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_two_subprojects_of_the_same_code_in_a_project_are_refused_naming_the_first(
    api: ContractClient, stage: Scene
) -> None:
    first = made(api, stage, "SP-CMD", "Poste de commande")
    second = add(api, stage, "SP-CMD", "Essais")
    assert second.status_code == 409
    assert faults(second) == [
        (
            "/code",
            "ALREADY_EXISTS",
            {
                "conflicting_object_id": first["subproject_id"],
                "conflicting_object_label": "Poste de commande",
            },
        )
    ]
    assert stored(stage) == 1


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_a_code_taken_by_another_subproject_is_refused_at_the_change(
    api: ContractClient, stage: Scene
) -> None:
    first = made(api, stage, "SP-1", "Un")
    other = made(api, stage, "SP-2", "Deux")
    refused = api.patch(
        path(stage, other["subproject_id"]),
        headers=stage.manager.headers,
        json={"code": "SP-1", "label": "Deux", "lock_version": 0},
    )
    assert refused.status_code == 409
    assert faults(refused)[0][2]["conflicting_object_id"] == first["subproject_id"]
    again = api.patch(
        path(stage, other["subproject_id"]),
        headers=stage.manager.headers,
        json={"code": "SP-2", "label": "Deux", "lock_version": 0},
    )
    # Nothing changes, nothing is written: the counter stays where it was.
    assert again.status_code == 200
    assert again.json()["lock_version"] == 0


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_two_creations_at_once_of_the_same_code_leave_one_subproject_and_one_refusal(
    api: ContractClient, stage: Scene
) -> None:
    def send(label: str) -> Any:
        return add(api, stage, "SP-RACE", label)

    with ThreadPoolExecutor(2) as pool:
        answers = list(pool.map(send, ["Premier", "Second"]))
    assert sorted(answer.status_code for answer in answers) == [201, 409]
    taken = next(answer for answer in answers if answer.status_code == 409)
    winner = next(answer for answer in answers if answer.status_code == 201)
    assert faults(taken)[0][2]["conflicting_object_id"] == winner.json()["subproject_id"]
    assert stored(stage) == 1


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_the_same_code_in_two_projects_is_not_a_collision(
    api: ContractClient, stage: Scene
) -> None:
    made(api, stage, "SP-CMD")
    other = api.post(PROJECTS, headers=stage.manager.headers, json={"label": "Autre"}).json()
    answer = api.post(
        f"{PROJECTS}/{other['project_id']}/subprojects",
        headers=stage.manager.headers,
        json={"code": "SP-CMD", "label": "Poste"},
    )
    assert answer.status_code == 201, answer.text


@pytest.mark.requirement("WF-PRJ-0050-A")
@pytest.mark.parametrize(
    ("code", "forbidden"),
    [("SP/01", ["/"]), ("A:B*C", [":", "*"]), ("[x]?", ["[", "]", "?"]), ("a\\b\\c", ["\\"])],
)
def test_a_code_with_a_character_a_tab_refuses_is_refused_naming_each_once(
    api: ContractClient, stage: Scene, code: str, forbidden: list[str]
) -> None:
    refused = add(api, stage, code)
    assert refused.status_code == 422
    assert faults(refused) == [
        ("/code", "SUBPROJECT_CODE_INVALID", {"forbidden_characters": forbidden})
    ]
    assert stored(stage) == 0


RESERVED = [
    ("Synthèse", "Synthèse"),
    ("synthèse", "Synthèse"),
    ("SYNTHÈSE", "Synthèse"),
    ("Synthèse ", "Synthèse"),
    ("  Synthèse", "Synthèse"),
    ("Synthèse ", "Synthèse"),
    (unicodedata.normalize("NFD", "Synthèse"), "Synthèse"),
    (unicodedata.normalize("NFD", "SYNTHÈSE"), "Synthèse"),
    ("Hors sous-projet", "Hors sous-projet"),
    ("hors sous-projet", "Hors sous-projet"),
    ("Hors  sous-projet", "Hors sous-projet"),
    ("Hors sous-projet", "Hors sous-projet"),
    ("HORS \t SOUS-PROJET ", "Hors sous-projet"),
]


@pytest.mark.requirement("WF-PRJ-0050-A")
@pytest.mark.parametrize(("code", "name"), RESERVED)
def test_a_reserved_name_is_refused_whatever_its_case_blanks_and_unicode_form(
    api: ContractClient, stage: Scene, code: str, name: str
) -> None:
    refused = add(api, stage, code)
    assert refused.status_code == 422
    assert faults(refused) == [("/code", "SUBPROJECT_CODE_INVALID", {"reserved_name": name})]
    assert stored(stage) == 0


@pytest.mark.requirement("WF-PRJ-0050-A")
@pytest.mark.parametrize(("code", "name"), RESERVED[:1] + RESERVED[3:4] + RESERVED[8:9])
def test_a_reserved_name_is_refused_at_the_change_as_at_the_creation(
    api: ContractClient, stage: Scene, code: str, name: str
) -> None:
    created = made(api, stage, "SP-1")
    refused = api.patch(
        path(stage, created["subproject_id"]),
        headers=stage.manager.headers,
        json={"code": code, "label": "Poste", "lock_version": 0},
    )
    assert refused.status_code == 422
    assert faults(refused) == [("/code", "SUBPROJECT_CODE_INVALID", {"reserved_name": name})]


@pytest.mark.requirement("WF-PRJ-0050-A")
@pytest.mark.parametrize("code", ["Synthese", "Synthèse 2", "Hors lot", "x" * 31])
def test_a_code_that_names_a_tab_is_accepted(api: ContractClient, stage: Scene, code: str) -> None:
    assert made(api, stage, code)["code"] == code


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_a_code_of_more_than_thirty_one_characters_is_refused_with_its_bound(
    api: ContractClient, stage: Scene
) -> None:
    refused = add(api, stage, "x" * 32)
    assert refused.status_code == 422
    assert faults(refused) == [("/code", "VALUE_TOO_LONG", {"max_length": 31})]
    assert stored(stage) == 0


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_an_empty_or_blank_code_or_label_is_refused_field_by_field(
    api: ContractClient, stage: Scene
) -> None:
    empty = add(api, stage, "", "")
    assert [(pointer, code) for pointer, code, _ in faults(empty)] == [
        ("/code", "VALUE_REQUIRED"),
        ("/label", "VALUE_REQUIRED"),
    ]
    blank = add(api, stage, "   ")
    assert faults(blank) == [("/code", "VALUE_REQUIRED", {})]


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_a_forbidden_code_and_an_empty_label_are_both_named_in_one_refusal(
    api: ContractClient, stage: Scene
) -> None:
    refused = add(api, stage, "A/B", "")
    assert refused.status_code == 422
    assert faults(refused) == [
        ("/code", "SUBPROJECT_CODE_INVALID", {"forbidden_characters": ["/"]}),
        ("/label", "VALUE_REQUIRED", {}),
    ]
    assert stored(stage) == 0


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_a_change_at_a_stale_version_is_refused_and_writes_nothing(
    api: ContractClient, stage: Scene
) -> None:
    created = made(api, stage, "SP-1")
    stale = api.patch(
        path(stage, created["subproject_id"]),
        headers=stage.manager.headers,
        json={"code": "SP-2", "label": "Poste", "lock_version": 3},
    )
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 0})
    listed = api.get(path(stage), headers=stage.manager.headers)
    assert [item["code"] for item in listed.json()] == ["SP-1"]


@pytest.mark.requirement("WF-PRJ-0050-A")
@pytest.mark.requirement("WF-DAT-0080-A")
def test_a_participant_neither_changes_nor_deletes_a_subproject(
    api: ContractClient, stage: Scene
) -> None:
    created = made(api, stage, "SP-1")
    where = path(stage, created["subproject_id"])
    changed = api.patch(
        where,
        headers=stage.participant.headers,
        json={"code": "SP-2", "label": "Poste", "lock_version": 0},
    )
    deleted = api.delete(where, headers=stage.participant.headers, params={"lock_version": 0})
    assert (changed.status_code, deleted.status_code) == (403, 403)
    assert stored(stage) == 1


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_a_change_that_changes_nothing_does_not_raise_the_version(
    api: ContractClient, stage: Scene
) -> None:
    created = made(api, stage, "SP-1", "Poste")
    same = api.patch(
        path(stage, created["subproject_id"]),
        headers=stage.manager.headers,
        json={"code": "SP-1", "label": "Poste", "lock_version": 0},
    )
    assert same.status_code == 200, same.text
    assert same.json()["lock_version"] == 0


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_a_participant_and_an_outsider_do_not_write_a_subproject(
    api: ContractClient, stage: Scene
) -> None:
    body = {"code": "SP-1", "label": "Un"}
    participant = api.post(path(stage), headers=stage.participant.headers, json=body)
    outsider = api.post(path(stage), headers=stage.outsider.headers, json=body)
    assert (participant.status_code, outsider.status_code) == (403, 404)
    assert stored(stage) == 0


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_a_participant_reads_the_list_without_commands_it_cannot_exercise(
    api: ContractClient, stage: Scene
) -> None:
    made(api, stage, "SP-1")
    listed = api.get(path(stage), headers=stage.participant.headers)
    assert listed.status_code == 200
    commands = listed.json()[0]["available_commands"]
    assert [(c["command"], c["missing_conditions"]) for c in commands] == [
        ("update", ["is_project_manager"]),
        ("delete", ["is_project_manager"]),
    ]
    outsider = api.get(path(stage), headers=stage.outsider.headers)
    assert outsider.status_code == 404
    reader = api.get(path(stage), headers=stage.reader.headers)
    assert reader.status_code == 200


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_the_list_is_searched_filtered_and_sorted_by_the_server(
    api: ContractClient, stage: Scene
) -> None:
    made(api, stage, "SP-B", "Alpha")
    made(api, stage, "SP-A", "Zèbre")
    made(api, stage, "SP-C", "Milieu")

    def codes(**query: object) -> list[str]:
        answer = api.get(path(stage), headers=stage.manager.headers, params=query)
        assert answer.status_code == 200, answer.text
        return [item["code"] for item in answer.json()]

    assert codes() == ["SP-A", "SP-B", "SP-C"]
    assert codes(sort_by="code", sort_order="desc") == ["SP-C", "SP-B", "SP-A"]
    assert codes(sort_by="label") == ["SP-B", "SP-C", "SP-A"]
    assert codes(sort_by="has_actual_costs") == ["SP-A", "SP-B", "SP-C"]
    assert codes(search="zebre") == ["SP-A"]
    assert codes(search="sp-c") == ["SP-C"]
    assert codes(has_actual_costs="false") == ["SP-A", "SP-B", "SP-C"]
    assert codes(has_actual_costs="true") == []


@pytest.mark.requirement("WF-DAT-0080-A")
def test_the_deletion_of_an_unreferenced_subproject_removes_it_from_the_base(
    api: ContractClient, stage: Scene
) -> None:
    created = made(api, stage, "SP-1")
    stale = api.delete(
        path(stage, created["subproject_id"]),
        headers=stage.manager.headers,
        params={"lock_version": 5},
    )
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 0})
    assert stored(stage) == 1
    deleted = api.delete(
        path(stage, created["subproject_id"]),
        headers=stage.manager.headers,
        params={"lock_version": 0},
    )
    assert deleted.status_code == 204
    assert stored(stage) == 0
    again = api.delete(
        path(stage, created["subproject_id"]),
        headers=stage.manager.headers,
        params={"lock_version": 0},
    )
    assert again.status_code == 404


@pytest.mark.requirement("WF-DAT-0080-A")
def test_a_subproject_of_another_project_is_neither_changed_nor_deleted_by_this_path(
    api: ContractClient, stage: Scene
) -> None:
    created = made(api, stage, "SP-1")
    other = api.post(PROJECTS, headers=stage.manager.headers, json={"label": "Autre"}).json()
    url = f"{PROJECTS}/{other['project_id']}/subprojects/{created['subproject_id']}"
    deleted = api.delete(url, headers=stage.manager.headers, params={"lock_version": 0})
    changed = api.patch(
        url, headers=stage.manager.headers, json={"code": "X", "label": "X", "lock_version": 0}
    )
    assert (deleted.status_code, changed.status_code) == (404, 404)
    assert stored(stage) == 1


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_a_terminal_project_lists_no_command_and_refuses_every_write_naming_the_condition(
    api: ContractClient, stage: Scene
) -> None:
    created = made(api, stage, "SP-1")
    put_in_state(stage.owner, stage.project["project_id"], "completed")
    listed = api.get(path(stage), headers=stage.manager.headers)
    assert listed.json()[0]["available_commands"] == []
    refused = (
        add(api, stage, "SP-2"),
        api.patch(
            path(stage, created["subproject_id"]),
            headers=stage.manager.headers,
            json={"code": "SP-3", "label": "x", "lock_version": 0},
        ),
        api.delete(
            path(stage, created["subproject_id"]),
            headers=stage.manager.headers,
            params={"lock_version": 0},
        ),
    )
    for answer in refused:
        assert refusal(answer) == (
            409,
            "STATE_FORBIDS_OPERATION",
            {"missing_condition": NOT_TERMINAL},
        )
    assert stored(stage) == 1


@pytest.mark.requirement("WF-DAT-0080-A")
def test_a_refusal_of_the_deletion_names_the_first_condition_in_the_order_of_the_command(
    api: ContractClient, stage: Scene, monkeypatch: pytest.MonkeyPatch
) -> None:
    created = made(api, stage, "SP-1")

    # The question of the actual costs, answered as when a cost is charged (US-1610/L3); that of
    # EP-07, as it answers when a line of the current revision bears the subproject.
    def charged(_session: object, ids: Any) -> frozenset[Any]:
        return frozenset(ids)

    def bearing(_session: object, _project: object, ids: Any) -> frozenset[Any]:
        return frozenset(ids)

    def named(_session: object, _project: object, ids: Any) -> dict[Any, tuple[object, ...]]:
        return {each: (object(),) for each in ids}

    monkeypatch.setattr(f"{INTERFACE}.subprojects_estimated", bearing)
    monkeypatch.setattr(f"{INTERFACE}.subproject_estimate_lines", named)
    monkeypatch.setattr(f"{INTERFACE}.subprojects_with_actual_costs", charged)
    listed = api.get(path(stage), headers=stage.manager.headers).json()[0]
    assert listed["available_commands"][1] == {
        "command": "delete",
        "is_available": False,
        "missing_conditions": [
            "subproject_without_actual_costs",
            "subproject_without_estimate_lines",
        ],
    }
    refused = api.delete(
        path(stage, created["subproject_id"]),
        headers=stage.manager.headers,
        params={"lock_version": 0},
    )
    assert refusal(refused) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "subproject_without_actual_costs"},
    )
    assert stored(stage) == 1


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_a_project_without_subproject_lists_none_and_a_participant_holding_it_may_not_write(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    assert api.get(path(stage), headers=stage.manager.headers).json() == []
    colleague: Person = person(
        stage.database, realm, "project_settings.read", "project_settings.write"
    )
    contribute(stage.database, stage.project["project_id"], colleague, "contributor")
    refused = api.post(path(stage), headers=colleague.headers, json={"code": "A", "label": "A"})
    assert refused.status_code == 403


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_witness_loads_the_subprojects_of_its_project_under_the_identifiers_it_imposes(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    reader = person(witness, realm, "project_settings.read", "all_projects_read")
    value = json.loads((WITNESS / "subprojects.json").read_text(encoding="utf-8"))["value"]
    project_id = json.loads((WITNESS / "project.json").read_text(encoding="utf-8"))["value"]
    answer = api.get(f"{PROJECTS}/{project_id['project_id']}/subprojects", headers=reader.headers)
    assert answer.status_code == 200, answer.text
    assert [(item["subproject_id"], item["code"], item["label"]) for item in answer.json()] == [
        (item["subproject_id"], item["code"], item["label"]) for item in value
    ]
    # The actual costs of the witness are imputed to both (US-1650/L2), as the example says.
    assert (
        [item["has_actual_costs"] for item in answer.json()]
        == [item["has_actual_costs"] for item in value]
        == [True, True]
    )
