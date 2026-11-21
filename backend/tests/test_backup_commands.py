# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The commands a backup announces are served, and refused with the condition they lack (#2241).

``retainBackup`` marks a backup to keep or releases it, and the commands ``retain`` and ``release``
a backup announces are available exactly when it does; ``startBackup``, ``downloadBackup`` and
``startRestore`` answer 409 ``STATE_FORBIDS_OPERATION``, ``params.missing_condition`` naming the
first condition the command of the backup lacks (``backup_verified``, ``no_backup_running``,
``no_restore_running``), and queue or transmit nothing (US-2910/L2). Each person is an account
written around the service; every answer is checked against the contract.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from access_rows import account, role
from backup_rows import Row, days, recorded
from installations import written_task
from realm import KEY, TestRealm
from sqlalchemy import func, select
from support import ContractClient, bearer

from waterfall.core.backups.tables import Backup
from waterfall.platform.tasks import BackgroundTask

if TYPE_CHECKING:
    from waterfall.platform.database import Database

pytestmark = pytest.mark.story("US-2910")

BACKUPS = "/api/v1/backups"
RESTORES = "/api/v1/restores"
READ = "backups.read"
WRITE = "backups.write"
RESTORE = "platform_restore"
CONDITIONS = {
    "backup_running": "no_backup_running",
    "restore_running": "no_restore_running",
    "unverified": "backup_verified",
}

type Person = Callable[..., dict[str, str]]


@pytest.fixture
def person(database: Database, realm: TestRealm) -> Person:
    """Give a maker of accounts, each holding a role of the permissions given: its header."""

    def make(*permissions: str) -> dict[str, str]:
        subject = f"subject-{uuid4()}"
        held = role(database, f"Rôle {uuid4().hex[:8]}", permissions=permissions)
        account(database, "Martin", uuid4().hex[:8], roles=(held,), idp_subject=subject)
        return bearer(realm.token(subject, KEY))

    return make


def command(body: dict[str, Any], name: str) -> dict[str, Any]:
    """Give a command of the backup a body describes, or fail if it is not announced."""
    [found] = [each for each in body["available_commands"] if each["command"] == name]
    return found


def refused_as(response: Any, condition: str) -> None:
    """Check a refusal: 409 ``STATE_FORBIDS_OPERATION``, the condition it lacks named."""
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "STATE_FORBIDS_OPERATION"
    assert response.json()["params"] == {"missing_condition": condition}


@pytest.mark.requirement("WF-ADM-0170-A")
def test_a_backup_marked_to_keep_is_released_and_marked_again_by_retain_backup(
    api: ContractClient, database: Database, person: Person
) -> None:
    # « Une sauvegarde marquée survit à la rotation. » : the mark is set by ``retainBackup``, and
    # the backup announces the command that changes it back, ``release``, then ``retain`` again.
    backup_id = recorded(database, days(1))
    keeper = person(READ, WRITE)
    path = f"{BACKUPS}/{backup_id}"
    assert command(api.get(path, headers=keeper).json(), "retain")["is_available"]
    marked = api.patch(path, headers=keeper, json={"is_retained": True})
    assert marked.status_code == 200
    assert marked.json()["is_retained"] is True
    assert command(marked.json(), "release")["is_available"]
    released = api.patch(path, headers=keeper, json={"is_retained": False})
    assert released.status_code == 200
    assert released.json()["is_retained"] is False
    assert command(released.json(), "retain")["is_available"]
    with database.transaction() as session:
        assert session.get_one(Backup, backup_id).is_retained is False


@pytest.mark.requirement("WF-ADM-0170-A")
def test_marking_a_backup_marked_already_or_released_already_changes_nothing(
    api: ContractClient, database: Database, person: Person
) -> None:
    # The mark sets the state intended, without a counter: asked twice, it gives the same state.
    backup_id = recorded(database, days(1), Row(is_retained=True))
    keeper = person(READ, WRITE)
    again = api.patch(f"{BACKUPS}/{backup_id}", headers=keeper, json={"is_retained": True})
    assert (again.status_code, again.json()["is_retained"]) == (200, True)


def test_a_backup_is_marked_only_under_the_permission_to_change_the_backups_and_if_it_exists(
    api: ContractClient, database: Database, person: Person
) -> None:
    backup_id = recorded(database, days(1))
    path = f"{BACKUPS}/{backup_id}"
    refused = api.patch(path, headers=person(READ), json={"is_retained": True})
    assert (refused.status_code, refused.json()["params"]) == (403, {"missing_permission": WRITE})
    unknown = api.patch(
        f"{BACKUPS}/{uuid4()}", headers=person(READ, WRITE), json={"is_retained": True}
    )
    assert unknown.status_code == 404
    malformed = api.patch(path, headers=person(READ, WRITE), json={})
    assert malformed.status_code == 422
    with database.transaction() as session:
        assert session.get_one(Backup, backup_id).is_retained is False


@pytest.mark.requirement("WF-ADM-0160-A")
def test_marking_a_backup_while_a_restoration_runs_is_refused_as_the_command_says_it_in_advance(
    api: ContractClient, database: Database, person: Person
) -> None:
    # The command is announced unavailable, ``no_restore_running`` missing; asked all the same, it
    # is refused with that condition and nothing is written.
    backup_id = recorded(database, days(1), Row(is_retained=True))
    written_task(database, "restore", "running")
    keeper = person(READ, WRITE)
    path = f"{BACKUPS}/{backup_id}"
    announced = command(api.get(path, headers=keeper).json(), "release")
    assert (announced["is_available"], announced["missing_conditions"]) == (
        False,
        [CONDITIONS["restore_running"]],
    )
    refused_as(
        api.patch(path, headers=keeper, json={"is_retained": False}), CONDITIONS["restore_running"]
    )
    with database.transaction() as session:
        assert session.get_one(Backup, backup_id).is_retained is True


@pytest.mark.requirement("WF-ADM-0150-A")
@pytest.mark.parametrize("state", ["backup_running", "restore_running"])
def test_a_backup_started_while_another_or_a_restoration_runs_is_refused_and_queues_nothing(
    api: ContractClient, database: Database, person: Person, state: str
) -> None:
    # « Only one at a time »: the condition that lacks is named, the task queued stays alone.
    written_task(database, "backup" if state == "backup_running" else "restore", "running")
    refused_as(api.post(BACKUPS, headers=person(WRITE)), CONDITIONS[state])
    with database.transaction() as session:
        kinds = list(session.scalars(select(BackgroundTask.kind)))
    assert kinds == ["backup" if state == "backup_running" else "restore"]


@pytest.mark.requirement("WF-ADM-0150-A")
def test_a_backup_awaiting_its_verification_does_not_refuse_another_one(
    api: ContractClient, database: Database, person: Person
) -> None:
    # A backup runs from its queuing to the production of its file: one whose task has ended,
    # its verification pending, withholds nothing.
    recorded(database, days(1), Row(verification="pending"))
    started = api.post(BACKUPS, headers=person(WRITE))
    assert started.status_code == 202
    with database.transaction() as session:
        count = session.scalar(select(func.count()).where(BackgroundTask.kind == "backup"))
    assert count == 2


@pytest.mark.requirement("WF-ADM-0150-A")
@pytest.mark.parametrize("verification", ["pending", "failed"])
def test_a_backup_whose_verification_has_not_passed_is_not_downloaded_and_says_so_in_advance(
    api: ContractClient, database: Database, person: Person, verification: str
) -> None:
    backup_id = recorded(database, days(1), Row(verification=verification))
    keeper = person(READ, WRITE)
    path = f"{BACKUPS}/{backup_id}"
    announced = command(api.get(path, headers=keeper).json(), "download")
    assert (announced["is_available"], announced["missing_conditions"]) == (
        False,
        [CONDITIONS["unverified"]],
    )
    refused_as(api.get(f"{path}/content", headers=keeper), CONDITIONS["unverified"])


def asked(backup_id: UUID, database: Database) -> dict[str, object]:
    """Ask for the restoration of a backup of the list, confirmed with its date."""
    with database.transaction() as session:
        taken_at = session.get_one(Backup, backup_id).taken_at
    return {
        "backup_id": str(backup_id),
        "confirmed": True,
        "acknowledged_backup_taken_at": taken_at.isoformat(),
    }


@pytest.mark.requirement("WF-ADM-0160-A")
@pytest.mark.parametrize(
    ("state", "verification"),
    [
        ("unverified", "failed"),
        ("unverified", "pending"),
        ("backup_running", "passed"),
        ("restore_running", "passed"),
    ],
)
def test_a_restoration_the_command_says_unavailable_is_refused_with_the_condition_it_lacks(
    api: ContractClient, database: Database, person: Person, state: str, verification: str
) -> None:
    # The condition the ``restore`` command lists first is the one the refusal names, and it is the
    # one announced: the two are the same definition.
    backup_id = recorded(database, days(1), Row(verification=verification))
    if state != "unverified":
        written_task(database, "backup" if state == "backup_running" else "restore", "running")
    restorer = person(READ, RESTORE)
    announced = command(api.get(f"{BACKUPS}/{backup_id}", headers=restorer).json(), "restore")
    assert not announced["is_available"]
    assert announced["missing_conditions"][0] == CONDITIONS[state]
    refused_as(
        api.post(RESTORES, headers=restorer, json=asked(backup_id, database)), CONDITIONS[state]
    )
    with database.transaction() as session:
        queued = session.scalar(select(func.count()).where(BackgroundTask.kind == "restore"))
    assert queued == (1 if state == "restore_running" else 0)


@pytest.mark.requirement("WF-ADM-0160-A")
def test_a_restoration_while_another_is_queued_is_refused_naming_the_restoration_running(
    api: ContractClient, database: Database, person: Person
) -> None:
    # A restoration asked while another is queued or running: ``no_restore_running``, as the
    # contract describes it, where the refusal named no condition before (#1035).
    backup_id = recorded(database, days(1))
    written_task(database, "restore", "queued")
    refused_as(
        api.post(RESTORES, headers=person(READ, RESTORE), json=asked(backup_id, database)),
        CONDITIONS["restore_running"],
    )
