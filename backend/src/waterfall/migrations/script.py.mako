# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""${message}"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    """Apply the migration."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Undo the migration, as long as nothing written since depends on it."""
    ${downgrades if downgrades else "pass"}
