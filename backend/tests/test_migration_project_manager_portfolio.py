# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The predefined project manager no longer reads the portfolio: migration 0038 (US-2690/L2)."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import insert, select

from waterfall.core.access_roles.predefined import MANAGER, PROJECT_MANAGER
from waterfall.core.access_roles.tables import AccessRole, AccessRolePermission, Permission
from waterfall.migrations.runner import downgrade, upgrade

if TYPE_CHECKING:
    from sqlalchemy import Engine

PORTFOLIO = "portfolio_projects.read"
MOMENT = datetime(2026, 11, 19, tzinfo=UTC)
# The roles of an installation made before the migration: the three delivered, the project manager
# with the permission the bootstrap used to give, a role the company created that holds the same,
# a project manager deleted, and a manager the company modified to hold the quality of creation.
ROLES: dict[str, tuple[bool, bool, tuple[str, ...]]] = {
    "Chef de projet": (True, False, (PORTFOLIO, *PROJECT_MANAGER)),
    "Manager": (True, False, MANAGER),
    "Administrateur": (True, False, ("users.write", "access_roles.write")),
    "Direction de projet": (False, False, (PORTFOLIO, *PROJECT_MANAGER)),
    "Ancien chef de projet": (True, True, (PORTFOLIO, *PROJECT_MANAGER)),
    "Manager créateur": (True, False, (*MANAGER, "project_create")),
}


def grants(engine: Engine) -> dict[str, set[str]]:
    """Read the permissions each role holds, by its label."""
    with engine.connect() as connection:
        rows = connection.execute(
            select(AccessRole.label, Permission.code)
            .join(AccessRolePermission, AccessRolePermission.access_role_id == AccessRole.id)
            .join(Permission, Permission.id == AccessRolePermission.permission_id)
        ).all()
    held: dict[str, set[str]] = {label: set() for label in ROLES}
    for label, code in rows:
        held[label].add(code)
    return held


@pytest.mark.requirement("WF-PTF-0030-A")
def test_the_migration_takes_the_reading_of_the_portfolio_from_the_predefined_project_manager_alone(
    empty_engine: Engine,
) -> None:
    # Propre à US-2690 (#3355) : « une migration la lui retire sur une plateforme installée, sans
    # toucher aux autres rôles ni à un rôle que l'entreprise a créé ». The project manager is known
    # by what it holds, not by its label; the descent gives the permission back to it alone.
    upgrade(empty_engine, "0037")
    with empty_engine.begin() as connection:
        identifiers = dict(connection.execute(select(Permission.code, Permission.id)).all())
        for label, (predefined, deleted, codes) in ROLES.items():
            role_id = uuid4()
            connection.execute(
                insert(AccessRole).values(
                    id=role_id,
                    label=label,
                    is_predefined=predefined,
                    deleted_at=MOMENT if deleted else None,
                    created_at=MOMENT,
                    updated_at=MOMENT,
                )
            )
            connection.execute(
                insert(AccessRolePermission),
                [
                    {"access_role_id": role_id, "permission_id": identifiers[code]}
                    for code in dict.fromkeys(codes)
                ],
            )
    before = grants(empty_engine)
    assert PORTFOLIO in before["Chef de projet"]
    upgrade(empty_engine, "0038")
    after = grants(empty_engine)
    assert after["Chef de projet"] == before["Chef de projet"] - {PORTFOLIO}
    assert {label: codes for label, codes in after.items() if label != "Chef de projet"} == {
        label: codes for label, codes in before.items() if label != "Chef de projet"
    }
    downgrade(empty_engine, "0037")
    assert grants(empty_engine) == before
