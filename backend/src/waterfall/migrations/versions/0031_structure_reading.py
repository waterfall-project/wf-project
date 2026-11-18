# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of a structure of a marked revision, kept (EP-26, "Tables et migrations", US-2270).

``structure_reading``: by structure, its project, its revision, the format of the code that wrote
it, the digest of the settings it was read with, the body of ``listNodes`` read whole, compressed,
and the instant it was kept. Partitioned by project as the content of a revision (WF-DAT-0050): the
function of ``0026`` creates its partition with the others for each project created, reading the
partitioned tables at each call, and the trigger that refuses the truncation of the table and of
each partition is the one every partitioned table has; the partitions the projects that exist lack
are created here. It follows its structure (``CASCADE``), the structure named with its revision.
No rule of immutability: a reading is made again when its format or its settings are no longer the
code's. No row is to take up: a reading is kept at its first reading. The service may read,
insert, change and delete one.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "structure_reading"

# The refusal of the truncation of the table, which each partition receives as well.
TRUNCATE = """
CREATE FUNCTION structure_reading_refuse_truncate() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $$
BEGIN
    RAISE EXCEPTION 'the structure_reading is never truncated' USING ERRCODE = 'restrict_violation';
END
$$;
CREATE TRIGGER structure_reading_refuse_truncate BEFORE TRUNCATE ON structure_reading
FOR EACH STATEMENT EXECUTE FUNCTION structure_reading_refuse_truncate();
"""

# The partitions the projects that exist lack.
EXISTING = """
DO $$
DECLARE
    project uuid;
    partition text;
BEGIN
    FOR project IN SELECT id FROM public.project LOOP
        partition := 'structure_reading_p_' || replace(project::text, '-', '');
        EXECUTE format(
            'CREATE TABLE public.%I PARTITION OF public.structure_reading FOR VALUES IN (%L)',
            partition,
            project
        );
        EXECUTE format(
            'CREATE TRIGGER structure_reading_refuse_truncate BEFORE TRUNCATE ON public.%I '
            'FOR EACH STATEMENT EXECUTE FUNCTION public.structure_reading_refuse_truncate()',
            partition
        );
    END LOOP;
END
$$
"""

GRANT = """
DO $$
BEGIN
    EXECUTE format(
        'GRANT SELECT, INSERT, UPDATE, DELETE ON structure_reading TO %I',
        current_database() || '_service'
    );
END
$$
"""


def upgrade() -> None:
    """Create the table, its refusal of the truncation, the partitions of the projects; grant it."""
    op.create_table(
        TABLE,
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("structure_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("format", sa.Integer(), nullable=False),
        sa.Column("settings_digest", sa.LargeBinary(), nullable=False),
        sa.Column("document", sa.LargeBinary(), nullable=False),
        sa.Column("kept_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("project_id", "structure_id"),
        sa.ForeignKeyConstraint(
            ["project_id", "structure_id", "revision_id"],
            ["cost_structure.project_id", "cost_structure.id", "cost_structure.revision_id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("format >= 1", name="format_positive"),
        postgresql_partition_by="LIST (project_id)",
    )
    op.execute(TRUNCATE)
    op.execute(EXISTING)
    op.execute(GRANT)


def downgrade() -> None:
    """Drop the table and its partitions, then its refusal of the truncation: the readings kept go.

    Nothing is lost that a reading does not make again.
    """
    op.drop_table(TABLE)
    op.execute("DROP FUNCTION structure_reading_refuse_truncate()")
