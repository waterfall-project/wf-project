# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The journal of audit: an action inscribed in its transaction, and no way to change it after.

The refusals are tried as the service meets them — by a role of the service, the one the tests
connect as — and as the owner of the tables, whom only the trigger stops (WF-SEC-0030).
"""

import re
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from openapi_core import OpenAPI
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from support import SERVICE_ROLE, operations

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.api.contract import models
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
    record,
)
from waterfall.platform.database import Base, Database, create_database_engine
from waterfall.platform.logs import logging_context

SOURCES = Path(__file__).resolve().parents[1] / "src" / "waterfall"
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


def read(database: Database, identifier: UUID) -> AuditEntry:
    """Read an inscription back."""
    with database.transaction() as session:
        return session.execute(select(AuditEntry).where(AuditEntry.id == identifier)).scalar_one()


def count(database: Database) -> int:
    """Count the inscriptions of the journal."""
    with database.engine.connect() as connection:
        return connection.execute(text("SELECT count(*) FROM audit_entry")).scalar_one()


@pytest.fixture
def owner(database_url: str) -> Iterator[Engine]:
    """Give an engine of the owner of the tables, on the database the service sees."""
    engine = create_database_engine(database_url)
    yield engine
    engine.dispose()


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
def test_an_inscription_never_carries_a_secret(database: Database, params: object) -> None:
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
        "UPDATE audit_entry SET object_label = 'Administrateur'",
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


def read_labels(database: Database) -> list[str | None]:
    """List the labels of the objects the journal names, unchanged by what was refused."""
    with database.engine.connect() as connection:
        return list(connection.execute(text("SELECT object_label FROM audit_entry")).scalars())


@pytest.mark.requirement("WF-SEC-0030-A")
def test_the_role_of_the_service_holds_insert_and_select_on_the_journal_and_nothing_more(
    database: Database,
) -> None:
    with database.engine.connect() as connection:
        grants = connection.execute(
            text(
                "SELECT table_name, privilege_type FROM information_schema.role_table_grants "
                "WHERE grantee = :role"
            ),
            {"role": SERVICE_ROLE},
        ).all()
        role = connection.execute(
            text(
                "SELECT rolsuper, rolcreaterole, rolbypassrls, "
                "(SELECT count(*) FROM pg_class WHERE relowner = pg_roles.oid) "
                "FROM pg_roles WHERE rolname = :role"
            ),
            {"role": SERVICE_ROLE},
        ).one()
        connected_as = connection.execute(
            text(
                "SELECT pg_has_role(current_user, :role, 'USAGE'), rolsuper FROM pg_roles "
                "WHERE rolname = current_user"
            ),
            {"role": SERVICE_ROLE},
        ).one()
    held: dict[str, set[str]] = {}
    for table, privilege in grants:
        held.setdefault(table, set()).add(privilege)
    every_change = {"SELECT", "INSERT", "UPDATE", "DELETE"}
    assert held == {
        table.name: {"SELECT", "INSERT"} if table.name == "audit_entry" else every_change
        for table in Base.metadata.sorted_tables
    }
    assert tuple(role) == (False, False, False, 0)
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


@pytest.mark.requirement("WF-SEC-0030-A")
def test_no_code_of_the_service_but_its_migrations_changes_the_journal() -> None:
    change = re.compile(
        r"(update|delete)\(\s*AuditEntry|(UPDATE|DELETE\s+FROM|TRUNCATE)\s+audit_entry",
        re.IGNORECASE,
    )
    offending = [
        path.relative_to(SOURCES).as_posix()
        for path in SOURCES.rglob("*.py")
        if "migrations" not in path.parts and change.search(path.read_text(encoding="utf-8"))
    ]
    assert offending == []
