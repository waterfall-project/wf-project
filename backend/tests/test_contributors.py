# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The contributors of a project (US-0930, WF-PRJ-0060, WF-ADM-0070), through the service.

``listContributors``, ``setContributors`` and ``listContributorSuggestions`` on projects created
through the service, every answer checked against the contract: the creator project manager, who
may read the project and who may write its list, the last project manager, the accounts refused at
their line, the rescue of a project whose project managers are all deactivated, and the list the
witness loads.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from projects_support import PROJECTS, Person, Scene, person, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import event, insert, select, update
from sqlalchemy.orm import Session
from support import WITNESS, raw_account, wait_for_a_lock

from waterfall.core.projects.interface import (
    ContributorEntry,
    ContributorsToWrite,
    Viewer,
    set_contributors,
)
from waterfall.core.projects.interface.contributors import changes
from waterfall.core.projects.tables import Contributor, Project
from waterfall.core.users.interface import anonymize_account
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act, AuditEntry
from waterfall.platform.database import utc_now
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from collections.abc import Callable

    from httpx2 import Response
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

RESCUE = ("project_settings.read", "project_settings.write", "all_projects_read")
MANAGER = "project_manager"
CONTRIBUTOR = "contributor"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


def path(stage: Scene) -> str:
    """Give the path of the contributors of the project of the scene."""
    return f"{PROJECTS}/{stage.project['project_id']}/contributors"


def account(
    database: Database,
    first_name: str,
    last_name: str,
    *,
    active: bool = True,
    anonymized: bool = False,
) -> UUID:
    """Write an account around the service, active, deactivated or anonymised."""
    columns: dict[str, object] = {"state": "active" if active else "deactivated"}
    if anonymized:
        columns |= {
            "first_name": None,
            "last_name": None,
            "email": None,
            "state": "deactivated",
            "anonymized_at": datetime(2026, 10, 2, tzinfo=UTC),
        }
    else:
        columns |= {
            "first_name": first_name,
            "last_name": last_name,
            "email": f"{uuid4().hex}@example.org",
        }
    row = raw_account(**columns)
    with database.transaction() as session:
        session.execute(insert(UserAccount).values(**row))
    return UUID(str(row["id"]))


def inscribe(database: Database, stage: Scene, user_id: UUID, kind: str) -> None:
    """Inscribe an account on the project of the scene, around the service."""
    with database.transaction() as session:
        session.execute(
            insert(Contributor).values(
                project_id=UUID(stage.project["project_id"]), user_account_id=user_id, kind=kind
            )
        )


def deactivate(owner: Engine, user_id: UUID) -> None:
    """Deactivate an account, as the synchronisation of the directory does."""
    with owner.begin() as connection:
        connection.execute(
            update(UserAccount).where(UserAccount.id == user_id).values(state="deactivated")
        )


def read(api: ContractClient, stage: Scene, who: Person, query: str = "") -> dict[str, Any]:
    """Read the list as ``who`` does; give the body of a 200."""
    answer = api.get(f"{path(stage)}?{query}", headers=who.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def write(
    api: ContractClient, stage: Scene, who: Person, lines: list[tuple[UUID, str]], version: Any
) -> Response:
    """Write the whole list as ``who`` does, at the counter ``version``."""
    body = {
        "contributors": [{"user_id": str(user_id), "kind": kind} for user_id, kind in lines],
        "lock_version": version,
    }
    return api.put(path(stage), headers=who.headers, json=body)


def refusal(response: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("params", {})


def faults(response: Any) -> list[tuple[str, str]]:
    """Give, by field, the pointer and the code of a refusal."""
    return [(field["pointer"], field["code"]) for field in response.json()["fields"]]


def names(body: dict[str, Any]) -> list[str | None]:
    """Give the displayed names of a list, in its order."""
    return [item["display_name"] for item in body["items"]]


def kinds_of(stage: Scene) -> dict[UUID, str]:
    """Read the kinds stored on the project of the scene."""
    with stage.database.transaction() as session:
        rows = session.execute(select(Contributor.user_account_id, Contributor.kind))
        return dict(rows.all())


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_the_creator_of_a_project_is_its_project_manager_and_writes_the_list(
    api: ContractClient, stage: Scene
) -> None:
    first = read(api, stage, stage.manager)
    assert [(item["kind"], item["is_active"]) for item in first["items"]] == [
        (MANAGER, True),
        (CONTRIBUTOR, True),
    ]
    assert first["items"][0]["user_id"] == str(stage.manager.user_id)
    assert first["lock_version"] == 0
    colleague = account(stage.database, "Lucas", "Petit")
    lines = [(stage.manager.user_id, MANAGER), (colleague, CONTRIBUTOR)]
    answer = write(api, stage, stage.manager, lines, 0)
    # The participant was not sent back: the list is written whole, and it is withdrawn.
    assert answer.status_code == 200, answer.text
    assert answer.json()["lock_version"] == 1
    assert names(answer.json()) == ["Camille Martin", "Lucas Petit"]
    assert kinds_of(stage) == {stage.manager.user_id: MANAGER, colleague: CONTRIBUTOR}
    # The listing of the project says the same counter (ContributorList.lock_version).
    assert read(api, stage, stage.manager)["lock_version"] == 1


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_an_account_that_is_no_contributor_neither_opens_the_project_nor_finds_the_list(
    api: ContractClient, stage: Scene
) -> None:
    hidden: tuple[int, str, dict[str, Any]] = (404, "NOT_FOUND", {})
    opened = api.get(f"{PROJECTS}/{stage.project['project_id']}", headers=stage.outsider.headers)
    assert refusal(opened) == hidden
    assert refusal(api.get(path(stage), headers=stage.outsider.headers)) == hidden
    lines = [(stage.manager.user_id, MANAGER)]
    assert refusal(write(api, stage, stage.outsider, lines, 0)) == hidden
    suggested = api.get(f"{path(stage)}/suggestions", headers=stage.outsider.headers)
    assert refusal(suggested) == hidden
    unknown = api.get(f"{PROJECTS}/{uuid4()}/contributors", headers=stage.manager.headers)
    assert refusal(unknown) == hidden
    # Holding every project open is no quality on this one: the list is read, not written.
    assert read(api, stage, stage.reader)["lock_version"] == 0
    refused = write(api, stage, stage.reader, lines, 0)
    assert refusal(refused) == (403, "PERMISSION_MISSING", {"missing_permission": RESCUE[1]})
    assert kinds_of(stage)[stage.manager.user_id] == MANAGER


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_a_participant_opens_the_project_and_reads_the_list_but_cannot_write_it(
    api: ContractClient, stage: Scene
) -> None:
    opened = api.get(f"{PROJECTS}/{stage.project['project_id']}", headers=stage.participant.headers)
    assert opened.status_code == 200
    assert read(api, stage, stage.participant)["lock_version"] == 0
    lines = [(stage.participant.user_id, MANAGER), (stage.manager.user_id, MANAGER)]
    refused = write(api, stage, stage.participant, lines, 0)
    assert refusal(refused) == (
        403,
        "NOT_PROJECT_MANAGER",
        {"missing_condition": "is_project_manager"},
    )
    # Inscribed as a project manager, the participant writes at the next request.
    promoted = write(api, stage, stage.manager, lines, 0)
    assert promoted.status_code == 200
    assert write(api, stage, stage.participant, lines, 1).status_code == 200


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_the_only_project_manager_is_neither_withdrawn_nor_made_a_participant(
    api: ContractClient, stage: Scene
) -> None:
    withdrawn = write(api, stage, stage.manager, [(stage.participant.user_id, CONTRIBUTOR)], 0)
    assert refusal(withdrawn) == (409, "LAST_PROJECT_MANAGER", {})
    both = [(stage.manager.user_id, CONTRIBUTOR), (stage.participant.user_id, CONTRIBUTOR)]
    assert refusal(write(api, stage, stage.manager, both, 0)) == (409, "LAST_PROJECT_MANAGER", {})
    # Nothing was written, not even the counter.
    assert kinds_of(stage)[stage.manager.user_id] == MANAGER
    assert read(api, stage, stage.manager)["lock_version"] == 0
    # Accepted as soon as a second project manager is inscribed, in the same list or before.
    second = [(stage.manager.user_id, CONTRIBUTOR), (stage.participant.user_id, MANAGER)]
    assert write(api, stage, stage.manager, second, 0).status_code == 200
    alone = [(stage.participant.user_id, MANAGER)]
    assert write(api, stage, stage.participant, alone, 1).status_code == 200


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_two_project_managers_each_withdrawing_the_other_leave_one_project_manager(
    api: ContractClient, stage: Scene
) -> None:
    # The list is written under the lock of the project, at the counter read: of two writes that
    # read the same list, the second is refused as stale, and the project keeps a manager.
    inscribe(stage.database, stage, stage.outsider.user_id, MANAGER)
    retirements = [
        (stage.manager, [(stage.manager.user_id, CONTRIBUTOR), (stage.outsider.user_id, MANAGER)]),
        (stage.outsider, [(stage.manager.user_id, MANAGER), (stage.outsider.user_id, CONTRIBUTOR)]),
    ]

    def send(retirement: tuple[Person, list[tuple[UUID, str]]]) -> Any:
        who, lines = retirement
        return write(api, stage, who, lines, 0)

    with ThreadPoolExecutor(2) as pool:
        answers = list(pool.map(send, retirements))
    assert sorted(answer.status_code for answer in answers) == [200, 412]
    stale = next(answer for answer in answers if answer.status_code == 412)
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 1})
    stored = kinds_of(stage)
    assert list(stored.values()).count(MANAGER) == 1


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_a_writer_withdrawn_while_it_waits_for_the_lock_is_judged_on_the_list_as_it_stands(
    api: ContractClient, stage: Scene
) -> None:
    # The quality was read by the evaluation in a transaction of its own: the write reads it again
    # under the lock of the project (WF-ADM-0090). The manager is made a participant while its
    # write waits; its write is refused as a participant's, and writes nothing.
    inscribe(stage.database, stage, stage.outsider.user_id, MANAGER)
    lines = [(stage.manager.user_id, MANAGER), (stage.outsider.user_id, MANAGER)]
    with ThreadPoolExecutor(1) as other, Session(stage.database.engine) as holding:
        holding.execute(
            select(Project.id)
            .where(Project.id == UUID(stage.project["project_id"]))
            .with_for_update()
        )
        writing = other.submit(write, api, stage, stage.manager, lines, 0)
        wait_for_a_lock(stage.database)
        holding.execute(
            update(Contributor)
            .where(Contributor.user_account_id == stage.manager.user_id)
            .values(kind=CONTRIBUTOR)
        )
        holding.commit()
        answer = writing.result(timeout=10)
    assert refusal(answer) == (
        403,
        "NOT_PROJECT_MANAGER",
        {"missing_condition": "is_project_manager"},
    )
    assert kinds_of(stage)[stage.manager.user_id] == CONTRIBUTOR


@pytest.mark.requirement("WF-ADM-0070-A")
def test_a_contributor_deactivated_since_its_inscription_is_listed_and_signalled(
    api: ContractClient, owner: Engine, stage: Scene
) -> None:
    leaver = account(stage.database, "Alix", "Moreau")
    inscribe(stage.database, stage, leaver, CONTRIBUTOR)
    deactivate(owner, leaver)
    body = read(api, stage, stage.manager)
    by_name = {item["display_name"]: item["is_active"] for item in body["items"]}
    assert by_name == {"Camille Martin": True, "Inès Martin": True, "Alix Moreau": False}
    assert [
        item["user_id"] for item in read(api, stage, stage.manager, "is_active=false")["items"]
    ] == [str(leaver)]
    inactive = read(api, stage, stage.manager, "is_active=true")
    assert "Alix Moreau" not in names(inactive)
    # Listed as it was read, it stays through a write that does not change it.
    kept = [(item["user_id"], item["kind"]) for item in body["items"]]
    lines = [(UUID(user_id), kind) for user_id, kind in kept]
    assert write(api, stage, stage.manager, lines, 0).status_code == 200
    assert leaver in kinds_of(stage)


@pytest.mark.requirement("WF-ADM-0070-A")
def test_the_lines_a_deactivated_contributor_wrote_keep_its_name(
    api: ContractClient, owner: Engine, stage: Scene
) -> None:
    deactivate(owner, stage.manager.user_id)
    opened = api.get(f"{PROJECTS}/{stage.project['project_id']}", headers=stage.reader.headers)
    assert opened.status_code == 200
    assert opened.json()["audit"]["created_by"]["display_name"] == "Camille Martin"
    # The list does not remove it: it is signalled.
    listed = read(api, stage, stage.reader)
    first = listed["items"][0]
    assert (first["display_name"], first["is_active"]) == ("Camille Martin", False)


@pytest.mark.requirement("WF-ADM-0070-A")
def test_an_account_that_is_unknown_or_deactivated_is_refused_at_its_line(
    api: ContractClient, owner: Engine, stage: Scene
) -> None:
    leaver = account(stage.database, "Alix", "Moreau")
    inscribe(stage.database, stage, leaver, CONTRIBUTOR)
    deactivate(owner, leaver)
    newcomer = account(stage.database, "Noa", "Roux", active=False)
    lines = [
        (stage.manager.user_id, MANAGER),
        (leaver, MANAGER),
        (newcomer, CONTRIBUTOR),
        (uuid4(), CONTRIBUTOR),
        (stage.manager.user_id, CONTRIBUTOR),
    ]
    refused = write(api, stage, stage.manager, lines, 0)
    assert refused.status_code == 422
    assert faults(refused) == [
        ("/contributors/1/user_id", "USER_INACTIVE"),
        ("/contributors/2/user_id", "USER_INACTIVE"),
        ("/contributors/3/user_id", "UNKNOWN_USER"),
        ("/contributors/4/user_id", "VALIDATION_FAILED"),
    ]
    assert kinds_of(stage)[leaver] == CONTRIBUTOR
    assert read(api, stage, stage.manager)["lock_version"] == 0


def test_an_account_written_twice_is_refused_at_its_repeated_line(
    api: ContractClient, stage: Scene
) -> None:
    # The second kind would silently overwrite the first: the repeated line is refused, the first
    # judged as the others (#2163, ``contributors_account_doubled``).
    colleague = account(stage.database, "Lucas", "Petit")
    lines = [
        (stage.manager.user_id, MANAGER),
        (colleague, CONTRIBUTOR),
        (colleague, MANAGER),
    ]
    refused = write(api, stage, stage.manager, lines, 0)
    assert refused.status_code == 422
    assert refused.json()["code"] == "VALIDATION_FAILED"
    assert faults(refused) == [("/contributors/2/user_id", "VALIDATION_FAILED")]
    assert colleague not in kinds_of(stage)
    assert read(api, stage, stage.manager)["lock_version"] == 0


def test_a_list_of_more_than_five_hundred_lines_is_refused_whole(
    api: ContractClient, stage: Scene
) -> None:
    # The bound of the contract (``maxItems: 500``, #2162): the 501st line refuses the list before
    # any line is judged under the lock; five hundred lines are judged, and refused here only for
    # the accounts the installation has not.
    over = [(stage.manager.user_id, MANAGER)] + [(uuid4(), CONTRIBUTOR) for _ in range(500)]
    refused = write(api, stage, stage.manager, over, 0)
    assert refused.status_code == 422
    body = refused.json()
    assert body["code"] == "VALIDATION_FAILED"
    assert body["fields"] == [
        {"pointer": "/contributors", "code": "VALUE_TOO_LONG", "params": {"max_length": 500}}
    ]
    judged = write(api, stage, stage.manager, over[:500], 0)
    assert judged.status_code == 422
    assert len(faults(judged)) == 499
    assert set(faults(judged)) == {
        (f"/contributors/{row}/user_id", "UNKNOWN_USER") for row in range(1, 500)
    }
    assert read(api, stage, stage.manager)["lock_version"] == 0


def test_the_accounts_of_a_list_are_read_in_bulk_whatever_its_size(
    api: ContractClient, stage: Scene
) -> None:
    # The accounts of the lines are read in bulk (#2167): the statements that read ``user_account``
    # around a write and a reading of the list are as many for 3 lines as for 48. Only the
    # statements on that table are counted, so that no other thread's can make the count vary.
    # Deactivated and anonymised accounts keep their label, as before.
    leaver = account(stage.database, "Alix", "Moreau", active=False)
    forgotten = account(stage.database, "", "", anonymized=True)
    crowd = [account(stage.database, f"Prenom{row}", f"Nom{row}") for row in range(47)]
    statements: list[str] = []

    def count(*caught: Any) -> None:
        statements.append(caught[2])

    def accounts_read(call: Callable[[], Response]) -> tuple[Response, int]:
        statements.clear()
        event.listen(stage.database.engine, "before_cursor_execute", count)
        try:
            answer = call()
        finally:
            event.remove(stage.database.engine, "before_cursor_execute", count)
        reads = [
            each
            for each in statements
            if each.lstrip().upper().startswith("SELECT") and "user_account" in each
        ]
        return answer, len(reads)

    def listing() -> Response:
        return api.get(path(stage), headers=stage.manager.headers)

    # Deactivated and anonymised accounts are inscribed around the service: the write refuses them.
    inscribe(stage.database, stage, leaver, CONTRIBUTOR)
    inscribe(stage.database, stage, forgotten, CONTRIBUTOR)
    listed, few_listed = accounts_read(listing)
    assert listed.status_code == 200, listed.text
    few_items = len(listed.json()["items"])
    items = {item["user_id"]: item for item in listed.json()["items"]}
    assert (items[str(leaver)]["display_name"], items[str(leaver)]["is_active"]) == (
        "Alix Moreau",
        False,
    )
    assert items[str(forgotten)]["is_active"] is False
    assert items[str(stage.manager.user_id)]["is_active"]
    few = [(stage.manager.user_id, MANAGER), (crowd[0], CONTRIBUTOR), (crowd[1], CONTRIBUTOR)]
    written, few_written = accounts_read(
        lambda: write(api, stage, stage.manager, few, listed.json()["lock_version"])
    )
    assert written.status_code == 200, written.text
    assert names(written.json())[0] == "Camille Martin"
    for each in crowd[2:]:
        inscribe(stage.database, stage, each, CONTRIBUTOR)
    listed, many_listed = accounts_read(listing)
    assert len(listed.json()["items"]) == len(crowd) + 1
    assert len(listed.json()["items"]) > few_items
    many = [(stage.manager.user_id, MANAGER), *((each, CONTRIBUTOR) for each in crowd)]
    written, many_written = accounts_read(
        lambda: write(api, stage, stage.manager, many, listed.json()["lock_version"])
    )
    assert written.status_code == 200, written.text
    assert len(written.json()["items"]) == len(many)
    # A floor: a listener that saw nothing would make the two counts equal at zero (#2277).
    assert few_listed >= 1
    assert few_written >= 1
    assert many_written == few_written
    assert many_listed == few_listed


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_a_list_is_refused_stale_or_without_the_counter_it_was_read_with(
    api: ContractClient, stage: Scene
) -> None:
    lines = [(stage.manager.user_id, MANAGER)]
    assert write(api, stage, stage.manager, lines, 0).status_code == 200
    stale = write(api, stage, stage.manager, lines, 0)
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 1})
    for sent in (None, "absent"):
        body: dict[str, Any] = {"contributors": [{"user_id": str(lines[0][0]), "kind": MANAGER}]}
        if sent is None:
            body["lock_version"] = None
        refused = api.put(path(stage), headers=stage.manager.headers, json=body)
        assert refused.status_code == 422
        assert faults(refused) == [("/lock_version", "VALUE_REQUIRED")]
    empty = api.put(
        path(stage), headers=stage.manager.headers, json={"contributors": [], "lock_version": 1}
    )
    assert empty.status_code == 422
    assert faults(empty) == [("/contributors", "VALUE_REQUIRED")]


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_a_filtered_reading_gives_no_counter_so_that_it_is_not_written_back(
    api: ContractClient, stage: Scene
) -> None:
    for query in ("search=martin", "kinds=project_manager", "is_active=true"):
        assert read(api, stage, stage.manager, query)["lock_version"] is None, query
    assert read(api, stage, stage.manager, "sort_by=kind&sort_order=desc")["lock_version"] == 0


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_a_terminal_project_refuses_the_write_of_its_list(
    api: ContractClient, stage: Scene
) -> None:
    put_in_state(stage.owner, stage.project["project_id"], "completed")
    refused = write(api, stage, stage.manager, [(stage.manager.user_id, MANAGER)], 0)
    assert refusal(refused) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "project_not_terminal"},
    )
    assert read(api, stage, stage.manager)["lock_version"] == 0


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_the_list_is_searched_filtered_and_sorted_by_the_server(
    api: ContractClient, owner: Engine, stage: Scene
) -> None:
    ines = account(stage.database, "Inès", "Roux")
    lucas = account(stage.database, "Lucas", "Petit")
    ghost = account(stage.database, "", "", active=False, anonymized=True)
    soren = account(stage.database, "Søren", "Åberg")
    ligature = account(stage.database, "Œdipe", "Łukasz")
    for user_id in (ines, lucas, ghost, soren, ligature):
        inscribe(stage.database, stage, user_id, CONTRIBUTOR)
    # By default, the project managers first, then the names; an anonymised account after the
    # names of its kind, which no name ever finds.
    assert names(read(api, stage, stage.manager)) == [
        "Camille Martin",
        "Inès Martin",
        "Lucas Petit",
        "Inès Roux",
        "Søren Åberg",
        "Œdipe Łukasz",
        None,
    ]
    # A search ignores the case and the accents of the displayed name.
    assert names(read(api, stage, stage.manager, "search=INES")) == ["Inès Martin", "Inès Roux"]
    assert names(read(api, stage, stage.manager, "search=roux")) == ["Inès Roux"]
    # As the contract says: the transliteration of ``unaccent``, ligatures and barred letters.
    assert names(read(api, stage, stage.manager, "search=soren")) == ["Søren Åberg"]
    assert names(read(api, stage, stage.manager, "search=aberg")) == ["Søren Åberg"]
    assert names(read(api, stage, stage.manager, "search=oedipe")) == ["Œdipe Łukasz"]
    assert names(read(api, stage, stage.manager, "search=lukasz")) == ["Œdipe Łukasz"]
    assert names(read(api, stage, stage.manager, "kinds=project_manager")) == ["Camille Martin"]
    assert names(read(api, stage, stage.manager, "sort_by=display_name")) == [
        "Camille Martin",
        "Inès Martin",
        "Inès Roux",
        "Lucas Petit",
        "Søren Åberg",
        "Œdipe Łukasz",
        None,
    ]
    assert names(read(api, stage, stage.manager, "sort_by=display_name&sort_order=desc")) == [
        None,
        "Œdipe Łukasz",
        "Søren Åberg",
        "Lucas Petit",
        "Inès Roux",
        "Inès Martin",
        "Camille Martin",
    ]
    by_kind = read(api, stage, stage.manager, "sort_by=kind&sort_order=desc")
    assert [item["kind"] for item in by_kind["items"]][-1] == MANAGER
    deactivate(owner, lucas)
    by_state = read(api, stage, stage.manager, "sort_by=is_active")
    assert [item["is_active"] for item in by_state["items"]] == [True] * 5 + [False] * 2
    anonymized = [item for item in by_state["items"] if item["display_name"] is None]
    assert [item["is_active"] for item in anonymized] == [False]
    bad = api.get(f"{path(stage)}?kinds=boss", headers=stage.manager.headers)
    assert bad.status_code == 422
    assert faults(bad) == [("/query/kinds", "VALIDATION_FAILED")]


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_the_suggestions_are_empty_while_no_line_employs_a_role(
    api: ContractClient, stage: Scene
) -> None:
    for who in (stage.manager, stage.participant, stage.reader):
        answer = api.get(f"{path(stage)}/suggestions", headers=who.headers)
        assert (answer.status_code, answer.json()) == (200, [])


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_a_project_whose_project_managers_are_all_deactivated_is_rescued_by_a_holder_of_both(
    api: ContractClient, owner: Engine, database: Database, realm: TestRealm, stage: Scene
) -> None:
    rescuer = person(database, realm, *RESCUE, name="Dominique")
    deactivate(owner, stage.manager.user_id)
    successor = stage.participant.user_id
    # The list is read, and its counter given, by the holder of every project.
    assert read(api, stage, rescuer)["lock_version"] == 0
    # A list without an active project manager is refused, the deactivated one kept or not.
    kept = [(stage.manager.user_id, MANAGER), (successor, CONTRIBUTOR)]
    assert refusal(write(api, stage, rescuer, kept, 0)) == (409, "LAST_PROJECT_MANAGER", {})
    rescued = [(stage.manager.user_id, MANAGER), (successor, MANAGER)]
    answer = write(api, stage, rescuer, rescued, 0)
    assert answer.status_code == 200, answer.text
    assert [(item["kind"], item["is_active"]) for item in answer.json()["items"]] == [
        (MANAGER, False),
        (MANAGER, True),
    ]
    assert answer.json()["lock_version"] == 1
    # Once an active project manager is inscribed, the rescue is over: no other entry is opened.
    assert refusal(write(api, stage, rescuer, rescued, 1)) == (
        403,
        "NOT_CONTRIBUTOR",
        {"missing_condition": "is_contributor"},
    )
    assert api.get(path(stage), headers=rescuer.headers).status_code == 200


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_the_rescue_inscribes_a_new_project_manager_absent_from_the_list(
    api: ContractClient, owner: Engine, database: Database, realm: TestRealm, stage: Scene
) -> None:
    rescuer = person(database, realm, *RESCUE, name="Dominique")
    deactivate(owner, stage.manager.user_id)
    newcomer = account(database, "Nora", "Blanc")
    # The participant kept: the rescue removes none (#3988).
    participant = stage.participant.user_id
    lines = [(stage.manager.user_id, MANAGER), (participant, CONTRIBUTOR), (newcomer, MANAGER)]
    answer = write(api, stage, rescuer, lines, 0)
    assert answer.status_code == 200, answer.text
    assert kinds_of(stage) == {
        stage.manager.user_id: MANAGER,
        participant: CONTRIBUTOR,
        newcomer: MANAGER,
    }
    assert answer.json()["lock_version"] == 1


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_the_rescue_is_refused_on_a_terminal_project(
    api: ContractClient, owner: Engine, database: Database, realm: TestRealm, stage: Scene
) -> None:
    rescuer = person(database, realm, *RESCUE, name="Dominique")
    deactivate(owner, stage.manager.user_id)
    put_in_state(owner, stage.project["project_id"], "completed")
    lines = [(stage.manager.user_id, MANAGER), (stage.participant.user_id, MANAGER)]
    assert refusal(write(api, stage, rescuer, lines, 0)) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "project_not_terminal"},
    )
    assert read(api, stage, rescuer)["lock_version"] == 0


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_the_rescue_is_closed_to_the_holder_of_the_settings_without_every_project_open(
    api: ContractClient, owner: Engine, stage: Scene
) -> None:
    deactivate(owner, stage.manager.user_id)
    lines = [(stage.participant.user_id, MANAGER)]
    # An outsider who holds the settings but not every project: the project does not exist for it.
    assert refusal(write(api, stage, stage.outsider, lines, 0)) == (404, "NOT_FOUND", {})


@pytest.mark.requirement("WF-QUA-0040-A")
def test_the_witness_loads_the_contributors_of_its_project_under_the_counter_of_its_example(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    reader = person(witness, realm, "project_settings.read", "all_projects_read")
    value = json.loads((WITNESS / "contributors.json").read_text(encoding="utf-8"))["value"]
    project_id = json.loads((WITNESS / "project.json").read_text(encoding="utf-8"))["value"]
    answer = api.get(f"{PROJECTS}/{project_id['project_id']}/contributors", headers=reader.headers)
    assert answer.status_code == 200
    assert answer.json() == value
    other = api.get(
        f"{PROJECTS}/01926f3a-7c00-7000-8000-000000000002/contributors", headers=reader.headers
    )
    assert other.status_code == 200
    assert other.json() == {"items": [], "lock_version": 0}


EVENTS = "/api/v1/audit-events"
type Inscribed = tuple[str, str, str, str | None]


def managers_inscribed(
    api: ContractClient, database: Database, realm: TestRealm, stage: Scene
) -> list[Inscribed]:
    """Read, as an auditor, the inscriptions of the project managers of the project, oldest first.

    Each as its action, its author, the account of the contributor and its label.
    """
    auditor = person(database, realm, "audit_log.read", name="Alix")
    actions = "project_manager_add,project_manager_remove,project_manager_change"
    query = f"project_id={stage.project['project_id']}&actions={actions}&sort_order=asc"
    answer = api.get(f"{EVENTS}?{query}", headers=auditor.headers)
    assert answer.status_code == 200, answer.text
    found: list[Inscribed] = []
    for entry in answer.json()["items"]:
        assert entry["object"]["kind"] == "contributor"
        assert entry["object"]["revision"] is None
        assert entry["project"]["project_id"] == stage.project["project_id"]
        assert entry["params"] == {}
        audited = entry["object"]
        found.append(
            (entry["action"], entry["actor"]["user_id"], audited["object_id"], audited["label"])
        )
    return found


def shown(api: ContractClient, stage: Scene) -> dict[str, str | None]:
    """Give the names the list shows, by account."""
    items = read(api, stage, stage.manager)["items"]
    return {item["user_id"]: item["display_name"] for item in items}


@pytest.mark.requirement("WF-SEC-0030-A")
@pytest.mark.requirement("WF-PRJ-0060-A")
def test_the_registration_the_change_and_the_removal_of_a_project_manager_are_inscribed(
    api: ContractClient, database: Database, realm: TestRealm, stage: Scene
) -> None:
    # « L'inscription d'un chef de projet figure au journal d'audit » ; its removal and its change
    # of capacity too (WF-SEC-0030), one inscription each, by its author. A participant
    # registered or removed is none.
    newcomer = account(database, "Nora", "Blanc")
    helper = account(database, "Sacha", "Lefèvre")
    manager, participant = stage.manager.user_id, stage.participant.user_id
    first = [(manager, MANAGER), (participant, MANAGER), (newcomer, MANAGER)]
    first.append((helper, CONTRIBUTOR))
    assert write(api, stage, stage.manager, first, 0).status_code == 200
    names = shown(api, stage)
    second = [(manager, MANAGER), (participant, CONTRIBUTOR)]
    assert write(api, stage, stage.manager, second, 1).status_code == 200
    by = str(manager)
    assert managers_inscribed(api, database, realm, stage) == [
        ("project_manager_change", by, str(participant), names[str(participant)]),
        ("project_manager_add", by, str(newcomer), "Nora Blanc"),
        ("project_manager_change", by, str(participant), names[str(participant)]),
        ("project_manager_remove", by, str(newcomer), "Nora Blanc"),
    ]


# The one inscription of the creator of a project: its creation, by it, and no registration of a
# project manager (``project_manager_add``), though the creation makes it one (DECISIONS.md,
# US-2980/L1): no test walks the actions of the journal, and one that would names this exemption.
CREATOR_INSCRIBED = "project_create"


@pytest.mark.requirement("WF-SEC-0030-A")
def test_the_creator_of_a_project_is_inscribed_by_its_creation_and_not_as_a_project_manager(
    api: ContractClient, database: Database, realm: TestRealm, stage: Scene
) -> None:
    assert managers_inscribed(api, database, realm, stage) == []
    auditor = person(database, realm, "audit_log.read", name="Camille")
    query = f"project_id={stage.project['project_id']}&actions={CREATOR_INSCRIBED}"
    answer = api.get(f"{EVENTS}?{query}", headers=auditor.headers)
    assert answer.status_code == 200, answer.text
    assert [(entry["action"], entry["actor"]["user_id"]) for entry in answer.json()["items"]] == [
        (CREATOR_INSCRIBED, str(stage.manager.user_id))
    ]


@pytest.mark.requirement("WF-SEC-0030-A")
@pytest.mark.parametrize("first", ["listing", "anonymizing"])
def test_a_project_manager_withdrawn_while_its_account_is_anonymised_is_inscribed_without_its_name(
    api: ContractClient, stage: Scene, first: str
) -> None:
    # The name of a contributor is read under a share lock on its account (``inscribed_names``):
    # the list written first, its inscription is forgotten by the anonymisation that waited for
    # it; the anonymisation first, the list that waited reads the account anonymised, and
    # inscribes no name. Either way the journal keeps no name of an anonymised account.
    withdrawn = account(stage.database, "Nora", "Blanc")
    inscribe(stage.database, stage, withdrawn, MANAGER)
    deactivate(stage.owner, withdrawn)
    with stage.database.transaction() as session:
        counter = session.scalars(
            select(UserAccount.lock_version).where(UserAccount.id == withdrawn)
        ).one()
    entries = (
        ContributorEntry(stage.manager.user_id, MANAGER),
        ContributorEntry(stage.participant.user_id, CONTRIBUTOR),
    )
    listed = ContributorsToWrite(entries, read(api, stage, stage.manager)["lock_version"])
    author = stage.manager.user_id
    writes: dict[str, Callable[[Session], object]] = {
        "listing": lambda session: set_contributors(
            session,
            UUID(stage.project["project_id"]),
            listed,
            Viewer(author, ()),
            Act(author, utc_now()),
        ),
        "anonymizing": lambda session: anonymize_account(
            session, withdrawn, counter, Act(author, utc_now())
        ),
    }
    [second] = [name for name in writes if name != first]

    def waiting() -> None:
        with logging_context(correlation_id=second), stage.database.transaction() as session:
            writes[second](session)

    with ThreadPoolExecutor(1) as other:
        with logging_context(correlation_id=first), stage.database.transaction() as session:
            writes[first](session)
            sent = other.submit(waiting)
            wait_for_a_lock(stage.database)
            assert not sent.done()
        sent.result(timeout=10)
    with stage.database.transaction() as session:
        inscribed = session.execute(
            select(AuditEntry.action, AuditEntry.object_label).where(
                AuditEntry.object_kind == "contributor", AuditEntry.object_id == withdrawn
            )
        ).all()
        anonymized = session.scalars(
            select(UserAccount.anonymized_at).where(UserAccount.id == withdrawn)
        ).one()
    assert [tuple(row) for row in inscribed] == [("project_manager_remove", None)]
    assert anonymized is not None


def witness_value(name: str) -> dict[str, Any]:
    """Give the value of an example of the witness, by its name."""
    return json.loads((WITNESS / f"{name}.json").read_text(encoding="utf-8"))["value"]


def written(items: list[dict[str, Any]]) -> list[ContributorEntry]:
    """Give the lines of a list of the contract as the service writes them."""
    return [ContributorEntry(UUID(item["user_id"]), item["kind"]) for item in items]


def held_kinds(items: list[dict[str, Any]]) -> dict[UUID, Any]:
    """Give the kind of each account of a list of the contract, as the service reads it."""
    return {UUID(item["user_id"]): item["kind"] for item in items}


def heading(name: str) -> tuple[str, UUID]:
    """Give the inscription at the head of an example of the journal: its action, its account."""
    head = witness_value(f"audit_events_manager_{name}")["items"][0]
    assert head["object"]["kind"] == "contributor"
    return head["action"], UUID(head["object"]["object_id"])


@pytest.mark.requirement("WF-SEC-0030-A")
def test_the_inscriptions_of_the_examples_are_those_the_service_makes_of_their_lists() -> None:
    # The rule of the inscriptions is written twice, by the service (``changes``) and by the
    # generator of the examples (``wftools.mockauditmanagers.changes``), which the back cannot
    # import: the service plays here the lists of the witness, and finds the action and the
    # account at the head of each of the three examples. The list the rescue writes and the one
    # that follows ``contributors_set`` are no example: the list read, the account of the example
    # added as project manager, or withdrawn.
    before, after = (
        witness_value("contributors")["items"],
        witness_value("contributors_set")["items"],
    )
    assert changes(held_kinds(before), written(after)) == [heading("changed")]
    action, rescued = heading("added")
    read = witness_value("contributors_without_active_manager")["items"]
    rescue = [*read, {"user_id": str(rescued), "kind": MANAGER}]
    assert rescued not in held_kinds(read)
    assert changes(held_kinds(read), written(rescue)) == [(action, rescued)]
    action, withdrawn = heading("removed")
    kept = [item for item in after if UUID(item["user_id"]) != withdrawn]
    assert len(kept) == len(after) - 1
    assert changes(held_kinds(after), written(kept)) == [(action, withdrawn)]
    assert [action for action, _ in map(heading, ("changed", "added", "removed"))] == [
        "project_manager_change",
        "project_manager_add",
        "project_manager_remove",
    ]


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_after_a_rescue_the_journal_presents_the_project_manager_it_inscribed(
    api: ContractClient, owner: Engine, database: Database, realm: TestRealm, stage: Scene
) -> None:
    # The project manager a non-contributor inscribes, when the last one is deactivated, is
    # inscribed in the journal by the rescuer, named by the account it registered.
    rescuer = person(database, realm, *RESCUE, name="Dominique")
    deactivate(owner, stage.manager.user_id)
    newcomer = account(database, "Nora", "Blanc")
    lines = [
        (stage.manager.user_id, MANAGER),
        (stage.participant.user_id, CONTRIBUTOR),
        (newcomer, MANAGER),
    ]
    answer = write(api, stage, rescuer, lines, 0)
    assert answer.status_code == 200, answer.text
    assert managers_inscribed(api, database, realm, stage) == [
        ("project_manager_add", str(rescuer.user_id), str(newcomer), "Nora Blanc")
    ]


@pytest.mark.requirement("WF-PRJ-0060-A")
@pytest.mark.parametrize(
    "beyond", ["participant_removed", "manager_demoted", "participant_added", "stale_counter"]
)
def test_the_rescuer_neither_removes_a_participant_nor_changes_another_line(
    api: ContractClient, database: Database, realm: TestRealm, stage: Scene, beyond: str
) -> None:
    # « Un non-contributeur qui inscrit un chef de projet sur un projet dont le dernier est
    # désactivé ne peut retirer aucun participant », nor change or add any other line than a
    # project manager (#3988): 403, nothing written, nothing inscribed. The list it judges is the
    # one at the counter sent: a counter gone stale is refused first, 412 (DECISIONS.md).
    rescuer = person(database, realm, *RESCUE, name="Dominique")
    newcomer = account(database, "Nora", "Blanc")
    other = account(database, "Sacha", "Lefèvre")
    manager, participant = stage.manager.user_id, stage.participant.user_id
    counter = 0
    if beyond == "stale_counter":
        changed = [(manager, MANAGER), (participant, CONTRIBUTOR), (other, CONTRIBUTOR)]
        assert write(api, stage, stage.manager, changed, 0).status_code == 200
        counter = 1
    deactivate(stage.owner, manager)
    lines = {
        "participant_removed": [(manager, MANAGER), (newcomer, MANAGER)],
        "manager_demoted": [
            (manager, CONTRIBUTOR),
            (participant, CONTRIBUTOR),
            (newcomer, MANAGER),
        ],
        "participant_added": [
            (manager, MANAGER),
            (participant, CONTRIBUTOR),
            (newcomer, MANAGER),
            (other, CONTRIBUTOR),
        ],
        "stale_counter": [(manager, MANAGER), (newcomer, MANAGER)],
    }[beyond]
    before = kinds_of(stage)
    assert refusal(write(api, stage, rescuer, lines, 0)) == (
        (412, "STALE_LOCK_VERSION", {"expected_lock_version": 1})
        if beyond == "stale_counter"
        else (403, "NOT_CONTRIBUTOR", {"missing_condition": "is_contributor"})
    )
    assert kinds_of(stage) == before
    assert read(api, stage, rescuer)["lock_version"] == counter
    assert managers_inscribed(api, database, realm, stage) == []


type Stamps = tuple[datetime, UUID | None, datetime, UUID | None]


def stamps(database: Database) -> dict[UUID, Stamps]:
    """Read the columns of audit of each line of the list, by account."""
    with database.transaction() as session:
        rows = session.execute(
            select(
                Contributor.user_account_id,
                Contributor.created_at,
                Contributor.created_by,
                Contributor.updated_at,
                Contributor.updated_by,
            )
        )
        return {
            user_id: (created_at, created_by, updated_at, updated_by)
            for user_id, created_at, created_by, updated_at, updated_by in rows
        }


@pytest.mark.requirement("WF-DAT-0070-A")
def test_each_line_of_the_list_bears_the_moment_and_the_author_of_its_write(
    api: ContractClient, database: Database, stage: Scene
) -> None:
    # The creator inscribed by the creation, a line added and a line changed: each its dates and
    # its authors; a line unchanged keeps its own.
    newcomer = account(database, "Nora", "Blanc")
    manager, participant = stage.manager.user_id, stage.participant.user_id
    before = stamps(database)
    assert before[manager][1] == before[manager][3] == manager
    lines = [(manager, MANAGER), (participant, MANAGER), (newcomer, CONTRIBUTOR)]
    assert write(api, stage, stage.manager, lines, 0).status_code == 200
    after = stamps(database)
    assert after[manager] == before[manager]
    created, created_by, updated, updated_by = after[newcomer]
    assert (created_by, updated_by) == (manager, manager)
    assert created == updated > before[manager][2]
    assert after[participant][:2] == before[participant][:2]
    assert after[participant][2:] == (updated, manager)
