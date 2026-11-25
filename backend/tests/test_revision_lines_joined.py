# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The readings that question the lines of a revision join them in the database (US-3070/L3b).

The own estimate of a risk is whole in the current revision, with its base: each as large as the
project (EP-30, "Entier dans la révision en cours, élagué au marquage"). The readings that count or
question the lines of a revision — the stamp of the lines the key of the indicators reads, the
categories of labour a revision employs — or of every project — the categories a line employs —
join them in the database rather than list their nodes into the service and send them back (#4912):
what they count is unchanged, an own estimate's lines among them, a base's left out (US-3050).
"""

from typing import TYPE_CHECKING

import pytest
from amendments_support import on
from estimate_support import Costing, Lines, costing
from projects_support import Scene
from projects_support import scene as make_scene
from risks_support import Costed, Risks, costed
from test_amendments_base_counted import labour

from waterfall.core.estimate.interface import category_is_employed, lines_stamp

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

WIRING, WIRED = "Câblage", "Câblage MO"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a fresh platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories the lines name, the labour one rated 65.00 for the year."""
    return costing(stage.database)


@pytest.fixture
def project(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed(api, stage, costs)


@pytest.mark.story("US-3070")
def test_a_line_only_an_own_estimate_adds_is_counted_and_employs_its_category_its_base_neither(
    api: ContractClient, project: Costed, costs: Costing
) -> None:
    # A labour line the own estimate of a risk adds employs its category and counts in the stamp of
    # the lines of the revision; its base, which holds a copy of every line of the main structure,
    # adds none to the count.
    risks = Risks(api, project)
    project_id, revision_id = project.project_id, project.revision_id
    with project.stage.database.transaction() as session:
        before = lines_stamp(session, project_id, revision_id).count
        assert category_is_employed(session, {costs.labour}) == frozenset()
    risk = risks.declared(label="Grue")
    with project.stage.database.transaction() as session:
        declared = lines_stamp(session, project_id, revision_id).count
    tree = on(project.tree, risk["structure_id"])
    Lines(tree).made(tree.made(WIRING), **labour(costs, WIRED))
    with project.stage.database.transaction() as session:
        after = lines_stamp(session, project_id, revision_id).count
        employed = category_is_employed(session, {costs.labour, costs.material})
    # The main structure gains the provision line, the own estimate a copy of each line before it.
    assert declared == 2 * before + 1
    assert after == declared + 1
    assert employed == {costs.labour, costs.material}
