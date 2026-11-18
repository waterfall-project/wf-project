# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The counter of the lines of cost the key of the cache reads: migration 0033 (US-1720/L3)."""

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from costs_support import insert_cost_line, write_import
from project_rows import insert_project
from sqlalchemy import func, select, text

from waterfall.core.costs.tables import CostLine
from waterfall.migrations.runner import downgrade, upgrade

if TYPE_CHECKING:
    from sqlalchemy import Engine

COLUMN = (
    "SELECT data_type, is_nullable, column_default FROM information_schema.columns "
    "WHERE table_name = 'cost_line' AND column_name = 'lock_version'"
)


def versions_of_cost_lines(engine: Engine) -> list[int]:
    """Read the counter of each line of cost."""
    with engine.connect() as connection:
        return list(connection.execute(select(CostLine.lock_version)).scalars())


@pytest.mark.requirement("WF-DAT-0130-A")
def test_the_counter_of_the_lines_of_cost_starts_at_zero_and_the_descent_drops_it(
    empty_engine: Engine,
) -> None:
    # Propre à l'US (#3629) : une ligne qui existe avant la migration reçoit 0, une insérée après
    # aussi ; la colonne est un entier non nul d'une table non partitionnée ; la descente la
    # retire, et les lignes restent.
    upgrade(empty_engine, "0032")
    project = uuid4()
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=project))
        connection.execute(select(func.create_project_partitions(project)))
        imported = write_import(connection, project)
        insert_cost_line(connection, imported)
    upgrade(empty_engine, "0033")
    assert versions_of_cost_lines(empty_engine) == [0]
    with empty_engine.begin() as connection:
        insert_cost_line(connection, imported, document_number="5100001235")
        column = connection.execute(text(COLUMN)).one()
        partitioned = connection.execute(
            text(
                "SELECT count(*) FROM pg_partitioned_table WHERE partrelid = 'cost_line'::regclass"
            )
        ).scalar_one()
    assert versions_of_cost_lines(empty_engine) == [0, 0]
    assert tuple(column) == ("integer", "NO", "0")
    assert partitioned == 0
    downgrade(empty_engine, "0032")
    with empty_engine.connect() as connection:
        assert connection.execute(text(COLUMN)).all() == []
        assert connection.execute(select(func.count()).select_from(CostLine)).scalar_one() == 2
