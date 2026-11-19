# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The base of a differential, and the counter it was taken at (EP-08, "Tables et migrations").

``cost_structure`` admits the kind ``base``: the copy of the main structure a differential is read
against and updated from, which no operation serves (US-3050). It receives ``differential_id``, the
differential whose base the structure is: there if and only if the kind is ``base``, a key to the
differential with its project and its revision — a base lives in the revision of its differential
—, one base at most by differential (a partial unique index, which holds the key of the
partition). And ``main_lock_version``, the counter the main structure bore when the base of a
differential was taken: there if and only if the kind is ``amendment``; the differential is up to
date while the main structure bears it; never negative, 0 for a differential copied out of date,
which the main structure never bears.

Added to the partitioned table, the columns, the checks, the key and the index go to each
partition; the columns are born null. No row is to take up: no differential exists but in the
databases of development, which are made again — one there refuses the check, and the migration
with it.

The descent refuses the kind ``base`` again; it fails while a base exists.
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

TABLE = "cost_structure"
# The kinds of a structure before and after.
FORMER_KINDS = ("main", "amendment", "risk")
KINDS = (*FORMER_KINDS, "base")
BASE_INDEX = "uq_cost_structure_base"


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _kinds(kinds: tuple[str, ...]) -> None:
    constraint = op.f(f"ck_{TABLE}_kind_known")
    op.drop_constraint(constraint, TABLE, type_="check")
    op.create_check_constraint(constraint, TABLE, _in("kind", kinds))


def upgrade() -> None:
    """Admit the base of a differential, which names it; keep the counter it was taken at."""
    op.add_column(TABLE, sa.Column("differential_id", sa.Uuid(), nullable=True))
    op.add_column(TABLE, sa.Column("main_lock_version", sa.Integer(), nullable=True))
    _kinds(KINDS)
    op.create_check_constraint(
        "differential_of_its_kind", TABLE, "(differential_id IS NOT NULL) = (kind = 'base')"
    )
    op.create_check_constraint(
        "main_counter_of_its_kind", TABLE, "(main_lock_version IS NOT NULL) = (kind = 'amendment')"
    )
    op.create_check_constraint("main_counter_not_negative", TABLE, "main_lock_version >= 0")
    op.create_foreign_key(
        None,
        TABLE,
        TABLE,
        ["project_id", "differential_id", "revision_id"],
        ["project_id", "id", "revision_id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        BASE_INDEX,
        TABLE,
        ["project_id", "differential_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'base'"),
    )


def downgrade() -> None:
    """Refuse the base of a differential again; fails while one exists."""
    op.drop_index(BASE_INDEX, table_name=TABLE)
    op.drop_constraint(op.f(f"fk_{TABLE}_project_id_{TABLE}"), TABLE, type_="foreignkey")
    op.drop_constraint(op.f(f"ck_{TABLE}_main_counter_not_negative"), TABLE, type_="check")
    op.drop_constraint(op.f(f"ck_{TABLE}_main_counter_of_its_kind"), TABLE, type_="check")
    op.drop_constraint(op.f(f"ck_{TABLE}_differential_of_its_kind"), TABLE, type_="check")
    _kinds(FORMER_KINDS)
    op.drop_column(TABLE, "main_lock_version")
    op.drop_column(TABLE, "differential_id")
