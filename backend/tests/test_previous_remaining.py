# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The remaining to commit of the review before, copied at the opening of a revision (US-1580/L2).

A project In progress (``remaining_support``): its current revision, opened from a reference marked
in pricing, has no remaining before the review; reestimated, marked In progress, it gives the next
revision opened from it the figures and the re-estimated amount of each of its lines
(``previous_*``), read by ``listNodes`` beside the current ones; a line created since has none, and
a marked revision keeps its own. Every answer is checked against the contract.
"""

from typing import TYPE_CHECKING, Any

import pytest
from estimate_support import Costing, Lines, costing
from nodes_support import Tree, opened
from projects_support import Scene
from projects_support import scene as make_scene
from remaining_support import Review, in_progress, line_named, review_marked

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

BASIS = "reestimated_amount_basis"
PREVIOUS = (
    "previous_quantity",
    "previous_hours",
    "previous_unit_disbursement",
    "previous_reestimated_amount",
)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name, rated 65.00 for the year."""
    return costing(stage.database)


@pytest.fixture
def review(api: ContractClient, stage: Scene, costs: Costing) -> Review:
    """Give the project In progress: the wiring, its supplies at 100 and its labour at 100 hours."""

    def build(tree: Tree, lines: Lines) -> None:
        wiring = tree.made("Câblage")
        supplies = {"cost_category_id": str(costs.material), "unit_disbursement": "100"}
        lines.made(wiring, label="Fournitures", quantity="2", **supplies)
        lines.made(
            wiring,
            label="Raccordement",
            quantity="1",
            resource_role_id=str(costs.role),
            hours="100",
        )

    return in_progress(api, stage, build)


def previous(line: dict[str, Any]) -> tuple[Any, ...]:
    """Give the four figures of the review before of a line, as the reading gives them."""
    return tuple(line["estimate_line"][name] for name in PREVIOUS)


def reestimated(tree: Tree, label: str, reason: str | None = None, **figures: str) -> None:
    """Re-estimate the line of a label, as the manager does."""
    line = line_named(tree, label)
    sent = {BASIS: figures, "lock_version": line["lock_version"], "reason": reason}
    path = f"{tree.path}/nodes/{line['node_id']}/remaining"
    answer = tree.api.put(path, headers=tree.stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text


@pytest.mark.requirement("WF-RAE-0040-A")
def test_a_revision_opened_from_an_offer_marked_in_pricing_has_no_remaining_before(
    review: Review,
) -> None:
    # « Le reste à engager précédent est celui de la dernière révision marquée à l'état En
    # cours » : the reference was marked in pricing, an offer, no review (EP-09).
    for label in ("Fournitures", "Raccordement"):
        assert previous(line_named(review.tree, label)) == (None, None, None, None)


@pytest.mark.requirement("WF-RAE-0040-A")
def test_a_revision_opened_from_a_review_reads_the_figures_of_each_line_before_beside_its_own(
    api: ContractClient, review: Review, stage: Scene, costs: Costing
) -> None:
    # « Les montants et les grandeurs sont présents pour chaque ligne, au reste à engager
    # précédent et courant. » The review is the current revision, reestimated and marked In
    # progress; the next one copies its figures as its lines' previous ones.
    current = review.tree
    reestimated(current, "Fournitures", "Revue de novembre", unit_disbursement="120")
    reestimated(current, "Raccordement", hours="80")
    review_marked(stage, current.revision, "v2.0")
    following = Tree(api, stage, opened(api, stage))
    supplies, wiring = line_named(following, "Fournitures"), line_named(following, "Raccordement")
    assert previous(supplies) == ("2", None, "120.00", "240.00")
    assert previous(wiring) == ("1", "80", None, "5200.00")
    # The current figures are the same until a review changes them; the reason the line keeps.
    assert supplies["estimate_line"]["reestimated_amount"] == "240.00"
    assert supplies["estimate_line"]["remaining_reason"] == "Revue de novembre"
    # A line created since has none; a review leaves the figures before as they are.
    added = Lines(following).made(
        following.made("Reprise"),
        label="Borniers",
        quantity="1",
        cost_category_id=str(costs.material),
        unit_disbursement="30",
    )
    assert previous(added["nodes"][0]) == (None, None, None, None)
    reestimated(following, "Fournitures", unit_disbursement="90")
    assert previous(line_named(following, "Fournitures")) == ("2", None, "120.00", "240.00")
    # The marked review keeps its own, none: it was opened from the offer.
    assert previous(line_named(current, "Fournitures")) == (None, None, None, None)
    # The previous figures are filtered and sorted on as the others (WF-IHM-0060).
    query = "?kinds=estimate_line&previous_reestimated_amount_min=1000"
    assert [item["estimate_line"]["label"] for item in following.items(query)] == ["Raccordement"]
    query = "?kinds=estimate_line&sort_by=previous_reestimated_amount&sort_order=desc"
    labels = [item["estimate_line"]["label"] for item in following.items(query)]
    # Under each task: the wiring's lines by their amount before, the line added under its own.
    assert labels == ["Raccordement", "Fournitures", "Borniers"]
