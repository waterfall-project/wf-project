# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The writes of the roles in the core: the guard of the last administrator, the predefined roles.

What the API does not reach here: two writes at once, the code and the parameters a refusal of
the guard takes for the write that runs under it, a permission outside the catalogue, the roles
the bootstrap creates, and a text that holds a NUL anywhere in a model of the contract.
"""

import json
import threading
from uuid import UUID

import pytest
from access_rows import ADMINISTRATION, DAY, holder, role
from pydantic import ValidationError
from sqlalchemy import select, text, update
from support import CONTRACT

from waterfall.api.contract.base import NUL_FAULT, nul_path
from waterfall.api.contract.models import AccessRoleWrite, Description, DisplayPreferences
from waterfall.core.access_roles.interface import (
    LAST_ADMINISTRATOR,
    Act,
    RoleWrite,
    create_role,
    guard_last_administrator,
    predefined_roles,
    read_role,
    update_role,
)
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import AuditEntry
from waterfall.platform.database import Database
from waterfall.platform.errors import ConflictError, UnprocessableError
from waterfall.platform.logs import logging_context

CORRELATION = "test-access-roles-guard"
# The example of the contract that gives the roles of an installation, the three predefined ones.
WITNESS = CONTRACT.parents[2] / "fixtures" / "api" / "access_roles.json"
# The platform writes, as the bootstrap does.
PLATFORM = Act(None, DAY)
# How long a test waits for a transaction to queue on the lock of the rule.
QUEUED_WITHIN = 10.0


def administration_of(database: Database, role_id: UUID) -> set[str]:
    """Give the permissions of administration that a role grants."""
    with database.transaction() as session:
        return set(read_role(session, role_id).permissions) & set(ADMINISTRATION)


def waits_on_an_advisory_lock(database: Database) -> bool:
    """Tell whether a transaction waits for an advisory lock, within a few seconds."""
    query = text("SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND NOT granted")
    waited = threading.Event()
    for _ in range(int(QUEUED_WITHIN * 20)):
        with database.engine.connect() as connection:
            if connection.scalar(query):
                return True
        waited.wait(0.05)
    return False


def test_two_writes_that_each_take_one_of_the_last_two_administrators_do_not_both_pass(
    database: Database,
) -> None:
    # Each of two roles makes one administrator; each write withdraws one of them. Alone, each
    # would pass, a second administrator remaining. The second write queues on the lock of the
    # rule, reads under it the first one committed, and is refused: one administrator remains.
    first = role(database, "Direction", permissions=ADMINISTRATION, holders=(holder(database),))
    second = role(
        database, "Administration", permissions=ADMINISTRATION, holders=(holder(database),)
    )
    refusals: list[str] = []

    def withdraw_second() -> None:
        try:
            with logging_context(correlation_id=CORRELATION), database.transaction() as session:
                update_role(session, second, RoleWrite("Administration", []), 0, PLATFORM)
        except ConflictError as refusal:
            refusals.append(refusal.code)

    concurrent = threading.Thread(target=withdraw_second)
    with logging_context(correlation_id=CORRELATION), database.transaction() as session:
        update_role(session, first, RoleWrite("Direction", []), 0, PLATFORM)
        concurrent.start()
        # Without the lock, the second write would not wait: it would decide on the first not
        # yet committed, and pass too.
        queued = waits_on_an_advisory_lock(database)
    concurrent.join(QUEUED_WITHIN)
    assert queued
    assert not concurrent.is_alive()
    assert refusals == [LAST_ADMINISTRATOR]
    assert administration_of(database, first) == set()
    assert administration_of(database, second) == set(ADMINISTRATION)


@pytest.mark.requirement("WF-ADM-0120-A")
def test_the_guard_refuses_with_the_code_of_the_write_it_guards_and_nothing_is_written(
    database: Database,
) -> None:
    # The deactivation of an account, which its command says in advance, is refused by its own
    # code and parameters (US-0360): the guard takes them from the write it runs.
    administrator = holder(database)
    role(database, "Direction", permissions=ADMINISTRATION, holders=(administrator,))
    with (
        pytest.raises(ConflictError) as raised,
        logging_context(correlation_id=CORRELATION),
        database.transaction() as session,
        guard_last_administrator(
            session, "STATE_FORBIDS_OPERATION", {"missing_condition": "last_administrator"}
        ),
    ):
        session.execute(
            update(UserAccount).where(UserAccount.id == administrator).values(state="deactivated")
        )
    assert (raised.value.code, raised.value.params) == (
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "last_administrator"},
    )
    with database.transaction() as session:
        state = session.scalar(select(UserAccount.state).where(UserAccount.id == administrator))
    assert state == "active"


def test_an_installation_without_administrator_is_not_refused_for_having_none(
    database: Database,
) -> None:
    # Before its bootstrap, an installation has no administrator: a write leaves it none, as it
    # found it, and is not refused for it.
    held = role(database, "Direction", permissions=("users.write",), holders=(holder(database),))
    with logging_context(correlation_id=CORRELATION), database.transaction() as session:
        changed = update_role(session, held, RoleWrite("Direction", []), 0, PLATFORM)
    assert (changed.permissions, changed.lock_version) == ((), 1)


def test_a_permission_outside_the_catalogue_is_refused_by_the_core_too(database: Database) -> None:
    # The API refuses it first, by the enumeration of the contract; the core does not trust it.
    with (
        pytest.raises(UnprocessableError) as raised,
        logging_context(correlation_id=CORRELATION),
        database.transaction() as session,
    ):
        create_role(session, RoleWrite("Rapports", ["planning.read", "reports.read"]), PLATFORM)
    assert [(field.pointer, field.code) for field in raised.value.fields] == [
        ("/permissions/1", "VALIDATION_FAILED")
    ]


def test_the_predefined_roles_are_those_of_the_example_of_the_contract() -> None:
    # The administrator reads the journal of audit (WF-ADM-0100 revised); the bootstrap gives
    # this description to the installation, in its default language.
    witness = json.loads(WITNESS.read_text(encoding="utf-8"))["value"]
    delivered = {
        entry["label"]: tuple(entry["permissions"]) for entry in witness if entry["is_predefined"]
    }
    described = predefined_roles("fr")
    assert {entry.label: entry.permissions for entry in described} == delivered
    assert "audit_log.read" in next(e for e in described if e.key == "administrator").permissions
    assert [entry.label for entry in predefined_roles("en")] == [
        "Administrator",
        "Project manager",
        "Manager",
    ]


def test_the_platform_creates_the_predefined_roles_and_inscribes_them_as_itself(
    database: Database,
) -> None:
    with logging_context(correlation_id=CORRELATION), database.transaction() as session:
        created = [
            create_role(
                session, RoleWrite(entry.label, entry.permissions, is_predefined=True), PLATFORM
            )
            for entry in predefined_roles("fr")
        ]
    assert [(view.is_predefined, view.created_by) for view in created] == [(True, None)] * 3
    assert [view.permissions for view in created] == [
        entry.permissions for entry in predefined_roles("fr")
    ]
    with database.transaction() as session:
        inscribed = session.execute(
            select(AuditEntry.action, AuditEntry.actor_user_id, AuditEntry.correlation_id)
        ).all()
    assert [tuple(row) for row in inscribed] == [("access_role_create", None, CORRELATION)] * 3


@pytest.mark.parametrize(
    ("value", "path"),
    [
        ("Chif\x00freur", ()),
        (["planning.read", "\x00"], (1,)),
        ({"widths": {"label\x00": 120}}, ("widths",)),
        ({"widths": {"label": "\x00"}}, ("widths", "label")),
        ({"sets": {"\x00"}}, ("sets",)),
        (Description("Chif\x00freur"), ()),
        ("Chiffreur", None),
        ([1, None, True, {"label": ["Chiffreur"]}], None),
    ],
)
def test_a_nul_is_found_at_any_depth_of_a_value_and_where_it_lies(
    value: object, path: tuple[int | str, ...] | None
) -> None:
    assert nul_path(value) == path


@pytest.mark.parametrize(
    ("model", "body", "location"),
    [
        (AccessRoleWrite, {"label": "Chif\x00freur", "permissions": []}, ("label",)),
        # A nested model refuses it at its own field, under the field that holds it.
        (
            DisplayPreferences,
            {"grids": {"tasks": {"filters": {"label": "\x00"}}}},
            ("grids", "tasks", "filters"),
        ),
        (DisplayPreferences, {"grids": {"t\x00": None}}, ("grids",)),
    ],
)
def test_every_model_of_the_contract_refuses_a_nul_at_its_field(
    model: type[AccessRoleWrite | DisplayPreferences],
    body: dict[str, object],
    location: tuple[str, ...],
) -> None:
    with pytest.raises(ValidationError) as raised:
        model.model_validate(body)
    assert [(fault["type"], fault["loc"]) for fault in raised.value.errors()] == [
        (NUL_FAULT, location)
    ]
