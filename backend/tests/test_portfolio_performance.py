# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The performance of the portfolio, read on the service (``getPortfolioPerformance``; US-2710).

The indices of the sums of the projects In progress, their variances and projections, the
distribution by zone and the evolution by quarter, on the projects of the fabrics
(``portfolio_support``): the documents ``project`` their markings kept are set to the amounts of the
sentence under test, as a marking of EP-10 would have kept them, then read at a past date. The
current day is read against the indicators of the project that the service gives. Every answer is
validated against the contract by the client of the tests.
"""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from costs_support import cost, load_import
from indicators_support import thresholds
from portfolio_support import (
    READ_ON,
    REVIEW,
    Portfolio,
    another_in_progress,
    at,
    current_of,
    portfolio,
)
from projects_support import MANAGING, Scene
from projects_support import scene as make_scene
from sqlalchemy import select, text, update

from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.projects.interface import Viewer
from waterfall.core.resource_settings.tables import OrgNode, ResourceRole
from waterfall.core.revisions.interface import create_revision, mark_revision
from waterfall.platform.audit import Act
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

PERFORMANCE = "/api/v1/portfolio/performance"
INDICATORS = "/api/v1/projects/{project_id}/indicators"
# The current day of the tests of the day, after the whole chronology of the fabrics.
NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
# Two days of the chronology: both projects In progress, then the completed one out of it.
BOTH = date(2026, 4, 14)
# The fixture of the example of WF-PTF-0070-A: its two projects, and the projection it expects.
EXAMPLE = Path(__file__).resolve().parents[2] / "fixtures" / "portfolio"
WATCH, ALERT = "0.9", "0.8"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give the platform of a scene: its sessions and its project."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def fabrics(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Portfolio:
    """Give the four projects of the fabrics, on the platform of a scene."""
    stage: Scene = make_scene(api, owner, database, realm)
    return portfolio(api, stage)


def example() -> dict[str, Any]:
    """Read the fixture of the example of the projection at the observed rate of the sums."""
    path = EXAMPLE / "projection_at_observed_rate.json"
    document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return document


def figures(project: dict[str, str], planned: str, remaining: str) -> dict[str, str]:
    """Give the amounts a project keeps: those of the example, with its planned value, remaining."""
    return {**project, "planned_value": planned, "remaining": remaining}


def kept(
    owner: Engine, revision_id: UUID, amounts: dict[str, str], cost: str, schedule: str
) -> None:
    """Set the document ``project`` a marking kept to amounts and indices, as a marking keeps them.

    A marked revision is immutable: the trigger that says so is set aside, as a superuser. An index
    is its text, or ``-`` for one not computable.
    """

    def computable(shown: str, reason: str) -> dict[str, Any]:
        if shown == "-":
            return {
                "value": {"is_computable": False, "value": None, "reason": reason},
                "zone": None,
            }
        return {"value": {"is_computable": True, "value": shown, "reason": None}, "zone": None}

    where = (RevisionIndicator.revision_id == revision_id) & (RevisionIndicator.kind == "project")
    with owner.begin() as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        held = connection.execute(
            select(RevisionIndicator.document).where(where, RevisionIndicator.scope == "project")
        ).scalar_one()
        document = {
            **held,
            **amounts,
            "cost_index": computable(cost, "no_actual_cost"),
            "schedule_index": computable(schedule, "no_planned_value"),
        }
        connection.execute(
            update(RevisionIndicator)
            .where(where, RevisionIndicator.scope == "project")
            .values(document=document)
        )


def read(api: ContractClient, fabrics: Portfolio, query: str = "") -> dict[str, Any]:
    """Read the performance as the manager that reads the portfolio does; the contract judges it."""
    answer = api.get(f"{PERFORMANCE}{query}", headers=fabrics.stage.reader.headers)
    assert answer.status_code == 200, answer.text
    body: dict[str, Any] = answer.json()
    return body


def review_of(fabrics: Portfolio, project: str) -> UUID:
    """Give the review marked of the project In progress or of the one completed."""
    chosen = fabrics.in_progress if project == "running" else fabrics.completed
    return chosen.marked[REVIEW][0]


def two_projects(owner: Engine, fabrics: Portfolio) -> None:
    """Keep the two projects of the example: budget 1 000, earned value 400 and 500, cost 500."""
    first, second = example()["projects"]
    kept(owner, review_of(fabrics, "running"), figures(first, "600.00", "700.00"), "0.8", "0.6667")
    kept(owner, review_of(fabrics, "completed"), figures(second, "500.00", "600.00"), "1", "1")


@pytest.mark.requirement("WF-PTF-0070-A")
def test_the_indices_are_ratios_of_sums_of_the_projects_in_progress_alone_and_the_rate_is_2222(
    api: ContractClient, fabrics: Portfolio, owner: Engine
) -> None:
    # Without a cost nor a planned value kept, no index is computable and says why, and the
    # projection at the observed rate is not while the aggregated cost index is not; the two
    # others are sums of the projects.
    thresholds(fabrics.stage, WATCH, ALERT)
    empty = read(api, fabrics, f"?as_of={BOTH}")
    no_cost = {"is_computable": False, "value": None, "reason": "no_actual_cost"}
    assert empty["cost_index"] == {"value": no_cost, "zone": None}
    assert empty["schedule_index"]["value"]["reason"] == "no_planned_value"
    assert empty["projections"]["at_observed_rate"] == no_cost
    assert empty["projections"]["variance_at_observed_rate"] is None
    assert (empty["projections"]["at_budget"], empty["projections"]["project_manager"]) == (
        "3040.00",
        "3040.00",
    )
    # « L'indice de coût agrégé est le rapport de la somme des valeurs acquises à la somme des
    # coûts réels des projets du périmètre. » : earned values 400 and 500 over costs 500 and 500
    # give 0.9, planned values 600 and 500 give 0.8182 — the indices of the projects, 0.8 and 1, and
    # 0.6667 and 1, would give 0.9 and 0.8333 as a mean. Four decimals, each sum already rounded.
    two_projects(owner, fabrics)
    body = read(api, fabrics, f"?as_of={BOTH}")
    assert body["scope"] == {
        "states": ["in_progress"],
        "as_of": "2026-04-14",
        "from": "2025-04-15",
        "to": "2026-04-14",
        "org_node_id": None,
        "org_node_label": None,
        "project_count": 2,
    }
    assert body["reference_budget"] == "2000.00"
    assert body["cost_index"] == {
        "value": {"is_computable": True, "value": "0.9", "reason": None},
        "zone": "nominal",
    }
    assert body["schedule_index"]["value"]["value"] == "0.8182"
    # The variances are the sums of those of the projects: -100 and 0, -200 and 0.
    assert (body["cost_variance"], body["schedule_variance"]) == ("-100.00", "-200.00")
    # « Sur deux projets de budget 1 000, de valeur acquise 400 et 500 et de coût réel 500 et 500,
    # la projection au rythme constaté agrégée vaut 2 222 et non 2 250. » : the example of the
    # harness, by its fixture, on the service. At budget, the cost plus the budget less the earned
    # value (1 000 + 2 000 - 900); by the project manager the cost plus the remaining to commit
    # (1 000 + 1 300); each less the budget.
    data = example()
    projections = body["projections"]
    observed = projections["at_observed_rate"]
    assert observed == {"is_computable": True, "value": data["at_observed_rate"], "reason": None}
    assert observed["value"].split(".")[0] == data["at_observed_rate_whole"]
    assert observed["value"] != f"{data['mean_of_indices_projection']}.00"
    assert (projections["at_budget"], projections["project_manager"]) == ("2100.00", "2300.00")
    assert (projections["variance_at_budget"], projections["variance_project_manager"]) == (
        "100.00",
        "300.00",
    )
    assert projections["variance_at_observed_rate"] == "222.22"

    # « … seuls les projets en cours du périmètre y contribuent ; scope.states nomme les états
    # demandés » : the offer and the project completed in the period, asked, change no sum and
    # stay out of the count; asking none of the projects In progress retains none.
    default = read(api, fabrics, f"?as_of={READ_ON}")
    asked = read(api, fabrics, f"?as_of={READ_ON}&states=in_progress,pricing,completed")
    assert asked["scope"]["states"] == ["in_progress", "pricing", "completed"]
    assert asked["scope"]["project_count"] == 1
    assert {name: value for name, value in asked.items() if name != "scope"} == {
        name: value for name, value in default.items() if name != "scope"
    }
    none = read(api, fabrics, f"?as_of={READ_ON}&states=pricing,completed")
    assert (none["scope"]["states"], none["scope"]["project_count"]) == (
        ["pricing", "completed"],
        0,
    )
    assert none["reference_budget"] == "0.00"
    assert none["cost_index"]["value"]["is_computable"] is False
    assert all(each["project_count"] == 0 for each in none["zone_distribution"])


@pytest.mark.requirement("WF-PTF-0070-A")
def test_the_distribution_counts_each_project_once_by_index_in_zones_classified_at_the_reading(
    api: ContractClient, fabrics: Portfolio, owner: Engine
) -> None:
    # « La répartition par zone compte chaque projet une fois. » : once by index; the cost index of
    # the projects, 0.8 and 1, is in watch and nominal at the thresholds 0.9 and 0.8; the schedule
    # index of one, not computable, is in none of the zones of that index.
    thresholds(fabrics.stage, WATCH, ALERT)
    first, second = example()["projects"]
    running, completed = review_of(fabrics, "running"), review_of(fabrics, "completed")
    kept(owner, running, figures(first, "600.00", "700.00"), "0.8", "0.6667")
    kept(owner, completed, figures(second, "0.00", "600.00"), "1", "-")

    def counted(distribution: list[dict[str, Any]]) -> dict[str, list[int]]:
        by_zone = {(each["index"], each["zone"]): each["project_count"] for each in distribution}
        return {
            index: [by_zone[(index, zone)] for zone in ("nominal", "watch", "alert")]
            for index in ("cost", "schedule")
        }

    body = read(api, fabrics, f"?as_of={BOTH}")
    assert [(each["index"], each["zone"]) for each in body["zone_distribution"]] == [
        ("cost", "nominal"),
        ("cost", "watch"),
        ("cost", "alert"),
        ("schedule", "nominal"),
        ("schedule", "watch"),
        ("schedule", "alert"),
    ]
    assert counted(body["zone_distribution"]) == {"cost": [1, 1, 0], "schedule": [0, 0, 1]}
    # The zones are classified at the reading, on the thresholds read now, for a document kept as
    # for one of the day (EP-10): at 0.95 and 0.85 the project of 1 stays nominal and the one of 0.8
    # goes to alert; the aggregated cost index, 0.9 on 1 000 of cost, goes from nominal to watch,
    # its value unchanged.
    thresholds(fabrics.stage, "0.95", "0.85")
    after = read(api, fabrics, f"?as_of={BOTH}")
    assert counted(after["zone_distribution"]) == {"cost": [1, 0, 1], "schedule": [0, 0, 1]}
    assert body["cost_index"]["value"] == after["cost_index"]["value"]
    assert (body["cost_index"]["zone"], after["cost_index"]["zone"]) == ("nominal", "watch")


@pytest.mark.requirement("WF-PTF-0070-A")
def test_the_evolution_has_a_point_by_quarter_each_read_at_its_last_day_and_never_changes_after(
    api: ContractClient, fabrics: Portfolio, owner: Engine
) -> None:
    # « … un point par trimestre civil que la période touche, du plus ancien au plus récent,
    # chaque indice lu au dernier jour du trimestre, et à la date de calcul pour celui qui la
    # contient, dont les indices égalent ceux du jour ; un trimestre sans projet en cours est non
    # calculable. » : read on 3 June, the project completed on 15 April is In progress on
    # 31 March — both give 0.9 and 0.8182 —, and no project is before 2026.
    thresholds(fabrics.stage, WATCH, ALERT)
    two_projects(owner, fabrics)
    body = read(api, fabrics, f"?as_of={READ_ON}")
    quarterly = body["quarterly"]
    assert [each["quarter"] for each in quarterly] == [
        "2025-Q2",
        "2025-Q3",
        "2025-Q4",
        "2026-Q1",
        "2026-Q2",
    ]
    for empty in quarterly[:3]:
        assert empty["cost_index"] == {
            "is_computable": False,
            "value": None,
            "reason": "no_actual_cost",
        }
        assert empty["schedule_index"]["reason"] == "no_planned_value"
    assert (quarterly[3]["cost_index"]["value"], quarterly[3]["schedule_index"]["value"]) == (
        "0.9",
        "0.8182",
    )
    # On 3 June the project completed is out of the sums: the point of the quarter that holds the
    # date is the top of the answer, the project In progress alone.
    assert (body["cost_index"]["value"]["value"], body["schedule_index"]["value"]["value"]) == (
        "0.8",
        "0.6667",
    )
    assert quarterly[4]["cost_index"] == body["cost_index"]["value"]
    assert quarterly[4]["schedule_index"] == body["schedule_index"]["value"]
    # A period asked bounds the quarters: January to March touches the first quarter alone, read on
    # its last day, 31 March; a period that runs past the date repeats the reading of that date.
    first = read(api, fabrics, f"?as_of={READ_ON}&from=2026-01-01&to=2026-03-31")["quarterly"]
    assert [each["quarter"] for each in first] == ["2026-Q1"]
    assert first[0]["cost_index"]["value"] == "0.9"
    past = read(api, fabrics, f"?as_of={READ_ON}&from=2026-04-01&to=2026-12-31")["quarterly"]
    assert [each["quarter"] for each in past] == ["2026-Q2", "2026-Q3", "2026-Q4"]
    assert past[0]["cost_index"] == past[1]["cost_index"] == past[2]["cost_index"]
    # « L'évolution trimestrielle à une date passée ne change pas quand une révision est marquée
    # après cette date. » : a revision opened and marked on 10 June, after the reading of 3 June,
    # leaves it as it was — the document of the new marking is read on the 10th and after.
    database = fabrics.stage.database
    running = fabrics.in_progress.project_id
    act = Act(fabrics.stage.manager.user_id, at(6, 10))
    viewer = Viewer(fabrics.stage.manager.user_id, MANAGING)
    with logging_context(correlation_id="marking"), database.transaction() as session:
        create_revision(session, running, act, viewer)
        mark_revision(session, current_of(session, running), "Revue de juin", None, act)
    assert read(api, fabrics, f"?as_of={READ_ON}") == body
    # « org_node_id ne restreint que la main-d'œuvre » : the past quarters are read without the
    # node, which changes no figure — a node that exists, asked, leaves the past quarters as they
    # are (the one that holds the date is the top of the answer).
    with database.transaction() as session:
        node_id = session.scalar(
            select(OrgNode.id)
            .join(ResourceRole, ResourceRole.org_node_id == OrgNode.id)
            .where(ResourceRole.id == fabrics.costs.role)
        )
    on_node = read(api, fabrics, f"?as_of={READ_ON}&org_node_id={node_id}")
    assert on_node["scope"]["org_node_id"] == str(node_id)
    assert on_node["quarterly"][:4] == quarterly[:4]
    later = read(api, fabrics, "?as_of=2026-06-10")
    assert later["cost_index"] != body["cost_index"]


@pytest.mark.requirement("WF-PTF-0070-A")
def test_the_current_day_sums_the_indicators_of_the_day_of_the_projects_in_progress(
    api: ContractClient, fabrics: Portfolio, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The performance of one project In progress is its own indicators: the sums of one project,
    # the indices of the day, the variances and the three projections as the project gives them,
    # and the quarter that holds the current day is read as the day is.
    for route in ("portfolio_performance", "project_indicators"):
        monkeypatch.setattr(f"waterfall.api.{route}.utc_now", lambda: NOW)
    thresholds(fabrics.stage, WATCH, ALERT)
    running = fabrics.in_progress.project_id
    load_import(fabrics.stage, running, [cost("FA-1001", None, "100.00")])
    # A second project In progress, with a cost imported too: the portfolio reads the sums of the
    # two as the screen reads them, the answers of ``getProjectIndicators`` of each.
    second = another_in_progress(api, fabrics, "Second chantier", "PRJ-2673")
    load_import(fabrics.stage, second, [cost("FA-1002", None, "250.00")])
    own, other = (
        api.get(INDICATORS.format(project_id=each), headers=fabrics.stage.manager.headers).json()
        for each in (running, second)
    )
    body = read(api, fabrics)
    assert body["scope"]["as_of"] == "2026-11-19"
    assert body["scope"]["project_count"] == 2
    budget = Decimal(own["reference_budget"]) + Decimal(other["reference_budget"])
    assert body["reference_budget"] == f"{budget:.2f}"
    earned = Decimal(own["earned_value"]) + Decimal(other["earned_value"])
    spent = Decimal(own["actual_cost"]) + Decimal(other["actual_cost"])
    assert spent > 0
    assert body["cost_index"]["value"] == {
        "is_computable": True,
        "value": f"{(earned / spent).quantize(Decimal('0.0001')).normalize():f}",
        "reason": None,
    }
    assert body["cost_variance"] == f"{earned - spent:.2f}"
    assert body["cost_index"]["value"]["is_computable"] is True
    last = body["quarterly"][-1]
    assert last["quarter"] == "2026-Q4"
    assert last["cost_index"] == body["cost_index"]["value"]
    assert last["schedule_index"] == body["schedule_index"]["value"]


@pytest.mark.requirement("WF-PTF-0070-A")
def test_a_period_inverted_a_state_unknown_a_node_unknown_and_a_missing_permission_are_refused(
    api: ContractClient, stage: Scene
) -> None:
    # The period, the node and the states are refused, 422, each designated: the period and the
    # node by the scope of every view, a state by the query, which it cannot read. « … la lecture
    # est sous portfolio_performance.read » : the project manager, who does not read the portfolio,
    # does not see the view (404), an anonymous caller is refused (401); the manager reads it.
    headers = stage.reader.headers
    inverted = api.get(f"{PERFORMANCE}?from=2026-03-31&to=2026-01-01", headers=headers)
    assert inverted.status_code == 422
    assert [(each["pointer"], each["code"]) for each in inverted.json()["fields"]] == [
        ("/query/to", "VALUE_OUT_OF_RANGE")
    ]
    unknown = api.get(f"{PERFORMANCE}?states=finished&org_node_id={UUID(int=1)}", headers=headers)
    assert unknown.status_code == 422
    assert [each["pointer"] for each in unknown.json()["fields"]] == ["/query/states"]
    node = api.get(f"{PERFORMANCE}?org_node_id={UUID(int=1)}", headers=headers)
    assert [(each["pointer"], each["code"]) for each in node.json()["fields"]] == [
        ("/query/org_node_id", "UNKNOWN_ORG_NODE")
    ]
    assert api.get(PERFORMANCE, headers=stage.manager.headers).status_code == 404
    assert api.get(PERFORMANCE).status_code == 401
    assert api.get(PERFORMANCE, headers=headers).status_code == 200
