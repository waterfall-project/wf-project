# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The roles an account is given: roles of the installation, not deleted (WF-ADM-0050).

A role sent that the installation does not have, or no longer, is refused at its rank. The roles
are read under the lock of the guard of the last administrator, which the deletion of a role takes
too: a role is never given while it is being deleted, nor deleted while it is being given
(WF-ADM-0090, WF-ADM-0120). The attribution is inscribed in the journal of audit, with the roles
granted, each by its identifier and its label at that moment (WF-SEC-0030).
"""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from waterfall.core.access_roles.administrators import guard_last_administrator
from waterfall.core.access_roles.roles import roles_held
from waterfall.core.access_roles.tables import AccessRole, UserAccessRole
from waterfall.platform.audit import Act, AuditObject, AuditValue, Inscription, record
from waterfall.platform.errors import FieldError, UnprocessableError

UNKNOWN_ACCESS_ROLE = "UNKNOWN_ACCESS_ROLE"
VALIDATION_FAILED = "VALIDATION_FAILED"


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


def give_first_roles(
    session: Session, account: tuple[UUID, str], role_ids: Sequence[UUID], act: Act
) -> None:
    """Give an account just created its first roles, and inscribe them; or refuse them (422).

    The roles are read under the lock of the guard, which the deletion of a role holds while it
    counts the holders: a role deleted meanwhile is unknown here, and one given here is held
    there. A new account takes the administration from nobody: the guard refuses nothing else.
    ``account`` is the account by its identifier and its label, as the journal names it.
    """
    if not role_ids:
        return
    user_id, label = account
    with guard_last_administrator(session):
        faults = unknown_roles(session, role_ids)
        if faults:
            raise UnprocessableError(VALIDATION_FAILED, fields=faults)
        session.execute(
            insert(UserAccessRole),
            [
                {"user_account_id": user_id, "access_role_id": role_id}
                for role_id in dict.fromkeys(role_ids)
            ],
        )
    granted: list[AuditValue] = [
        {"access_role_id": str(held.access_role_id), "label": held.label}
        for held in roles_held(session, user_id)
    ]
    audited = AuditObject("user", user_id, label)
    params: dict[str, AuditValue] = {"access_roles_granted": granted, "access_roles_withdrawn": []}
    record(session, Inscription("user_access_roles_set", act.actor, audited, act.at, params=params))
