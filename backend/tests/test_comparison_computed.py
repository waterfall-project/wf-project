# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The values the planning engine computes modify no task of a comparison (US-3300/L5, #4312).

WF-REV-0080 modifies a task by « ses dates, sa durée, son état et son parent ». Its total float and
its membership of the critical path are computed from the whole structure, and change when another
task does, the task itself unchanged: they make no task modified, and bear no difference. An offer
of two parallel branches of three days is marked; the amendment lengthens a task of the critical
path and is marked. Both bodies, read from what is kept and from the rows, are the same.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from nodes_support import Tree, opened
from projects_support import Scene
from projects_support import scene as make_scene
from test_comparison import by_label, compared, follow, mark

from waterfall.api.comparison import comparison_body, kept_comparison
from waterfall.api.nodes import node_body, read_body
from waterfall.core.estimate.interface import ComparisonAsked, compare_revisions
from waterfall.core.planning.interface import NodeFilters

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

REQUIREMENT = "WF-REV-0080-A"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


def days(count: str) -> dict[str, Any]:
    """Give the facet of a task of so many days."""
    return {"duration": {"value": count, "unit": "d"}}


@pytest.fixture
def pair(api: ContractClient, stage: Scene) -> tuple[dict[str, Any], dict[str, Any]]:
    """Mark an offer of two branches of three days, then an amendment that lengthens the first.

    « Études » bears « Conception » (2 d), which « Plans » (1 d) follows; « Achats » bears
    « Commande » (3 d); « Recette » (1 d) stands alone. « Conception », « Plans » and « Commande »
    are critical; « Recette » carries two days of float. The amendment makes « Conception » four
    days long: « Plans » moves two days later, « Commande » leaves the critical path, two days of
    float gained, its dates kept, and « Recette » gains two days of float.
    """
    offer = opened(api, stage)
    tree = Tree(api, stage, offer)
    studies = tree.made("Études")
    design = tree.made("Conception", parent_id=studies["node_id"], task=days("2"))
    follow(tree, tree.made("Plans", parent_id=studies["node_id"], task=days("1")), design)
    buying = tree.made("Achats")
    tree.made("Commande", parent_id=buying["node_id"], task=days("3"))
    tree.made("Recette", task=days("1"))
    mark(stage, offer, "v1.0")
    amendment = opened(api, stage)
    following = Tree(api, stage, amendment)
    following.changed(by_label(following.items())["Conception"], duration=days("4")["duration"])
    mark(stage, amendment, "v2.0")
    return offer, amendment


def task_of(found: dict[str, Any], label: str) -> dict[str, Any]:
    """Give the time facet of a node returned, by its label."""
    return by_label(found["items"])[label]["task"]


def rows_and_kept(stage: Scene, base: dict[str, Any], read: dict[str, Any]) -> tuple[bytes, bytes]:
    """Give the body of the comparison read from the rows, and that read from what is kept."""
    asked = ComparisonAsked(UUID(base["revision_id"]), UUID(read["revision_id"]), NodeFilters())
    project_id = UUID(stage.project["project_id"])
    with stage.database.transaction() as session:
        found = compare_revisions(session, project_id, asked, node_body)
        rows = bytes(read_body(comparison_body(found, None)).body)
        kept = kept_comparison(session, project_id, asked, None)
    assert kept is not None
    return rows, bytes(read_body(kept).body)


@pytest.mark.requirement(REQUIREMENT)
def test_a_critical_task_lengthened_modifies_it_the_tasks_it_moves_and_their_summaries_alone(
    api: ContractClient, stage: Scene, pair: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    # « pour une tâche, ses dates, sa durée, son état et son parent » : the task lengthened, the
    # one it moves and the summary of both modified; the task whose float alone changes, which
    # leaves the critical path, and its summary unchanged, without a base or a difference.
    offer, amendment = pair
    found = compared(api, stage, (offer, amendment))
    before = compared(api, stage, (offer, offer))
    critical = [task_of(each, "Commande")["is_critical"] for each in (found, before)]
    assert critical == [False, True]
    assert task_of(found, "Recette")["total_float"] != task_of(before, "Recette")["total_float"]
    nodes = by_label(found["items"])
    assert nodes["Conception"]["changes"] == ["dates", "duration"]
    assert nodes["Conception"]["deltas"] == {
        "task": {"duration": {"value": "2", "unit": "d"}, "finish": 2}
    }
    assert nodes["Plans"]["changes"] == ["dates"]
    assert "dates" in nodes["Études"]["changes"]
    marks = {label: nodes[label]["difference"] for label in nodes}
    assert marks == {
        "Études": "modified",
        "Conception": "modified",
        "Plans": "modified",
        "Achats": "unchanged",
        "Commande": "unchanged",
        "Recette": "unchanged",
    }
    assert {nodes[each]["base"] is None for each in ("Achats", "Commande", "Recette")} == {True}
    rows, kept = rows_and_kept(stage, offer, amendment)
    assert rows == kept


@pytest.mark.requirement(REQUIREMENT)
def test_a_task_that_enters_the_critical_path_without_moving_is_unchanged(
    api: ContractClient, stage: Scene, pair: tuple[dict[str, Any], dict[str, Any]]
) -> None:
    # The offer compared with the amendment that follows it, its base: « Commande » enters the
    # critical path, its dates kept, and is unchanged, as « Achats »; « Conception », shorter, and
    # « Plans », earlier, are modified.
    offer, amendment = pair
    found = compared(api, stage, (amendment, offer))
    assert task_of(found, "Commande")["is_critical"] is True
    nodes = by_label(found["items"])
    marks = {label: nodes[label]["difference"] for label in nodes}
    assert marks == {
        "Études": "modified",
        "Conception": "modified",
        "Plans": "modified",
        "Achats": "unchanged",
        "Commande": "unchanged",
        "Recette": "unchanged",
    }
    rows, kept = rows_and_kept(stage, amendment, offer)
    assert rows == kept
