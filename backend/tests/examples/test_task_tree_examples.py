# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric example of the depth of the task tree (US-2780/L1), without a base.

The layout of the picture (``layout_task_tree``) of a plan of summaries, from the fixture
``task_tree_level_two.json`` (WF-PLA-0110). That the tree holds the summaries alone — no leaf, no
milestone —, and the levels a reading returns (``summaries_only``, ``max_level`` of
``filters.retained``), take a ``Reading`` of the structure, which reads the tracking of the tasks
on a database: ``test_task_tree_export.py`` replays them there.
"""

from datetime import date
from typing import TYPE_CHECKING, cast

import pytest

from waterfall.core.planning.task_tree_image import TreeNode, layout_task_tree

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]


def _nodes(plan: dict[str, object]) -> tuple[TreeNode, ...]:
    return tuple(
        TreeNode(label, _nodes(cast("dict[str, object]", below))) for label, below in plan.items()
    )


@pytest.mark.requirement("WF-PLA-0110-A")
def test_the_tree_at_level_two_draws_the_summaries_of_the_first_two_levels_under_the_project(
    example: Callable[[str], Example],
) -> None:
    # « Sur un planning de quatre niveaux, l'affichage demandé au niveau 2 ne représente que les
    # récapitulatives des deux premiers niveaux, sous le nœud du projet. » The drawing half.
    data = example("WF-PLA-0110-A#7e0f932d2ca2")
    plan = _nodes(cast("dict[str, object]", data["plan"]))
    layout = layout_task_tree(
        project=TreeNode("Projet", plan),
        depth=cast("int", data["depth"]),
        language="fr",
        revision="Révision 1",
        computed_on=date(2026, 3, 2),
    )
    assert [(box.label, box.level) for box in layout.boxes[1:]] == [
        tuple(each) for each in cast("list[list[object]]", data["drawn"])
    ]
    assert (layout.boxes[0].label, layout.boxes[0].level) == ("Projet", 0)
    # Each box of the first level hangs from the project (the box 0), the others from their parent.
    parents = {
        layout.boxes[child].label: layout.boxes[parent].label for parent, child in layout.edges
    }
    assert parents == {
        "Études": "Projet",
        "Conception": "Études",
        "Chantier": "Projet",
        "Pose": "Chantier",
    }
