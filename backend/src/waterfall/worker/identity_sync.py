# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The task ``identity_sync``: the accounts of the identity provider read into Waterfall.

The provider is asked first to synchronise each directory it federates, then its accounts are read
by pages (WF-ADM-0070). Each person of the directory or of an external provider gets an account
without any role, or is attached by her address to the account that holds it if she comes from the
directory (#707); the accounts the provider holds follow its name, first name and address; those it
no longer holds are deactivated, each under the guard of the last administrator, who is kept active
and reported (WF-ADM-0120). A local account is never touched. The local accounts of the provider
that Waterfall does not know and that never had a password — left by a creation Waterfall did not
complete (#811) — are removed from the provider, once old enough that no creation is still under
way. Every write of Waterfall is the platform's (WF-DAT-0070), and the report is kept.

What the provider is asked comes before the guard is taken: no administrator waits on Keycloak. The
lock of the rule of the last administrator is taken before any row of an account, as the routes
that change an account take it: the reading and a route never wait each on what the other holds.
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from waterfall.core.access_roles.interface import guard_deactivation, lock_administrators
from waterfall.core.users.interface import (
    HeldAccount,
    NotAdmitted,
    SyncReport,
    deactivate_unheld,
    follow,
    known_subjects,
    record_report,
    unheld_accounts,
)
from waterfall.platform.database import utc_now
from waterfall.platform.errors import ConflictError
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin, ProviderAccount, RealmAccount
from waterfall.platform.logs import get_logger
from waterfall.platform.settings import ServiceSettings
from waterfall.platform.tasks import Task

# How old a local account of the provider unknown to Waterfall is before it is removed: a creation
# under way has written it in the provider, and not yet in Waterfall.
GRACE = timedelta(hours=1)
# The codes a person left as she was is reported with, by why she has no account.
REPORTED = {
    NotAdmitted.ADDRESS_TAKEN: "ALREADY_EXISTS",
    NotAdmitted.NAME_NOT_STORABLE: "VALIDATION_FAILED",
}
LAST_ADMINISTRATOR = "LAST_ADMINISTRATOR"

logger = get_logger(__name__)


class IdentitySync:
    """Read the accounts of the provider, as the worker runs a task ``identity_sync``."""

    def __init__(self, admin: KeycloakAdmin, grace: timedelta = GRACE) -> None:
        self.admin = admin
        self.grace = grace

    @classmethod
    def of(cls, settings: ServiceSettings) -> "IdentitySync":
        """Reach the provider the settings name, as the service account of its realm."""
        return cls(KeycloakAdmin(Keycloak(settings), settings))

    def __call__(self, session: Session, task: Task) -> dict[str, Any]:
        """Read, follow, deactivate, remove; keep the report, and give its counts."""
        self.admin.synchronize_directories()
        listed = self.admin.list_accounts()
        known = known_subjects(session)
        people: list[ProviderAccount] = []
        orphans: list[RealmAccount] = []
        for account in listed:
            person = self.person(account, known)
            if isinstance(person, ProviderAccount):
                people.append(person)
            elif person:
                orphans.append(account)
        removed = self.remove_orphans(orphans)
        held = {account.subject for account in listed}
        unheld = [
            account
            for account in unheld_accounts(session, held)
            if self.admin.read_account(account.subject) is None
        ]
        counts, skipped = write_accounts(session, people, unheld, utc_now())
        report = SyncReport(
            task.task_id,
            utc_now(),
            counts["created"],
            counts["updated"],
            counts["deactivated"],
            skipped,
            removed,
        )
        record_report(session, report)
        return {
            "created": report.created,
            "updated": report.updated,
            "deactivated": report.deactivated,
        }

    def person(self, account: RealmAccount, known: frozenset[str]) -> ProviderAccount | bool:
        """Describe an account of the realm as a person to follow, or tell a local one unknown.

        ``True`` for a local account Waterfall does not know, ``False`` for one the realm no longer
        holds. Whether an external provider relays an account is asked of one the list does not
        tell the origin of and Waterfall does not know: the origin of a known one is Waterfall's.
        """
        if account.is_federated or account.subject in known:
            return ProviderAccount(
                account.subject,
                account.last_name,
                account.first_name,
                account.email,
                is_federated=account.is_federated,
                is_relayed=False,
            )
        read = self.admin.read_account(account.subject)
        if read is None:
            return False
        return read if read.is_relayed else True

    def remove_orphans(self, orphans: list[RealmAccount]) -> list[str]:
        """Remove the local accounts of the realm unknown to Waterfall, without a password (#811).

        Only those older than the grace: a creation under way is in the provider before Waterfall.
        """
        removed: list[str] = []
        before = utc_now() - self.grace
        for account in orphans:
            if account.created_at > before or self.admin.has_password(account.subject):
                continue
            self.admin.remove_account(account.subject)
            logger.info("identity_sync.orphan_removed", subject=account.subject)
            removed.append(account.email)
        return removed


def write_accounts(
    session: Session, people: list[ProviderAccount], unheld: list[HeldAccount], at: datetime
) -> tuple[dict[str, int], list[tuple[str, str]]]:
    """Follow the persons, then deactivate the accounts no longer held; give counts and skipped.

    Under the lock of the rule, taken before any row: each deactivation runs under the guard of the
    last administrator, who is kept and reported (WF-ADM-0120).
    """
    lock_administrators(session)
    counts = {"created": 0, "updated": 0, "unchanged": 0, "deactivated": 0}
    skipped: list[tuple[str, str]] = []
    for person in people:
        followed = follow(session, person, at)
        if isinstance(followed, NotAdmitted):
            code = REPORTED.get(followed)
            if code is not None:
                skipped.append((person.email, code))
            logger.info("identity_sync.not_followed", subject=person.subject, reason=followed)
        else:
            counts[followed] += 1
    for account in unheld:
        try:
            with session.begin_nested(), guard_deactivation(session):
                deactivated = deactivate_unheld(session, account, at)
        except ConflictError:
            skipped.append((account.email, LAST_ADMINISTRATOR))
            logger.warning("identity_sync.last_administrator_kept", user_id=str(account.user_id))
        else:
            counts["deactivated"] += deactivated
    return counts, skipped
