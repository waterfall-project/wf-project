# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The roles an account is given: roles of the installation, not deleted (WF-ADM-0050).

A role sent that the installation does not have, or no longer, is refused at its rank. The roles
are read under the lock of the guard of the last administrator, which the deletion of a role takes
too: a role is never given while it is being deleted, nor deleted while it is being given
(WF-ADM-0090, WF-ADM-0120). The guard's lock is taken before the account is locked, as by every
write that takes it. An attribution is inscribed in the journal of audit, with the roles granted
and withdrawn, each by its identifier and its label at that moment (WF-SEC-0030).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from waterfall.core.access_roles.administrators import guard_last_administrator
from waterfall.core.access_roles.roles import HeldRole, roles_held
from waterfall.core.access_roles.tables import AccessRole, UserAccessRole
from waterfall.core.users.interface import (
    display_name,
    lock_account_for_change,
    note_account_change,
)
from waterfall.platform.audit import Act, AuditObject, AuditValue, Inscription, record
from waterfall.platform.errors import FieldError, UnprocessableError

UNKNOWN_ACCESS_ROLE = "UNKNOWN_ACCESS_ROLE"
VALIDATION_FAILED = "VALIDATION_FAILED"


@dataclass(frozen=True, slots=True)
class Attribution:
    """The roles an account holds once its roles are set, and those it was withdrawn."""

    held: list[HeldRole]
    withdrawn: list[HeldRole]

    @property
    def withdraws_all(self) -> bool:
        """Whether the account held roles and holds none any more (WF-SEC-0020)."""
        return bool(self.withdrawn) and not self.held


def unknown_roles(session: Session, role_ids: Sequence[UUID]) -> tuple[FieldError, ...]:
    """Point at each role sent that the installation does not have, or no longer, by its rank."""
    if not role_ids:
        return ()
    known = set(
        session.scalars(
            select(AccessRole.id).where(
                AccessRole.id.in_(role_ids), AccessRole.deleted_at.is_(None)
            )
        )
    )
    return tuple(
        FieldError(f"/access_role_ids/{rank}", UNKNOWN_ACCESS_ROLE)
        for rank, role_id in enumerate(role_ids)
        if role_id not in known
    )


def _refuse_unknown(session: Session, role_ids: Sequence[UUID]) -> None:
    faults = unknown_roles(session, role_ids)
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=faults)


def _give(session: Session, user_id: UUID, role_ids: Sequence[UUID]) -> None:
    if role_ids:
        session.execute(
            insert(UserAccessRole),
            [{"user_account_id": user_id, "access_role_id": role_id} for role_id in role_ids],
        )


def _inscribe(
    session: Session,
    account: tuple[UUID, str | None],
    change: tuple[Sequence[HeldRole], Sequence[HeldRole]],
    act: Act,
) -> None:
    """Inscribe an attribution to an account: the roles granted, then those withdrawn."""
    granted, withdrawn = change
    params: dict[str, AuditValue] = {
        "access_roles_granted": [
            {"access_role_id": str(held.access_role_id), "label": held.label} for held in granted
        ],
        "access_roles_withdrawn": [
            {"access_role_id": str(held.access_role_id), "label": held.label} for held in withdrawn
        ],
    }
    audited = AuditObject("user", *account)
    record(session, Inscription("user_access_roles_set", act.actor, audited, act.at, params=params))


def give_first_roles(
    session: Session, account: tuple[UUID, str | None], role_ids: Sequence[UUID], act: Act
) -> None:
    """Give an account just created its first roles, and inscribe them; or refuse them (422).

    The roles are read under the lock of the guard, which the deletion of a role holds while it
    counts the holders: a role deleted meanwhile is unknown here, and one given here is held
    there. A new account takes the administration from nobody: the guard refuses nothing else.
    ``account`` is the account by its identifier and its label, as the journal names it.
    """
    if not role_ids:
        return
    user_id, _ = account
    with guard_last_administrator(session):
        _refuse_unknown(session, role_ids)
        _give(session, user_id, list(dict.fromkeys(role_ids)))
    _inscribe(session, account, (roles_held(session, user_id), ()), act)


def set_access_roles(
    session: Session, user_id: UUID, role_ids: Sequence[UUID], lock_version: int, act: Act
) -> Attribution:
    """Set the roles of an account whose version is the one read, and inscribe the change.

    Under the guard, the account is locked — refused if unknown (404) or at another version
    (412) —, then the roles sent are read: one the installation does not have, or no longer, is
    refused at its rank (422). Roles that would take the administration from the last account
    that holds it are refused (409, WF-ADM-0120); giving it more stays possible. Roles the account
    already holds are kept, a role sent twice is held once, and an attribution that changes
    nothing writes nothing. The change applies at the next request of the account, whose
    permissions are read at each one (WF-ADM-0090).
    """
    with guard_last_administrator(session):
        account = lock_account_for_change(session, user_id, lock_version)
        _refuse_unknown(session, role_ids)
        before = roles_held(session, user_id)
        wanted = list(dict.fromkeys(role_ids))
        withdrawn = [held for held in before if held.access_role_id not in wanted]
        kept = {held.access_role_id for held in before}
        given = [role_id for role_id in wanted if role_id not in kept]
        if not withdrawn and not given:
            return Attribution(before, [])
        if withdrawn:
            session.execute(
                delete(UserAccessRole).where(
                    UserAccessRole.user_account_id == user_id,
                    UserAccessRole.access_role_id.in_([held.access_role_id for held in withdrawn]),
                )
            )
        _give(session, user_id, given)
        note_account_change(session, user_id, lock_version, act)
    after = roles_held(session, user_id)
    granted = [held for held in after if held.access_role_id in given]
    label = display_name(account.first_name, account.last_name)
    _inscribe(session, (user_id, label), (granted, withdrawn), act)
    return Attribution(after, withdrawn)
