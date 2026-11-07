# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The quality of project manager, judged again under the lock of the project (#2207).

A write reserved to the project managers (WF-PRJ-0060) is evaluated in a transaction of its own
before the route locks the project. A project manager withdrawn from the list meanwhile, by
``setContributors``, passed that evaluation: the route judges him again under the lock it takes
(``require_project_manager``). Each such write is tried against a list written meanwhile that
demotes its caller, which holds the lock of the project until it commits.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any
from uuid import UUID

import asked_contributors
import asked_lifecycle
import asked_projects
import asked_revisions
import asked_subprojects
import asked_work_breakdown
import pytest
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import func, select
from support import wait_for_a_lock

from waterfall.core.projects.interface import (
    ContributorEntry,
    ContributorsToWrite,
    Viewer,
    set_contributors,
)
from waterfall.core.projects.tables import Project, Subproject, WorkPackage
from waterfall.core.revisions.tables import Revision

if TYPE_CHECKING:
    from collections.abc import Callable

    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

# A write of the manager of the project of the scene, ready to be sent; and what it would change.
type Send = Callable[[], Any]

MANAGER_ONLY = {
    name
    for router in (
        asked_projects,
        asked_subprojects,
        asked_work_breakdown,
        asked_revisions,
        asked_lifecycle,
    )
    for name, quality in router.ON_PROJECT.items()
    if quality == "project_manager"
}


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


def project_path(stage: Scene) -> str:
    """Give the path of the project of the scene."""
    return f"{PROJECTS}/{stage.project['project_id']}"


def sent_by_the_manager(api: ContractClient, stage: Scene) -> dict[str, Send]:
    """Give, by operation, the write the manager sends; each would succeed without the demotion."""
    path, headers = project_path(stage), stage.manager.headers
    created = api.post(f"{path}/subprojects", headers=headers, json={"code": "A", "label": "A"})
    changed = api.post(f"{path}/subprojects", headers=headers, json={"code": "B", "label": "B"})
    revision = api.post(f"{path}/revisions", headers=headers, json={}).json()
    version = api.get(path, headers=headers).json()["lock_version"]
    breakdown = api.get(f"{path}/work-breakdown", headers=headers).json()
    return {
        "updateProject": lambda: api.patch(
            path, headers=headers, json={"label": "Autre", "lock_version": version}
        ),
        "createSubproject": lambda: api.post(
            f"{path}/subprojects", headers=headers, json={"code": "C", "label": "C"}
        ),
        "updateSubproject": lambda: api.patch(
            f"{path}/subprojects/{created.json()['subproject_id']}",
            headers=headers,
            json={"code": "A2", "label": "A2", "lock_version": 0},
        ),
        "deleteSubproject": lambda: api.delete(
            f"{path}/subprojects/{changed.json()['subproject_id']}?lock_version=0",
            headers=headers,
        ),
        "setWorkBreakdown": lambda: api.put(
            f"{path}/work-breakdown",
            headers=headers,
            json={
                "work_packages": [{"label": "Lot", "order_items": []}],
                "lock_version": breakdown["lock_version"],
            },
        ),
        "abandonRevision": lambda: api.delete(
            f"{path}/revisions/{revision['revision_id']}?lock_version={revision['lock_version']}",
            headers=headers,
        ),
        "markRevision": lambda: api.post(
            f"{path}/revisions/{revision['revision_id']}/mark",
            headers=headers,
            json={"version_name": "V1", "lock_version": revision["lock_version"]},
        ),
        "exitProject": lambda: api.post(
            f"{path}/exit",
            headers=headers,
            json={
                "to_state": "abandoned",
                "confirmed": True,
                "lock_version": version,
                "current_revision": {"action": "abandon"},
            },
        ),
    }


def written(stage: Scene) -> tuple[Any, ...]:
    """Give what the manager's writes change: the project, its subprojects, work and revisions."""
    with stage.database.transaction() as session:
        project = session.execute(
            select(
                Project.label,
                Project.state,
                Project.lock_version,
                Project.work_breakdown_lock_version,
                Project.current_revision_id,
            )
        ).one()
        counts = [
            session.scalar(select(func.count()).select_from(table))
            for table in (Subproject, WorkPackage, Revision)
        ]
        labels = sorted(session.scalars(select(Subproject.code)))
    return (*project, *counts, labels)


def demote_the_manager(stage: Scene, api: ContractClient, during: Send) -> Any:
    """Send a write while the list of the contributors demotes its manager, uncommitted.

    The list is written under the lock of the project, as ``setContributors`` does: the write waits
    for it, then finds its caller a plain contributor, the other one becoming the project manager.
    """
    path = project_path(stage)
    counter = api.get(f"{path}/contributors", headers=stage.manager.headers).json()["lock_version"]
    write = ContributorsToWrite(
        (
            ContributorEntry(stage.participant.user_id, "project_manager"),
            ContributorEntry(stage.manager.user_id, "contributor"),
        ),
        counter,
    )
    with ThreadPoolExecutor(1) as other, stage.database.transaction() as listing:
        set_contributors(
            listing, UUID(stage.project["project_id"]), write, Viewer(stage.manager.user_id, ())
        )
        sending = other.submit(during)
        wait_for_a_lock(stage.database)
        assert not sending.done()
    return sending.result(timeout=10)


@pytest.mark.requirement("WF-PRJ-0060-A")
@pytest.mark.parametrize(
    "operation",
    [
        "updateProject",
        "createSubproject",
        "updateSubproject",
        "deleteSubproject",
        "setWorkBreakdown",
        "abandonRevision",
        "markRevision",
        "exitProject",
    ],
)
def test_a_write_reserved_to_the_project_managers_finds_its_caller_demoted_under_the_lock(
    api: ContractClient, stage: Scene, operation: str
) -> None:
    send = sent_by_the_manager(api, stage)[operation]
    before = written(stage)
    answer = demote_the_manager(stage, api, send)
    assert answer.status_code == 403, answer.text
    body = answer.json()
    assert (body["code"], body["params"]) == (
        "NOT_PROJECT_MANAGER",
        {"missing_condition": "is_project_manager"},
    )
    assert written(stage) == before


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_a_caller_withdrawn_from_the_project_meanwhile_is_refused_as_a_stranger_is(
    api: ContractClient, stage: Scene
) -> None:
    # No longer a contributor: 403 ``NOT_CONTRIBUTOR`` for who holds ``all_projects_read``, 404 for
    # who does not (the manager of the scene holds none).
    path = project_path(stage)
    send = sent_by_the_manager(api, stage)["updateProject"]
    counter = api.get(f"{path}/contributors", headers=stage.manager.headers).json()["lock_version"]
    write = ContributorsToWrite(
        (ContributorEntry(stage.participant.user_id, "project_manager"),), counter
    )
    with ThreadPoolExecutor(1) as other, stage.database.transaction() as listing:
        set_contributors(
            listing, UUID(stage.project["project_id"]), write, Viewer(stage.manager.user_id, ())
        )
        sending = other.submit(send)
        wait_for_a_lock(stage.database)
    answer = sending.result(timeout=10)
    assert (answer.status_code, answer.json()["code"]) == (404, "NOT_FOUND")


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_every_operation_reserved_to_the_project_managers_is_tried_against_a_demotion(
    api: ContractClient, stage: Scene
) -> None:
    # A route reserved to the project managers that is added joins the list above, with the other
    # one that judges its caller under the lock, ``setContributors`` (``test_contributors.py``).
    tried = set(sent_by_the_manager(api, stage))
    assert tried == MANAGER_ONLY
    assert asked_contributors.ON_PROJECT["setContributors"] == "project_manager"
