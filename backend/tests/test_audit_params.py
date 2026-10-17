# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The parameters each writer of the journal inscribes are those the contract reads (#706).

``AuditParams`` is a closed object: a parameter the contract does not declare, or of another type,
makes ``listAuditEvents`` fail as a whole on the inscription that carries it. Each writer of the
core is called here by the function its route or its task calls, and every inscription it writes
is read back through the model of the contract. A module of the core that inscribes — by
``record``, or by the ``inscribe`` of the accounts — and is not called here fails the test: a
writer to come is tried as these are.
"""

import ast
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from access_rows import account
from sqlalchemy import select
from task_handlers import deposit

import waterfall
from waterfall import __version__
from waterfall.api.contract.models import AuditParams
from waterfall.core.access_roles.interface import (
    RoleWrite,
    create_role,
    delete_role,
    give_first_roles,
    set_access_roles,
    update_role,
)
from waterfall.core.backups.interface import TakenBackup, add_backup, inscribe_restoration
from waterfall.core.users.interface import (
    HeldAccount,
    Identity,
    IdentityChange,
    NotAdmitted,
    add_account_of_provider,
    anonymize_account,
    change_account,
    create_local_account,
    deactivate_unheld,
    follow,
    inscribe_password_link,
    set_account_activation,
)
from waterfall.platform.audit import Act, AuditActor, AuditEntry, AuditObject
from waterfall.platform.database import Database, utc_now
from waterfall.platform.keycloak_admin import ProviderAccount
from waterfall.platform.logs import logging_context
from waterfall.platform.queue import TaskQueue

CORRELATION = "req-params"
# The moment the backups are taken, which their inscriptions bear.
TAKEN_AT = datetime(2026, 10, 1, 1, 0, tzinfo=UTC)
# The modules of the core that inscribe in the journal, each one called below.
WRITERS = {
    "waterfall.core.access_roles.attributions",
    "waterfall.core.access_roles.roles",
    "waterfall.core.backups.interface",
    "waterfall.core.users.identity",
    "waterfall.core.users.password_link",
    "waterfall.core.users.provider",
    "waterfall.core.users.states",
}
# What a module imports to inscribe: the inscription of the journal, or that of the accounts.
INSCRIPTIONS = {
    ("waterfall.platform.audit", "record"),
    ("waterfall.core.users.identity", "inscribe"),
}


def inscribing_modules() -> set[str]:
    """Name the modules of the service that import an inscription (``INSCRIPTIONS``)."""
    root = Path(waterfall.__file__).parent
    found: set[str] = set()
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any(
            isinstance(node, ast.ImportFrom)
            and any((node.module, alias.name) in INSCRIPTIONS for alias in node.names)
            for node in ast.walk(tree)
        ):
            parts = path.relative_to(root.parent).with_suffix("").parts
            found.add(".".join(parts))
    return found


def write_every_action(database: Database, queue: TaskQueue) -> UUID:
    """Do each action the core inscribes, by the functions the routes and the worker call.

    Camille Martin is the author of each, but the accounts of the provider — added, followed,
    attached and deactivated by the platform (WF-ADM-0070) — and one of the two backups, which
    the platform takes; give her identifier.
    """
    author = account(database, "Martin", "Camille")
    act = Act(author, utc_now())
    platform = Act(None, utc_now())
    with logging_context(correlation_id=CORRELATION):
        with database.transaction() as session:
            pilot = create_role(session, RoleWrite("Pilote", ["planning.read"]), act)
        with database.transaction() as session:
            change = RoleWrite("Pilotage", ["users.read"])
            update_role(session, pilot.access_role_id, change, pilot.lock_version, act)
        with database.transaction() as session:
            identity = Identity("Montgolfier", "Jeanne", "jeanne@example.org")
            jeanne = create_local_account(session, identity, "kc-jeanne", act)
            held = [pilot.access_role_id]
            give_first_roles(session, (jeanne.user_id, "Jeanne Montgolfier"), held, act)
        user_id, version = jeanne.user_id, jeanne.lock_version
        with database.transaction() as session:
            renamed = IdentityChange(first_name="Jeanne-Marie")
            version = change_account(session, user_id, renamed, version, act).lock_version
        with database.transaction() as session:
            set_access_roles(session, user_id, [], version, act)
            version += 1
        with database.transaction() as session:
            inscribe_password_link(session, user_id, act)
        for is_active in (False, True, False):
            with database.transaction() as session:
                version = set_account_activation(
                    session, user_id, is_active=is_active, lock_version=version, act=act
                ).lock_version
        with database.transaction() as session:
            anonymize_account(session, user_id, version, act)
        for subject, is_federated in (("kc-paul", True), ("kc-lea", False)):
            provider = ProviderAccount(
                subject, "Durand", subject, f"{subject}@example.org", is_federated, not is_federated
            )
            with database.transaction() as session:
                add_account_of_provider(session, provider, platform.at)
        renamed_paul = ProviderAccount(
            "kc-paul", "Durand", "Paul", "kc-paul@example.org", is_federated=True, is_relayed=False
        )
        with database.transaction() as session:
            follow(session, renamed_paul, platform.at)
        # A new federation gives Léa, whose address an account holds, another subject (#707).
        lea = ProviderAccount(
            "kc-lea-2", "Durand", "Léa", "kc-lea@example.org", is_federated=True, is_relayed=False
        )
        with database.transaction() as session:
            attached = add_account_of_provider(session, lea, platform.at)
        assert not isinstance(attached, NotAdmitted)
        with database.transaction() as session:
            held = HeldAccount(attached.user_id, "kc-lea-2")
            assert deactivate_unheld(session, held, platform.at)
        with database.transaction() as session:
            delete_role(session, pilot.access_role_id, act)
    for requested_by in (author, None):
        task_id = deposit(database, queue, "backup", requested_by)
        taken = TakenBackup(
            task_id, TAKEN_AT, 2048, f"{task_id}.tar", __version__, "0013", is_verified=True
        )
        with logging_context(correlation_id=CORRELATION), database.transaction() as session:
            add_backup(session, taken, Act(requested_by, TAKEN_AT))
    with logging_context(correlation_id=CORRELATION), database.transaction() as session:
        named = AuditActor(author, "Camille Martin")
        inscribe_restoration(session, AuditObject("backup", uuid4(), None), named, utc_now())
    return author


@pytest.mark.requirement("WF-SEC-0030-A")
def test_each_writer_of_the_journal_inscribes_parameters_the_contract_reads(
    database: Database, queue: TaskQueue
) -> None:
    # « Chacune des actions énumérées produit une inscription datée et attribuée » — that the
    # consultation reads: each is dated by the moment of its action and attributed to its author,
    # named — Camille Martin, whose name the anonymisation of Jeanne keeps —, or to the platform,
    # unnamed; and every parameter written passes the closed model of the contract.
    assert inscribing_modules() == WRITERS
    before = utc_now()
    author = write_every_action(database, queue)
    after = utc_now()
    with database.transaction() as session:
        entries = list(session.scalars(select(AuditEntry)))
    attributed = [
        (entry.action, entry.actor_user_id, entry.actor_display_name) for entry in entries
    ]
    assert sorted(each for each in attributed if each[1] is None) == [
        ("backup", None, None),
        ("user_create", None, None),
        ("user_create", None, None),
        ("user_deactivate", None, None),
        ("user_update", None, None),
        ("user_update", None, None),
    ]
    by_camille = [each for each in attributed if each[1] is not None]
    assert {(actor, name) for _, actor, name in by_camille} == {(author, "Camille Martin")}
    assert ("user_anonymize", author, "Camille Martin") in by_camille
    for entry in entries:
        dated = (
            entry.occurred_at == TAKEN_AT
            if entry.action == "backup"
            else (before <= entry.occurred_at <= after)
        )
        assert dated, entry.action
    written = [(entry.action, entry.params) for entry in entries]
    assert {action for action, _ in written} == {
        "access_role_create",
        "access_role_update",
        "access_role_delete",
        "user_create",
        "user_update",
        "user_access_roles_set",
        "password_link_create",
        "user_deactivate",
        "user_reactivate",
        "user_anonymize",
        "backup",
        "restore",
    }
    # The attachment of a person of the directory to the account of her address says so (#707).
    assert ("user_update", {"fields": ["first_name"], "attached": True}) in written
    for action, params in written:
        read = AuditParams.model_validate(params)
        assert read.model_dump(mode="json", exclude_unset=True) == params, action
