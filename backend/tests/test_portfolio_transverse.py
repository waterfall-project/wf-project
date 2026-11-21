# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What holds across the eight views of the portfolio, read on the service (US-2670/L4).

The criteria of US-2670 that no view closes alone, proved on every view the sentence names: the
projects In pricing included or not, a past date that nothing posterior reaches, a project
completed today and In progress on a past date, the node, the review just marked, the permissions
of the eight views and the project a reader opens, the scope each answer gives back and the one rule
of the periods. The four projects of the fabrics (``portfolio_support``) on the platform of a scene,
read at the date of the witness, 3 June 2026, or on a current day the tests pin to a day after the
whole chronology. Every answer is validated against the contract by the client of the tests.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from costs_support import cost, load_import
from portfolio_listing_support import READ, read, served
from portfolio_support import (
    OFFER,
    READ_ON,
    REVIEW,
    Portfolio,
    another_in_progress,
    at,
    node,
    portfolio,
)
from portfolio_transverse_support import (
    COUNTED,
    NODAL,
    NOW,
    VIEWS,
    exited,
    marked_on,
    now_is,
    plant_risks,
    weighted,
)
from projects_support import Scene
from projects_support import scene as make_scene
from sqlalchemy import select

from waterfall.core.resource_settings.tables import ResourceRole

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def fabrics(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Portfolio:
    """Give the four projects of the fabrics, on the platform of a scene."""
    stage: Scene = make_scene(api, owner, database, realm)
    return portfolio(api, stage)


# --- The projects In pricing ---------------------------------------------------------------------


@pytest.mark.requirement("WF-PTF-0010-A")
@pytest.mark.requirement("WF-PRJ-0090-A")
def test_the_projects_in_pricing_add_their_weighted_contribution_to_each_view_that_retains_them(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # « Le même portefeuille calculé avec et sans les projets en chiffrage donne des valeurs
    # différentes, et la différence égale la contribution de ces projets, pondérée par leur
    # probabilité de gain, hors le pipeline brut et la vue des risques, où elle ne l'est pas » : on
    # the value, the workload, the cost structure and the S-curve, read with ``in_progress`` then
    # ``in_progress,pricing``. The offer is priced as the project In progress — the same task, the
    # same eight hours and thousand of material —, so that its contribution is that project's figure
    # at 40 %, which « 40 % de sa charge dans le plan de charge agrégé pondéré » says of the hours.
    plant_risks(
        owner,
        [
            (fabrics.in_progress.marked[REVIEW][0], "Retard du fournisseur", "60.00"),
            (fabrics.offer.marked[OFFER][0], "Retard de livraison", "250.00"),
        ],
    )
    reader = fabrics.stage.reader
    found = {
        (view, states): served(api, reader, view, f"{READ}&states={states}")
        for view in (
            "projects",
            "value",
            "workload",
            "cost-structure",
            "cost-curve",
            "risks",
            "performance",
        )
        for states in ("in_progress", "pricing", "in_progress,pricing")
    }

    def without(view: str) -> Any:
        return found[view, "in_progress"]

    def only(view: str) -> Any:
        return found[view, "pricing"]

    def both(view: str) -> Any:
        return found[view, "in_progress,pricing"]

    assert both("value")["scope"]["project_count"] == 2
    # The list: the row of the offer comes with ``pricing``, whole and in the state it holds. The
    # health of the control (``getPortfolioPilotHealth``) is not read here: it counts the projects
    # In progress alone, a state it does not count being without effect, so that no offer adds to it.
    rows = {
        states: [(each["project_id"], each["state"]) for each in found["projects", states]["items"]]
        for states in ("in_progress", "pricing", "in_progress,pricing")
    }
    offer = (str(fabrics.offer.project_id), "pricing")
    assert rows["pricing"] == [offer]
    assert offer not in rows["in_progress"]
    assert sorted(rows["in_progress,pricing"]) == sorted([*rows["in_progress"], offer])
    # The value: the order book is the projects In progress, the pipeline the offers, gross whole
    # and weighted at 40 %; the difference of the weighted pipeline is the offer at its probability.
    assert both("value")["order_book"] == without("value")["order_book"]
    gross = Decimal(both("value")["pipeline_gross"]) - Decimal(without("value")["pipeline_gross"])
    assert gross == Decimal(without("value")["order_book"]) > 0
    difference = Decimal(both("value")["pipeline_weighted"]) - Decimal(
        without("value")["pipeline_weighted"]
    )
    assert difference == weighted(gross) < gross
    # The workload: each month of the difference is the hours of the project In progress at 40 %.
    months = [each["hours"] for each in without("workload")["monthly_totals"]]
    added = [
        Decimal(now["hours"]) - Decimal(before["hours"])
        for now, before in zip(
            both("workload")["monthly_totals"], without("workload")["monthly_totals"], strict=True
        )
    ]
    assert added == [weighted(hours) for hours in months]
    assert any(each > 0 for each in added)
    # The cost structure, each cost type and each node of the labour.
    for key in ("budget_by_cost_type", "remaining_by_cost_type", "labor_by_org_node"):
        added_by_key = {
            each["key"]: Decimal(each["amount"]) - Decimal(base["amount"])
            for each, base in zip(
                both("cost-structure")[key], without("cost-structure")[key], strict=True
            )
        }
        assert added_by_key == {
            each["key"]: weighted(each["amount"]) for each in without("cost-structure")[key]
        }
    # The S-curve: at every date the difference is the offer's own, and at the last of each series
    # the project In progress at 40 %.
    for series, base, offer in zip(
        both("cost-curve")["series"],
        without("cost-curve")["series"],
        only("cost-curve")["series"],
        strict=True,
    ):
        for point, before, alone in zip(
            series["points"], base["points"], offer["points"], strict=True
        ):
            assert Decimal(point["amount"]) - Decimal(before["amount"]) == Decimal(alone["amount"])
        assert Decimal(offer["points"][-1]["amount"]) == weighted(base["points"][-1]["amount"])
    # The risks: the offer's provision of 250 counts whole, not at 40 % (100): 60 + 250.
    assert without("risks")["identified_total"] == "60.00"
    assert only("risks")["identified_total"] == "250.00"
    assert both("risks")["identified_total"] == "310.00"
    # The performance counts the projects In progress alone: a state it does not count is no effect.
    assert both("performance")["cost_variance"] == without("performance")["cost_variance"]
    assert both("performance")["scope"]["project_count"] == 1
    assert both("performance")["scope"]["states"] == ["in_progress", "pricing"]


# --- The past date -------------------------------------------------------------------------------


@pytest.mark.requirement("WF-PTF-0010-A")
def test_a_past_date_is_reached_by_no_later_marking_no_later_import_and_no_later_transition(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « Calculé à une date passée, il ne change pas quand une révision est marquée après cette
    # date » : the eight views, read as of 3 June, give the same answer before and after a review
    # marked on 10 June, an import of actual costs of 12 June and the completion of the project on
    # 1 July. A date after the completion is another portfolio: the control that the writes landed.
    reader = fabrics.stage.reader
    running = fabrics.in_progress.project_id
    query = f"as_of={READ_ON}&states={COUNTED}"
    before = {view: served(api, reader, view, query) for view in VIEWS}
    after_marking, after_import = (f"as_of={day}&states={COUNTED}" for day in ("2026-06-11", "2026-06-13"))
    unwritten = [served(api, reader, "projects", each) for each in (after_marking, after_import)]
    marked_on(api, fabrics, running, "Revue de juin", at(6, 10))
    load_import(fabrics.stage, running, [cost("FA-2001", None, "250.00")], at=at(6, 12))
    exited(fabrics, running, "completed", at(7, 1))
    for view in VIEWS:
        assert served(api, reader, view, query) == before[view], view
    assert before["performance"]["scope"]["project_count"] == 1
    # The control that the writes landed, so that the stability is not true of nothing: a date after
    # the marking, then after the import, then after the completion, gives another answer.
    written = [served(api, reader, "projects", each) for each in (after_marking, after_import)]
    assert written[0] != unwritten[0]
    assert written[1] != unwritten[1]
    assert written[1] != written[0]
    assert served(api, reader, "performance", "as_of=2026-07-02")["scope"]["project_count"] == 0


@pytest.mark.requirement("WF-PTF-0010-A")
def test_a_project_completed_today_is_among_the_projects_in_progress_on_a_past_date(
    api: ContractClient, fabrics: Portfolio, monkeypatch: pytest.MonkeyPatch
) -> None:
    # « Un projet terminé aujourd'hui, en cours à une date passée, compte parmi les projets en
    # cours du portefeuille calculé à cette date » : a second project is completed on the current
    # day, 19 November at noon. Read as of the 18th, every view counts it In progress; as of the
    # 19th, or without a date, it is Completed: out of the projects In progress, in the period's.
    now_is(monkeypatch)
    second = another_in_progress(api, fabrics, "Second chantier", "PRJ-2674")
    exited(fabrics, second, "completed", NOW)
    reader = fabrics.stage.reader
    for view in VIEWS:
        counts = [
            served(api, reader, view, query)["scope"]["project_count"]
            for query in ("as_of=2026-11-18", "as_of=2026-11-19", "")
        ]
        assert counts == [2, 1, 1], view
    today = "from=2026-11-19&to=2026-11-19&states=completed"
    assert [
        served(api, reader, "projects", f"{today}&{query}")["scope"]["project_count"]
        for query in ("as_of=2026-11-18", "as_of=2026-11-19", "")
    ] == [0, 1, 1]


# --- The node ------------------------------------------------------------------------------------


@pytest.mark.requirement("WF-PTF-0010-A")
def test_the_node_restricts_only_the_labour_and_an_unknown_node_is_refused_on_every_view(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « Le filtre par nœud laisse inchangés les totaux hors main-d'œuvre » : a node with no role
    # restricts the workload and the labour of the cost structure to nothing, and changes no amount
    # of the list, of the value, of the performance, nor the material of the cost structure; the
    # node of the role changes nothing at all. « un nœud inconnu est refusé par 422 sur
    # /query/org_node_id ».
    database = fabrics.stage.database
    reader = fabrics.stage.reader
    with database.transaction() as session:
        own = session.scalar(
            select(ResourceRole.org_node_id).where(ResourceRole.id == fabrics.costs.role)
        )
    assert own is not None
    elsewhere = node(database, "AUTRE")
    query = f"{READ}&states={COUNTED}"
    for view in NODAL:
        whole = served(api, reader, view, query)
        on_own = served(api, reader, view, f"{query}&org_node_id={own}")
        elsewhere_only = served(api, reader, view, f"{query}&org_node_id={elsewhere}")
        assert on_own["scope"]["org_node_id"] == str(own), view
        assert elsewhere_only["scope"]["org_node_label"] == "Nœud AUTRE", view
        assert on_own | {"scope": whole["scope"]} == whole, view
        if view not in ("workload", "cost-structure"):
            assert elsewhere_only | {"scope": whole["scope"]} == whole, view
        refused = read(api, reader, view, f"{query}&org_node_id={UUID(int=1)}")
        assert refused.status_code == 422, view
        assert [(each["pointer"], each["code"]) for each in refused.json()["fields"]] == [
            ("/query/org_node_id", "UNKNOWN_ORG_NODE")
        ], view
    workload = served(api, reader, "workload", f"{query}&org_node_id={elsewhere}")
    assert workload["roles"] == []
    assert {each["hours"] for each in workload["monthly_totals"]} == {"0.00"}
    whole = served(api, reader, "cost-structure", query)
    structure = served(api, reader, "cost-structure", f"{query}&org_node_id={elsewhere}")
    assert structure["labor_by_org_node"] == []
    material = [each for each in whole["budget_by_cost_type"] if each["label"] == "Matériel"]
    assert material
    assert [
        each for each in structure["budget_by_cost_type"] if each["label"] == "Matériel"
    ] == material
    assert [
        each for each in structure["remaining_by_cost_type"] if each["label"] == "Matériel"
    ] == [each for each in whole["remaining_by_cost_type"] if each["label"] == "Matériel"]
