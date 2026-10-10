# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The catalogue of permissions, delivered with the platform and not modifiable (WF-ADM-0100).

A migration of data: an installation has the catalogue because it applies the migrations
(WF-EXP-0020), and a permission a later epic adds is one more migration, with its value in
``PermissionCode`` of the contract. The order is that of the contract: the functions of second
level in the order of the tree, each read then written, a function in reading alone read only —
the journal of audit, which is never changed (WF-SEC-0030) —, then the irreversible actions in the
order WF-ADM-0100 names them, then the two structuring permissions.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from waterfall.platform.identifiers import new_id

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FUNCTIONS = (
    ("FBS-1.1", "users"),
    ("FBS-1.2", "access_roles"),
    ("FBS-1.3", "system_status"),
    ("FBS-1.4", "backups"),
    ("FBS-1.5", "audit_log"),
    ("FBS-2.1", "portfolio_projects"),
    ("FBS-2.2", "portfolio_workload"),
    ("FBS-2.3", "portfolio_performance"),
    ("FBS-2.4", "portfolio_cost_structure"),
    ("FBS-2.5", "portfolio_risks"),
    ("FBS-2.6", "portfolio_cost_curve"),
    ("FBS-2.7", "portfolio_pilot_health"),
    ("FBS-3.1", "cost_settings"),
    ("FBS-3.2", "resource_settings"),
    ("FBS-3.3", "risk_settings"),
    ("FBS-3.4", "indicator_settings"),
    ("FBS-4.1", "revisions"),
    ("FBS-4.2", "project_settings"),
    ("FBS-4.3", "planning"),
    ("FBS-4.4", "estimate"),
    ("FBS-4.5", "remaining"),
    ("FBS-4.6", "risks"),
    ("FBS-4.7", "actual_costs"),
    ("FBS-4.8", "project_indicators"),
    ("FBS-4.9", "lifecycle"),
)
# The functions that have the permission to read alone (WF-ADM-0100).
READ_ONLY = frozenset({"FBS-1.5"})
IRREVERSIBLE = (
    "revision_mark",
    "revision_abandon",
    "reference_designate",
    "structure_merge",
    "project_exit",
    "risk_occurrence",
    "cost_line_exclude",
    "platform_restore",
)
STRUCTURING = ("project_create", "all_projects_read")

permission = sa.table(
    "permission",
    sa.column("id", sa.Uuid()),
    sa.column("code", sa.Text()),
    sa.column("kind", sa.Text()),
    sa.column("fbs_code", sa.Text()),
    sa.column("position", sa.SmallInteger()),
)


def catalogue() -> list[tuple[str, str, str | None]]:
    """List the permissions in their order: code, kind, function of second level."""
    rows: list[tuple[str, str, str | None]] = []
    for fbs_code, name in FUNCTIONS:
        rows.append((f"{name}.read", "function_read", fbs_code))
        if fbs_code not in READ_ONLY:
            rows.append((f"{name}.write", "function_write", fbs_code))
    rows += [(code, "irreversible", None) for code in IRREVERSIBLE]
    rows += [(code, "structuring", None) for code in STRUCTURING]
    return rows


def upgrade() -> None:
    """Write the catalogue."""
    op.bulk_insert(
        permission,
        [
            {"id": new_id(), "code": code, "kind": kind, "fbs_code": fbs_code, "position": index}
            for index, (code, kind, fbs_code) in enumerate(catalogue())
        ],
    )


def downgrade() -> None:
    """Empty the catalogue; a role that grants a permission keeps the descent from running."""
    op.execute(permission.delete())
