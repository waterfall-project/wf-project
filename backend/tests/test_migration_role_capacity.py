# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The hours a month of a role, calculated from its headcount: migration 0034 (US-2410/L2)."""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from estimate_support import role_image_row, write_reference
from project_rows import MARKED, STAMP, insert_project, insert_revision
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.orm import Session

from waterfall.core.estimate.tables import RevisionRole
from waterfall.core.resource_settings.interface import Capacity, read_roles
from waterfall.core.resource_settings.tables import Calendar, ResourceRole
from waterfall.core.revisions.tables import Revision
from waterfall.migrations.runner import downgrade, upgrade

if TYPE_CHECKING:
    from sqlalchemy import Engine

# The hours a month a role held in the column, and its constraint, before the migration.
HOURS = (
    "SELECT data_type, is_nullable FROM information_schema.columns "
    "WHERE table_name = 'resource_role' AND column_name = 'monthly_hours'"
)
CONSTRAINT = (
    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
    "WHERE conname = 'ck_resource_role_monthly_hours_not_negative'"
)


def entered(engine: Engine) -> dict[str, tuple[Decimal, Decimal]]:
    """Read the hours a month in the column, and the headcount, of each role by its code."""
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT code, monthly_hours, headcount FROM resource_role")
        ).all()
    return {code: (hours, headcount) for code, hours, headcount in rows}


def kept(engine: Engine) -> list[tuple[str, Decimal, Decimal]]:
    """Read the images of the roles a marked revision keeps: code, hours and headcount."""
    with engine.connect() as connection:
        rows = connection.execute(
            select(RevisionRole.code, RevisionRole.monthly_hours, RevisionRole.headcount)
        ).all()
    return [(code, hours, headcount) for code, hours, headcount in rows]


def served(engine: Engine) -> dict[str, Capacity]:
    """Read the capacity of each role by its code, as the service calculates it."""
    with Session(engine) as session:
        identifiers = session.scalars(select(ResourceRole.id)).all()
        roles = read_roles(session, identifiers, may_change=False)
    return {each.code: each.capacity for each in roles}


@pytest.mark.requirement("WF-REF-0100-A")
def test_the_migration_keeps_the_headcount_and_drops_the_hours_and_the_descent_calculates_them(
    empty_engine: Engine,
) -> None:
    # Propre à l'US : « l'effectif saisi des rôles existants fait foi, leurs heures saisies sont
    # abandonnées : la capacité d'un rôle peut changer à la migration ; les images des révisions
    # marquées gardent leurs heures d'alors ». The descent gives the column back filled with the
    # hours calculated — 2 * 40 * 52 / 12, and 0.5 * 0.03 * 52 / 12, 0.065, a half to the even —,
    # required and never negative; the rise drops them again, the headcount kept.
    upgrade(empty_engine)
    project, revision = uuid4(), uuid4()
    with empty_engine.begin() as connection:
        reference = write_reference(connection)
        thin = uuid4()
        days = {"monday": Decimal("0.03")} | dict.fromkeys(
            ("tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"), Decimal(0)
        )
        connection.execute(
            insert(Calendar).values(
                id=thin, label="Mince", is_default=False, is_active=True, **days, **STAMP
            )
        )
        full = uuid4()
        connection.execute(
            insert(Calendar).values(
                id=full,
                label="Pleine",
                is_default=False,
                is_active=True,
                **dict.fromkeys(("monday", "tuesday", "wednesday", "thursday", "friday"), 8),
                **dict.fromkeys(("saturday", "sunday"), 0),
                **STAMP,
            )
        )
        # A headcount with decimals on 40 hours a week: a remainder under 6, and one over 6.
        for code, headcount in (("BAS", "0.334"), ("HAUT", "0.335")):
            connection.execute(
                insert(ResourceRole).values(
                    id=uuid4(),
                    code=code,
                    label=code,
                    org_node_id=reference.org_node,
                    cost_category_id=reference.category,
                    calendar_id=full,
                    headcount=Decimal(headcount),
                    is_active=True,
                    **STAMP,
                )
            )
        connection.execute(
            insert(ResourceRole).values(
                id=uuid4(),
                code="DEMI",
                label="Demi",
                org_node_id=reference.org_node,
                cost_category_id=reference.category,
                calendar_id=thin,
                headcount=Decimal("0.5"),
                is_active=True,
                **STAMP,
            )
        )
        connection.execute(insert_project(id=project))
        connection.execute(select(func.create_project_partitions(project)))
        connection.execute(insert_revision(project, id=revision))
        connection.execute(
            insert(RevisionRole).values(**role_image_row(project, revision, reference))
        )
        connection.execute(update(Revision).where(Revision.id == revision).values(**MARKED))
    image = [("ING", Decimal(140), Decimal(2))]
    assert kept(empty_engine) == image
    calculated = served(empty_engine)
    assert set(calculated) == {"ING", "DEMI", "BAS", "HAUT"}
    downgrade(empty_engine, "0033")
    # What the descent fills is what the service calculated before it, role by role.
    assert {code: hours for code, (hours, _) in entered(empty_engine).items()} == {
        code: capacity.monthly_hours for code, capacity in calculated.items()
    }
    assert {code: head for code, (_, head) in entered(empty_engine).items()} == {
        code: capacity.headcount for code, capacity in calculated.items()
    }
    with empty_engine.connect() as connection:
        assert tuple(connection.execute(text(HOURS)).one()) == ("numeric", "NO")
        assert connection.execute(text(CONSTRAINT)).scalar_one() == (
            "CHECK ((monthly_hours >= (0)::numeric))"
        )
    assert kept(empty_engine) == image
    # Hours entered apart from the calculation, as before US-2410: given up by the rise.
    with empty_engine.begin() as connection:
        connection.execute(text("UPDATE resource_role SET monthly_hours = 140 WHERE code = 'ING'"))
    upgrade(empty_engine)
    with empty_engine.connect() as connection:
        assert connection.execute(text(HOURS)).all() == []
        assert connection.execute(text(CONSTRAINT)).all() == []
    assert served(empty_engine) == calculated
    assert kept(empty_engine) == image
