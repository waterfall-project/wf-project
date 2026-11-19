# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The predefined project manager no longer reads the portfolio (EP-11, US-2690; #3355).

WF-INTF-0010 names no view of the portfolio among the uses of a project manager, and the list of
the portfolio would show him the label, the code, the state, the budget and the indices of every
project of the installation, whether or not he opens it: the bootstrap no longer gives
``portfolio_projects.read`` to the predefined role (``access_roles.predefined``), and this migration
takes it from the roles of an installation already made. Data only: no column, no table.

The table does not say which of the predefined roles is the project manager — its label is
modifiable —, and the service recognises it by what it holds, as ``0030`` recognises the
administrator: a role delivered with the platform (``is_predefined``), not deleted, that holds
``project_create`` and does not hold ``all_projects_read``, which only the manager has. A role the
company created (``is_predefined`` false) keeps what it holds, the predefined manager and the
predefined administrator too, and every other permission of the project manager stays.

The same description is written in both directions, and it leaves two cases apart. The descent gives
the permission back to every predefined role it recognises, even one whose company had taken it
away: the table keeps no trace of who removed it, and the descent restores the delivered state.
A predefined role the company deprived of ``project_create`` is not recognised as the project
manager, so the ascent leaves it what it holds, ``portfolio_projects.read`` included — the method
of ``0030``, which knows a role by what it holds and misses the one a company has modified.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0038"
down_revision: str | None = "0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PORTFOLIO = "portfolio_projects.read"
QUALITY = "project_create"
READS_ALL = "all_projects_read"
PARAMETERS = {"portfolio": PORTFOLIO, "quality": QUALITY, "reads_all": READS_ALL}

# The project manager: a role delivered with the platform, not deleted, that holds the quality of
# creating a project and not that of reading every project. Written in both statements, as text.
TAKE = """
    WITH managers AS (
        SELECT role.id FROM access_role AS role
        WHERE role.is_predefined AND role.deleted_at IS NULL
          AND EXISTS (
            SELECT 1 FROM access_role_permission AS granted
            JOIN permission ON permission.id = granted.permission_id
            WHERE granted.access_role_id = role.id AND permission.code = :quality)
          AND NOT EXISTS (
            SELECT 1 FROM access_role_permission AS granted
            JOIN permission ON permission.id = granted.permission_id
            WHERE granted.access_role_id = role.id AND permission.code = :reads_all)
    )
    DELETE FROM access_role_permission
    WHERE permission_id = (SELECT id FROM permission WHERE code = :portfolio)
      AND access_role_id IN (SELECT id FROM managers)
"""
GIVE = """
    WITH managers AS (
        SELECT role.id FROM access_role AS role
        WHERE role.is_predefined AND role.deleted_at IS NULL
          AND EXISTS (
            SELECT 1 FROM access_role_permission AS granted
            JOIN permission ON permission.id = granted.permission_id
            WHERE granted.access_role_id = role.id AND permission.code = :quality)
          AND NOT EXISTS (
            SELECT 1 FROM access_role_permission AS granted
            JOIN permission ON permission.id = granted.permission_id
            WHERE granted.access_role_id = role.id AND permission.code = :reads_all)
    )
    INSERT INTO access_role_permission (access_role_id, permission_id)
    SELECT managers.id, permission.id FROM managers, permission
    WHERE permission.code = :portfolio
    ON CONFLICT DO NOTHING
"""


def upgrade() -> None:
    """Take ``portfolio_projects.read`` from the predefined project manager."""
    op.get_bind().execute(sa.text(TAKE), PARAMETERS)


def downgrade() -> None:
    """Give ``portfolio_projects.read`` back to the predefined project manager."""
    op.get_bind().execute(sa.text(GIVE), PARAMETERS)
