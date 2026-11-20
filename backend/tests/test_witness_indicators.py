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

- the reference is the offer 100 until the merge of the amendment 1 (EP-08): the reference budget
  falls short by the step of the amendment, the planned value by at most as much, the ratios and
  the projections that depend on them — each recomputed exactly, by its formula, on the fields of
  the witness — the deltas of the estimate, measured to the offer's estimate where the example's is
  to the 101's, and the budgets of the subprojects, which the offer does not declare, with the
  earned value of each mesh and the indices measured to them;
- the provisions of the identified risks and the lines the occurrence of a risk merged are EP-08's:
  the remaining, the projection of the project manager and what depends on them fall short by them;
- the contexts, ``is_stored``, the actual cost, the earned value, the dates of the milestones and
  the shapes and steps of the series are the examples'.

``SINCE`` names what the 101 read at its marking, 1 February, differs in from the example of the
day, 3 June: each such path is pinned to the 101's own estimate and indicators by an equality; the
``*_APART`` tables document only. Proved besides: the sums of the meshes, the projection of the
project manager, the offer refused, the time/time diagram, the documents of the 101 twice loaded.
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

# The causes of what the witness reads otherwise than the examples.
REFERENCE = "measured to the offer 100, the reference until the amendment 1 (EP-08)"
PROVISIONS = "the provisions and the lines of the occurrence of a risk (EP-08)"
BOTH = "the reference and the provisions (EP-08)"
# What the criterion does not list: see the header of the module.
SINCE = "the day against the marking, pinned to the 101's own estimate and indicators"

# The fields of the indicators of the day that differ from the example, each with its cause.
DAY_APART = {
    "/reference_budget": REFERENCE,
    "/planned_value": REFERENCE,
    "/schedule_variance": REFERENCE,
    "/schedule_index/value/value": REFERENCE,
    "/projections/at_budget": REFERENCE,
    "/projections/at_observed_rate/value": REFERENCE,
    "/projections/variance_at_observed_rate": REFERENCE,
    "/remaining": PROVISIONS,
    "/projections/project_manager": PROVISIONS,
    "/financial_progress/value": PROVISIONS,
    "/projections/variance_project_manager": BOTH,
}
# The same, kept by the marking of the 101: nothing is planned, spent or earned yet.
MARKED_APART = {
    "/reference_budget": REFERENCE,
    "/projections/at_budget": REFERENCE,
    "/remaining": PROVISIONS,
    "/projections/project_manager": PROVISIONS,
    "/projections/variance_project_manager": BOTH,
}
# The points of the indices on the day. The actual cost of each mesh is the example's; the earned
# value of a mesh, spread over the meshes by the budgets of the subprojects, which the offer 100
# does not declare, is what differs (``test_the_index_history_is_...``): the cost index and the
# planned value follow from it, then the schedule index and the zones.
INDEX_POINT_APART = {
    "/scopes[]/points[]/cost_index/value/value": "the earned value of a mesh, from its budgets",
    "/scopes[]/points[]/cost_index/zone": "the zone of that index, by its value",
    "/scopes[]/points[]/schedule_index/value/is_computable": "no planned value in a subproject",
    "/scopes[]/points[]/schedule_index/value/reason": "no planned value in a subproject",
    "/scopes[]/points[]/schedule_index/value/value": "the planned value, from the reference",
    "/scopes[]/points[]/schedule_index/zone": "the zone of that index, by its value",
}
# What the estimate of the 101 kept differs in from the example: the provision, the lines of the
# occurrence and the reference its deltas are measured to: the offer 100's estimate, where the
# example, read on the 102, measures to the 101 as marked.
ESTIMATE_APART = {
    "/by_cost_type[len]": PROVISIONS,
    "/by_cost_type[]/amount/value": PROVISIONS,
    "/by_cost_type[]/share/value": PROVISIONS,
    "/by_subproject[]/amount/value": PROVISIONS,
    "/by_subproject[]/share/value": PROVISIONS,
    "/by_work_package[]/amount/value": PROVISIONS,
    "/by_work_package[]/share/value": PROVISIONS,
    "/delta_to_previous_revision/value": REFERENCE,
    "/delta_to_reference/value": REFERENCE,
    "/provisions_identified": PROVISIONS,
    "/total/value": PROVISIONS,
}
# What the remaining of the 101 kept differs in from the example of the day. The provision, the
# reserve and the lines of the occurrence are EP-08's; the budgets of the subprojects, and the
# margins and the deltas measured to them, are the offer's, the reference. The amounts of
# the marking against those of the day (``SINCE``) are pinned to the 101's own estimate and
# indicators (``test_the_remaining_of_the_101_...``).
REMAINING_APART = {
    "/total": SINCE,
    "/by_cost_type[len]": PROVISIONS,
    "/by_cost_type[]/amount": SINCE,
    "/by_cost_type[]/share/value": SINCE,
    "/by_subproject[]/actual_cost": SINCE,
    "/by_subproject[]/budget": REFERENCE,
    "/by_subproject[]/is_over_budget": REFERENCE,
    "/by_subproject[]/remaining": SINCE,
    "/by_subproject[]/variance": REFERENCE,
    "/by_subproject[]/zone": REFERENCE,
    "/coverage/coverage_variance": PROVISIONS,
    "/coverage/occurred_cost": PROVISIONS,
    "/coverage/occurred_reestimated": PROVISIONS,
    "/coverage/remaining_provisions": PROVISIONS,
    "/coverage/reserve": PROVISIONS,
    "/delta_to_previous_revision": REFERENCE,
    "/delta_to_reference": REFERENCE,
}
CENT = D("0.01")
RATIO_STEP = D("0.0001")


def step() -> Decimal:
    """Give the step of the amendment 1, which the offer 100, the reference, does not carry."""
    steps = example("cost_curve")["steps"]
    assert [each["cause"] for each in steps] == ["amendment"]
    return D(steps[0]["amount"])


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


def provisions_of_the_day() -> Decimal:
    """Give what the remaining of the day lacks of the example: the provisions, the occurrence."""
    coverage = example("remaining_indicators")["coverage"]
    return D(coverage["remaining_provisions"]) + D(coverage["occurred_reestimated"])


def provisions_marked() -> Decimal:
    """Give what the remaining kept by the marking of the 101 lacks of the example: the reserve."""
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


def measured(ours: dict[str, Decimal], theirs: dict[str, Decimal]) -> dict[str, Decimal]:
    """Require a series measured to the offer to fall short of the example's by the step at most.

    From nothing at the origin, to the step at the end of the reference; the missing days are the
    zero points of the step of the amendment, which the offer lacks. Give the gap, by day.
    """
    gaps = {day: theirs[day] - ours[day] for day in sorted(ours)}
    assert all(0 <= each <= step() for each in gaps.values())
    assert gaps[max(gaps)] == step()
    assert list(gaps.values()) == sorted(gaps.values())
    missing = {day: amount for day, amount in theirs.items() if day not in ours}
    assert set(missing.values()) <= {D(0)}
    assert all(day < min(ours) for day in missing)
    return gaps


def gaps_of_the_projection(ours: dict[str, Decimal], theirs: dict[str, Decimal]) -> dict[str, Any]:
    """Give what the example's projection holds beyond the reading's, by day: the provisions."""
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
def test_the_indicators_of_the_day_are_the_example_but_for_the_reference_and_the_provisions(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    del the_day
    body = read(api, witness, realm, INDICATORS)
    expected = example("project_indicators")
    assert deviations(body, expected) == set(DAY_APART)
    # The contexts, the actual cost, the earned value, the variance of cost are the example's.
    assert body["context"] == expected["context"]
    assert body["context"]["is_stored"] is False
    # The reference budget and the budget the projection is measured to fall short by the step of
    # the amendment 1; the remaining and the projection of the project manager by the provisions.
    gap, later = ours_to_theirs(body, expected, "reference_budget", "remaining")
    assert gap == step()
    assert later == provisions_of_the_day()
    assert ours_to_theirs(body["projections"], expected["projections"], "at_budget") == [gap]
    assert ours_to_theirs(body["projections"], expected["projections"], "project_manager") == [
        later
    ]
    for each in (body, expected):
        manager, budget = D(each["projections"]["project_manager"]), D(each["reference_budget"])
        assert D(each["projections"]["variance_project_manager"]) == manager - budget
        assert manager == D(each["actual_cost"]) + D(each["remaining"])
    assert D(body["schedule_variance"]) == D(body["earned_value"]) - D(body["planned_value"])
    # The planned value falls short by the part of the step the offer would have planned by then:
    # between the gaps of the series of the planned value at the month ends around the day, the
    # series, cumulated, never falling back (the curve has no point on the day itself).
    curves, wanted = (
        read(api, witness, realm, f"{INDICATORS}/earned-value-curves"),
        example("earned_value_curves"),
    )
    gaps = measured(series_of(curves, "planned_value"), series_of(wanted, "planned_value"))
    before = max(day for day in gaps if day <= THE_DAY)
    after = min(day for day in gaps if day > THE_DAY)
    assert gaps[before] <= D(expected["planned_value"]) - D(body["planned_value"]) <= gaps[after]
    # The indicators that depend on the reference are its own formulas on the fields of the witness:
    # exact, to the rounding of the service (WF-IND-0040, WF-IND-0050, WF-IND-0060).
    spent, gained = D(body["actual_cost"]), D(body["earned_value"])
    fixed, left = D(body["reference_budget"]), D(body["remaining"])
    planned = D(body["planned_value"])
    at_rate = fixed * spent / gained
    projections = body["projections"]
    assert D(projections["at_observed_rate"]["value"]) == cents(at_rate)
    assert D(projections["variance_at_observed_rate"]) == cents(at_rate - fixed)
    assert D(projections["at_budget"]) == cents(spent + fixed - gained)
    assert D(projections["variance_at_budget"]) == cents(spent - gained)
    assert D(body["financial_progress"]["value"]) == four_places(spent / (spent + left))
    assert D(body["schedule_index"]["value"]["value"]) == four_places(gained / planned)
    assert D(body["cost_index"]["value"]["value"]) == four_places(gained / spent)


@QUA
def test_the_indicators_the_101_kept_are_the_example_but_for_the_reference_and_the_reserve(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # Nothing was planned, spent or earned at the marking: no index, the actual cost at nought; the
    # remaining counts the provisions of the identified risks, which are EP-08's.
    body = read(api, witness, realm, f"{INDICATORS}?{KEPT}")
    expected = example("project_indicators_marked")
    assert deviations(body, expected) == set(MARKED_APART)
    assert body["context"] == expected["context"]
    assert body["context"]["is_stored"] is True
    gap, later = ours_to_theirs(body, expected, "reference_budget", "remaining")
    assert gap == step()
    assert later == provisions_marked()
    assert ours_to_theirs(body["projections"], expected["projections"], "at_budget") == [gap]
    assert ours_to_theirs(body["projections"], expected["projections"], "project_manager") == [
        later
    ]
    assert D(body["projections"]["variance_project_manager"]) == D(
        body["projections"]["project_manager"]
    ) - D(body["reference_budget"])


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
def test_the_index_history_is_the_example_but_for_the_last_point_the_reference_measures(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    del the_day
    body = read(api, witness, realm, f"{INDICATORS}/index-history")
    expected = example("index_history")
    assert deviations(body, expected) == set(INDEX_POINT_APART)
    assert [(each["scope"], each["label"]) for each in body["scopes"]] == [
        (each["scope"], each["label"]) for each in expected["scopes"]
    ]
    # The points of the marking are the example's, the thresholds and the context too; only the day
    # differs, the reference and the budgets of the subprojects being the offer's.
    kept_points = [each["points"][:1] for each in body["scopes"]]
    assert deviations(kept_points, [each["points"][:1] for each in expected["scopes"]]) == set()
    for key in ("context", "thresholds"):
        assert body[key] == expected[key]
    # What differs on the day is the earned value of a mesh, from its budgets: the actual cost of
    # each mesh is the example's, by the remaining of its day (« maille » by « maille »), the cost
    # index being the earned value over it.
    spent = {
        each["key"]: D(each["actual_cost"])
        for each in example("remaining_indicators")["by_subproject"]
    }
    # The meshes spend, together, what the project spent (1 412 970,20 in the examples).
    assert sum(spent.values()) == D(example("project_indicators")["actual_cost"])
    assert set(spent) == set(MESHES) - {"project"}
    scopes = {mesh: read(api, witness, realm, f"{INDICATORS}?scope={mesh}") for mesh in MESHES}
    # A subproject names itself in its context as the example does, with its costs (#3653).
    subproject = example("project_indicators_subproject")
    for field in ("context", "actual_cost", "earned_value"):
        assert scopes[COMMAND_POST][field] == subproject[field], field
    earned_by_the_example = D(0)
    for found, wanted in zip(body["scopes"], expected["scopes"], strict=True):
        mesh, scope = found["scope"], scopes[found["scope"]]
        if mesh == "project":
            continue
        day, theirs = found["points"][-1], wanted["points"][-1]
        assert D(scope["actual_cost"]) == spent[mesh], mesh
        assert D(scope["cost_index"]["value"]["value"]) == four_places(
            D(scope["earned_value"]) / spent[mesh]
        )
        # The example's earned value, by its index: within the rounding of four decimals.
        implied = D(theirs["cost_index"]["value"]["value"]) * spent[mesh]
        earned_by_the_example += implied
        if D(scope["earned_value"]) != 0:
            assert abs(implied - D(scope["earned_value"])) > D("0.00005") * spent[mesh], mesh
        # The offer declares no budget for a subproject, so it plans and earns nothing there; out
        # of any subproject, the whole project: the earned and planned values of the project.
        reference = D(scope["reference_budget"])
        assert (reference == 0) == (mesh != UNASSIGNED)
        for field in ("earned_value", "planned_value"):
            assert D(scope[field]) == (D(scopes["project"][field]) if reference else 0), mesh
        # A zone follows its index: the zone of the reading's own value, on the thresholds of the
        # example (WF-REF-0170), whatever the example's value is.
        for axis, kind in (("cost_index", "cost"), ("schedule_index", "schedule")):
            shown = day[axis]["value"]["value"]
            assert day[axis]["zone"] == (
                None
                if shown is None
                else zone_of(
                    D(shown),
                    D(expected["thresholds"][f"{kind}_watch"]),
                    D(expected["thresholds"][f"{kind}_alert"]),
                )
            ), (mesh, axis)
    # The earned value of the project is the example's, and spread over its meshes by the example.
    tolerance = D("0.00005") * sum(spent.values())
    assert abs(earned_by_the_example - D(scopes["project"]["earned_value"])) <= tolerance
    assert scopes["project"]["earned_value"] == example("project_indicators")["earned_value"]


@QUA
def test_the_index_history_of_a_subproject_is_the_example_but_for_the_planned_value(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # The offer declares no budget for the subproject: nothing is planned, the schedule index of the
    # day is not computable where the example's, measured to the amendment 1, is nought.
    del the_day
    body = read(api, witness, realm, f"{INDICATORS}/index-history?scope={COMMAND_POST}")
    expected = example("index_history_subproject")
    assert deviations(body, expected) == {
        path for path in INDEX_POINT_APART if "schedule_index" in path
    }
    assert body["context"] == expected["context"]
    assert [each["scope"] for each in body["scopes"]] == [COMMAND_POST]
    (ours,), (theirs,) = body["scopes"], expected["scopes"]
    assert ours["points"][0] == theirs["points"][0]
    assert ours["points"][1]["schedule_index"]["value"]["reason"] == "no_planned_value"
    assert ours["points"][1]["cost_index"] == theirs["points"][1]["cost_index"]


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
def test_the_cost_curve_is_the_example_but_for_the_step_of_the_reference_and_the_provisions(
    api: ContractClient, witness: Database, realm: TestRealm, name: str, path: str
) -> None:
    # « La courbe de coûts … le coût réel s'arrête à la date de calcul, et la projection part de ce
    # point » : the context, the names and the actual cost are the example's, the budget measured to
    # the offer, without the step of the amendment, and the projection less the provisions.
    body = read(api, witness, realm, f"{BASE}{path}")
    expected = example(name)
    assert body["context"] == expected["context"]
    assert body["context"]["is_stored"] is False
    assert names_of(body) == names_of(expected)
    assert body["steps"] == []
    assert [(each["cause"], D(each["amount"])) for each in expected["steps"]] == [
        ("amendment", step())
    ]
    measured(series_of(body, "reference_budget"), series_of(expected, "reference_budget"))
    same_origin(series_of(body, "actual_cost"), series_of(expected, "actual_cost"))
    gaps = gaps_of_the_projection(
        series_of(body, "project_manager_projection"),
        series_of(expected, "project_manager_projection"),
    )
    assert set(gaps.values()) == {D(0), provisions_of_the_day()}
    assert gaps[min(gaps)] == 0
    assert gaps[max(gaps)] == provisions_of_the_day()
    assert (body["cash_out_by_month"] is None) == (expected["cash_out_by_month"] is None)


@QUA
def test_the_cash_out_is_the_example_but_for_the_provisions_and_sums_to_the_remaining(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # « ceux à venir, dont la somme égale le reste à engager » : the months and the past
    # disbursements are the example's, the forecast of June falls short by the provisions.
    del the_day
    body = read(api, witness, realm, f"{INDICATORS}/cost-curve?payment_delays=true")
    expected = example("cost_curve_payment_delays")
    assert [each["month"] for each in body["cash_out_by_month"]] == [
        each["month"] for each in expected["cash_out_by_month"]
    ]
    assert deviations(body["cash_out_by_month"], expected["cash_out_by_month"]) == {"[]/forecast"}
    gaps = {
        each["month"]: D(theirs["forecast"]) - D(each["forecast"])
        for each, theirs in zip(
            body["cash_out_by_month"], expected["cash_out_by_month"], strict=True
        )
        if each != theirs
    }
    assert gaps == {"2026-06": provisions_of_the_day()}
    indicators = read(api, witness, realm, INDICATORS)
    assert sum(D(each["forecast"]) for each in body["cash_out_by_month"]) == D(
        indicators["remaining"]
    )


@QUA
def test_the_cost_curve_of_a_subproject_is_the_example_but_for_the_budget_the_offer_lacks(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    # « le budget de référence de ses seules lignes » : the offer 100 declares no budget for the
    # subproject, its curve and its step are empty, and its reference budget nought; the actual cost
    # and the projection, of its own lines, are the example's.
    del the_day
    body = read(api, witness, realm, f"{INDICATORS}/cost-curve?scope={COMMAND_POST}")
    expected = example("cost_curve_subproject")
    assert body["context"] == expected["context"]
    assert names_of(body) == names_of(expected)
    assert (body["steps"], series_of(body, "reference_budget")) == ([], {})
    assert [each["cause"] for each in expected["steps"]] == ["amendment"]
    same_origin(series_of(body, "actual_cost"), series_of(expected, "actual_cost"))
    assert series_of(body, "project_manager_projection") == series_of(
        expected, "project_manager_projection"
    )
    scope = read(api, witness, realm, f"{INDICATORS}?scope={COMMAND_POST}")
    assert scope["reference_budget"] == "0.00"


@QUA
def test_the_earned_value_curves_are_the_example_but_for_the_planned_value_of_the_reference(
    api: ContractClient, witness: Database, realm: TestRealm, the_day: None
) -> None:
    del the_day
    body = read(api, witness, realm, f"{INDICATORS}/earned-value-curves")
    expected = example("earned_value_curves")
    assert deviations(body, expected) == {"/series[]/points[]/amount"}
    assert body["context"] == expected["context"]
    assert (body["steps"], expected["steps"]) == ([], [])
    assert names_of(body) == names_of(expected) == ["planned_value", "earned_value", "actual_cost"]
    for name in ("earned_value", "actual_cost"):
        assert series_of(body, name) == series_of(expected, name)
    planned, theirs = series_of(body, "planned_value"), series_of(expected, "planned_value")
    assert planned.keys() == theirs.keys()
    gaps = measured(planned, theirs)
    # The planned value is the reference budget cumulated, in both: the holes of the one are the
    # holes of the other, day by day, so the step is spread as the cost curve spreads it.
    curve, curve_of_the_example = (
        read(api, witness, realm, f"{INDICATORS}/cost-curve"),
        example("cost_curve"),
    )
    assert planned == series_of(curve, "reference_budget")
    same_origin(theirs, series_of(curve_of_the_example, "reference_budget"))
    assert gaps == measured(
        series_of(curve, "reference_budget"), series_of(curve_of_the_example, "reference_budget")
    )


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
def test_the_estimate_of_the_101_is_the_example_but_for_the_provision_the_risks_and_the_reference(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The lines of the 101 are those of the revision in progress at the example's day, but the
    # provision of the identified risk and the 200 of the lines the occurrence of a risk merged
    # afterwards (EP-08); the deltas are measured to the offer 100, the reference and the revision
    # marked before.
    body = read(api, witness, realm, f"{BASE}/estimate-indicators?{KEPT}")
    expected = example("estimate_indicators")
    marked = example("project_indicators_marked")
    assert body["context"] == marked["context"]
    assert deviations(without(body, {"context"}), without(expected, {"context"})) == set(
        ESTIMATE_APART
    )
    provision = D(expected["provisions_identified"])
    occurred = D(example("remaining_indicators")["coverage"]["occurred_reestimated"])
    assert body["provisions_identified"] == "0.00"
    ours, theirs = D(body["total"]["value"]), D(expected["total"]["value"])
    assert theirs - ours == provision + occurred
    # The natures but the provision; the labour the example's, the disbursements less the 200.
    wanted = {
        each["key"]: each for each in expected["by_cost_type"] if each["label"] != "Provision"
    }
    assert [each["key"] for each in body["by_cost_type"]] == list(wanted)
    assert [
        D(wanted[each["key"]]["amount"]["value"]) - D(each["amount"]["value"])
        for each in body["by_cost_type"]
    ] == [0, occurred]
    # The subprojects: the provision and the lines of the occurrence weigh on "out of any
    # subproject"; the work packages: on the one that bears them.
    assert [
        D(in_example["amount"]["value"]) - D(each["amount"]["value"])
        for each, in_example in zip(body["by_subproject"], expected["by_subproject"], strict=True)
    ] == [0, 0, provision + occurred]
    held = [
        (in_example["key"], D(in_example["amount"]["value"]) - D(each["amount"]["value"]))
        for each, in_example in zip(
            body["by_work_package"], expected["by_work_package"], strict=True
        )
    ]
    assert [each for each in held if each[1]] == [
        (expected["by_work_package"][0]["key"], provision + occurred)
    ]
    for dimension in ("by_cost_type", "by_subproject"):
        assert sum(D(each["amount"]["value"]) for each in body[dimension]) == ours
    # The reserve is the provision, the occurrence and the variance of the coverage, the three
    # of the remaining of the example; the 101 as marked is the 101's estimate and that reserve.
    coverage = example("remaining_indicators")["coverage"]
    assert provisions_marked() == (
        D(coverage["remaining_provisions"])
        + D(coverage["occurred_reestimated"])
        + D(coverage["coverage_variance"])
    )
    as_marked = D(marked["remaining"])
    assert as_marked == ours + provisions_marked()


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
def test_the_gap_to_the_example_is_the_provision_the_occurrence_and_the_reference(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # What the delta of the witness lacks of the example's, to the cent: the provision and the
    # occurrence of the total, and the reference, the offer's estimate over the 101's as marked, not
    # the step of the amendment (2 830.95) the reference budget falls short by.
    body, expected, offer = estimate_deltas(api, witness, realm)
    provision = D(expected["provisions_identified"])
    occurred = D(example("remaining_indicators")["coverage"]["occurred_reestimated"])
    as_marked = D(example("project_indicators_marked")["remaining"])
    # The one literal of the corpus, anchoring the identity: the offer over the 101 as marked.
    assert offer - as_marked == D("1013056.56")
    for delta in ("delta_to_reference", "delta_to_previous_revision"):
        gap = D(expected[delta]["value"]) - D(body[delta]["value"])
        assert gap == provision + occurred + (offer - as_marked), delta


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
def test_the_remaining_of_the_101_is_the_kept_indicators_of_the_project_less_the_reserve(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # Nothing was spent at the marking: the actual cost of each subproject is the example's of the
    # marking, nought, and the remaining the project kept, less the reserve of the risks (EP-08),
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
    assert total == D(marked["remaining"]) - provisions_marked()
    kept_project = read(api, witness, realm, f"{INDICATORS}?{KEPT}")
    assert total == D(kept_project["remaining"])
    # The natures and the subprojects of the example, but the provision; the coverage at nought.
    assert [(each["key"], each["label"]) for each in body["by_cost_type"]] == [
        (each["key"], each["label"])
        for each in expected["by_cost_type"]
        if each["label"] != "Provision"
    ]
    assert [(each["key"], each.get("label")) for each in body["by_subproject"]] == [
        (each["key"], each.get("label")) for each in expected["by_subproject"]
    ]
    assert {each["actual_cost"] for each in body["by_subproject"]} == {marked["actual_cost"]}
    # Nothing was spent: what remains is the estimate of the 101, by nature and by subproject, and
    # each share its nature's part of the total.
    estimate = read(api, witness, realm, f"{BASE}/estimate-indicators?{KEPT}")
    assert {each["key"]: each["amount"] for each in body["by_cost_type"]} == {
        each["key"]: each["amount"]["value"] for each in estimate["by_cost_type"]
    }
    assert {each["key"]: each["remaining"] for each in body["by_subproject"]} == {
        each["key"]: each["amount"]["value"] for each in estimate["by_subproject"]
    }
    for each in body["by_cost_type"]:
        assert D(each["share"]["value"]) == four_places(D(each["amount"]) / total)
    assert sum(D(each["amount"]) for each in body["by_cost_type"]) == total
    assert sum(D(each["remaining"]) for each in body["by_subproject"]) == total
    assert set(body["coverage"].values()) == {"0.00"}
    # Measured to the offer 100, each margin the budget less the actual cost and the remaining.
    match = (RevisionIndicator.revision_id == REVISION_100, RevisionIndicator.kind == "remaining")
    with witness.transaction() as session:
        offer = sum(
            (facet.reestimated_amount for _, facet in line_rows(session, REVISION_100).values()),
            D(0),
        )
        offered = session.scalars(select(RevisionIndicator.document).where(*match)).one()
    assert sum(D(each["budget"]) for each in body["by_subproject"]) == offer
    assert D(kept_project["reference_budget"]) == offer
    for each in body["by_subproject"]:
        margin = D(each["budget"]) - D(each["actual_cost"]) - D(each["remaining"])
        assert D(each["variance"]) == margin
        assert (each["is_over_budget"], each["zone"]) == (
            (True, "alert") if margin < 0 else (False, "nominal")
        )
    assert D(body["delta_to_reference"]) == sum(D(e["variance"]) for e in body["by_subproject"])
    # The offer 100 alone was marked before the 101: its remaining less the offer's (US-1670).
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
    assert len(first) == 21 + 3  # the workload, the costs and the milestones (US-2680/L2)
    held = [json.loads(row[4]) for row in first if row[0] not in PORTFOLIO]
    assert {each["context"]["is_stored"] for each in held} == {True}
    assert kinds_of(witness, REVISION_101) == {"estimate", "remaining", "project", *CURVES}


@QUA
def test_no_address_and_no_project_but_the_witness_s_appear_in_the_documents_the_101_kept(
    witness: Database,
) -> None:
    # « Aucune adresse électronique ni aucun libellé de projet réel n'y figure » : the documents
    # add nothing to the witness — their labels are those of its subprojects, natures and milestones
    # (US-2680/L2), and no text holds an address.
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
    allowed = {
        each["label"]
        for each in example("remaining_indicators")["by_subproject"]
        if "label" in each
    }
    allowed |= {each["label"] for each in example("remaining_indicators")["by_cost_type"]}
    allowed |= {each["label"] for each in example("estimate_indicators")["by_work_package"]}
    allowed |= {each["label"] for each in example("milestone_tracking")["milestones"]}
    assert labels
    assert labels <= allowed
    assert "@" not in json.dumps(found)
