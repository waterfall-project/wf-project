# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reserve of sets of partitions and its two functions: 0055 (US-2830/L4, #4801).

The functions run as the owner of the tables, and the role of the service alone may execute them;
it reads the reserve and writes nothing in it. A set made at 0055 is still whole at the head: a
migration that partitions a table after it gives the sets in reserve their partition, or the
creation would take a set it does not take (``take_project_partitions``, whole sets alone). The
descent drops the partitions of the sets in reserve, the reserve and its functions, and the tasks
of the filling.
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, insert, select, text
from sqlalchemy.exc import DBAPIError
from support import service_role

from waterfall.migrations.runner import downgrade, upgrade
from waterfall.platform.database import utc_now
from waterfall.platform.tasks import BackgroundTask

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from waterfall.platform.database import Database

# What the catalogue says of a function: its owner, whether it runs as it, its settings, and who
# may execute it.
FUNCTION = text(
    "SELECT pg_get_userbyid(proowner), prosecdef, proconfig, ARRAY(SELECT "
    "CASE WHEN acl.grantee = 0 THEN 'PUBLIC' ELSE pg_get_userbyid(acl.grantee) END "
    "|| ':' || acl.privilege_type FROM aclexplode(proacl) AS acl ORDER BY 1) "
    "FROM pg_proc WHERE oid = to_regprocedure(:signature)"
)
SIGNATURES = ("reserve_project_partitions(uuid, integer)", "take_project_partitions()")
# The partitions of a project, by the suffix of their names.
PARTITIONS = text("SELECT count(*) FROM pg_class WHERE relname LIKE '%\\_p\\_' || :suffix")


def reserve(engine: Engine, size: int) -> list[UUID]:
    """Make sets as the filling does, up to ``size``; give those made."""
    made: list[UUID] = []
    with engine.begin() as connection:
        while connection.scalar(select(func.reserve_project_partitions(each := uuid4(), size))):
            made.append(each)
    return made


@pytest.mark.story("US-2830")
def test_a_set_made_at_0055_is_whole_at_the_head_and_the_descent_drops_what_is_left(
    empty_engine: Engine,
) -> None:
    # Propre à l'US (notes de réalisation) : « la fonction et la table se créent par une migration
    # nouvelle ; les projets existants ne sont pas touchés ».
    upgrade(empty_engine, "0055")
    # Made together, taken in the order of their identifiers.
    first, second = sorted(reserve(empty_engine, 2))
    with empty_engine.begin() as connection:
        refused = select(func.reserve_project_partitions(uuid4(), -1))
        with pytest.raises(DBAPIError, match="at least nought"):
            connection.execute(refused)
    upgrade(empty_engine, "head")
    with empty_engine.begin() as connection:
        assert connection.scalar(select(func.take_project_partitions())) == first
        connection.execute(
            insert(BackgroundTask).values(
                id=uuid4(),
                kind="partition_reserve",
                status="queued",
                progress=0,
                payload={},
                correlation_id="migration",
                attempts=0,
                submitted_at=utc_now(),
            )
        )
    downgrade(empty_engine, "0054")
    with empty_engine.connect() as connection:
        assert connection.scalar(PARTITIONS, {"suffix": second.hex}) == 0
        assert connection.scalar(PARTITIONS, {"suffix": first.hex}) > 0
        assert connection.scalar(text("SELECT to_regclass('project_partition_reserve')")) is None
        for signature in SIGNATURES:
            found = connection.execute(FUNCTION, {"signature": signature}).first()
            assert found is None
        assert connection.scalar(select(func.count()).select_from(BackgroundTask)) == 0


@pytest.mark.requirement("WF-DAT-0050-A")
def test_the_functions_of_the_reserve_are_the_owners_and_the_service_alone_executes_them(
    database: Database, owner: Engine
) -> None:
    # As the function of the partitions of a project (0026): run as the owner of the tables, under
    # their own search path; the role of the service may execute them, and nothing else may, not
    # PUBLIC, which a function grants by default.
    service = service_role(database.engine.url)
    with owner.connect() as connection:
        tables_owner = connection.execute(
            text("SELECT pg_get_userbyid(relowner) FROM pg_class WHERE relname = 'project'")
        ).scalar_one()
        for signature in SIGNATURES:
            proowner, definer, config, grants = connection.execute(
                FUNCTION, {"signature": signature}
            ).one()
            assert (proowner, definer, config) == (
                tables_owner,
                True,
                ["search_path=pg_catalog, pg_temp"],
            )
            assert sorted(grants) == sorted([f"{proowner}:EXECUTE", f"{service}:EXECUTE"])
