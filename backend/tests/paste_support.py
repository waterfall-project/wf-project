# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the paste in the planning share: their fixtures and their steps (#3625).

The fixtures of the platform, the structure and the contributor, and the preview and the
confirmation of a block, which ``test_paste`` and ``test_paste_horizon`` read alike, declared once
so that the two files do not drift. A test file takes a fixture by naming it at its top
(``tree = paste_support.tree``): pytest reads it from there.
"""

from typing import TYPE_CHECKING, Any

import pytest
from history_support import counter
from nodes_support import Tree, opened, signed_in
from projects_support import scene as make_scene

if TYPE_CHECKING:
    from projects_support import Person, Scene
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


@pytest.fixture
def who(stage: Scene, realm: TestRealm) -> Person:
    """Give a contributor of the project whose token carries a session of sign-in."""
    return signed_in(stage, realm)


def preview(
    tree: Tree,
    target: dict[str, Any],
    column: str,
    rows: list[list[str]],
    who: Person | None = None,
) -> Any:
    """Preview a block pasted on a cell of a task; give the answer."""
    sent = {"target_node_id": target["node_id"], "target_column": column, "rows": rows}
    headers = (who or tree.stage.manager).headers
    return tree.api.post(f"{tree.path}/nodes/paste-preview", headers=headers, json=sent)


def planned(
    tree: Tree,
    target: dict[str, Any],
    column: str,
    rows: list[list[str]],
    who: Person | None = None,
) -> dict[str, Any]:
    """Preview a block that must be previewed; give the plan."""
    answer = preview(tree, target, column, rows, who)
    assert answer.status_code == 200, answer.text
    return answer.json()


def apply(
    tree: Tree, plan: dict[str, Any], who: Person | None = None, lock_version: int | None = None
) -> Any:
    """Confirm a plan at the counter of the structure unless one is sent; give the answer."""
    sent = {
        "paste_id": plan["paste_id"],
        "confirmed": True,
        "lock_version": counter(tree) if lock_version is None else lock_version,
    }
    headers = (who or tree.stage.manager).headers
    return tree.api.post(f"{tree.path}/nodes/paste", headers=headers, json=sent)


def applied(tree: Tree, plan: dict[str, Any], who: Person | None = None) -> dict[str, Any]:
    """Confirm a plan that must be confirmed; give what is answered."""
    answer = apply(tree, plan, who)
    assert answer.status_code == 200, answer.text
    return answer.json()
