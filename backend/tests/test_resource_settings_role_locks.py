# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The roles of resources under two writes that cross (US-0850, WF-REF-0030, 0040, 0080).

Each crossing holds, in a transaction of its own, the lock both writes wait for — the tree's, or
the natures' —, starts them, checks that they wait, then releases it: whichever comes first, the
state left is coherent, and no error of the base escapes. The service is loaded with the witness.
"""

import threading
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from sqlalchemy import func, select

from waterfall.api.resource_roles import category_admission
from waterfall.core.cost_settings.interface import (
    CostCategoryDraft,
    CostTypeDraft,
    create_cost_category,
    create_cost_type,
    set_cost_type_activation,
    update_cost_category,
    update_cost_type,
)
from waterfall.core.cost_settings.records import NATURES_LOCK
from waterfall.core.resource_settings.interface import (
    Capacity,
    RoleDraft,
    category_has_roles,
    create_role,
    read_node,
    read_role,
    set_activation,
    set_role_activation,
)
from waterfall.core.resource_settings.interface.org_nodes import TREE_LOCK
from waterfall.core.resource_settings.tables import OrgNode, ResourceRole
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import ConflictError, ServiceError

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from support import ContractClient, ReferenceSessions

    from waterfall.core.resource_settings.interface import (
        CategoryAdmission,
        NodeActivation,
        RoleView,
    )
    from waterfall.platform.database import Database


def witness_id(suffix: str) -> str:
    """Give an identifier of the witness by its last digits."""
    return f"01926f3a-7c00-7000-8000-{suffix:0>12}"


# The objects of the witness the tests name.
DT, BE_ELEC, STANDARD = (witness_id(each) for each in ("470", "471", "481"))
AUTOM, ING_ELEC, TECH_MES = (witness_id(each) for each in ("453", "451", "452"))


# Two writes that cross, under a lock both wait for: the tree's, or the natures'.


def hold_the_lock(database: Database, key: int = TREE_LOCK) -> tuple[Any, Any]:
    """Take an advisory lock in a transaction of its own; give the connection and the lock."""
    connection = database.engine.connect()
    transaction = connection.begin()
    connection.execute(select(func.pg_advisory_xact_lock(key)))
    return connection, transaction


def crossed(database: Database, *jobs: Any, key: int = TREE_LOCK) -> list[Any]:
    """Run the jobs at once while a lock is held, the tree's unless said, then release it.

    Each job waits for the lock, then runs in a transaction of its own; a refusal is its result.
    The results come in the order the jobs ended.
    """
    results: list[Any] = []

    def run(job: Any) -> None:
        try:
            with database.transaction() as session:
                results.append(job(session))
        except ServiceError as refused:
            results.append(refused)

    connection, transaction = hold_the_lock(database, key)
    threads = [threading.Thread(target=run, args=(job,)) for job in jobs]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=1)
    assert all(thread.is_alive() for thread in threads)
    transaction.commit()
    connection.close()
    for thread in threads:
        thread.join(timeout=10)
    assert len(results) == len(jobs)
    return results


def no_active_role_under_a_closed_node(database: Database) -> None:
    """Check that no active role hangs under a deactivated node."""
    with database.transaction() as session:
        left = session.scalars(
            select(ResourceRole.code)
            .join(OrgNode, OrgNode.id == ResourceRole.org_node_id)
            .where(ResourceRole.is_active, ~OrgNode.is_active)
        ).all()
    assert left == []


def node_off(node_id: str, lock_version: int) -> Any:
    """Give a job that deactivates a node at the version given."""
    act = Act(None, utc_now())

    def job(session: Session) -> NodeActivation:
        return set_activation(
            session, UUID(node_id), is_active=False, lock_version=lock_version, act=act
        )

    return job


@pytest.mark.requirement("WF-REF-0080-A")
def test_two_crossed_deactivations_of_a_node_and_of_its_parent_leave_no_role_active(
    witness: Database,
) -> None:
    with witness.transaction() as session:
        parent = read_node(session, UUID(DT), may_change=False).lock_version
        child = read_node(session, UUID(BE_ELEC), may_change=False).lock_version
        versions = {
            code: read_role(session, UUID(each), may_change=False).lock_version
            for code, each in (("ING-ELEC", ING_ELEC), ("TECH-MES", TECH_MES))
        }
    results = crossed(witness, node_off(DT, parent), node_off(BE_ELEC, child))
    # Whichever comes first, the other finds the tree it wrote: the child deactivated with the
    # parent is a version behind (412), or the parent deactivates what the child left.
    assert any(not isinstance(each, ServiceError) for each in results)
    no_active_role_under_a_closed_node(witness)
    with witness.transaction() as session:
        assert session.scalar(select(func.count()).where(ResourceRole.is_active)) == 0
        for code, each in (("ING-ELEC", ING_ELEC), ("TECH-MES", TECH_MES)):
            written = read_role(session, UUID(each), may_change=False).lock_version
            assert written == versions[code] + 1


@pytest.mark.requirement("WF-REF-0080-A")
def test_a_role_reactivated_while_its_node_is_deactivated_does_not_stay_active(
    witness: Database,
) -> None:
    act = Act(None, utc_now())
    with witness.transaction() as session:
        node = read_node(session, UUID(BE_ELEC), may_change=False).lock_version
        automation = read_role(session, UUID(AUTOM), may_change=False).lock_version

    def role_on(session: Session) -> RoleView:
        return set_role_activation(
            session, UUID(AUTOM), is_active=True, lock_version=automation, act=act
        )

    crossed(witness, role_on, node_off(BE_ELEC, node))
    no_active_role_under_a_closed_node(witness)
    with witness.transaction() as session:
        assert read_node(session, UUID(BE_ELEC), may_change=False).is_active is False
        assert read_role(session, UUID(AUTOM), may_change=False).is_active is False


# A role written while a nature or a category changes, under the lock of the natures (WF-REF-0030,
# WF-REF-0040): the role shares it, before the tree and its row, as every change of the cost
# settings takes it before their rows.


def labour_category(database: Database) -> tuple[UUID, UUID]:
    """Create a nature of labour and a category of it, bound by no role; give their identifiers."""
    act = Act(None, utc_now())
    with database.transaction() as session:
        nature = create_cost_type(session, CostTypeDraft("MO2", "Intérim", "labor"), act)
        draft = CostCategoryDraft("INT-1", "Intérim", "642", nature.cost_type_id)
        category = create_cost_category(session, draft, act)
    return nature.cost_type_id, category.cost_category_id


def interim(session: Session, category_id: UUID, admission: CategoryAdmission | None) -> RoleView:
    """Create a role on a category, as the cost settings told of it."""
    draft = RoleDraft(
        "INT",
        "Intérimaire",
        UUID(BE_ELEC),
        category_id,
        admission,
        UUID(STANDARD),
        Capacity(Decimal("140.00"), Decimal(1)),
    )
    return create_role(session, draft, Act(None, utc_now()))


def role_job(category_id: UUID) -> Any:
    """Give a job that creates a role on a category, as the API does: the category asked first."""

    def job(session: Session) -> RoleView:
        return interim(session, category_id, category_admission(session, category_id))

    return job


@pytest.mark.requirement("WF-REF-0030-A")
def test_a_nature_deactivated_while_a_role_is_created_on_its_category_leaves_a_coherent_state(
    api: ContractClient, reference_sessions: ReferenceSessions, witness: Database
) -> None:
    nature_id, category_id = labour_category(witness)
    act = Act(None, utc_now())

    def nature_off(session: Session) -> object:
        return set_cost_type_activation(
            session, nature_id, is_active=False, lock_version=0, act=act
        )

    # Both wait for the lock of the natures, then run in either order: no error of the base.
    results = crossed(witness, role_job(category_id), nature_off, key=NATURES_LOCK)
    refused = [each for each in results if isinstance(each, ServiceError)]
    with witness.transaction() as session:
        bound = category_has_roles(session, [category_id])
    # The role created first binds the nature, deactivated after; or the nature deactivated first
    # refuses the role, at its category.
    if refused:
        assert [(each.code, [(f.pointer, f.code) for f in each.fields]) for each in refused] == [
            ("VALIDATION_FAILED", [("/cost_category_id", "INACTIVE_REFERENCE_OBJECT")])
        ]
        assert bound == frozenset()
    else:
        assert bound == {category_id}
    costs = reference_sessions("cost_settings").changing
    natures = api.get("/api/v1/reference/cost-types?include_inactive=true", headers=costs)
    own = next(each for each in natures.json()["items"] if each["code"] == "MO2")
    assert own["is_active"] is False
    missing = own["available_commands"][1]["missing_conditions"]
    assert ("cost_type_without_role" in missing) is bool(bound)


def kind_changed(nature_id: UUID) -> Any:
    """Give a job that makes a nature of labour one of provision."""
    act = Act(None, utc_now())

    def job(session: Session) -> object:
        draft = CostTypeDraft("MO2", "Intérim", "provision")
        return update_cost_type(session, nature_id, draft, 0, act)

    return job


def category_moved(category_id: UUID, database: Database) -> Any:
    """Give a job that moves a category of labour under a new nature of provision."""
    act = Act(None, utc_now())
    with database.transaction() as session:
        draft = CostTypeDraft("PROV2", "Provisions", "provision")
        provision = create_cost_type(session, draft, act).cost_type_id

    def job(session: Session) -> object:
        draft = CostCategoryDraft("INT-1", "Intérim", "642", provision)
        return update_cost_category(session, category_id, draft, 0, act)

    return job


@pytest.mark.requirement("WF-REF-0030-A")
@pytest.mark.requirement("WF-REF-0040-A")
@pytest.mark.parametrize(
    ("change", "missing"),
    [("nature", "cost_type_without_role"), ("category", "cost_category_without_role")],
)
def test_a_change_of_kind_waits_for_the_role_being_attached_then_is_refused_for_it(
    witness: Database, change: str, missing: str
) -> None:
    nature_id, category_id = labour_category(witness)
    job = kind_changed(nature_id) if change == "nature" else category_moved(category_id, witness)
    results: list[Any] = []

    def run() -> None:
        try:
            with witness.transaction() as session:
                results.append(job(session))
        except ServiceError as refused:
            results.append(refused)

    other = threading.Thread(target=run)
    with witness.transaction() as session:
        # The role's transaction asks the category first, and holds what it was told: the change
        # waits for it, the role created, until it ends.
        admission = category_admission(session, category_id)
        other.start()
        other.join(timeout=1)
        assert other.is_alive()
        created = interim(session, category_id, admission)
        other.join(timeout=1)
        assert other.is_alive()
    other.join(timeout=10)
    assert len(results) == 1
    refused = results[0]
    assert isinstance(refused, ConflictError)
    assert (refused.code, refused.params["missing_condition"]) == (
        "STATE_FORBIDS_OPERATION",
        missing,
    )
    assert [each["code"] for each in refused.params["resource_roles"]] == [created.code]
