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
from portfolio_listing_support import PORTFOLIO, READ, served
from portfolio_support import Portfolio, at, portfolio
from projects_support import Scene
from projects_support import scene as make_scene
from sqlalchemy import select, text
from statements_support import heard, tables_of, touching

from waterfall.core.indicators.interface import PORTFOLIO_KINDS
from waterfall.core.indicators.tables import RevisionIndicator

if TYPE_CHECKING:
    from jsonschema_path import SchemaPath
    from projects_support import Person
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

# The eight views read with ``as_of``, by the name of their route.
VIEWS = (
    "projects",
    "value",
    "workload",
    "performance",
    "cost-structure",
    "risks",
    "cost-curve",
    "pilot-health",
)
# The tables of the nodes, of the tasks (and their links) and of the lines of an estimate.
LINES = ("node", "task", "task_link", "estimate_line")
# Where a view read at a past date finds what a marking kept: the documents, by revision.
KEPT = ("revision_indicator",)
# What a revision marked before the EPIC still gives: its revision and its project, no document.
BARE = ("revision", "project")
# Every state a project can be in, asked all the same: no view counts the ones it does not read.
STATES = "in_progress,pricing,completed,created,lost,abandoned"


@pytest.fixture
def fabrics(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Portfolio:
    """Give the four projects of the fabrics, on the platform of a scene."""
    stage: Scene = make_scene(api, owner, database, realm)
    return portfolio(api, stage)


def lines_read(
    api: ContractClient, reader: Person, engine: Engine, query: str, kept: tuple[str, ...]
) -> dict[str, list[str]]:
    """Read each view with a query that names a past date; give, by view, its statements on lines.

    Every view must answer and, to prove it was read, send a statement on one of the tables of
    ``kept``, the ones its documents are kept in: the session and the permissions send some of
    their own, whatever a view reads.
    """
    found: dict[str, list[str]] = {}
    for view in VIEWS:
        with heard(engine) as sent:
            served(api, reader, view, query)
        assert touching(sent, kept), view
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
        api, fabrics.stage.reader, fabrics.stage.database.engine, f"{READ}&states={STATES}", KEPT
    )
    assert reads == {view: [] for view in VIEWS}


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
    assert tables_of("SELECT 1 FROM a, node WHERE a.id = node.id") == {"a", "node"}
    assert tables_of("SELECT 1 FROM a x, b AS y, estimate_line ORDER BY 1") == {
        "a",
        "b",
        "estimate_line",
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
    reads = lines_read(api, fabrics.stage.reader, fabrics.stage.database.engine, READ, BARE)
    assert reads == {view: [] for view in VIEWS}
    assert documents(fabrics.stage.database) == bare
    # What the views render without a document: the revision counts by what it kept — its project,
    # its budget — and the figures that only a document carries are empty or nil.
    answers = {view: served(api, fabrics.stage.reader, view, READ) for view in VIEWS}
    rows = answers["projects"]["items"]
    assert [(row["state"], row["reference_budget"]) for row in rows] == [("in_progress", "1520.00")]
    assert answers["value"]["order_book"] == "1520.00"
    assert answers["value"]["pipeline_gross"] == "0.00"
    assert answers["performance"]["reference_budget"] == "1520.00"
    assert all(each["hours"] == "0.00" for each in answers["workload"]["monthly_totals"])
    assert answers["risks"]["identified_total"] == "0.00"
    assert answers["risks"]["heaviest"] == []
    assert answers["cost-structure"]["budget_by_cost_type"] == []
    assert answers["cost-structure"]["labor_by_org_node"] == []


def declares(schema: SchemaPath, key: str, depth: int = 0) -> bool:
    """Tell whether a schema of the contract, or any below it, declares a property of this name."""
    if depth > 16:
        message = "the schema nests deeper than any answer of the portfolio"
        raise AssertionError(message)
    if "properties" in schema:
        for name, below in (schema / "properties").str_items():
            if name == key or declares(below, key, depth + 1):
                return True
    for each in ("items", "additionalProperties"):
        opened = each in schema and isinstance((schema / each).read_value(), dict)
        if opened and declares(schema / each, key, depth + 1):
            return True
    for each in ("allOf", "oneOf", "anyOf"):
        if each in schema:
            for index in range(len(cast("list[object]", (schema / each).read_value()))):
                if declares(schema / each / index, key, depth + 1):
                    return True
    return False


@pytest.mark.story("US-2680")
@pytest.mark.parametrize("view", VIEWS)
def test_no_view_read_at_a_past_date_carries_is_stored_in_the_contract_yet(
    api: ContractClient, fabrics: Portfolio, view: str
) -> None:
    # Propre à l'US : « elle rend ``is_stored`` partout où le contrat le porte ». Aucune des huit
    # vues ne le porte aujourd'hui: the schema of the answer the route serves, whatever lies in
    # it, declares no ``is_stored``, and the answer carries none. The day the contract adds one,
    # this test fails, and must then ask that every ``is_stored`` of the answer be true — the
    # figures of a past date are those of the marking, never of the day.
    body = served(api, fabrics.stage.reader, view, READ)
    [schema] = api.schema("GET", f"{PORTFOLIO}/{view}", 200, "application/json")
    # The control: the schema is the one of this answer, it declares what the answer carries.
    assert declares(schema, next(iter(body))), view
    assert not declares(schema, "is_stored"), view
    assert not with_key(body, "is_stored"), view
