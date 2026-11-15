# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The two permissions of the function "installation" (WF-ADM-0100; EP-25, US-2120).

The installation (FBS-1.6, under administration: author's decisions of 2026-11-13, #3088, and of
2026-11-15, #3197) is viewed and modified like any function of second level: ``installation.read``
and ``installation.write`` enter the catalogue at the place the contract gives them, just after
``audit_log.read``, the permissions after it moving down two places in their order. A migration of
data, like ``0005`` and ``0006``: no screen creates a permission.

They are given to each role not deleted that holds the two permissions of administration of
WF-ADM-0120, ``users.write`` and ``access_roles.write``, and to no other: the table does not say
which role is the predefined administrator — its label is modifiable —, and the service recognises
an administrator so (author's decision of 2026-11-14). The descent takes them out of the roles,
then out of the catalogue, and moves the others back up.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FBS_CODE = "FBS-1.6"
ADDED = (("installation.read", "function_read"), ("installation.write", "function_write"))
CODES = [code for code, _ in ADDED]
AFTER = "audit_log.read"
# The permissions that make an administrator (WF-ADM-0120).
ADMINISTRATION = ("users.write", "access_roles.write")
# Far beyond any position, so that a shift never meets a position still held: the uniqueness of
# the position is checked row by row during an update.
APART = 10_000

permission = sa.table(
    "permission",
    sa.column("id", sa.Uuid()),
    sa.column("code", sa.Text()),
    sa.column("kind", sa.Text()),
    sa.column("fbs_code", sa.Text()),
    sa.column("position", sa.SmallInteger()),
)
access_role = sa.table(
    "access_role",
    sa.column("id", sa.Uuid()),
    sa.column("deleted_at", sa.DateTime(timezone=True)),
)
access_role_permission = sa.table(
    "access_role_permission",
    sa.column("access_role_id", sa.Uuid()),
    sa.column("permission_id", sa.Uuid()),
)


def _shift(after: int, by: int) -> None:
    """Move by ``by`` the permissions placed after ``after``, through positions apart."""
    later = permission.c.position > after
    op.execute(permission.update().where(later).values(position=permission.c.position + APART))
    op.execute(
        permission.update()
        .where(permission.c.position > after + APART)
        .values(position=permission.c.position - APART + by)
    )


def upgrade() -> None:
    """Make room after the journal of audit, write the two, give them to the administrators."""
    connection = op.get_bind()
    position: int = connection.execute(
        sa.select(permission.c.position).where(permission.c.code == AFTER)
    ).scalar_one()
    _shift(position, len(ADDED))
    op.bulk_insert(
        permission,
        [
            {
                "id": new_id(),
                "code": code,
                "kind": kind,
                "fbs_code": FBS_CODE,
                "position": position + 1 + rank,
            }
            for rank, (code, kind) in enumerate(ADDED)
        ],
    )
    granted = access_role_permission.alias("granted")
    held = sa.join(granted, permission, granted.c.permission_id == permission.c.id)
    administrators = (
        sa.select(granted.c.access_role_id)
        .select_from(held)
        .where(permission.c.code.in_(ADMINISTRATION))
        .group_by(granted.c.access_role_id)
        .having(sa.func.count() == len(ADMINISTRATION))
    )
    op.execute(
        access_role_permission.insert().from_select(
            ["access_role_id", "permission_id"],
            # Each administrator with each of the two: a product, which the join says.
            sa.select(access_role.c.id, permission.c.id)
            .select_from(sa.join(access_role, permission, sa.true()))
            .where(access_role.c.deleted_at.is_(None))
            .where(access_role.c.id.in_(administrators))
            .where(permission.c.code.in_(CODES)),
        )
    )


def downgrade() -> None:
    """Take the two permissions out of the roles, then out of the catalogue; close the gap."""
    connection = op.get_bind()
    position: int = connection.execute(
        sa.select(permission.c.position).where(permission.c.code == AFTER)
    ).scalar_one()
    removed = sa.select(permission.c.id).where(permission.c.code.in_(CODES))
    op.execute(
        access_role_permission.delete().where(access_role_permission.c.permission_id.in_(removed))
    )
    op.execute(permission.delete().where(permission.c.code.in_(CODES)))
    _shift(position, -len(ADDED))
