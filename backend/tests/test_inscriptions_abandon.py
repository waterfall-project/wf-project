# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The inscriptions of the lineages no node holds any more, at an abandonment (US-3340).

An inscription holds no key to a node: it follows its lineage from revision to revision
(WF-PLA-0060). The abandonment of a revision deletes the nodes it alone carries, and the
inscriptions of their lineages with them (#4417); one a marked revision still holds stays. Every
answer is checked against the contract (``ContractClient``).
"""

from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from nodes_support import Tree, inscribed, inscribed_lineages, mark, opened
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.mark.requirement("WF-DAT-0010-A")
def test_the_abandonment_of_a_revision_deletes_the_inscriptions_of_the_lineages_it_alone_carried(
    api: ContractClient, stage: Scene
) -> None:
    # « L'abandon d'une révision en cours ne laisse aucune ligne portant son identifiant. », for the
    # inscriptions, which carry a lineage: the task created in the revision abandoned and inscribed
    # to a timeline leaves none; the one a marked revision still carries keeps its own (#4417).
    marked = Tree(api, stage, opened(api, stage))
    kept = marked.made("Études")
    mark(stage, marked.revision)
    current = Tree(api, stage, opened(api, stage))
    created = current.made("Câblage")
    timeline = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/timelines",
        headers=stage.manager.headers,
        json={"label": "Comité de pilotage"},
    ).json()["timeline_id"]
    inscribed(stage, kept, timeline)
    inscribed(stage, created, timeline)
    assert inscribed_lineages(stage) == {UUID(kept["lineage_id"]), UUID(created["lineage_id"])}
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{current.revision['revision_id']}"
    read = api.get(path, headers=stage.manager.headers).json()
    answer = api.delete(
        f"{path}?lock_version={read['lock_version']}", headers=stage.manager.headers
    )
    assert answer.status_code == 204, answer.text
    assert inscribed_lineages(stage) == {UUID(kept["lineage_id"])}
