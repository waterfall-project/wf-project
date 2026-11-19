# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The eight views of the portfolio on the witness and its slice, read on 3 June 2026 (US-2770).

Each view sums what ``mockslicereadings`` says each project kept, as the design of EP-11 says a
view chooses, weighs and sums (« Les vues »), and answers in the form the contract gives it.
``make mock-data`` writes the description of the slice and these readings under
``fixtures/witness/portfolio/`` (``documents``), and ``make mock-data-up-to-date`` keeps them: the
loading of the slice and the comparison of the answers of the service with them are the next lot's
(US-2770/L2). Every view is asked the same way: at ``as_of`` 2026-06-03, with ``states`` naming the
projects in progress, in pricing and completed, the default period, horizon and threshold.
"""

from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, cast

from wftools import (
    mockhistory,
    mockindicators,
    mockportfolio,
    mockportfoliotime,
    mockrender,
    mockslice,
)
from wftools.mockslice import COMPLETED, DISMISSED, IDENTIFIED, IN_PROGRESS, LOST, PRICING
from wftools.mockslicereadings import (
    AS_OF,
    HORIZON,
    MAX_WEEKS,
    PERIOD_FROM,
    STATES,
    Kept,
    KeptRisk,
    Member,
    members,
)
from wftools.mockstructure import (
    CENT,
    JsonObject,
    JsonValue,
    computable,
    decimal,
    money,
    part_share,
    partition,
    share,
)
from wftools.mockwitness import FIXTURES, by_identifier, fixture

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

DESCRIPTION = (
    "Lecture attendue engendrée par `make mock-data` (`wftools.mocksliceviews`) : elle ne se "
    "retouche pas."
)
ZONES = ("nominal", "watch", "alert")


def _cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _sum(values: Iterable[Decimal]) -> Decimal:
    return sum(values, Decimal(0))


def _weight(kept: Kept, amount: Decimal) -> Decimal:
    """Return the part of an amount a project contributes: all of it, an offer's weighted once."""
    return _cents(amount * kept.probability) if kept.offer else amount


class Portfolio:
    """The projects of the witness at a day, as each view retains them."""

    def __init__(self, found: list[Member], day: date = AS_OF) -> None:
        self.members, self.day = found, day

    def retained(self, states: Iterable[str]) -> list[Member]:
        """Return the projects of the states a view counts, in the order of loading.

        A completed project is retained when it completed in the period, the default one
        (WF-PTF-0010); a lost or abandoned one never is.
        """
        kept = set(states)
        return [
            each
            for each in self.members
            if (state := each.state_on(self.day)) in kept
            and (state != COMPLETED or each.completed_in(PERIOD_FROM, self.day))
        ]

    def scope(self, states: Iterable[str], *, period: bool) -> JsonObject:
        """Return the scope: the states asked, and the number of projects the view counts."""
        return {
            "states": list(STATES),
            "as_of": self.day.isoformat(),
            "from": PERIOD_FROM.isoformat() if period else None,
            "to": self.day.isoformat() if period else None,
            "org_node_id": None,
            "org_node_label": None,
            "project_count": len(self.retained(states)),
        }

    def contributions(self, states: Iterable[str]) -> list[Kept]:
        """Return what the retained projects kept: an offer its estimate, another its indicators.

        A project with nothing of its kind kept contributes nothing (US-2670).
        """
        found: list[Kept] = []
        for each in self.retained(states):
            in_pricing = each.state_on(self.day) == PRICING
            kept = each.offer_on(self.day) if in_pricing else each.project_on(self.day)
            if kept is not None:
                found.append(kept)
        return found


# --- The list and the value (US-2690) -----------------------------------------------------------


def _index(numerator: Decimal, denominator: Decimal, reason: str) -> JsonObject:
    """Return an index and its zone, not computable on a nil denominator (WF-IND-0010)."""
    if denominator == 0:
        return {"value": {"is_computable": False, "value": None, "reason": reason}, "zone": None}
    found = share(numerator / denominator)
    return {"value": computable(decimal(found)), "zone": mockportfolio.zone(found)}


def _row(each: Member, day: date) -> JsonObject:
    state = cast("str", each.state_on(day))
    last = each.last_on(day)
    row: JsonObject = {
        "project_id": each.project_id,
        "label": each.label,
        "code": each.code,
        "state": state,
        "can_open": True,
        "reference_budget": None,
        "current_estimate": None,
        "win_probability": None,
        "project_manager_projection": None,
        "delta_to_reference": None,
        "cost_index": None,
        "schedule_index": None,
        "last_marked_at": None if last is None else mockhistory.stamp(last.marked),
    }
    if last is None:
        return row
    row["win_probability"] = decimal(last.probability)
    if last.offer:
        if state == PRICING:
            row["current_estimate"] = money(last.estimate)
        return row
    row["reference_budget"] = money(last.budget)
    row["cost_index"] = _index(last.earned, last.actual, "no_actual_cost")
    row["schedule_index"] = _index(last.earned, last.planned, "no_planned_value")
    if state == IN_PROGRESS:
        row["project_manager_projection"] = money(last.projection)
        row["delta_to_reference"] = money(last.projection - last.budget)
    return row


def projects(portfolio: Portfolio) -> JsonObject:
    """Return the list, sorted by label as without ``sort_by``: code points, then identifier."""
    rows = [_row(each, portfolio.day) for each in portfolio.retained(STATES)]
    rows.sort(key=lambda row: (str(row["label"]), str(row["project_id"])))
    return {
        "scope": portfolio.scope(STATES, period=False),
        "items": cast("list[JsonValue]", rows),
        "meta": {"limit": 50, "offset": 0, "total": len(rows)},
    }


def conversion(portfolio: Portfolio) -> JsonObject:
    """Return the offers won over those won or lost in the period, in the scope or not."""
    won = lost = 0
    for each in portfolio.members:
        for (_, left), (instant, state) in zip(each.history, each.history[1:], strict=False):
            if left == PRICING and PERIOD_FROM <= instant.date() <= portfolio.day:
                won += state == IN_PROGRESS
                lost += state == LOST
    if not won + lost:
        return {"is_computable": False, "value": None, "reason": "no_offer_out_of_pricing"}
    return computable(decimal(share(Decimal(won) / (won + lost))))


def value(portfolio: Portfolio) -> JsonObject:
    """Return the order book, the pipeline gross and weighted, the delivered and the conversion."""
    offers = [kept for kept in portfolio.contributions([PRICING]) if kept.offer]
    delivered = (each.project_on(portfolio.day) for each in portfolio.retained([COMPLETED]))
    return {
        "scope": portfolio.scope(STATES, period=True),
        "order_book": money(_sum(kept.budget for kept in portfolio.contributions([IN_PROGRESS]))),
        "pipeline_gross": money(_sum(kept.estimate for kept in offers)),
        "pipeline_weighted": money(_sum(_weight(kept, kept.estimate) for kept in offers)),
        "delivered": money(_sum(kept.actual for kept in delivered if kept is not None)),
        "conversion_rate": conversion(portfolio),
    }


# --- The workload (US-2700) ---------------------------------------------------------------------


def _months(first: date, count: int) -> list[str]:
    month = first.year * 12 + first.month - 1
    return [f"{rank // 12}-{rank % 12 + 1:02d}" for rank in range(month, month + count)]


def workload(portfolio: Portfolio) -> JsonObject:
    """Return the load by role and month: a project's remaining, an offer's weighted estimate.

    Each part rounded to the hundredth of an hour before the sum, an offer's weighted so; every
    active role, its capacity its monthly hours (WF-PTF-0060, WF-REF-0100).
    """
    states = (IN_PROGRESS, PRICING)
    months = _months(portfolio.day, HORIZON)
    hours: defaultdict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for kept in portfolio.contributions(states):
        for key, each in kept.hours.items():
            hours[key] += _cents(each * kept.probability) if kept.offer else each
    roles: list[JsonValue] = []
    capacities = Decimal(0)
    totals = dict.fromkeys(months, Decimal(0))
    for role in by_identifier("resource_roles", "resource_role_id"):
        if not role["is_active"]:
            continue
        capacity = Decimal(role["capacity"]["monthly_hours"])
        capacities += capacity
        entries: list[JsonValue] = []
        for month in months:
            load = hours[role["resource_role_id"], month]
            totals[month] += load
            entries.append(
                {
                    "month": month,
                    "hours": decimal(load),
                    "load_ratio": mockindicators.ratio(load, capacity, "no_capacity"),
                    "zone": mockportfoliotime.load_zone(load, capacity),
                }
            )
        roles.append(
            {
                "resource_role_id": role["resource_role_id"],
                "label": role["label"],
                "capacity_monthly_hours": decimal(capacity),
                "months": entries,
            }
        )
    return {
        "scope": portfolio.scope(states, period=False),
        "under_load_threshold": decimal(mockportfoliotime.UNDER_LOAD),
        "capacity_monthly_hours": decimal(capacities),
        "months": cast("list[JsonValue]", months),
        "monthly_totals": [
            {"month": month, "hours": decimal(total)} for month, total in totals.items()
        ],
        "roles": roles,
    }


# --- The performance (US-2710) ------------------------------------------------------------------


def progressing(portfolio: Portfolio, day: date) -> list[Kept]:
    """Return the kept indicators of the projects in progress on a day that have some."""
    return [
        kept
        for each in portfolio.members
        if each.state_on(day) == IN_PROGRESS and (kept := each.project_on(day)) is not None
    ]


def quarter_end(quarter: str) -> date:
    """Return the last day of a calendar quarter, ``2026-Q1``."""
    year, rank = int(quarter[:4]), int(quarter[-1])
    return date(year + rank // 4, rank * 3 % 12 + 1, 1) - timedelta(days=1)


def quarterly(portfolio: Portfolio) -> list[JsonValue]:
    """One point per quarter the period touches, read at its last day, the day's at the day."""
    points: list[JsonValue] = []
    for quarter in mockportfolio.quarters(PERIOD_FROM, portfolio.day):
        kept = progressing(portfolio, min(quarter_end(quarter), portfolio.day))
        earned = _sum(each.earned for each in kept)
        cost = _index(earned, _sum(each.actual for each in kept), "no_actual_cost")
        schedule = _index(earned, _sum(each.planned for each in kept), "no_planned_value")
        points.append(
            {"quarter": quarter, "cost_index": cost["value"], "schedule_index": schedule["value"]}
        )
    return points


def performance(portfolio: Portfolio) -> JsonObject:
    """Return the ratios of the sums of the projects in progress, never an average (WF-PTF-0020)."""
    kept = progressing(portfolio, portfolio.day)
    budget, planned = _sum(e.budget for e in kept), _sum(e.planned for e in kept)
    earned, actual = _sum(e.earned for e in kept), _sum(e.actual for e in kept)
    projection = _sum(e.projection for e in kept)
    at_budget = _sum(e.actual + e.budget - e.earned for e in kept)
    observed, total = mockportfolio.at_observed_rate(budget, actual, earned)
    zones: Counter[tuple[str, str | None]] = Counter()
    for each in kept:
        cost = _index(each.earned, each.actual, "no_actual_cost")
        schedule = _index(each.earned, each.planned, "no_planned_value")
        zones["cost", cast("str | None", cost["zone"])] += 1
        zones["schedule", cast("str | None", schedule["zone"])] += 1
    return {
        "scope": portfolio.scope([IN_PROGRESS], period=True),
        "reference_budget": money(budget),
        "cost_index": _index(earned, actual, "no_actual_cost"),
        "schedule_index": _index(earned, planned, "no_planned_value"),
        "cost_variance": money(earned - actual),
        "schedule_variance": money(earned - planned),
        "projections": {
            "at_budget": money(at_budget),
            "project_manager": money(projection),
            "at_observed_rate": observed,
            "variance_at_budget": money(at_budget - budget),
            "variance_project_manager": money(projection - budget),
            "variance_at_observed_rate": None if total is None else money(total - budget),
        },
        "zone_distribution": [
            {"index": index, "zone": zone, "project_count": zones[index, zone]}
            for index in ("cost", "schedule")
            for zone in ZONES
        ],
        "quarterly": quarterly(portfolio),
    }


# --- The structure of the costs (US-2720) -------------------------------------------------------


def _parts(amounts: dict[str, Decimal], labels: dict[str, str]) -> list[JsonValue]:
    """Return amounts by key in the order of the keys, their shares summing to one."""
    keys = [key for key in labels if key in amounts]
    found = partition([amounts[key] for key in keys], _sum(amounts[key] for key in keys))
    return [
        {"key": key, "label": labels[key], "amount": money(amounts[key]), "share": part_share(part)}
        for key, part in zip(keys, found, strict=True)
    ]


def cost_structure(portfolio: Portfolio) -> JsonObject:
    """Return the budget and the remaining by nature, and the labour by node of its roles.

    The budget without its provision lines, the remaining with them; an offer its estimate in
    both, weighted once by project and by key (WF-PTF-0080, M-07). The labour is that of the
    budget, grouped by the current node of each role (EP-11, « Ce que le cadrage décide »).
    """
    budget: defaultdict[str, Decimal] = defaultdict(Decimal)
    remaining: defaultdict[str, Decimal] = defaultdict(Decimal)
    nodes: defaultdict[str, Decimal] = defaultdict(Decimal)
    of_role = {
        role["resource_role_id"]: role["org_node_id"] for role in fixture("resource_roles")["items"]
    }
    for kept in portfolio.contributions(STATES):
        for key, amount in kept.budget_by_nature.items():
            budget[key] += _weight(kept, amount)
        for key, amount in kept.remaining_by_nature.items():
            remaining[key] += _weight(kept, amount)
        by_node: defaultdict[str, Decimal] = defaultdict(Decimal)
        for role, amount in kept.labour_by_role.items():
            by_node[of_role[role]] += amount
        for node, amount in by_node.items():
            nodes[node] += _weight(kept, amount)
    natures = {
        each["cost_type_id"]: each["label"] for each in by_identifier("cost_types", "cost_type_id")
    }
    labels = {
        each["org_node_id"]: each["label"]
        for each in sorted(fixture("org_nodes"), key=lambda node: str(node["org_node_id"]))
    }
    return {
        "scope": portfolio.scope(STATES, period=True),
        "budget_by_cost_type": _parts(dict(budget), natures),
        "remaining_by_cost_type": _parts(dict(remaining), natures),
        "labor_by_org_node": _parts(dict(nodes), labels),
    }


# --- The risks (US-2730) ------------------------------------------------------------------------


def _level(value: Decimal, levels: list[JsonObject]) -> int:
    """Return the level a value falls in: a value equal to a bound is of the level it opens."""
    return max(
        cast("int", level["level"])
        for level in levels
        if value >= Decimal(cast("str", level["lower"]))
    )


def risks(portfolio: Portfolio) -> JsonObject:
    """Return the identified risks of the scope without weighting, the matrix and the coverage.

    Each risk classed on the base of its project as its marking kept it: the reference budget,
    the estimate without provisions for an offer (WF-REF-0160); the reserve and the coverage of
    the projects in progress and completed alone (WF-PTF-0090, WF-RIS-0050).
    """
    matrix = mockhistory.readings()["risk_matrix"]
    probabilities = cast("list[JsonObject]", matrix["probability_levels"])
    severities = cast("list[JsonObject]", matrix["severity_levels"])
    zones = {
        (cell["probability_level"], cell["severity_level"]): cell["zone"]
        for cell in cast("list[JsonObject]", matrix["cells"])
    }
    found: list[tuple[Member, Kept, KeptRisk]] = []
    reserve = remaining = Decimal(0)
    for each in portfolio.retained(STATES):
        in_pricing = each.state_on(portfolio.day) == PRICING
        kept = each.offer_on(portfolio.day) if in_pricing else each.project_on(portfolio.day)
        if kept is None:
            continue
        identified = [risk for risk in kept.risks if risk.state == IDENTIFIED]
        found.extend((each, kept, risk) for risk in identified)
        if not in_pricing:
            reserve += kept.reserve
            remaining += _sum(risk.provision for risk in identified)
    occurred = dismissed = Decimal(0)
    for each in portfolio.retained(STATES):
        for instant, state, provision in each.outcomes:
            if PERIOD_FROM <= instant.date() <= portfolio.day:
                occurred += provision if state == "occurred" else 0
                dismissed += provision if state == DISMISSED else 0
    total = _sum(risk.provision for _, _, risk in found)
    points: list[JsonValue] = []
    counted: Counter[tuple[int, int]] = Counter()
    for each, kept, risk in found:
        ratio = risk.severity / kept.budget
        cell = (_level(risk.probability, probabilities), _level(ratio, severities))
        counted[cell] += 1
        points.append(
            {
                "risk_id": risk.risk_id,
                "label": risk.label,
                "probability": decimal(risk.probability),
                "severity_amount": money(risk.severity),
                "severity_ratio": computable(decimal(share(ratio))),
                "provision_amount": money(risk.provision),
                "state": IDENTIFIED,
                "zone": zones[cell],
                "project_id": each.project_id,
                "project_label": each.label,
                "can_open": True,
            }
        )
    heaviest = sorted(found, key=lambda entry: (-entry[2].provision, entry[2].risk_id))[:10]
    return {
        "scope": portfolio.scope(STATES, period=True),
        "identified_total": money(total),
        "heaviest": [
            {
                "risk_id": risk.risk_id,
                "label": risk.label,
                "project_id": each.project_id,
                "project_label": each.label,
                "can_open": True,
                "provision_amount": money(risk.provision),
            }
            for each, _, risk in heaviest
        ],
        "matrix": {
            "probability_levels": cast("list[JsonValue]", probabilities),
            "severity_levels": cast("list[JsonValue]", severities),
            "cells": [
                {
                    "probability_level": cell["probability_level"],
                    "severity_level": cell["severity_level"],
                    "count": counted[
                        cast("int", cell["probability_level"]),
                        cast("int", cell["severity_level"]),
                    ],
                    "zone": cell["zone"],
                }
                for cell in cast("list[JsonObject]", matrix["cells"])
            ],
            "points": points,
            "totals": {
                "total": money(total + occurred + dismissed),
                "identified": money(total),
                "occurred": money(occurred),
                "dismissed": money(dismissed),
                "reserve": money(reserve),
            },
        },
        "coverage": {
            "reserve": money(reserve),
            "remaining_provisions": money(remaining),
            "occurred_cost": money(Decimal(0)),
            "occurred_reestimated": money(Decimal(0)),
            "coverage_variance": money(reserve - remaining),
        },
        "period_outcome": {
            "occurred_provisions": money(occurred),
            "dismissed_provisions": money(dismissed),
        },
    }


# --- The S-curve (US-2740) ----------------------------------------------------------------------


def cost_curve(portfolio: Portfolio) -> JsonObject:
    """Return the sums, month by month, of the curves each project kept (WF-PTF-0100).

    The twelve months before that of the day, then the horizon: the reference budget at each end
    of month, the actual cost up to the day, the projection from it; an offer its curves weighted
    point by point, without its provisions for the budget, with them for the projection.
    """
    ends = mockportfoliotime.curve_months(portfolio.day, HORIZON)
    past = [end for end in ends if end < portfolio.day]
    ahead = [end for end in ends if end > portfolio.day]
    kept = portfolio.contributions(STATES)

    def points(read: str, days: list[date]) -> list[JsonValue]:
        return [
            {
                "date": day.isoformat(),
                "amount": money(_sum(_weight(each, getattr(each, read)(day)) for each in kept)),
            }
            for day in days
        ]

    return {
        "scope": portfolio.scope(STATES, period=True),
        "payment_delays": False,
        "series": [
            {"name": "reference_budget", "points": points("budget_curve", ends)},
            {"name": "actual_cost", "points": points("actual_curve", [*past, portfolio.day])},
            {
                "name": "project_manager_projection",
                "points": points("projection_curve", [portfolio.day, *ahead]),
            },
        ],
        "cash_out_by_month": None,
    }


# --- The health of the steering (US-2750) -------------------------------------------------------


def _signals(each: Member, day: date) -> list[JsonValue]:
    """Return the signals of a project in progress, in the order of the codes of the contract."""
    marked = each.kept_on(day)
    last = marked[-1]
    since = (
        marked[-2].marked
        if len(marked) > 1
        else next(instant for instant, state in each.history if state == IN_PROGRESS)
    )
    found: list[JsonValue] = []

    def signal(code: str, zone: str = "watch", params: JsonObject | None = None) -> None:
        named: JsonObject = {
            "project_id": each.project_id,
            "project_label": each.label,
            "can_open": True,
            "zone": zone,
            "code": code,
        }
        if params is not None:
            named["params"] = params
        found.append(named)

    days = (day - last.marked.date()).days
    if days > 7 * MAX_WEEKS:
        signal("review_overdue", params={"weeks_since_last_mark": days // 7})
    reviewed = {risk for risk, instant in each.reviews if since < instant <= last.marked}
    if any(r.state == IDENTIFIED and r.risk_id not in reviewed for r in last.risks):
        signal("risks_not_reviewed")
    if not any(since < instant <= last.marked for instant in each.imports):
        signal("no_actual_cost_since_last_review")
    for lineage, label, reference, completed in each.milestones:
        if reference < day and (completed is None or completed > day):
            signal(
                "contractual_milestone_overdue",
                "alert",
                {
                    "lineage_id": lineage,
                    "milestone_label": label,
                    "reference_date": reference.isoformat(),
                },
            )
    return found


def pilot_health(portfolio: Portfolio) -> JsonObject:
    """Return the four signals of the projects in progress, by project label (WF-PTF-0110).

    The review overdue past the delay of the reference, in whole weeks; a risk identified with no
    review between the last two marked revisions — since the passage to In progress without a
    previous one —; no import of actual costs in the same interval; a tracked milestone past its
    reference date that the kept marking did not see completed.
    """
    progressing_ = sorted(
        (each for each in portfolio.retained([IN_PROGRESS]) if each.kept_on(portfolio.day)),
        key=lambda each: (each.label, each.project_id),
    )
    return {
        "scope": portfolio.scope([IN_PROGRESS], period=False),
        "signals": [signal for each in progressing_ for signal in _signals(each, portfolio.day)],
    }


# --- The documents ------------------------------------------------------------------------------

VIEWS = (
    ("portfolio_projects", "getPortfolioProjects", projects),
    ("portfolio_value", "getPortfolioValue", value),
    ("portfolio_workload", "getPortfolioWorkload", workload),
    ("portfolio_performance", "getPortfolioPerformance", performance),
    ("portfolio_cost_structure", "getPortfolioCostStructure", cost_structure),
    ("portfolio_risks", "getPortfolioRisks", risks),
    ("portfolio_cost_curve", "getPortfolioCostCurve", cost_curve),
    ("pilot_health", "getPortfolioPilotHealth", pilot_health),
)
"""The eight views, by the name of their file, their operation and their computation."""

QUERY: JsonObject = {"as_of": AS_OF.isoformat(), "states": ",".join(STATES)}
"""The query every view is read with: the date of the witness, the three states."""


def readings() -> dict[str, JsonObject]:
    """Return the expected reading of each view, by file name, with the request that reads it."""
    portfolio = Portfolio(members())
    return {
        f"readings/{name}.json": {
            "summary": (
                f"Ce que {operation} doit répondre sur le témoin chargé avec la tranche du "
                f"portefeuille, lu au {AS_OF.isoformat()} par as_of : chaque projet par ce que "
                "sa dernière révision marquée à cette date a conservé (WF-PTF-0010, "
                "WF-DAT-0040, WF-QUA-0040)."
            ),
            "description": DESCRIPTION,
            "operation": operation,
            "query": QUERY,
            "value": compute(portfolio),
        }
        for name, operation, compute in VIEWS
    }


def documents() -> dict[str, JsonObject]:
    """Return every document of ``fixtures/witness/portfolio/``: the description, the readings."""
    return {
        **{f"projects/{name}": each for name, each in mockslice.description().items()},
        **readings(),
    }


SLICE_DIRECTORY = FIXTURES.parent / "witness" / "portfolio"
"""Where the slice lives, beside the examples of the contract and out of the contract."""

_NAME = "witness/portfolio"


def directory_of(fixtures: Path) -> Path:
    """Return where the slice is written for the examples of a directory.

    Beside ``fixtures/api``, the repository's; under any other directory — a test's —, inside it,
    so that a test never writes the repository.
    """
    return SLICE_DIRECTORY if fixtures == FIXTURES else fixtures / "witness" / "portfolio"


def _expected() -> dict[str, str]:
    return {name: mockrender.render(document) for name, document in documents().items()}


def write(directory: Path) -> list[Path]:
    """Write every document of the slice, removing a file of the directory none of them is."""
    expected = _expected()
    if directory.is_dir():
        for path in sorted(directory.rglob("*.json")):
            if path.relative_to(directory).as_posix() not in expected:
                path.unlink()
    written: list[Path] = []
    for name, text in expected.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
    return written


def check(directory: Path) -> list[str]:
    """Name each document of the slice missing or outdated, and each file left over."""
    expected = _expected()
    present = (
        {path.relative_to(directory).as_posix() for path in directory.rglob("*.json")}
        if directory.is_dir()
        else set[str]()
    )
    problems = [f"{_NAME}/{name} is left over" for name in sorted(present - expected.keys())]
    for name, text in expected.items():
        path = directory / name
        if not path.is_file():
            problems.append(f"{_NAME}/{name} is missing")
        elif path.read_bytes() != text.encode("utf-8"):
            problems.append(f"{_NAME}/{name} is outdated")
    return problems
