# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The journal of audit: an action inscribed in its transaction, and no way to change it after.

The refusals are tried as the service meets them — by a role of the service, the one the tests
connect as — and as the owner of the tables, whom only the trigger stops (WF-SEC-0030).
"""

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from openapi_core import OpenAPI
from sqlalchemy import Engine, insert, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from support import operations, raw_account, service_role

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.api.contract import models
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import (
    ACTIONS,
    OBJECT_KINDS,
    AuditActor,
    AuditEntry,
    AuditError,
    AuditObject,
    AuditProject,
    AuditRevision,
    Inscription,
    forget_account,
    record,
)
from waterfall.platform.database import Base, Database
from waterfall.platform.logs import logging_context

NOON = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
CORRELATION = "req-3f2a.9_b"
CLAIRE = AuditActor(uuid4(), "Claire Martin")


def role_created(**changes: Any) -> Inscription:
    """Give the inscription of the creation of a role by Claire, with the changes asked for."""
    created = Inscription(
        action="access_role_create",
        actor=CLAIRE,
        audited=AuditObject("access_role", uuid4(), "Auditeur"),
        occurred_at=NOON,
        params={"permissions": ["audit_log.read"], "is_predefined": False},
    )
    return replace(created, **changes)


def inscribe(database: Database, inscription: Inscription) -> UUID:
    """Inscribe an action in a transaction of its own, under the correlation of a request."""
    with logging_context(correlation_id=CORRELATION), database.transaction() as session:
        return record(session, inscription)


def hold_account(database: Database, user_id: UUID, *, is_anonymized: bool) -> None:
    """Write by hand the account the journal names, anonymised or not."""
    forgotten = dict.fromkeys(("last_name", "first_name", "email"))
    anonymized = {**forgotten, "anonymized_at": NOON, "state": "deactivated"}
    row = raw_account(id=user_id, email=f"{user_id.hex}@example.org")
    if is_anonymized:
        row.update(anonymized)
    with database.engine.begin() as connection:
        connection.execute(insert(UserAccount).values(**row))


def read(database: Database, identifier: UUID) -> AuditEntry:
    """Read an inscription back."""
    with database.transaction() as session:
        return session.execute(select(AuditEntry).where(AuditEntry.id == identifier)).scalar_one()


def count(database: Database) -> int:
    """Count the inscriptions of the journal."""
    with database.engine.connect() as connection:
        return connection.execute(text("SELECT count(*) FROM audit_entry")).scalar_one()


def test_an_action_is_inscribed_with_its_author_its_object_and_the_correlation_of_its_request(
    database: Database,
) -> None:
    audited = AuditObject("cost_structure", uuid4(), "Avenant 1", AuditRevision(uuid4(), None))
    project = AuditProject(uuid4(), "PRJ-001", "Modernisation du poste de commande")
    identifier = inscribe(database, role_created(audited=audited, project=project))
    entry = read(database, identifier)
    assert (entry.occurred_at, entry.actor_user_id, entry.actor_display_name) == (
        NOON,
        CLAIRE.user_id,
        "Claire Martin",
    )
    assert (entry.action, entry.object_kind, entry.object_id, entry.object_label) == (
        "access_role_create",
        "cost_structure",
        audited.object_id,
        "Avenant 1",
    )
    assert audited.revision is not None
    assert (entry.object_revision_id, entry.object_revision_label) == (
        audited.revision.revision_id,
        None,
    )
    assert (entry.project_id, entry.project_code, entry.project_label) == (
        project.project_id,
        "PRJ-001",
        "Modernisation du poste de commande",
    )
    assert entry.params == {"permissions": ["audit_log.read"], "is_predefined": False}
    assert entry.correlation_id == CORRELATION


def test_what_the_platform_does_by_itself_is_inscribed_without_an_account(
    database: Database,
) -> None:
    backup = AuditObject("backup", uuid4(), None)
    inscription = role_created(audited=backup, action="backup", actor=None, params={})
    entry = read(database, inscribe(database, inscription))
    assert (entry.actor_user_id, entry.actor_display_name, entry.object_label) == (None, None, None)
    assert (entry.project_id, entry.object_revision_id, entry.params) == (None, None, {})


def test_two_inscriptions_of_one_instant_are_ordered_as_they_were_written(
    database: Database,
) -> None:
    written = [inscribe(database, role_created()) for _ in range(5)]
    assert sorted(written) == written


def test_an_inscription_is_lost_with_the_action_whose_transaction_is_rolled_back(
    database: Database,
) -> None:
    def act_then_fail() -> None:
        with logging_context(correlation_id=CORRELATION), database.transaction() as session:
            record(session, role_created())
            raise LookupError

    with pytest.raises(LookupError):
        act_then_fail()
    assert count(database) == 0


def test_an_action_outside_any_request_or_task_is_a_defect_and_inscribes_nothing(
    database: Database,
) -> None:
    with pytest.raises(AuditError, match="correlation"), database.transaction() as session:
        record(session, role_created())
    assert count(database) == 0


@pytest.mark.parametrize(
    "params",
    [
        {"token": "abc"},
        {"link": {"setup_token": "abc"}},
        {"links": [{"expires_at": "2026-10-09T13:00:00Z"}, {"Password": "x"}]},
    ],
)
def test_an_inscription_refuses_a_field_named_as_a_secret_at_any_depth(
    database: Database, params: object
) -> None:
    with pytest.raises(AuditError, match="secret"):
        inscribe(database, role_created(action="password_link_create", params=params))
    assert count(database) == 0


def test_the_actions_and_the_natures_of_objects_are_those_of_the_contract() -> None:
    assert list(ACTIONS) == [action.value for action in models.AuditAction]
    assert list(OBJECT_KINDS) == [kind.value for kind in models.AuditObjectKind]


@pytest.mark.requirement("WF-SEC-0030-A")
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE audit_entry SET action = 'restore'",
        "UPDATE audit_entry SET object_label = NULL, occurred_at = now()",
        "DELETE FROM audit_entry",
        "TRUNCATE audit_entry",
    ],
)
def test_the_service_may_neither_update_nor_delete_an_inscription(
    database: Database, statement: str
) -> None:
    inscribe(database, role_created())
    with pytest.raises(ProgrammingError) as raised, database.engine.begin() as connection:
        connection.execute(text(statement))
    assert isinstance(raised.value.orig, psycopg.errors.InsufficientPrivilege)
    assert read_labels(database) == ["Auditeur"]


@pytest.mark.requirement("WF-SEC-0030-A")
@pytest.mark.parametrize(
    ("statement", "operation"),
    [
        ("UPDATE audit_entry SET object_label = 'Administrateur'", "UPDATE"),
        # The label of an object that is no account, made null.
        ("UPDATE audit_entry SET object_label = NULL", "UPDATE"),
        # The name of the author made null, and something else changed with it.
        ("UPDATE audit_entry SET actor_display_name = NULL, action = 'restore'", "UPDATE"),
        ("UPDATE audit_entry SET actor_display_name = NULL, params = '{}'", "UPDATE"),
        ("DELETE FROM audit_entry", "DELETE"),
        ("TRUNCATE audit_entry", "TRUNCATE"),
    ],
)
def test_the_database_refuses_an_update_or_a_deletion_even_to_the_owner_of_the_table(
    database: Database, owner: Engine, statement: str, operation: str
) -> None:
    inscribe(database, role_created())
    with pytest.raises(IntegrityError) as raised, owner.begin() as connection:
        connection.execute(text(statement))
    assert isinstance(raised.value.orig, psycopg.errors.RestrictViolation)
    assert f"audit_entry is never updated nor deleted: {operation} refused" in str(raised.value)
    assert read_labels(database) == ["Auditeur"]


@pytest.mark.requirement("WF-SEC-0030-A")
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE audit_entry SET actor_display_name = 'Administrateur'",
        "UPDATE audit_entry SET object_label = 'Administrateur'",
        # A role is no account: its label stays.
        "UPDATE audit_entry SET object_label = NULL",
        # An update that changes nothing is no anonymisation.
        "UPDATE audit_entry SET actor_display_name = actor_display_name",
        "UPDATE audit_entry SET object_label = object_label",
    ],
)
def test_the_service_may_rename_nothing_in_an_inscription_but_forget_the_name_of_an_account(
    database: Database, statement: str
) -> None:
    # The service may update the two labels that name an account, and the trigger admits no other
    # change of them than making null the name of an anonymised account (migration 0011).
    inscribe(database, role_created())
    with pytest.raises(IntegrityError) as raised, database.engine.begin() as connection:
        connection.execute(text(statement))
    assert isinstance(raised.value.orig, psycopg.errors.RestrictViolation)
    assert "audit_entry is never updated nor deleted: UPDATE refused" in str(raised.value)
    assert read_labels(database) == ["Auditeur"]


@pytest.mark.requirement("WF-SEC-0030-A")
@pytest.mark.parametrize("is_held", [True, False], ids=["active", "unknown"])
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE audit_entry SET actor_display_name = NULL",
        "UPDATE audit_entry SET object_label = NULL",
        "UPDATE audit_entry SET actor_display_name = NULL, object_label = NULL",
    ],
)
def test_the_name_of_an_account_that_is_not_anonymized_stays_in_the_journal(
    database: Database, owner: Engine, statement: str, *, is_held: bool
) -> None:
    # Claire is the author and the object, and is not anonymised: the module of the accounts
    # refuses that the journal forget her name, to the service as to the owner of the tables.
    if is_held:
        hold_account(database, CLAIRE.user_id, is_anonymized=False)
    claire = AuditObject("user", CLAIRE.user_id, "Claire Martin")
    inscribe(database, role_created(action="user_update", audited=claire))
    for engine in (database.engine, owner):
        with pytest.raises(IntegrityError) as raised, engine.begin() as connection:
            connection.execute(text(statement))
        assert isinstance(raised.value.orig, psycopg.errors.RestrictViolation)
        assert "forgets the name of an anonymised account alone: UPDATE refused" in str(
            raised.value
        )
    (row,) = rows(database)
    assert (row["actor_display_name"], row["object_label"]) == ("Claire Martin", "Claire Martin")


@pytest.mark.requirement("WF-SEC-0030-A")
def test_the_name_of_another_account_stays_when_an_account_is_anonymized(
    database: Database,
) -> None:
    # Claire is anonymised, Paul is not: the name of Paul, author of the inscription that names
    # Claire as its object, is not hers to forget.
    paul = AuditActor(uuid4(), "Paul Durand")
    hold_account(database, CLAIRE.user_id, is_anonymized=True)
    hold_account(database, paul.user_id, is_anonymized=False)
    claire = AuditObject("user", CLAIRE.user_id, "Claire Martin")
    inscribe(database, role_created(action="user_update", actor=paul, audited=claire))
    with pytest.raises(IntegrityError) as raised, database.engine.begin() as connection:
        connection.execute(
            text("UPDATE audit_entry SET actor_display_name = NULL, object_label = NULL")
        )
    assert isinstance(raised.value.orig, psycopg.errors.RestrictViolation)
    with database.engine.begin() as connection:
        connection.execute(text("UPDATE audit_entry SET object_label = NULL"))
    (row,) = rows(database)
    assert (row["actor_display_name"], row["object_label"]) == ("Paul Durand", None)


def rows(database: Database) -> list[dict[str, Any]]:
    """Read every inscription whole, in the order of the journal."""
    with database.engine.connect() as connection:
        query = text("SELECT to_jsonb(audit_entry) FROM audit_entry ORDER BY id")
        return list(connection.execute(query).scalars())


@pytest.mark.requirement("WF-SEC-0030-A")
def test_an_anonymized_account_is_named_by_no_inscription_whose_number_dates_and_actions_stay(
    database: Database,
) -> None:
    # « Après anonymisation d'un compte, aucune inscription ne porte plus son nom ; leur nombre,
    # leurs dates et leurs actions sont inchangés. » Claire acted, and was acted upon; Paul's own
    # name, and the label of the role, stay.
    paul = AuditActor(uuid4(), "Paul Durand")
    claire_as_object = AuditObject("user", CLAIRE.user_id, "Claire Martin")
    hold_account(database, CLAIRE.user_id, is_anonymized=True)
    inscribe(database, role_created())
    inscribe(database, role_created(action="user_update", actor=paul, audited=claire_as_object))
    inscribe(database, role_created(actor=paul, occurred_at=NOON.replace(hour=13)))
    before = rows(database)
    with logging_context(correlation_id=CORRELATION), database.transaction() as session:
        forget_account(session, CLAIRE.user_id)
    after = rows(database)
    assert not [row for row in after if "Claire Martin" in str(row)]
    assert [
        (row["occurred_at"], row["action"], row["actor_user_id"], row["object_id"]) for row in after
    ] == [
        (row["occurred_at"], row["action"], row["actor_user_id"], row["object_id"])
        for row in before
    ]
    forgotten = [
        {**row, "actor_display_name": None}
        if row["actor_user_id"] == str(CLAIRE.user_id)
        else {**row, "object_label": None}
        if row["object_id"] == str(CLAIRE.user_id)
        else row
        for row in before
    ]
    assert after == forgotten
    assert [row["actor_display_name"] for row in after] == [None, "Paul Durand", "Paul Durand"]


def test_an_account_forgotten_twice_is_forgotten_once(database: Database) -> None:
    hold_account(database, CLAIRE.user_id, is_anonymized=True)
    inscribe(database, role_created())
    for _ in range(2):
        with logging_context(correlation_id=CORRELATION), database.transaction() as session:
            forget_account(session, CLAIRE.user_id)
    (row,) = rows(database)
    assert (row["actor_display_name"], row["object_label"]) == (None, "Auditeur")


def read_labels(database: Database) -> list[str | None]:
    """List the labels of the objects the journal names, unchanged by what was refused."""
    with database.engine.connect() as connection:
        return list(connection.execute(text("SELECT object_label FROM audit_entry")).scalars())


# What the service needs on each table, and why; a table the code declares and this does not
# fails the test below, which says so (docs/dev/sql.md, "Le rôle du service").
SERVICE_RIGHTS: dict[str, set[str]] = {
    # Read by getInstallation, its settings changed by an administrator; its row inserted by the
    # bootstrap, as the owner (US-0420, #701); never deleted: it is the installation.
    "installation": {"SELECT", "UPDATE"},
    # Created, read, changed, deactivated; never deleted (WF-DAT-0080).
    "user_account": {"SELECT", "INSERT", "UPDATE"},
    # Inscribed and read; neither changed nor deleted (WF-SEC-0030).
    "audit_entry": {"SELECT", "INSERT"},
    # The catalogue, written by the migrations alone and read by the service (WF-ADM-0100).
    "permission": {"SELECT"},
    # Created, read, changed, marked deleted; never removed (WF-DAT-0080).
    "access_role": {"SELECT", "INSERT", "UPDATE"},
    # Two associations of two keys: a row is added or removed, never changed.
    "access_role_permission": {"SELECT", "INSERT", "DELETE"},
    "user_access_role": {"SELECT", "INSERT", "DELETE"},
    # Submitted, followed, run and ended; never deleted by the service until a rule of retention
    # comes (§4.4.1).
    "background_task": {"SELECT", "INSERT", "UPDATE"},
    # Recorded by the worker and read; neither marked nor deleted until EP-13 (WF-ADM-0170).
    "backup": {"SELECT", "INSERT"},
    # The report of a reading of the accounts, kept and read; neither changed nor deleted.
    "identity_sync_report": {"SELECT", "INSERT"},
}


@pytest.mark.requirement("WF-SEC-0030-A")
def test_the_role_of_the_service_holds_insert_and_select_on_the_journal_and_nothing_more(
    database: Database,
) -> None:
    service = service_role(database.engine.url)
    with database.engine.connect() as connection:
        grants = connection.execute(
            text(
                "SELECT table_name, privilege_type FROM information_schema.role_table_grants "
                "WHERE grantee = :role"
            ),
            {"role": service},
        ).all()
        role = connection.execute(
            text(
                "SELECT rolsuper, rolcreaterole, rolbypassrls, "
                "(SELECT count(*) FROM pg_class WHERE relowner = pg_roles.oid) "
                "FROM pg_roles WHERE rolname = :role"
            ),
            {"role": service},
        ).one()
        journal_columns_updated = set(
            connection.execute(
                text(
                    "SELECT column_name FROM information_schema.column_privileges "
                    "WHERE grantee = :role AND table_name = 'audit_entry' "
                    "AND privilege_type = 'UPDATE'"
                ),
                {"role": service},
            ).scalars()
        )
        connected_as = connection.execute(
            text(
                "SELECT pg_has_role(current_user, :role, 'USAGE'), rolsuper FROM pg_roles "
                "WHERE rolname = current_user"
            ),
            {"role": service},
        ).one()
    held: dict[str, set[str]] = {}
    for table, privilege in grants:
        held.setdefault(table, set()).add(privilege)
    tables = {table.name for table in Base.metadata.sorted_tables}
    undeclared = tables - SERVICE_RIGHTS.keys()
    assert not undeclared, f"declare in SERVICE_RIGHTS what the service needs on {undeclared}"
    assert held == {name: SERVICE_RIGHTS[name] for name in tables}
    assert tuple(role) == (False, False, False, 0)
    # And the update of the two labels that name an account, which an anonymisation makes null.
    assert journal_columns_updated == {"actor_display_name", "object_label"}
    assert tuple(connected_as) == (True, False)


@pytest.mark.requirement("WF-SEC-0030-A")
def test_no_endpoint_modifies_or_deletes_an_inscription(
    contract: OpenAPI, services: Services
) -> None:
    declared = operations(contract)
    journal = {
        method for method, path in declared.values() if path.startswith("/api/v1/audit-events")
    }
    assert journal == {"GET"}
    served = create_app(services).openapi()["paths"]
    for path, item in served.items():
        for method, operation in item.items():
            assert declared[operation["operationId"]] == (method.upper(), path)
