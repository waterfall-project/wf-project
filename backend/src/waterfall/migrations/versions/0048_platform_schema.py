# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The schema ``platform``, which a restoration leaves in place; the tasks of the schedule (EP-13).

The maintenance of a restoration and the state of the restoration that holds it leave Redis for two
tables of a schema of their own, ``platform`` (US-2830, #956, ``waterfall.platform.maintenance``):
a backup dumps ``public`` alone, and a restoration replaces it alone. Each table holds one row at
most; the role of the service reads them, and the owner alone writes them — the service of the
restoration. A restoration of a backup taken before this revision applies it again over the
schema it left in place: what is there is then left as it is, the maintenance it holds included,
and only what follows, in ``public``, is applied. The schema, each table and the rights are made
where they are missing — a schema made by hand without its tables is completed.

``background_task.kind`` admits the three kinds the platform schedules — the purge, the external
copy of a backup, the test of a restoration —, after those of the contract and in that order, as
the code declares them. Requested by nobody, they are listed to nobody. The report of a reading of
the accounts goes with its task (#921): the purge of the tasks deletes it with them.

Both constraints are replaced in the transaction of the migration: the tasks and the reports hold
a few rows a day, which the checks read at once.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0048"
down_revision: str | None = "0047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "platform"
TASKS = "background_task"
REPORTS = "identity_sync_report"
KINDS_BEFORE = (
    "import_analysis",
    "import_apply",
    "revision_mark",
    "structure_merge",
    "risk_occurrence",
    "export",
    "backup",
    "restore",
    "identity_sync",
)
SCHEDULED = ("purge", "backup_copy", "restore_test")
KINDS = (*KINDS_BEFORE, *SCHEDULED)
GRANT = """
DO $$
BEGIN
    EXECUTE format('GRANT USAGE ON SCHEMA platform TO %I', current_database() || '_service');
    EXECUTE format(
        'GRANT SELECT ON platform.maintenance, platform.restoration TO %I',
        current_database() || '_service'
    );
END
$$
"""


def upgrade() -> None:
    """Make the schema ``platform``, its tables and rights where missing; admit the kinds, etc.

    A report of the accounts goes with its task.
    """
    _create_platform()
    _replace_kinds(KINDS)
    _replace_report_key("CASCADE")


def downgrade() -> None:
    """Drop the schema ``platform``, the tasks of the schedule, and refuse a task with its report.

    A maintenance held and the state of its restoration are lost with the schema, and the tasks of
    the three kinds of the schedule are deleted, which the former constraint refuses.
    """
    _replace_report_key("RESTRICT")
    kind = sa.column("kind", sa.Text())
    op.execute(sa.table(TASKS, kind).delete().where(kind.in_(SCHEDULED)))
    _replace_kinds(KINDS_BEFORE)
    op.execute(sa.schema.DropSchema(SCHEMA, cascade=True))


def _create_platform() -> None:
    op.execute(sa.schema.CreateSchema(SCHEMA, if_not_exists=True))
    op.create_table(
        "maintenance",
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="single_row"),
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.create_table(
        "restoration",
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=True),
        sa.Column("correlation_id", sa.Text(), nullable=False),
        sa.Column("attempts", sa.SmallInteger(), nullable=False),
        sa.Column("caches_cleared", sa.Boolean(), nullable=False),
        sa.Column("abandoned", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="single_row"),
        sa.CheckConstraint("attempts >= 1", name="attempts_positive"),
        sa.CheckConstraint("jsonb_typeof(payload) = 'object'", name="payload_object"),
        schema=SCHEMA,
        if_not_exists=True,
    )
    op.execute(GRANT)


def _listed(values: tuple[str, ...]) -> str:
    return ", ".join(repr(value) for value in values)


def _replace_kinds(kinds: tuple[str, ...]) -> None:
    constraint = op.f(f"ck_{TASKS}_kind_known")
    op.drop_constraint(constraint, TASKS, type_="check")
    op.create_check_constraint(constraint, TASKS, f"kind IN ({_listed(kinds)})")


def _replace_report_key(on_delete: str) -> None:
    key = op.f(f"fk_{REPORTS}_task_id_{TASKS}")
    op.drop_constraint(key, REPORTS, type_="foreignkey")
    op.create_foreign_key(key, REPORTS, TASKS, ["task_id"], ["id"], ondelete=on_delete)
