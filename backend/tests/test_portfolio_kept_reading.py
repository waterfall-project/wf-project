# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a view of the portfolio reads at a past date: what a marking kept, no more (US-2680/L4).

The eight views — the list, the value, the workload, the performance, the cost structure, the
risks, the S-curve and the health of the pilotage — are read with ``as_of`` on the four projects of
the fabrics (``portfolio_support``): the statements each sends are heard, and none reads the tables
of the nodes, of the tasks, nor of the lines of an estimate (WF-DAT-0040). ``lines_read`` takes the
client, the reader and the engine of any platform: the three hundred projects of the reference
dataset (WF-QUA-0040, EP-13) replay it with their own.

What a marking kept does not move with what comes after it: a later import of actual costs leaves
it as it was. A revision marked before this EPIC kept none of the documents of the portfolio and
receives none (decision of the author of 17 November 2026): it contributes by what it kept.
"""

import json
from typing import TYPE_CHECKING, Any, cast

import pytest
from costs_support import cost, load_import
from portfolio_listing_support import READ, served
from portfolio_support import Portfolio, at, portfolio
from projects_support import Scene
from projects_support import scene as make_scene
from sqlalchemy import select, text
from statements_support import heard, tables_of, touching

from waterfall.api.contract import models
from waterfall.core.indicators.interface import PORTFOLIO_KINDS
from waterfall.core.indicators.tables import RevisionIndicator

if TYPE_CHECKING:
    from collections.abc import Mapping

    from projects_support import Person
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

# The eight views read with ``as_of``, by the name of their route, and the model of their answer.
VIEWS: Mapping[str, Any] = {
    "projects": models.PortfolioProjectRow,
    "value": models.PortfolioValue,
    "workload": models.PortfolioWorkload,
    "performance": models.PortfolioPerformance,
    "cost-structure": models.PortfolioCostStructure,
    "risks": models.PortfolioRisks,
    "cost-curve": models.PortfolioCostCurve,
    "pilot-health": models.PilotHealth,
}
# The tables of the nodes, of the tasks (and their links) and of the lines of an estimate.
LINES = ("node", "task", "task_link", "estimate_line")
# Every state a project can be in, asked all the same: no view counts the ones it does not read.
STATES = "in_progress,pricing,completed,created,lost,abandoned"


@pytest.fixture
def fabrics(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Portfolio:
    """Give the four projects of the fabrics, on the platform of a scene."""
    stage: Scene = make_scene(api, owner, database, realm)
    return portfolio(api, stage)


def lines_read(
    api: ContractClient, reader: Person, engine: Engine, query: str
) -> dict[str, list[str]]:
    """Read each view with a query that names a past date; give, by view, its statements on lines.

    Every view must answer and send at least one statement: a view that is silent was not read.
    """
    found: dict[str, list[str]] = {}
    for view in VIEWS:
        with heard(engine) as sent:
            served(api, reader, view, query)
        assert sent, view
        found[view] = touching(sent, LINES)
    return found


def documents(database: Database) -> list[tuple[Any, ...]]:
    """Give the documents every revision kept, by revision, kind and scope."""
    with database.transaction() as session:
        rows = session.scalars(
            select(RevisionIndicator).order_by(
                RevisionIndicator.revision_id, RevisionIndicator.kind, RevisionIndicator.scope
            )
        )
        return [
            (
                row.revision_id,
                row.kind,
                row.scope,
                row.computed_at,
                row.created_by,
                json.dumps(row.document, sort_keys=True),
            )
            for row in rows
        ]


def with_key(value: object, key: str) -> list[object]:
    """Give every value a key holds, wherever it stands in an answer."""
    if isinstance(value, dict):
        below = cast("dict[str, object]", value)
        found: list[object] = [below[key]] if key in below else []
        for each in below.values():
            found.extend(with_key(each, key))
        return found
    if isinstance(value, list):
        found = []
        for each in cast("list[object]", value):
            found.extend(with_key(each, key))
        return found
    return []


@pytest.mark.requirement("WF-DAT-0040-A")
def test_no_view_read_at_a_past_date_reads_a_node_a_task_nor_a_line_of_an_estimate(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « Aucune vue de portefeuille à une date passée […] ne lit de ligne de tâche ni de ligne de
    # devis. » The eight views, on every project the fabrics hold, at the date of the witness,
    # 3 June 2026: none sends a statement on the nodes, the tasks nor the lines (écart: the three
    # hundred projects are EP-13's, which replays ``lines_read`` on its own platform).
    reads = lines_read(
        api, fabrics.stage.reader, fabrics.stage.database.engine, f"{READ}&states={STATES}"
    )
    assert reads == {view: [] for view in VIEWS}


@pytest.mark.requirement("WF-DAT-0040-A")
def test_the_statements_heard_name_their_tables_and_the_day_reads_the_lines(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # The control of the test above, so that its silence means something: a statement names its
    # tables, those of a node of the organisation or of a background task are not those of the
    # nodes and of the tasks, and a view read on the current day, with no past date, does read
    # the lines.
    assert tables_of('SELECT a FROM "public".node AS n JOIN task ON task.id = n.id') == {
        "node",
        "task",
    }
    assert not touching(["SELECT 1 FROM background_task", "SELECT * FROM org_node"], LINES)
    with heard(fabrics.stage.database.engine) as sent:
        served(api, fabrics.stage.reader, "workload", "")
    assert touching(sent, LINES)


@pytest.mark.requirement("WF-DAT-0040-A")
def test_the_documents_of_a_marked_revision_are_the_same_after_a_later_import_of_costs(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « Les indicateurs conservés d'une révision marquée sont identiques avant et après un import
    # de coûts réels postérieur » — « les documents du portefeuille ne changent pas davantage »:
    # every document the marked revisions kept, those of the portfolio among them, is the same
    # after an import that came later, and the views that read them at the date of the marking
    # answer the same.
    before = documents(fabrics.stage.database)
    assert {each[1] for each in before} >= PORTFOLIO_KINDS
    views = ("projects", "value", "workload", "performance", "cost-structure", "cost-curve")
    first = {view: served(api, fabrics.stage.reader, view, READ) for view in views}
    load_import(
        fabrics.stage,
        fabrics.in_progress.project_id,
        [cost("FA-2680", None, "420.00")],
        at=at(5, 20),
    )
    assert documents(fabrics.stage.database) == before
    assert {view: served(api, fabrics.stage.reader, view, READ) for view in views} == first


@pytest.mark.story("US-2680")
def test_a_revision_marked_before_the_epic_keeps_none_of_the_documents_and_receives_none(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # Propre à l'US : « une révision marquée avant cet EPIC n'a pas ces documents, et n'en reçoit
    # pas » (décision de l'auteur du 2026-11-17): the fabrics lose every document of the portfolio
    # — what the marking of before the EPIC left — and the eight views answer at a past date,
    # without a line read, and none writes a document: the revisions contribute by what they kept.
    with owner.begin() as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        connection.execute(text("DELETE FROM revision_indicator WHERE kind LIKE 'portfolio\\_%'"))
    bare = documents(fabrics.stage.database)
    assert bare
    assert not {each[1] for each in bare} & PORTFOLIO_KINDS
    reads = lines_read(api, fabrics.stage.reader, fabrics.stage.database.engine, READ)
    assert reads == {view: [] for view in VIEWS}
    assert documents(fabrics.stage.database) == bare


@pytest.mark.story("US-2680")
@pytest.mark.parametrize("view", list(VIEWS))
def test_a_view_read_at_a_past_date_says_stored_wherever_the_contract_carries_it(
    api: ContractClient, fabrics: Portfolio, view: str
) -> None:
    # Propre à l'US : « elle rend ``is_stored`` partout où le contrat le porte »: every
    # ``is_stored`` of the answer of a view read at a past date is true — its figures are those of
    # the marking, never of the day — and a view whose schema carries it carries it in its answer.
    body = served(api, fabrics.stage.reader, view, READ)
    carried = "is_stored" in json.dumps(VIEWS[view].model_json_schema())
    stored = with_key(body, "is_stored")
    assert all(each is True for each in stored)
    assert bool(stored) or not carried
