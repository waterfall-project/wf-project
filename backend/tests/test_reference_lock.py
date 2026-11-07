# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lock of the minimal reference between a creation of a project and the writes that empty it.

A project is created once the four questions of the minimal reference are answered yes
(WF-CYC-0120): the creation shares ``REFERENCE_LOCK`` before it asks them and holds it to the
commit, and every write that can turn an answer into no takes it exclusively before it reads
anything (#2154). The platform is an installation as the bootstrap leaves it, completed with a
category of labour and a role of resources, run without Keycloak.
"""

from concurrent.futures import Future, ThreadPoolExecutor
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from installed_reference import install
from projects_support import complete_reference
from sqlalchemy import func, select
from support import wait_for_a_lock

from waterfall.bootstrap import INSTALL_LOCK
from waterfall.core.access_roles.administrators import ADMINISTRATORS_LOCK
from waterfall.core.cost_settings.interface import (
    CostCategoryDraft,
    CostTypeDraft,
    missing_prerequisites,
    set_cost_category_activation,
    set_cost_type_activation,
    update_cost_category,
    update_cost_type,
)
from waterfall.core.cost_settings.records import NATURES_LOCK
from waterfall.core.cost_settings.tables import CostCategory, CostType
from waterfall.core.projects.interface import ProjectDraft, Viewer, create_project
from waterfall.core.projects.tables import Project
from waterfall.core.resource_settings.interface import (
    CalendarContent,
    WeeklyHours,
    create_calendar,
    set_activation,
    set_default_calendar,
    set_role_activation,
    share_reference,
    update_calendar,
)
from waterfall.core.resource_settings.interface.calendars import DEFAULT_LOCK
from waterfall.core.resource_settings.interface.org_nodes import TREE_LOCK
from waterfall.core.resource_settings.interface.readiness import REFERENCE_LOCK
from waterfall.core.resource_settings.tables import Calendar, OrgNode, ResourceRole
from waterfall.platform.audit import FORGETTING_LOCK, Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import ConflictError
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy import Engine
    from sqlalchemy.orm import Session

    from waterfall.platform.database import Database

type Job = Callable[[Session], object]

ACT = Act(None, utc_now())
EIGHT, NONE = Decimal(8), Decimal(0)
FULL_WEEK = WeeklyHours(EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, NONE, NONE)


@pytest.fixture
def reference(owner: Engine, database: Database) -> Database:
    """Give a database whose minimal reference holds: the bootstrap's, with labour and a role."""
    install(owner)
    complete_reference(database)
    return database


def the_writes(database: Database) -> dict[str, Job]:
    """Give, by name, a job for each write that takes the lock of the reference exclusively."""
    with database.transaction() as session:

        def row(
            model: type[CostType | CostCategory | ResourceRole | OrgNode | Calendar], **by: object
        ) -> tuple[UUID, int]:
            found = session.execute(select(model.id, model.lock_version).filter_by(**by)).one()
            return found.id, found.lock_version

        labour, labour_version = row(CostType, code="MO")
        provision, provision_version = row(CostType, kind="provision")
        category, category_version = row(CostCategory, code="MO-001")
        role, role_version = row(ResourceRole, code="ING")
        node, node_version = row(OrgNode, code="DIR")
        calendar, calendar_version = row(Calendar, is_default=True)
    nature = CostTypeDraft("MO", "Main-d'œuvre", "labor")
    kept = CostCategoryDraft("MO-001", "Ingénierie", "641001", labour)
    week = CalendarContent("Standard", FULL_WEEK)

    def deactivation(function: Callable[..., object], target: UUID, lock_version: int) -> Job:
        return lambda s: function(s, target, is_active=False, lock_version=lock_version, act=ACT)

    return {
        "update_cost_type": lambda s: update_cost_type(s, labour, nature, labour_version, ACT),
        "deactivate_cost_type": deactivation(
            set_cost_type_activation, provision, provision_version
        ),
        "update_cost_category": lambda s: update_cost_category(
            s, category, kept, category_version, ACT
        ),
        "deactivate_cost_category": deactivation(
            set_cost_category_activation, category, category_version
        ),
        "deactivate_role": deactivation(set_role_activation, role, role_version),
        "deactivate_node": deactivation(set_activation, node, node_version),
        "update_calendar": lambda s: update_calendar(s, calendar, week, calendar_version, ACT),
        "designate_calendar": lambda s: set_default_calendar(s, calendar, calendar_version, ACT),
        "create_default_calendar": lambda s: create_calendar(
            s, CalendarContent("Autre", FULL_WEEK), ACT, default=True
        ),
    }


def start(database: Database, job: Job) -> tuple[ThreadPoolExecutor, Future[object]]:
    """Run a job in a transaction of its own, in another thread."""
    pool = ThreadPoolExecutor(1)

    def run() -> object:
        with database.transaction() as session:
            return job(session)

    return pool, pool.submit(run)


def create(session: Session) -> object:
    """Create a project as the service does."""
    viewer = Viewer(uuid4(), ("all_projects_read",))
    with logging_context(correlation_id="the-creation"):
        return create_project(session, ProjectDraft("Course"), ACT, viewer)


def project_count(database: Database) -> int:
    """Count the projects written."""
    with database.transaction() as session:
        return session.scalar(select(func.count()).select_from(Project)) or 0


@pytest.mark.requirement("WF-CYC-0120-A")
@pytest.mark.parametrize(
    "name",
    [
        "update_cost_type",
        "deactivate_cost_type",
        "update_cost_category",
        "deactivate_cost_category",
        "deactivate_role",
        "deactivate_node",
        "update_calendar",
        "designate_calendar",
        "create_default_calendar",
    ],
)
def test_a_write_that_can_empty_the_reference_waits_for_a_creation_in_progress(
    reference: Database, name: str
) -> None:
    job = the_writes(reference)[name]
    with reference.transaction() as creating:
        create(creating)
        pool, writing = start(reference, job)
        wait_for_a_lock(reference)
        assert not writing.done()
    writing.result(timeout=10)
    pool.shutdown()
    assert project_count(reference) == 1


@pytest.mark.requirement("WF-CYC-0120-A")
def test_a_creation_waits_for_a_deactivation_that_empties_the_reference_and_is_refused(
    reference: Database,
) -> None:
    provision_off = the_writes(reference)["deactivate_cost_type"]
    with reference.transaction() as deactivating:
        provision_off(deactivating)
        pool, creating = start(reference, create)
        wait_for_a_lock(reference)
        assert not creating.done()
    with pytest.raises(ConflictError) as refused:
        creating.result(timeout=10)
    pool.shutdown()
    assert refused.value.code == "REFERENCE_INCOMPLETE"
    assert refused.value.params == {"missing_prerequisites": ["active_provision_category"]}
    assert project_count(reference) == 0
    with reference.transaction() as session:
        assert missing_prerequisites(session) == ("active_provision_category",)


@pytest.mark.requirement("WF-CYC-0120-A")
def test_two_creations_share_the_lock_of_the_reference_without_waiting_for_each_other(
    reference: Database,
) -> None:
    # The creations themselves meet elsewhere (the partitions of a project are created by DDL):
    # what is shared is the lock.
    with reference.transaction() as first:
        share_reference(first)
        pool, second = start(reference, share_reference)
        second.result(timeout=10)
        pool.shutdown()


@pytest.mark.requirement("WF-CYC-0120-A")
def test_the_key_of_the_lock_of_the_reference_is_distinct_from_the_other_advisory_keys() -> None:
    others = [
        INSTALL_LOCK,
        ADMINISTRATORS_LOCK,
        NATURES_LOCK,
        DEFAULT_LOCK,
        TREE_LOCK,
        FORGETTING_LOCK,
    ]
    assert REFERENCE_LOCK not in others
