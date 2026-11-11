# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The work breakdown of a project (US-0950, WF-PRJ-0020), through the service.

``getWorkBreakdown`` and ``setWorkBreakdown`` on projects created through the service, every
answer checked against the contract: the work package and the order item a project is born with,
the whole writing under its own counter, the refusals field by field, the elements left out, the
filtered readings, two concurrent writings, and the work breakdown the witness loads.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from projects_support import PROJECTS, Person, Scene, person, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import func, select
from support import WITNESS

from waterfall.core.projects.tables import Deliverable, OrderItem, Project, WorkPackage

if TYPE_CHECKING:
    from httpx2 import Response
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


def path(stage: Scene) -> str:
    """Give the path of the work breakdown of the project of the scene."""
    return f"{PROJECTS}/{stage.project['project_id']}/work-breakdown"


def read(api: ContractClient, stage: Scene, who: Person, query: str = "") -> dict[str, Any]:
    """Read the work breakdown as ``who`` does; give the body of a 200."""
    answer = api.get(f"{path(stage)}?{query}", headers=who.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def write(
    api: ContractClient, stage: Scene, who: Person, packages: list[dict[str, Any]], version: Any
) -> Response:
    """Write the whole work breakdown as ``who`` does, at the counter ``version``."""
    body = {"work_packages": packages, "lock_version": version}
    return api.put(path(stage), headers=who.headers, json=body)


def package(label: str, *items: dict[str, Any], id_: str | None = None) -> dict[str, Any]:
    """Give a work package to write; new if it has no identifier."""
    entry: dict[str, Any] = {"label": label, "order_items": list(items)}
    if id_ is not None:
        entry["work_package_id"] = id_
    return entry


def item(label: str, *deliverables: dict[str, Any], id_: str | None = None) -> dict[str, Any]:
    """Give an order item to write; new if it has no identifier."""
    entry: dict[str, Any] = {"label": label, "deliverables": list(deliverables)}
    if id_ is not None:
        entry["order_item_id"] = id_
    return entry


def deliverable(label: str, id_: str | None = None) -> dict[str, Any]:
    """Give a deliverable to write; new if it has no identifier."""
    entry: dict[str, Any] = {"label": label}
    if id_ is not None:
        entry["deliverable_id"] = id_
    return entry


def refusal(response: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("params", {})


def faults(response: Any) -> list[tuple[str, str]]:
    """Give, by field, the pointer and the code of a refusal."""
    return [(field["pointer"], field["code"]) for field in response.json()["fields"]]


def labels(body: dict[str, Any]) -> list[Any]:
    """Give the labels of a reading as nested lists: package, then its items, then deliverables."""
    return [
        [
            package["label"],
            [
                [item["label"], [d["label"] for d in item["deliverables"]]]
                for item in package["order_items"]
            ],
        ]
        for package in body["work_packages"]
    ]


def counts(stage: Scene) -> tuple[int, int, int]:
    """Count the rows stored of the three tables."""
    with stage.database.transaction() as session:
        packages, items, deliverables = (
            session.scalar(select(func.count()).select_from(table)) or 0
            for table in (WorkPackage, OrderItem, Deliverable)
        )
    return packages, items, deliverables


def first(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Write a work breakdown of two packages through the manager; give the answer."""
    answer = write(
        api,
        stage,
        stage.manager,
        [
            package(
                "Lot A",
                item("Poste A1", deliverable("Plan"), deliverable("Notice")),
                item("Poste A2"),
            ),
            package("Lot B", item("Poste B1", deliverable("Rapport"))),
        ],
        1,
    )
    assert answer.status_code == 200, answer.text
    return answer.json()


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_a_project_without_a_work_breakdown_has_a_work_package_and_a_bare_order_item(
    api: ContractClient, stage: Scene
) -> None:
    body = read(api, stage, stage.manager)
    label = stage.project["label"]
    assert labels(body) == [[label, [[label, []]]]]
    assert body["lock_version"] == 1
    assert all(
        element["is_match"] and element["attached_task"] is None
        for element in body["work_packages"] + body["work_packages"][0]["order_items"]
    )
    assert counts(stage) == (1, 1, 0)


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_an_order_item_can_be_written_without_deliverable(
    api: ContractClient, stage: Scene
) -> None:
    answer = write(api, stage, stage.manager, [package("Lot", item("Poste seul"))], 1)
    assert answer.status_code == 200, answer.text
    assert labels(answer.json()) == [["Lot", [["Poste seul", []]]]]
    assert counts(stage) == (1, 1, 0)


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_the_whole_work_breakdown_is_written_and_new_elements_receive_their_identifier(
    api: ContractClient, stage: Scene
) -> None:
    answer = first(api, stage)
    assert answer["lock_version"] == 2
    assert labels(answer) == [
        ["Lot A", [["Poste A1", ["Plan", "Notice"]], ["Poste A2", []]]],
        ["Lot B", [["Poste B1", ["Rapport"]]]],
    ]
    ids = [
        element[key]
        for lot in answer["work_packages"]
        for element, key in [(lot, "work_package_id")]
        + [(i, "order_item_id") for i in lot["order_items"]]
        + [(d, "deliverable_id") for i in lot["order_items"] for d in i["deliverables"]]
    ]
    assert len(set(ids)) == len(ids) == 8
    assert read(api, stage, stage.manager) == answer
    assert counts(stage) == (2, 3, 3)


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_an_element_sent_back_with_its_identifier_is_renamed_moved_and_reordered(
    api: ContractClient, stage: Scene
) -> None:
    lots = first(api, stage)["work_packages"]
    lot_a, lot_b = lots
    item_a1, item_a2 = lot_a["order_items"]
    plan, notice = item_a1["deliverables"]
    # The lots exchange their places, a post goes to the other lot, the deliverables exchange theirs
    # and one goes under another post: every slot is taken again at once.
    answer = write(
        api,
        stage,
        stage.manager,
        [
            package(
                "Lot B bis",
                item(
                    "Poste B1",
                    *[
                        deliverable(
                            "Rapport", lot_b["order_items"][0]["deliverables"][0]["deliverable_id"]
                        )
                    ],
                    id_=lot_b["order_items"][0]["order_item_id"],
                ),
                item("Poste A2", id_=item_a2["order_item_id"]),
                id_=lot_b["work_package_id"],
            ),
            package(
                "Lot A",
                item(
                    "Poste A1",
                    deliverable("Notice", notice["deliverable_id"]),
                    deliverable("Plan", plan["deliverable_id"]),
                    id_=item_a1["order_item_id"],
                ),
                id_=lot_a["work_package_id"],
            ),
        ],
        2,
    )
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert labels(body) == [
        ["Lot B bis", [["Poste B1", ["Rapport"]], ["Poste A2", []]]],
        ["Lot A", [["Poste A1", ["Notice", "Plan"]]]],
    ]
    assert body["work_packages"][0]["work_package_id"] == lot_b["work_package_id"]
    assert body["work_packages"][0]["order_items"][1]["order_item_id"] == item_a2["order_item_id"]
    assert body["lock_version"] == 3
    assert counts(stage) == (2, 3, 3)


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_an_element_left_out_is_deleted_for_good_with_what_it_holds(
    api: ContractClient, stage: Scene
) -> None:
    lot_a, lot_b = first(api, stage)["work_packages"]
    answer = write(
        api,
        stage,
        stage.manager,
        [
            package(
                "Lot B",
                item("Poste B1", id_=lot_b["order_items"][0]["order_item_id"]),
                id_=lot_b["work_package_id"],
            )
        ],
        2,
    )
    assert answer.status_code == 200, answer.text
    assert labels(answer.json()) == [["Lot B", [["Poste B1", []]]]]
    assert counts(stage) == (1, 1, 0)
    with stage.database.transaction() as session:
        assert session.scalar(select(func.count()).where(WorkPackage.deleted_at.is_not(None))) == 0
    assert lot_a["work_package_id"] not in [
        lot["work_package_id"] for lot in read(api, stage, stage.manager)["work_packages"]
    ]


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_a_counter_that_is_stale_or_null_and_a_work_breakdown_without_package_are_refused(
    api: ContractClient, stage: Scene
) -> None:
    first(api, stage)
    stale = write(api, stage, stage.manager, [package("Lot", item("Poste"))], 1)
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 2})
    nulled = write(api, stage, stage.manager, [package("Lot", item("Poste"))], None)
    assert nulled.status_code == 422
    assert faults(nulled) == [("/lock_version", "VALUE_REQUIRED")]
    empty = write(api, stage, stage.manager, [], 2)
    assert empty.status_code == 422
    assert faults(empty) == [("/work_packages", "VALUE_REQUIRED")]
    assert counts(stage) == (2, 3, 3)
    assert read(api, stage, stage.manager)["lock_version"] == 2


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_a_filtered_reading_sent_back_is_refused_for_its_null_counter(
    api: ContractClient, stage: Scene
) -> None:
    first(api, stage)
    filtered = read(api, stage, stage.manager, "search=lot")
    assert filtered["lock_version"] is None
    sent = api.put(
        path(stage),
        headers=stage.manager.headers,
        json={
            "work_packages": [],
            "lock_version": filtered["lock_version"],
        },
    )
    assert sent.status_code == 422
    assert ("/lock_version", "VALUE_REQUIRED") in faults(sent)


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_a_label_that_is_empty_or_too_long_is_refused_at_its_field(
    api: ContractClient, stage: Scene
) -> None:
    refused = write(
        api,
        stage,
        stage.manager,
        [
            package(
                "",
                item("x" * 301, deliverable("")),
                item("Poste", deliverable("y" * 301), deliverable("   ")),
            )
        ],
        1,
    )
    assert refused.status_code == 422
    assert faults(refused) == [
        ("/work_packages/0/label", "VALUE_REQUIRED"),
        ("/work_packages/0/order_items/0/label", "VALUE_TOO_LONG"),
        ("/work_packages/0/order_items/0/deliverables/0/label", "VALUE_REQUIRED"),
        ("/work_packages/0/order_items/1/deliverables/0/label", "VALUE_TOO_LONG"),
        ("/work_packages/0/order_items/1/deliverables/1/label", "VALIDATION_FAILED"),
    ]
    assert counts(stage) == (1, 1, 0)


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_an_identifier_unknown_forged_or_of_another_nature_is_refused_at_its_field(
    api: ContractClient, stage: Scene
) -> None:
    lot_a = first(api, stage)["work_packages"][0]
    item_id = lot_a["order_items"][0]["order_item_id"]
    deliverable_id = lot_a["order_items"][0]["deliverables"][0]["deliverable_id"]
    refused = write(
        api,
        stage,
        stage.manager,
        [
            package(
                "Lot",
                item("Poste", id_=str(uuid4())),
                item("Autre", id_=deliverable_id),
                item("Troisième", deliverable("Plan", item_id), id_=item_id),
                id_=item_id,
            )
        ],
        2,
    )
    assert refused.status_code == 422
    assert faults(refused) == [
        ("/work_packages/0/work_package_id", "UNKNOWN_WORK_BREAKDOWN_ITEM"),
        ("/work_packages/0/order_items/0/order_item_id", "UNKNOWN_WORK_BREAKDOWN_ITEM"),
        ("/work_packages/0/order_items/1/order_item_id", "UNKNOWN_WORK_BREAKDOWN_ITEM"),
        ("/work_packages/0/order_items/2/order_item_id", "DUPLICATE_WORK_BREAKDOWN_ITEM"),
        (
            "/work_packages/0/order_items/2/deliverables/0/deliverable_id",
            "DUPLICATE_WORK_BREAKDOWN_ITEM",
        ),
    ]
    assert counts(stage) == (2, 3, 3)
    assert read(api, stage, stage.manager)["lock_version"] == 2


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_an_identifier_sent_twice_is_refused_at_each_occurrence_after_the_first(
    api: ContractClient, stage: Scene
) -> None:
    lot_a = first(api, stage)["work_packages"][0]
    plan = lot_a["order_items"][0]["deliverables"][0]["deliverable_id"]
    refused = write(
        api,
        stage,
        stage.manager,
        [
            package(
                "Lot",
                item("Poste", deliverable("Un", plan), deliverable("Deux", plan)),
                item("Autre", deliverable("Trois", plan)),
            )
        ],
        2,
    )
    assert refused.status_code == 422
    assert faults(refused) == [
        (
            "/work_packages/0/order_items/0/deliverables/1/deliverable_id",
            "DUPLICATE_WORK_BREAKDOWN_ITEM",
        ),
        (
            "/work_packages/0/order_items/1/deliverables/0/deliverable_id",
            "DUPLICATE_WORK_BREAKDOWN_ITEM",
        ),
    ]


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_the_work_breakdown_is_read_by_a_participant_and_the_reader_but_written_by_a_manager(
    api: ContractClient, stage: Scene
) -> None:
    for who in (stage.participant, stage.reader):
        assert read(api, stage, who)["lock_version"] == 1
    hidden = api.get(path(stage), headers=stage.outsider.headers)
    assert refusal(hidden) == (404, "NOT_FOUND", {})
    unknown = api.get(f"{PROJECTS}/{uuid4()}/work-breakdown", headers=stage.manager.headers)
    assert refusal(unknown) == (404, "NOT_FOUND", {})
    body = [package("Lot", item("Poste"))]
    assert refusal(write(api, stage, stage.participant, body, 1)) == (
        403,
        "NOT_PROJECT_MANAGER",
        {"missing_condition": "is_project_manager"},
    )
    assert refusal(write(api, stage, stage.outsider, body, 1)) == (404, "NOT_FOUND", {})
    assert refusal(write(api, stage, stage.reader, body, 1))[0] == 403
    assert counts(stage) == (1, 1, 0)


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_a_terminal_project_refuses_the_writing(api: ContractClient, stage: Scene) -> None:
    put_in_state(stage.owner, stage.project["project_id"], "lost")
    refused = write(api, stage, stage.manager, [package("Lot", item("Poste"))], 1)
    assert refusal(refused) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "project_not_terminal"},
    )
    assert read(api, stage, stage.manager)["lock_version"] == 1


def pend_marking(api: ContractClient, stage: Scene) -> None:
    """Open the current revision and ask for its marking: a real task of the queue, pending."""
    base = f"{PROJECTS}/{stage.project['project_id']}/revisions"
    opened = api.post(base, headers=stage.manager.headers, json={})
    assert opened.status_code == 201, opened.text
    revision = opened.json()
    asked = api.post(
        f"{base}/{revision['revision_id']}/mark",
        headers=stage.manager.headers,
        json={"version_name": "v1.0", "lock_version": revision["lock_version"]},
    )
    assert asked.status_code == 202, asked.text


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_a_background_task_that_writes_in_the_project_refuses_the_writing(
    api: ContractClient, stage: Scene
) -> None:
    pend_marking(api, stage)
    refused = write(api, stage, stage.manager, [package("Lot", item("Poste"))], 1)
    assert refusal(refused) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "no_background_task_running"},
    )
    assert counts(stage) == (1, 1, 0)
    assert read(api, stage, stage.manager)["lock_version"] == 1


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_a_terminal_project_is_refused_before_the_background_task(
    api: ContractClient, stage: Scene
) -> None:
    pend_marking(api, stage)
    put_in_state(stage.owner, stage.project["project_id"], "lost")
    refused = write(api, stage, stage.manager, [package("Lot", item("Poste"))], 1)
    assert refusal(refused) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "project_not_terminal"},
    )


def rename(api: ContractClient, stage: Scene, label: str, version: int) -> None:
    """Rename the project as its manager does, at the version ``version``."""
    renamed = api.patch(
        f"{PROJECTS}/{stage.project['project_id']}",
        headers=stage.manager.headers,
        json={"label": label, "lock_version": version},
    )
    assert renamed.status_code == 200, renamed.text


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_the_birth_work_breakdown_follows_the_label_of_the_project(
    api: ContractClient, stage: Scene
) -> None:
    rename(api, stage, "Beta", 1)
    body = read(api, stage, stage.manager)
    assert body["lock_version"] == 1
    (lot,) = body["work_packages"]
    assert (lot["label"], [poste["label"] for poste in lot["order_items"]]) == ("Beta", ["Beta"])


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_a_work_breakdown_that_was_written_keeps_its_labels_when_the_project_is_renamed(
    api: ContractClient, stage: Scene
) -> None:
    written = write(api, stage, stage.manager, [package("Lot saisi", item("Poste saisi"))], 1)
    assert written.status_code == 200, written.text
    rename(api, stage, "Beta", 1)
    body = read(api, stage, stage.manager)
    (lot,) = body["work_packages"]
    assert body["lock_version"] == 2
    assert (lot["label"], lot["order_items"][0]["label"]) == ("Lot saisi", "Poste saisi")


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_two_writings_at_the_same_counter_write_once_and_the_other_is_refused_stale(
    api: ContractClient, stage: Scene
) -> None:
    def send(label: str) -> Any:
        return write(api, stage, stage.manager, [package(label, item("Poste"))], 1)

    with ThreadPoolExecutor(2) as pool:
        answers = list(pool.map(send, ["Premier", "Second"]))
    assert sorted(answer.status_code for answer in answers) == [200, 412]
    stale = next(answer for answer in answers if answer.status_code == 412)
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 2})
    stored = read(api, stage, stage.manager)
    assert stored["lock_version"] == 2
    assert len(stored["work_packages"]) == 1
    assert counts(stage) == (1, 1, 0)


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_the_reading_searches_the_labels_and_keeps_the_containers_of_what_it_retains(
    api: ContractClient, stage: Scene
) -> None:
    first(api, stage)
    found = read(api, stage, stage.manager, "search=PLAN")
    assert found["lock_version"] is None
    assert labels(found) == [["Lot A", [["Poste A1", ["Plan"]]]]]
    assert [lot["is_match"] for lot in found["work_packages"]] == [False]
    assert [i["is_match"] for i in found["work_packages"][0]["order_items"]] == [False]
    assert found["work_packages"][0]["order_items"][0]["deliverables"][0]["is_match"] is True
    # A package whose own label matches is retained without what it holds.
    by_lot = read(api, stage, stage.manager, "search=lot")
    assert labels(by_lot) == [["Lot A", []], ["Lot B", []]]
    assert all(lot["is_match"] for lot in by_lot["work_packages"])
    assert read(api, stage, stage.manager, "search=introuvable")["work_packages"] == []


@pytest.mark.requirement("WF-PRJ-0020-A")
def test_the_reading_filters_by_kind_and_combines_the_filters(
    api: ContractClient, stage: Scene
) -> None:
    first(api, stage)
    items = read(api, stage, stage.manager, "kinds=order_item")
    assert labels(items) == [
        ["Lot A", [["Poste A1", []], ["Poste A2", []]]],
        ["Lot B", [["Poste B1", []]]],
    ]
    assert [lot["is_match"] for lot in items["work_packages"]] == [False, False]
    assert items["lock_version"] is None
    many = read(api, stage, stage.manager, "kinds=work_package,deliverable")
    assert labels(many) == [
        ["Lot A", [["Poste A1", ["Plan", "Notice"]]]],
        ["Lot B", [["Poste B1", ["Rapport"]]]],
    ]
    assert [lot["is_match"] for lot in many["work_packages"]] == [True, True]
    assert [i["is_match"] for lot in many["work_packages"] for i in lot["order_items"]] == [
        False,
        False,
    ]
    both = read(api, stage, stage.manager, "kinds=order_item&search=a2")
    assert labels(both) == [["Lot A", [["Poste A2", []]]]]
    bad = api.get(f"{path(stage)}?kinds=boss", headers=stage.manager.headers)
    assert bad.status_code == 422
    assert faults(bad) == [("/query/kinds", "VALIDATION_FAILED")]


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_witness_loads_its_work_breakdown_under_its_identifiers_and_counter(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    reader = person(witness, realm, "project_settings.read", "all_projects_read")
    value = json.loads((WITNESS / "work_breakdown.json").read_text(encoding="utf-8"))["value"]
    project = json.loads((WITNESS / "project.json").read_text(encoding="utf-8"))["value"]
    answer = api.get(f"{PROJECTS}/{project['project_id']}/work-breakdown", headers=reader.headers)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    # The one difference: the tasks that bear a work package are EP-06's, none exists yet.
    assert body["work_packages"][0]["attached_task"] is None
    assert value["work_packages"][0]["attached_task"] is not None
    value["work_packages"][0]["attached_task"] = None
    assert body == value
    # The project born with its default only keeps it.
    other = api.get(
        f"{PROJECTS}/01926f3a-7c00-7000-8000-000000000002/work-breakdown", headers=reader.headers
    )
    assert other.status_code == 200
    assert other.json()["lock_version"] == 1
    assert len(other.json()["work_packages"]) == 1
    with witness.transaction() as session:
        assert (
            session.scalar(
                select(Project.work_breakdown_lock_version).where(
                    Project.id == UUID(project["project_id"])
                )
            )
            == value["lock_version"]
        )
