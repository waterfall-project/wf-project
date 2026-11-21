# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of the witness, kept and of the day, compared with the examples (US-1740/L1).

Laid by US-1660/L1, the socle of EP-10, so that no two stories create the same file; US-1740 writes
its tests here (EP-10, "Les tests du back"). ``load-witness`` marks the offer 100 and the amendment
101 by the transaction of the worker (``load_marking``), so that the 101 keeps its documents at its
instant, the 1 February 2026 at 9:00, and the 102 is read on the day of the examples, the 3 June.

What the service reads of the loaded witness is compared with the examples of the contract —
``project_indicators``, ``project_indicators_marked``, ``project_indicators_offer``,
``index_history`` and ``index_history_subproject``, ``milestone_tracking``, ``cost_curve``,
``cost_curve_payment_delays``, ``cost_curve_subproject``, ``earned_value_curves``, and the estimate
and the remaining of the 101 — compared as they are, but for what the witness does not reach, each
named with its cause where the test stands:

- since EP-08 (US-2650/L1) the reference is the 101 the merge of the amendment 1 marks and the
  risks bear their provisions: the indicators, the index histories and the earned value curves are
  the examples', without reserve; what stays apart is #4278's — the two lines the occurrence of 752
  grafted, of tasks completed, which the examples count to the remaining and the service does not,
  and the step of the amendment the cost curves of the examples draw from an offer marked in
  pricing —, each to the cent;
- the contexts, ``is_stored``, the actual cost, the earned value, the dates of the milestones and
  the shapes and steps of the series are the examples'.

``SINCE`` names what the 101 read at its marking, 1 February, differs in from the example of the
day, 3 June, which holds the work since: each such path is pinned to the 101's own estimate and
indicators by an equality, in the test that names it. The causes of the ``*_APART`` tables
document only: the tests compare their paths, never their causes.

The invariants the witness proves: the sums of the meshes, the projection of the project manager,
the offer refused, the points of the time/time diagram, the documents of the 101 on two platforms.
"""

import json
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any, cast

import pytest
from installed_reference import install
from projects_support import PROJECTS, READING, person
from sqlalchemy import select
from test_witness import load, wipe
from test_witness_lines import line_rows
from test_witness_lines_reads import deviations
from test_witness_projects import REVISION_100, REVISION_101, REVISION_102, without
from witness_support import PRJ_001, READ_AT, example, read

from waterfall.core.indicators import interface as indicators_interface
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.witness import loader, revisions

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

D = Decimal
QUA = pytest.mark.requirement("WF-QUA-0040-A")

CURVES = {"cost_curve", "cost_curve_payment_delays", "earned_value_curves"}
PORTFOLIO = indicators_interface.PORTFOLIO_KINDS
# The subprojects of the witness, "Poste de commande" and "Essais et mise en service", and the
# meshes the indicators are computed on: the project, each subproject, "out of any subproject".
COMMAND_POST = "01926f3a-7c00-7000-8000-000000000801"
TESTING = "01926f3a-7c00-7000-8000-000000000802"
UNASSIGNED = "unassigned"
MESHES = ("project", COMMAND_POST, TESTING, UNASSIGNED)
BASE = f"{PROJECTS}/{PRJ_001}"
INDICATORS = f"{BASE}/indicators"
KEPT = f"revision_id={REVISION_101}"
MARKED_AT = "2026-02-01T09:00:00Z"
THE_DAY = "2026-06-03"

# What the witness reads otherwise than the examples, by #4278: the lines the occurrence of 752
# grafted, of tasks completed, which the examples count to the remaining.
OCCURRED = "the lines of the occurrence of 752, of tasks completed (#4278)"
# What the 101 kept differs in from the example of the day, which holds the work since: each such
# path is pinned to the 101's own estimate and indicators by an equality, in the test that names it.
SINCE = "the day against the marking, pinned to the 101's own estimate and indicators"

# The fields of the indicators of the day that differ from the example, each with its cause.
DAY_APART = {
    "/remaining": OCCURRED,
    "/projections/project_manager": OCCURRED,
    "/projections/variance_project_manager": OCCURRED,
}
# What the estimate the 101 kept differs in from the example of the day.
ESTIMATE_APART = {
    "/by_cost_type[]/amount/value": SINCE,
    "/by_cost_type[]/share/value": SINCE,
    "/by_subproject[]/amount/value": SINCE,
    "/by_subproject[]/share/value": SINCE,
    "/by_work_package[]/amount/value": SINCE,
    "/by_work_package[]/share/value": SINCE,
    "/delta_to_previous_revision/value": SINCE,
    "/delta_to_reference/value": SINCE,
    "/provisions_identified": SINCE,
    "/total/value": SINCE,
}
# What the remaining the 101 kept differs in from the example of the day.
REMAINING_APART = {
    "/total": SINCE,
    "/by_cost_type[]/amount": SINCE,
    "/by_cost_type[]/share/value": SINCE,
    "/by_subproject[]/actual_cost": SINCE,
    "/by_subproject[]/budget": SINCE,
    "/by_subproject[]/is_over_budget": SINCE,
    "/by_subproject[]/remaining": SINCE,
    "/by_subproject[]/variance": SINCE,
    "/by_subproject[]/zone": SINCE,
    "/coverage/coverage_variance": SINCE,
    "/coverage/occurred_cost": SINCE,
    "/coverage/occurred_reestimated": SINCE,
    "/coverage/remaining_provisions": SINCE,
    "/delta_to_previous_revision": SINCE,
    "/delta_to_reference": SINCE,
}
CENT = D("0.01")
RATIO_STEP = D("0.0001")


def step() -> Decimal:
    """Give the step of the amendment 1 the cost curve of the example draws (#4278)."""
    steps = example("cost_curve")["steps"]
    assert [each["cause"] for each in steps] == ["amendment"]
    return D(steps[0]["amount"])


def occurred() -> Decimal:
    """Give the re-estimate of the lines the occurrence of 752 grafted, which the examples count."""
    items = example("volume/nodes_thousand")["items"]
    found = [
        D(each["estimate_line"]["reestimated_amount"])
        for each in items
        if each["kind"] == "estimate_line" and each["origin_risk_id"] is not None
    ]
    assert len(found) == 2
    return sum(found, D(0))


def cents(amount: Decimal) -> Decimal:
    """Round an amount to the cent, half away from zero, as the service does (WF-DAT-0100)."""
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def four_places(ratio: Decimal) -> Decimal:
    """Round a ratio or an index to four decimals, half to even, as the service does."""
    return ratio.quantize(RATIO_STEP, rounding=ROUND_HALF_EVEN)


def zone_of(value: Decimal, watch: Decimal, alert: Decimal) -> str:
    """Give the zone of an index: nominal from the watch on, watch from the alert on."""
    if value >= watch:
        return "nominal"
    return "watch" if value >= alert else "alert"


def provisions_marked() -> Decimal:
    """Give the reserve for risks of the reference 101, the provisions it bore at its marking."""
    return D(example("remaining_indicators")["coverage"]["reserve"])


def same_origin(ours: dict[str, Decimal], theirs: dict[str, Decimal]) -> None:
    """Require the points of a series to be the example's, but for the zero points before them.

    The example draws the origin of the series where the amendment 1 steps the budget, the end of
    January; the witness, measured to the offer 100, starts where its first point is.
    """
    assert {day: ours[day] for day in ours} == {day: theirs[day] for day in ours}
    missing = {day: amount for day, amount in theirs.items() if day not in ours}
    assert set(missing.values()) <= {D(0)}
    assert all(day < min(ours) for day in missing)


def gaps_of_the_projection(ours: dict[str, Decimal], theirs: dict[str, Decimal]) -> dict[str, Any]:
    """Give what the example's projection holds beyond the reading's, by day."""
    assert ours.keys() == theirs.keys()
    return {day: theirs[day] - ours[day] for day in ours}


def zulu(instant: datetime) -> str:
    """Write an instant as the examples do."""
    return instant.isoformat().replace("+00:00", "Z")


def documents_of(value: object) -> list[dict[str, Any]]:
    """Give the dictionaries of a value, at any depth."""
    if isinstance(value, dict):
        mapped = cast("dict[str, object]", value)
        return [mapped, *(each for part in mapped.values() for each in documents_of(part))]
    if isinstance(value, list):
        listed = cast("list[object]", value)
        return [each for part in listed for each in documents_of(part)]
    return []


@pytest.fixture
def the_day(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the day the service reads as today to that of the examples, 3 June 2026 at 14:05."""
    for module in (
        "estimate_indicators",
        "index_history",
        "indicator_curves",
        "milestone_tracking",
        "project_indicators",
        "remaining_indicators",
    ):
        monkeypatch.setattr(f"waterfall.api.{module}.utc_now", lambda: READ_AT)


def refused(api: ContractClient, witness: Database, realm: TestRealm, url: str) -> Any:
    """Read a route of the service as a reader of all the projects; require its refusal, 409."""
    answer = api.get(url, headers=person(witness, realm, *READING).headers)
    assert answer.status_code == 409, answer.text
    return answer.json()


def ours_to_theirs(ours: dict[str, Any], theirs: dict[str, Any], *fields: str) -> list[Decimal]:
    """Give what an amount of the example holds beyond the reading's, for each field."""
    return [D(theirs[field]) - D(ours[field]) for field in fields]


def series_of(body: dict[str, Any], name: str) -> dict[str, Decimal]:
    """Give the points of a series by day."""
    (found,) = [each for each in body["series"] if each["name"] == name]
    return {point["date"]: D(point["amount"]) for point in found["points"]}


def names_of(body: dict[str, Any]) -> list[str]:
    """Give the names of the series of a curve, in order."""
    return [each["name"] for each in body["series"]]


def kinds_of(database: Database, revision_id: UUID) -> set[str]:
    """Give the kinds of document a revision of the witness kept for EP-10, not the portfolio."""
    with database.transaction() as session:
        found = session.scalars(
            select(RevisionIndicator.kind).where(RevisionIndicator.revision_id == revision_id)
        )
        return set(found) - PORTFOLIO


def kept(database: Database, revision_id: UUID) -> list[tuple[Any, ...]]:
    """Give the documents a revision kept, by kind and mesh, as the cent holds them."""
    with database.transaction() as session:
        found = session.scalars(
            select(RevisionIndicator).where(RevisionIndicator.revision_id == revision_id)
        )
        return sorted(
            (
                row.kind,
                row.scope,
                row.computed_at,
                row.created_by,
                json.dumps(row.document, sort_keys=True),
            )
            for row in found
        )


@pytest.mark.requirement("WF-DAT-0040-A")
def test_the_witness_loaded_keeps_the_indicators_of_its_marked_revisions(witness: Database) -> None:
    # ``load_marking`` marks each revision of the witness by the transaction of the worker, so that
    # ``compute_indicators`` keeps its documents: the offer 100, marked in pricing, its estimate and
    # its remaining; the amendment 101, marked In progress, those two and its project indicators.
    # The three curves of each scope are kept with the project indicators (US-1690/L3); no slice is.
    assert kinds_of(witness, REVISION_100) == {"estimate", "remaining"}
    assert kinds_of(witness, REVISION_101) == {"estimate", "remaining", "project", *CURVES}


def test_the_witness_has_one_extending_the_loader_s_and_it_names_the_indicators() -> None:
    # The convention is the loader's (#3552): the interface of the indicators, imported there,
    # fills ``register_indicators`` for every marking the witness makes, none in ``revisions``.
    assert indicators_interface in loader.EXTENDING
    assert not hasattr(revisions, "EXTENDING")


@QUA
def test_the_101_keeps_its_documents_for_the_project_each_subproject_and_out_of_any(
    witness: Database,
) -> None:
    # The estimate, the project indicators and the three curves on each mesh, the remaining once on
    # the project; all at the marking, 1 February at 9:00, by the platform (the portfolio's apart).
    with witness.transaction() as session:
        every = session.scalars(
            select(RevisionIndicator).where(RevisionIndicator.revision_id == REVISION_101)
        ).all()
    found = [row for row in every if row.kind not in PORTFOLIO]
    assert sorted((row.kind, row.scope) for row in found) == sorted(
        [(kind, mesh) for kind in ("estimate", "project", *CURVES) for mesh in MESHES]
        + [("remaining", "project")]
    )
    assert {zulu(row.computed_at) for row in found} == {MARKED_AT}
    assert {row.document["context"]["is_stored"] for row in found} == {True}


@QUA
def test_the_indicators_of_the_day_are_the_example_but_for_the_lines_of_the_occurrence(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    del the_day
    body = read(api, witness, realm, INDICATORS)
    expected = example("project_indicators")
    assert deviations(body, expected) == set(DAY_APART)
    assert body["context"] == expected["context"]
    assert body["context"]["is_stored"] is False
    # The remaining and the projection of the project manager fall short by the lines of the
    # occurrence the example counts (#4278), the variance as much.
    assert ours_to_theirs(body, expected, "remaining") == [occurred()]
    assert ours_to_theirs(
        body["projections"], expected["projections"], "project_manager", "variance_project_manager"
    ) == [occurred(), occurred()]
    manager, budget = D(body["projections"]["project_manager"]), D(body["reference_budget"])
    assert D(body["projections"]["variance_project_manager"]) == manager - budget
    assert manager == D(body["actual_cost"]) + D(body["remaining"])


@QUA
def test_the_indicators_the_101_kept_are_the_example(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # Nothing was planned, spent or earned at the marking: no index, the actual cost at nought; the
    # remaining counts the provisions of the identified risks, the reference the 101's (EP-08).
    body = read(api, witness, realm, f"{INDICATORS}?{KEPT}")
    assert deviations(body, example("project_indicators_marked")) == set()
    assert body["context"]["is_stored"] is True


@QUA
@pytest.mark.parametrize(
    "path",
    [
        "/indicators",
        "/indicators/cost-curve",
        "/indicators/cost-curve?payment_delays=true",
        "/indicators/earned-value-curves",
    ],
)
def test_the_offer_100_is_refused_its_indicators_and_curves_as_the_example_says(
    api: ContractClient, witness: Database, realm: TestRealm, path: str
) -> None:
    # Marked in pricing, the offer kept only its estimate and its remaining: the four reads are
    # refused as a project that is not in progress is, but without a parameter, the project being.
    joiner = "&" if "?" in path else "?"
    body = refused(api, witness, realm, f"{BASE}{path}{joiner}revision_id={REVISION_100}")
    expected = example("project_indicators_offer")
    assert deviations(body, expected) == {"/correlation_id"}
    assert body["code"] == "STATE_FORBIDS_OPERATION"
    assert body.get("params") is None


@QUA
def test_the_index_history_is_the_example(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # Every mesh, its points at the marking of the 101 and on the day, measured to the 101 (EP-08).
    del the_day
    body = read(api, witness, realm, f"{INDICATORS}/index-history")
    assert deviations(body, example("index_history")) == set()


@QUA
def test_the_index_history_of_a_subproject_is_the_example(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # The 101 declares the budgets of the subprojects: the subproject plans and earns (EP-08).
    del the_day
    body = read(api, witness, realm, f"{INDICATORS}/index-history?scope={COMMAND_POST}")
    assert deviations(body, example("index_history_subproject")) == set()


@QUA
def test_the_index_of_the_day_is_the_indicators_of_the_day_of_each_mesh(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # The last point of each mesh is the indices the mesh reads on the day, the zones too.
    del the_day
    body = read(api, witness, realm, f"{INDICATORS}/index-history")
    assert [each["scope"] for each in body["scopes"]] == list(MESHES)
    for found in body["scopes"]:
        indicators = read(api, witness, realm, f"{INDICATORS}?scope={found['scope']}")
        day = found["points"][-1]
        assert day["at"] == indicators["context"]["computed_at"]
        assert day["revision_id"] == str(REVISION_102)
        assert day["cost_index"] == indicators["cost_index"], found["scope"]
        assert day["schedule_index"] == indicators["schedule_index"], found["scope"]
        # The point of the marking is the document the 101 kept, whatever came after.
        marked = read(api, witness, realm, f"{INDICATORS}?scope={found['scope']}&{KEPT}")
        assert found["points"][0]["cost_index"] == marked["cost_index"]
        assert found["points"][0]["schedule_index"] == marked["schedule_index"]


@QUA
def test_the_time_time_diagram_is_the_example_its_points_those_of_the_revisions_marked_in_progress(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # The dates of the milestones are the example's. One point per revision marked In progress — the
    # 101; the offer, marked in pricing, gives none — and a last at the day; the milestone completed
    # on 24 April ends on the diagonal, none after; the other, at the day, a horizontal.
    del the_day
    body = read(api, witness, realm, f"{INDICATORS}/milestone-tracking")
    expected = example("milestone_tracking")
    assert deviations(body, expected) == set()
    assert body["context"] == expected["context"]
    completed, pending = body["milestones"]
    assert [len(each["points"]) for each in body["milestones"]] == [2, 2]
    assert completed["points"][0]["marked_at"] == pending["points"][0]["marked_at"] == MARKED_AT
    assert completed["completed_on"] == "2026-04-24"
    last = completed["points"][-1]
    assert (last["marked_at"][:10], last["forecast_date"]) == ("2026-04-24", "2026-04-24")
    assert pending["completed_on"] is None
    assert pending["points"][-1]["marked_at"] == body["context"]["computed_at"]
    assert pending["points"][-1]["forecast_date"] == pending["points"][0]["forecast_date"]


@QUA
@pytest.mark.usefixtures("the_day")
@pytest.mark.parametrize(
    ("name", "path"),
    [
        ("cost_curve", "/indicators/cost-curve"),
        ("cost_curve_payment_delays", "/indicators/cost-curve?payment_delays=true"),
    ],
)
def test_the_cost_curve_is_the_example_but_for_the_step_and_the_lines_of_the_occurrence(
    api: ContractClient, witness: Database, realm: TestRealm, name: str, path: str
) -> None:
    # « La courbe de coûts … le coût réel s'arrête à la date de calcul, et la projection part de ce
    # point » : the context, the names, the reference budget and the actual cost are the
    # example's, but for the step of the amendment and its points before (#4278); the projection
    # less the lines of the occurrence, from the day on (#4278).
    body = read(api, witness, realm, f"{BASE}{path}")
    expected = example(name)
    assert body["context"] == expected["context"]
    assert body["context"]["is_stored"] is False
    assert names_of(body) == names_of(expected)
    assert body["steps"] == []
    assert [(each["cause"], D(each["amount"])) for each in expected["steps"]] == [
        ("amendment", step())
    ]
    same_origin(series_of(body, "reference_budget"), series_of(expected, "reference_budget"))
    same_origin(series_of(body, "actual_cost"), series_of(expected, "actual_cost"))
    gaps = gaps_of_the_projection(
        series_of(body, "project_manager_projection"),
        series_of(expected, "project_manager_projection"),
    )
    assert set(gaps.values()) == {D(0), occurred()}
    assert gaps[min(gaps)] == 0
    assert gaps[max(gaps)] == occurred()
    assert (body["cash_out_by_month"] is None) == (expected["cash_out_by_month"] is None)


@QUA
def test_the_cash_out_is_the_example_but_for_the_lines_of_the_occurrence_and_sums_to_the_remaining(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # « ceux à venir, dont la somme égale le reste à engager » : the months and the past
    # disbursements are the example's, the forecast of June less the lines of the occurrence the
    # example counts (#4278), the provisions included.
    del the_day
    body = read(api, witness, realm, f"{INDICATORS}/cost-curve?payment_delays=true")
    expected = example("cost_curve_payment_delays")
    assert [each["month"] for each in body["cash_out_by_month"]] == [
        each["month"] for each in expected["cash_out_by_month"]
    ]
    gaps = {
        each["month"]: D(theirs["forecast"]) - D(each["forecast"])
        for each, theirs in zip(
            body["cash_out_by_month"], expected["cash_out_by_month"], strict=True
        )
        if each != theirs
    }
    assert gaps == {"2026-06": occurred()}
    indicators = read(api, witness, realm, INDICATORS)
    assert sum(D(each["forecast"]) for each in body["cash_out_by_month"]) == D(
        indicators["remaining"]
    )


@QUA
def test_the_cost_curve_of_a_subproject_is_the_example_but_for_the_step(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # « le budget de référence de ses seules lignes » : the 101 declares the budget of the
    # subproject (EP-08); its curve is the example's but for the step of the amendment and its
    # points before (#4278).
    del the_day
    body = read(api, witness, realm, f"{INDICATORS}/cost-curve?scope={COMMAND_POST}")
    expected = example("cost_curve_subproject")
    assert body["context"] == expected["context"]
    assert names_of(body) == names_of(expected)
    assert body["steps"] == []
    assert [each["cause"] for each in expected["steps"]] == ["amendment"]
    for name in ("reference_budget", "actual_cost"):
        same_origin(series_of(body, name), series_of(expected, name))
    assert series_of(body, "project_manager_projection") == series_of(
        expected, "project_manager_projection"
    )


@QUA
def test_the_earned_value_curves_are_the_example(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # The planned value measured to the 101, the reference (EP-08).
    del the_day
    body = read(api, witness, realm, f"{INDICATORS}/earned-value-curves")
    assert deviations(body, example("earned_value_curves")) == set()


@QUA
@pytest.mark.parametrize("kept_by_the_marking", [False, True])
def test_the_sums_of_the_meshes_are_the_project_s_the_indicators_the_estimate_and_the_curves(
    api: ContractClient,
    witness: Database,
    realm: TestRealm,
    the_day: None,
    kept_by_the_marking: bool,
) -> None:
    # « Le calcul d'un sous-projet est celui du projet sur ses seules lignes » (WF-IND-0020): the
    # amounts of the project are those of its two subprojects and of "out of any subproject",
    # added, to the cent, the day and as the 101 kept them.
    del the_day
    named = f"&{KEPT}" if kept_by_the_marking else ""
    found = {
        mesh: read(api, witness, realm, f"{INDICATORS}?scope={mesh}{named}") for mesh in MESHES
    }
    for field in (
        "reference_budget",
        "planned_value",
        "earned_value",
        "actual_cost",
        "remaining",
        "cost_variance",
        "schedule_variance",
    ):
        assert D(found["project"][field]) == sum(D(found[mesh][field]) for mesh in MESHES[1:]), (
            field
        )
    estimates = {
        mesh: read(api, witness, realm, f"{BASE}/estimate-indicators?scope={mesh}{named}")
        for mesh in MESHES
    }
    assert D(estimates["project"]["total"]["value"]) == sum(
        D(estimates[mesh]["total"]["value"]) for mesh in MESHES[1:]
    )
    # Each mesh answers the amounts of the others only through its own lines.
    for mesh in MESHES:
        assert estimates[mesh]["context"]["scope"] == mesh
        assert found[mesh]["context"]["scope"] == mesh
    assert all(each["context"]["is_stored"] is kept_by_the_marking for each in found.values())
    assert all(each["context"]["is_stored"] is kept_by_the_marking for each in estimates.values())


@QUA
@pytest.mark.parametrize("kept_by_the_marking", [False, True])
def test_the_projection_of_the_project_manager_is_the_actual_cost_and_the_remaining_of_each_mesh(
    api: ContractClient,
    witness: Database,
    realm: TestRealm,
    the_day: None,
    kept_by_the_marking: bool,
) -> None:
    # « la projection du chef de projet, qui part du coût réel et étale le reste à engager » : the
    # curve of each mesh ends on the projection its indicators give, and starts, on the day, on the
    # actual cost; the 101 kept its curves as it kept its indicators.
    del the_day
    named = f"&{KEPT}" if kept_by_the_marking else ""
    for mesh in MESHES:
        indicators = read(api, witness, realm, f"{INDICATORS}?scope={mesh}{named}")
        curve = read(api, witness, realm, f"{INDICATORS}/cost-curve?scope={mesh}{named}")
        projection = series_of(curve, "project_manager_projection")
        assert curve["context"]["is_stored"] is kept_by_the_marking
        manager = D(indicators["projections"]["project_manager"])
        assert projection[max(projection)] == manager, mesh
        assert manager == D(indicators["actual_cost"]) + D(indicators["remaining"]), mesh
        assert series_of(curve, "actual_cost")[max(series_of(curve, "actual_cost"))] == D(
            indicators["actual_cost"]
        )
        values = series_of(
            read(api, witness, realm, f"{INDICATORS}/earned-value-curves?scope={mesh}{named}"),
            "earned_value",
        )
        assert values[max(values)] == D(indicators["earned_value"]), mesh


@QUA
def test_the_estimate_of_the_101_is_the_example_but_for_the_work_since_its_marking(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The lines of the 101, its provisions at its marking — the reserve for risks of the reference
    # (WF-RIS-0050) — where the example, read on the 102, holds the provision of 751 since raised,
    # 753 dismissed, 752 occurred (EP-08); its deltas measured to the offer 100, marked before.
    body = read(api, witness, realm, f"{BASE}/estimate-indicators?{KEPT}")
    expected = example("estimate_indicators")
    marked = example("project_indicators_marked")
    assert body["context"] == marked["context"]
    assert deviations(without(body, {"context"}), without(expected, {"context"})) == set(
        ESTIMATE_APART
    )
    assert D(body["provisions_identified"]) == provisions_marked()
    ours = D(body["total"]["value"])
    assert ours == D(marked["remaining"])
    assert [each["key"] for each in body["by_cost_type"]] == [
        each["key"] for each in expected["by_cost_type"]
    ]
    for dimension in ("by_cost_type", "by_subproject"):
        assert sum(D(each["amount"]["value"]) for each in body[dimension]) == ours


@QUA
def test_the_deltas_of_the_estimate_of_the_101_are_measured_to_the_offer_100(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The deltas of the witness are measured to the offer 100, the reference and the revision
    # marked before: the 101's total less the offer's estimate, the same for both.
    body, _, offer = estimate_deltas(api, witness, realm)
    assert D(body["delta_to_reference"]["value"]) == D(body["total"]["value"]) - offer
    assert body["delta_to_previous_revision"] == body["delta_to_reference"]


@QUA
def test_the_deltas_of_the_example_estimate_are_its_total_less_the_101_as_marked(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # Those of the example, read on the 102, are measured to the 101 as marked, and its total holds
    # the provision and the occurrence: the example's delta is its total less the 101 as marked, the
    # variance of the coverage, nought of the witness.
    _, expected, _ = estimate_deltas(api, witness, realm)
    coverage = example("remaining_indicators")["coverage"]
    as_marked = D(example("project_indicators_marked")["remaining"])
    for delta in ("delta_to_reference", "delta_to_previous_revision"):
        assert D(expected["total"]["value"]) - D(expected[delta]["value"]) == as_marked, delta
        assert D(expected[delta]["value"]) == -D(coverage["coverage_variance"]), delta


@QUA
def test_the_deltas_of_the_example_are_those_of_the_day_to_the_101_the_witness_kept(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The example, read on the 102, measures its deltas to the 101 as marked: its total less the
    # total the witness's 101 kept, to the cent (EP-08).
    body, expected, _ = estimate_deltas(api, witness, realm)
    for delta in ("delta_to_reference", "delta_to_previous_revision"):
        assert D(expected[delta]["value"]) == D(expected["total"]["value"]) - D(
            body["total"]["value"]
        ), delta


def estimate_deltas(
    api: ContractClient, witness: Database, realm: TestRealm
) -> tuple[dict[str, Any], dict[str, Any], Decimal]:
    """Give the estimate of the 101, the example's and the offer 100's estimate they measure to."""
    body = read(api, witness, realm, f"{BASE}/estimate-indicators?{KEPT}")
    with witness.transaction() as session:
        offer = sum(
            (facet.reestimated_amount for _, facet in line_rows(session, REVISION_100).values()),
            D(0),
        )
    return body, example("estimate_indicators"), offer


@QUA
def test_the_remaining_of_the_101_is_the_kept_indicators_of_the_project(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # Nothing was spent at the marking: the actual cost of each subproject is the example's of the
    # marking, nought, and the remaining the project kept, provisions of the risks included (EP-08),
    # spread over its natures and its subprojects. The examples of the day are compared by their
    # paths, the work since the marking being theirs.
    body = read(api, witness, realm, f"{BASE}/remaining-indicators?{KEPT}")
    expected = example("remaining_indicators")
    marked = example("project_indicators_marked")
    assert body["context"] == marked["context"]
    assert deviations(without(body, {"context"}), without(expected, {"context"})) == set(
        REMAINING_APART
    )
    total = D(body["total"])
    kept_project = read(api, witness, realm, f"{INDICATORS}?{KEPT}")
    assert total == D(marked["remaining"]) == D(kept_project["remaining"])
    assert [(each["key"], each["label"]) for each in body["by_cost_type"]] == [
        (each["key"], each["label"]) for each in expected["by_cost_type"]
    ]
    assert [(each["key"], each.get("label")) for each in body["by_subproject"]] == [
        (each["key"], each.get("label")) for each in expected["by_subproject"]
    ]
    assert {each["actual_cost"] for each in body["by_subproject"]} == {marked["actual_cost"]}
    # Nothing was spent: what remains is the estimate of the 101, by nature and by subproject.
    estimate = read(api, witness, realm, f"{BASE}/estimate-indicators?{KEPT}")
    assert {each["key"]: each["amount"] for each in body["by_cost_type"]} == {
        each["key"]: each["amount"]["value"] for each in estimate["by_cost_type"]
    }
    assert {each["key"]: each["remaining"] for each in body["by_subproject"]} == {
        each["key"]: each["amount"]["value"] for each in estimate["by_subproject"]
    }
    assert sum(D(each["amount"]) for each in body["by_cost_type"]) == total
    assert sum(D(each["remaining"]) for each in body["by_subproject"]) == total
    # The coverage at the marking: the reserve is the provisions it bears, nothing occurred.
    coverage = body["coverage"]
    assert D(coverage["reserve"]) == D(coverage["remaining_provisions"]) == provisions_marked()
    assert (coverage["occurred_cost"], coverage["coverage_variance"]) == ("0.00", "0.00")
    # Measured to the 101 itself, the reference: each margin the budget less the actual cost and
    # the remaining.
    for each in body["by_subproject"]:
        margin = D(each["budget"]) - D(each["actual_cost"]) - D(each["remaining"])
        assert D(each["variance"]) == margin
        assert (each["is_over_budget"], each["zone"]) == (
            (True, "alert") if margin < 0 else (False, "nominal")
        )
    assert D(body["delta_to_reference"]) == sum(D(e["variance"]) for e in body["by_subproject"])
    # The offer 100 alone was marked before the 101: its remaining less the offer's (US-1670).
    match = (RevisionIndicator.revision_id == REVISION_100, RevisionIndicator.kind == "remaining")
    with witness.transaction() as session:
        offered = session.scalars(select(RevisionIndicator.document).where(*match)).one()
    assert D(body["delta_to_previous_revision"]) == total - D(offered["total"])


@QUA
def test_two_platforms_loaded_with_the_witness_keep_the_same_documents_for_the_101_to_the_cent(
    witness: Database, owner: Engine, service_database_url: str
) -> None:
    # « Deux engendrements successifs donnent des données identifiantes identiques » : the documents
    # the marking of the 101 kept — their kind, their mesh, their instant, their author and every
    # amount of every document — are the same on a platform neuve loaded again.
    first = kept(witness, REVISION_101)
    wipe(owner)
    install(owner)
    assert load(service_database_url) == 0
    assert kept(witness, REVISION_101) == first
    assert len(first) == 21 + 4  # the workload, the costs, the risks, the milestones (US-2680)
    held = [json.loads(row[4]) for row in first if row[0] not in PORTFOLIO]
    assert {each["context"]["is_stored"] for each in held} == {True}
    assert kinds_of(witness, REVISION_101) == {"estimate", "remaining", "project", *CURVES}


@QUA
def test_no_address_and_no_project_but_the_witness_s_appear_in_the_documents_the_101_kept(
    witness: Database,
) -> None:
    # « Aucune adresse électronique ni aucun libellé de projet réel n'y figure » : the documents
    # add nothing to the witness — their labels are those of its subprojects, natures, milestones
    # and risks (US-2680/L2), and no text holds an address.
    with witness.transaction() as session:
        found = [
            row.document
            for row in session.scalars(
                select(RevisionIndicator).where(RevisionIndicator.revision_id == REVISION_101)
            )
        ]
    labels = {
        each["label"]
        for document in found
        for each in documents_of(document)
        if isinstance(each.get("label"), str)
    }
    remaining = example("remaining_indicators")
    allowed = {each["label"] for each in remaining["by_subproject"] if "label" in each}
    allowed |= {each["label"] for each in remaining["by_cost_type"]}
    allowed |= {each["label"] for each in example("estimate_indicators")["by_work_package"]}
    allowed |= {each["label"] for each in example("milestone_tracking")["milestones"]}
    # The portfolio's risks document (EP-11) names the risks of the witness (EP-08).
    allowed |= {each["label"] for each in example("risks")["items"]}
    assert labels
    assert labels <= allowed
    assert "@" not in json.dumps(found)
