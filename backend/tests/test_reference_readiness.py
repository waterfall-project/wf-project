# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The minimal reference a project needs (US-0810/L2, WF-CYC-0120).

``getReferenceReadiness`` on an installation as its bootstrap leaves it (``installed_reference``),
then completed or deprived of a prerequisite by writing its tables around the service — the roles
of resources have no interface to create them yet (US-0850). The examples of the contract
(``fixtures/api/reference_readiness*.json``) are the oracle; every answer is checked against it.
"""

import json
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from installed_reference import holding, install
from sqlalchemy import insert, select, update
from support import WITNESS

from waterfall.core.cost_settings.interface import (
    CostCategoryDraft,
    CostTypeDraft,
    create_cost_category,
    create_cost_type,
)
from waterfall.core.cost_settings.tables import CostCategory, CostType
from waterfall.core.resource_settings.interface import NodeWrite, create_node
from waterfall.core.resource_settings.tables import DAYS, Calendar, ResourceRole
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from uuid import UUID

    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.platform.database import Database

READINESS = "/api/v1/reference/readiness"


def example(name: str) -> dict[str, Any]:
    """Read the value of an example of the contract."""
    document = json.loads((WITNESS / f"{name}.json").read_text(encoding="utf-8"))
    return document["value"]


@pytest.fixture
def installed(owner: Engine, database: Database) -> Database:
    """Give the database of an installation as its bootstrap leaves it."""
    install(owner)
    return database


@pytest.fixture
def headers(installed: Database, realm: TestRealm) -> dict[str, str]:
    """Give a session that holds no permission: the minimal reference asks for none."""
    return holding(installed, realm)


def labour_category(session: Session) -> UUID:
    """Create an active category of labour under an active nature of labour; give it."""
    act = Act(None, utc_now())
    nature = create_cost_type(session, CostTypeDraft("MO", "Main-d'œuvre", "labor"), act)
    draft = CostCategoryDraft("MO-001", "Ingénierie", "641001", nature.cost_type_id)
    return create_cost_category(session, draft, act).cost_category_id


def active_role(session: Session, category_id: UUID) -> None:
    """Write an active role of resources under a node, the category and the default calendar."""
    act = Act(None, utc_now())
    node = create_node(session, NodeWrite("DIR", "Direction"), act)
    calendar_id = session.scalars(select(Calendar.id).where(Calendar.is_default)).one()
    session.execute(
        insert(ResourceRole).values(
            id=new_id(),
            code="ING",
            label="Ingénieur",
            org_node_id=node.node_id,
            cost_category_id=category_id,
            calendar_id=calendar_id,
            monthly_hours=Decimal(140),
            headcount=Decimal(2),
            is_active=True,
            created_at=act.at,
            updated_at=act.at,
        )
    )


def read(api: ContractClient, headers: dict[str, str]) -> dict[str, Any]:
    """Read the minimal reference."""
    response = api.get(READINESS, headers=headers)
    assert response.status_code == 200
    return response.json()


@pytest.mark.requirement("WF-CYC-0120-A")
@pytest.mark.requirement("WF-EXP-0020-A")
def test_a_new_installation_lacks_a_category_of_labour_and_a_role_and_nothing_else(
    api: ContractClient, headers: dict[str, str]
) -> None:
    # « Sur une installation neuve, dont la seule catégorie est celle des provisions pour risques,
    # la création est refusée en nommant la catégorie de main-d'œuvre et le rôle manquants » : the
    # refusal is EP-04's; the minimal reference names them, in the order of the enumeration.
    assert read(api, headers) == example("reference_readiness_incomplete")
    assert api.get(READINESS).status_code == 401


@pytest.mark.requirement("WF-CYC-0120-A")
def test_the_reference_is_complete_once_a_category_of_labour_and_a_role_are_there(
    api: ContractClient, installed: Database, headers: dict[str, str]
) -> None:
    with installed.transaction() as session:
        category_id = labour_category(session)
    assert read(api, headers) == {"is_complete": False, "missing": ["active_resource_role"]}
    with installed.transaction() as session:
        active_role(session, category_id)
    assert read(api, headers) == example("reference_readiness")


@pytest.mark.requirement("WF-CYC-0120-A")
def test_a_reference_without_an_active_category_of_provision_names_it(
    api: ContractClient, installed: Database, headers: dict[str, str]
) -> None:
    # « Sur un référentiel dont aucune catégorie de type provision pour risques n'est active, la
    # création est refusée en nommant ce prérequis » : the last one deactivated.
    with installed.transaction() as session:
        active_role(session, labour_category(session))
        provision = select(CostType.id).where(CostType.kind == "provision")
        session.execute(
            update(CostCategory)
            .where(CostCategory.cost_type_id.in_(provision))
            .values(is_active=False)
        )
    assert read(api, headers) == example("reference_readiness_without_provision")


@pytest.mark.requirement("WF-CYC-0120-A")
def test_a_category_under_a_deactivated_nature_counts_for_nothing(
    api: ContractClient, installed: Database, headers: dict[str, str]
) -> None:
    with installed.transaction() as session:
        active_role(session, labour_category(session))
        session.execute(update(CostType).values(is_active=False))
    assert read(api, headers)["missing"] == ["active_cost_category", "active_provision_category"]


@pytest.mark.requirement("WF-CYC-0120-A")
def test_each_prerequisite_missing_is_named_in_the_order_of_the_enumeration(
    api: ContractClient, installed: Database, headers: dict[str, str]
) -> None:
    # A default calendar without any hour in its week, no category active, no role: all four.
    with installed.transaction() as session:
        session.execute(update(Calendar).values(dict.fromkeys(DAYS, Decimal(0))))
        session.execute(update(CostCategory).values(is_active=False))
    assert read(api, headers) == {
        "is_complete": False,
        "missing": [
            "default_calendar_with_hours",
            "active_cost_category",
            "active_provision_category",
            "active_resource_role",
        ],
    }
    # One day of work is enough for the calendar.
    with installed.transaction() as session:
        session.execute(update(Calendar).values(sunday=Decimal("0.5")))
    assert "default_calendar_with_hours" not in read(api, headers)["missing"]


@pytest.mark.requirement("WF-CYC-0120-A")
def test_a_deactivated_role_counts_for_nothing(
    api: ContractClient, installed: Database, headers: dict[str, str]
) -> None:
    with installed.transaction() as session:
        active_role(session, labour_category(session))
        session.execute(update(ResourceRole).values(is_active=False))
    assert read(api, headers)["missing"] == ["active_resource_role"]
