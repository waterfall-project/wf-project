# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The functions in reading alone lose their permission to write (WF-ADM-0100 revised, #739).

The state of the system (FBS-1.3) and the seven views of the portfolio (FBS-2.1 to FBS-2.7) have
only the permission to read, like the journal of audit: the eight permissions to write leave the
catalogue, and the roles that granted them. The other permissions keep their position, so the
order stays that of the contract; the descent puts the eight back at the positions they held.
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

from waterfall.platform.identifiers import new_id

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

READ_ONLY = (
    ("FBS-1.3", "system_status"),
    ("FBS-2.1", "portfolio_projects"),
    ("FBS-2.2", "portfolio_workload"),
    ("FBS-2.3", "portfolio_performance"),
    ("FBS-2.4", "portfolio_cost_structure"),
    ("FBS-2.5", "portfolio_risks"),
    ("FBS-2.6", "portfolio_cost_curve"),
    ("FBS-2.7", "portfolio_pilot_health"),
)
WRITE_CODES = [f"{name}.write" for _, name in READ_ONLY]

permission = sa.table(
    "permission",
    sa.column("id", sa.Uuid()),
    sa.column("code", sa.Text()),
    sa.column("kind", sa.Text()),
    sa.column("fbs_code", sa.Text()),
    sa.column("position", sa.SmallInteger()),
)
access_role_permission = sa.table(
    "access_role_permission",
    sa.column("access_role_id", sa.Uuid()),
    sa.column("permission_id", sa.Uuid()),
)


def upgrade() -> None:
    """Take the eight permissions to write out of the roles, then out of the catalogue."""
    removed = sa.select(permission.c.id).where(permission.c.code.in_(WRITE_CODES))
    op.execute(
        access_role_permission.delete().where(access_role_permission.c.permission_id.in_(removed))
    )
    op.execute(permission.delete().where(permission.c.code.in_(WRITE_CODES)))


def downgrade() -> None:
    """Put the eight permissions back, each just after its permission to read; no role gets them."""
    connection = op.get_bind()
    rows: list[dict[str, Any]] = []
    for fbs_code, name in READ_ONLY:
        position: int = connection.execute(
            sa.select(permission.c.position).where(permission.c.code == f"{name}.read")
        ).scalar_one()
        rows.append(
            {
                "id": new_id(),
                "code": f"{name}.write",
                "kind": "function_write",
                "fbs_code": fbs_code,
                "position": position + 1,
            }
        )
    op.bulk_insert(permission, rows)
