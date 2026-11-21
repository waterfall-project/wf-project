# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The own estimates a copy renames, as the session reads them afterwards (US-3060/L3, #4041).

``rename_own_estimates`` writes the labels by one statement that does not synchronize the session:
the structures a copy added to it must read the new label, not the one they were copied with.
"""

from typing import TYPE_CHECKING

import pytest
from merges_support import client, costed_project
from sqlalchemy import select

from waterfall.core.revisions.interface import rename_own_estimates
from waterfall.core.revisions.tables import CostStructure

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from realm import TestRealm
    from risks_support import Costed
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings


@pytest.fixture
def api(
    contract: OpenAPI,
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
) -> ContractClient:
    """Give a client of the application."""
    return client(contract, database, keycloak, realm_settings, queue)


@pytest.fixture
def project(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed_project(api, owner, database, realm)


@pytest.mark.story("US-3060")
def test_a_structure_the_session_holds_reads_the_label_it_was_renamed_to(
    database: Database, project: Costed
) -> None:
    # The copy of a revision adds the structures it copies to the session with the label of their
    # source; the rename of the own estimates, one statement, must leave them reading the label of
    # their risk (#4041).
    with database.transaction() as session:
        structure = session.get(CostStructure, (project.project_id, project.structure_id))
        assert structure is not None
        before = structure.label
        rename_own_estimates(session, project.project_id, {project.structure_id: "Retard"})
        assert structure.label == "Retard"
        assert before != "Retard"
        stored = session.scalars(
            select(CostStructure.label).where(CostStructure.id == project.structure_id)
        ).one()
        assert stored == "Retard"
