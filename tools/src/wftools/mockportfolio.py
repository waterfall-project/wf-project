# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Generate the portfolio of the volumes the fake back serves (EP-02/L2, US-0240/L3).

The three hundred projects of §4.6.2 that ``getPortfolioProjects`` lists, the witness project
and the offer of the other examples first, and the views summed from the same rows — value,
performance, structure of the costs, risks —, so that the list and the views tell the same
story. ``wftools.mockdata`` writes them in ``fixtures/api/volume/``. Nothing here reads the clock
or draws at random: every value drawn comes from the seed and from what it describes.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from functools import cache
from typing import Any, cast

from wftools import mockhistory, mocktoday
from wftools.mockstructure import (
    AS_OF,
    CENT,
    JsonObject,
    JsonValue,
    decimal,
    draw,
    money,
)
from wftools.mockwitness import PROJECTS, RISKS, fixture, identifier

PROJECT_COUNT = 300

WATCH_THRESHOLD = Decimal("0.9")
ALERT_THRESHOLD = Decimal("0.8")
"""The thresholds of the zones of an index, those of the Vérif of WF-REF-0170-A."""


# --- The portfolio of three hundred projects -------------------------------------------

_SUBJECTS = (
    "Modernisation",
    "Extension",
    "Rénovation",
    "Automatisation",
    "Mise en conformité",
    "Remplacement",
    "Construction",
)
_OBJECTS = (
    "du poste de commande",
    "de la ligne d'essais",
    "de la station de pompage",
    "du banc de mesure",
    "de l'atelier de montage",
    "du réseau de distribution",
    "de la sous-station",
    "du système de supervision",
    "de l'unité de traitement",
    "du magasin automatisé",
    "de la chaufferie",
)
_WIN_PROBABILITIES = ("0.2", "0.3", "0.4", "0.6", "0.8")


def zone(index: Decimal) -> str:
    """Return the zone of an index, as the server classes it by the thresholds (WF-REF-0170)."""
    if index >= WATCH_THRESHOLD:
        return "nominal"
    if index >= ALERT_THRESHOLD:
        return "watch"
    return "alert"


_SITES = ("Lyon", "Grenoble", "Dunkerque", "Toulouse")

UNOPENABLE_EVERY = 7
"""Which generated projects the reader cannot open (WF-PTF-0030): every seventh, by its number.

The list is read by a user without « consulter tous les projets », contributor of the witness,
of the offer and of every other project but these: they count in the totals and show their
label and code, without a link (WF-ADM-0110).
"""


def can_open(n: int) -> bool:
    """Return whether the reader can open the n-th generated project of the portfolio."""
    return n % UNOPENABLE_EVERY != 0


def portfolio() -> JsonObject:
    """Return the answer of getPortfolioProjects: the witness and the offer, then the others."""
    universe = universe_rows()
    taken = {str(row["label"]) for row in universe}
    rows: list[JsonValue] = [*universe]
    # Each generated label is a subject, an object and a site; the witness project and the
    # offer keep theirs, and no other project takes their subject and object.
    names = [
        f"{subject} {thing}"
        for thing in _OBJECTS
        for subject in _SUBJECTS
        if f"{subject} {thing}" not in taken
    ]
    for n in range(len(universe) + 1, PROJECT_COUNT + 1):
        rank = n - len(universe) - 1
        label = f"{names[rank % len(names)]} — {_SITES[rank // len(names)]}"
        rows.append(_portfolio_row(n, label))
    return {
        "scope": {
            "states": ["in_progress", "pricing"],
            "as_of": AS_OF.isoformat(),
            "from": None,
            "to": None,
            "org_node_id": None,
            "org_node_label": None,
            "project_count": PROJECT_COUNT,
        },
        "items": rows,
        # The whole portfolio in one page: the largest page the contract allows.
        "meta": {"limit": 500, "offset": 0, "total": PROJECT_COUNT},
    }


PAGE = 50
"""The projects of a page of the list asked by pages: the second one, of the volume."""


def portfolio_page(answer: JsonObject) -> JsonObject:
    """Return the second page of fifty projects of the list, as the server pages it."""
    items = cast("list[JsonValue]", answer["items"])
    page: JsonObject = dict(answer)
    page["items"] = items[PAGE : 2 * PAGE]
    page["meta"] = {"limit": PAGE, "offset": PAGE, "total": len(items)}
    return page


def universe_rows() -> list[JsonObject]:
    """Return the rows of the witness project and of the offer, from their fixtures.

    The witness project shows its indicators today, read in memory (``mocktoday``), never from
    the file the same command writes, and the date its reference
    revision was marked; the offer, without revision, has neither budget nor index.
    """
    project = fixture("project")
    indicators = cast("dict[str, Any]", mocktoday.project_today())
    offer = fixture("project_pricing")
    marked = next(
        revision["marked_at"]
        for revision in fixture("revisions")["items"]
        if revision["revision_id"] == project["reference_revision_id"]
    )
    witness: JsonObject = {
        "project_id": project["project_id"],
        "label": project["label"],
        "code": project["code"],
        "state": project["state"],
        "can_open": True,
        "reference_budget": indicators["reference_budget"],
        "current_estimate": None,
        "win_probability": project["win_probability"],
        "project_manager_projection": indicators["projections"]["project_manager"],
        "delta_to_reference": indicators["projections"]["variance_project_manager"],
        "cost_index": indicators["cost_index"],
        "schedule_index": indicators["schedule_index"],
        "last_marked_at": marked,
    }
    pricing: JsonObject = {
        "project_id": offer["project_id"],
        "label": offer["label"],
        "code": offer["code"],
        "state": offer["state"],
        "can_open": True,
        "reference_budget": None,
        "current_estimate": None,
        "win_probability": offer["win_probability"],
        "project_manager_projection": None,
        "delta_to_reference": None,
        "cost_index": None,
        "schedule_index": None,
        "last_marked_at": None,
    }
    return [witness, pricing]


def _portfolio_row(n: int, label: str) -> JsonObject:
    amount = Decimal(draw(f"amount/{n}", 2_000, 200_000)) * 100
    row: JsonObject = {
        "project_id": identifier(PROJECTS, n),
        "label": label,
        "code": f"PRJ-{n:03d}",
        "can_open": can_open(n),
    }
    if n % 10 == 0:
        pricing: JsonObject = {
            "state": "pricing",
            "reference_budget": None,
            "current_estimate": money(amount),
            "win_probability": _WIN_PROBABILITIES[draw(f"win/{n}", 0, len(_WIN_PROBABILITIES) - 1)],
            "project_manager_projection": None,
            "delta_to_reference": None,
            "cost_index": None,
            "schedule_index": None,
            "last_marked_at": None,
        }
        return row | pricing
    projection = amount * draw(f"projection/{n}", 95, 115) / 100
    marked = date(2026, 2, 2) + timedelta(days=draw(f"marked/{n}", 0, 25))
    progressing: JsonObject = {
        "state": "in_progress",
        "reference_budget": money(amount),
        "current_estimate": None,
        "win_probability": "1",
        "project_manager_projection": money(projection),
        "delta_to_reference": money(projection - amount),
        "cost_index": _index(Decimal(draw(f"cost/{n}", 70, 120)) / 100),
        "schedule_index": _index(Decimal(draw(f"schedule/{n}", 70, 120)) / 100),
        "last_marked_at": f"{marked.isoformat()}T17:00:00Z",
    }
    return row | progressing


def _index(value: Decimal) -> JsonObject:
    return {
        "value": {"is_computable": True, "value": decimal(value), "reason": None},
        "zone": zone(value),
    }


# --- The views of the portfolio, summed from its projects ----------------------------------

PERIOD_FROM = date(2025, 3, 17)
"""The start of the period of the views that read one: the year up to the day of the examples."""

_RATIO = Decimal("0.0001")
"""The places of a share or a rate the server gives: a ratio of sums, never rounded before."""

_RISK_SUBJECTS = (
    "Retard d'approvisionnement",
    "Reprise des fondations",
    "Défaillance d'un sous-traitant",
    "Dérive du coût de l'acier",
    "Indisponibilité d'un poste d'essais",
    "Non-conformité à la réception",
)

_CONVERSION_RATE = "0.4"
"""Ten offers out of pricing over the period, four of them won: the Vérif of WF-PTF-0050-A."""


@dataclass(frozen=True)
class Earned:
    """What a project in progress contributes to the sums of the portfolio (WF-PTF-0020)."""

    budget: Decimal
    planned: Decimal
    earned: Decimal
    actual: Decimal
    projection: Decimal

    @property
    def remaining(self) -> Decimal:
        """The remaining to commit: the projection of the project manager, less the actual cost."""
        return self.projection - self.actual


@cache
def _witness() -> tuple[str, Earned]:
    """Return the witness project, and the values of earned value of its indicators."""
    indicators = cast("dict[str, Any]", mocktoday.project_today())
    return fixture("project")["project_id"], Earned(
        budget=Decimal(indicators["reference_budget"]),
        planned=Decimal(indicators["planned_value"]),
        earned=Decimal(indicators["earned_value"]),
        actual=Decimal(indicators["actual_cost"]),
        projection=Decimal(indicators["projections"]["project_manager"]),
    )


def earned(row: JsonObject) -> Earned:
    """Return the values of earned value of a project in progress of the portfolio.

    The witness project's are those of its indicators; another's are drawn so that the indices
    of its row are theirs: an actual cost drawn from its budget, the earned value at its cost
    index, the planned value at its schedule index.
    """
    witness, values = _witness()
    if row["project_id"] == witness:
        return values
    budget = Decimal(cast("str", row["reference_budget"]))
    actual = (budget * draw(f"spent/{row['project_id']}", 20, 80) / 100).quantize(CENT)
    value = actual * _index_of(row, "cost_index")
    return Earned(
        budget=budget,
        planned=(value / _index_of(row, "schedule_index")).quantize(CENT),
        earned=value.quantize(CENT),
        actual=actual,
        projection=Decimal(cast("str", row["project_manager_projection"])),
    )


def _index_of(row: JsonObject, name: str) -> Decimal:
    index = cast("JsonObject", row[name])
    return Decimal(cast("str", cast("JsonObject", index["value"])["value"]))


def _scope(rows: list[JsonObject], states: list[JsonValue], *, period: bool) -> JsonObject:
    return {
        "states": states,
        "as_of": AS_OF.isoformat(),
        "from": PERIOD_FROM.isoformat() if period else None,
        "to": AS_OF.isoformat() if period else None,
        "org_node_id": None,
        "org_node_label": None,
        "project_count": sum(1 for row in rows if row["state"] in states),
    }


def _ratio(numerator: Decimal, denominator: Decimal) -> str:
    return decimal((numerator / denominator).quantize(_RATIO))


def portfolio_value(rows: list[JsonObject]) -> JsonObject:
    """Return the answer of getPortfolioValue over the rows of the portfolio (WF-PTF-0050).

    The order book sums the budgets of the projects in progress, the pipeline the estimates of
    the offers that have one, raw and weighted by their probability of winning; no project of the
    scope is completed, and nothing is delivered.
    """
    offers = [row for row in rows if row["state"] == "pricing" and row["current_estimate"]]
    weighted = sum(
        (
            Decimal(cast("str", row["current_estimate"]))
            * Decimal(cast("str", row["win_probability"]))
            for row in offers
        ),
        Decimal(0),
    )
    return {
        "scope": _scope(rows, ["in_progress", "pricing"], period=True),
        "order_book": money(sum((each.budget for each in _progressing(rows)), Decimal(0))),
        "pipeline_gross": money(
            sum((Decimal(cast("str", row["current_estimate"])) for row in offers), Decimal(0))
        ),
        "pipeline_weighted": money(weighted),
        "delivered": money(Decimal(0)),
        "conversion_rate": {"is_computable": True, "value": _CONVERSION_RATE, "reason": None},
    }


def _progressing(rows: list[JsonObject]) -> list[Earned]:
    return [earned(row) for row in rows if row["state"] == "in_progress"]


_QUARTERS = ("2025-Q2", "2025-Q3", "2025-Q4", "2026-Q1")
"""The quarters of the evolution: the first before any cost was spent, the last the day's."""


def portfolio_performance(rows: list[JsonObject]) -> JsonObject:
    """Return the answer of getPortfolioPerformance over the projects in progress (WF-PTF-0070).

    Each index is the ratio of the sums (WF-PTF-0020); the distribution counts each project
    once in the zone of each of its indices, none when its index has no zone; the evolution runs
    over the four quarters up to the day of the examples, the last one that day's, the first not
    computable, nothing having been spent nor planned yet.
    """
    sums = _progressing(rows)
    budget = sum((each.budget for each in sums), Decimal(0))
    planned = sum((each.planned for each in sums), Decimal(0))
    value = sum((each.earned for each in sums), Decimal(0))
    actual = sum((each.actual for each in sums), Decimal(0))
    projection = sum((each.projection for each in sums), Decimal(0))
    cost = (value / actual).quantize(CENT)
    schedule = (value / planned).quantize(CENT)
    at_budget = actual + budget - value
    at_rate = (actual + (budget - value) * actual / value).quantize(CENT)
    return {
        "scope": _scope(rows, ["in_progress"], period=False),
        "reference_budget": money(budget),
        "cost_index": _index(cost),
        "schedule_index": _index(schedule),
        "cost_variance": money(value - actual),
        "schedule_variance": money(value - planned),
        "projections": {
            "at_budget": money(at_budget),
            "project_manager": money(projection),
            "at_observed_rate": {"is_computable": True, "value": money(at_rate), "reason": None},
            "variance_at_budget": money(at_budget - budget),
            "variance_project_manager": money(projection - budget),
            "variance_at_observed_rate": money(at_rate - budget),
        },
        "zone_distribution": [
            {"index": index, "zone": name, "project_count": count}
            for index in ("cost", "schedule")
            for name, count in _zones(rows, f"{index}_index").items()
        ],
        "quarterly": [
            {
                "quarter": quarter,
                "cost_index": _drift(quarter, "cost", cost, last=quarter == _QUARTERS[-1]),
                "schedule_index": _drift(
                    quarter, "schedule", schedule, last=quarter == _QUARTERS[-1]
                ),
            }
            for quarter in _QUARTERS
        ],
    }


def _zones(rows: list[JsonObject], name: str) -> dict[str, int]:
    counted = Counter(
        cast("JsonObject", row[name])["zone"]
        for row in rows
        if row["state"] == "in_progress" and row[name] is not None
    )
    return {zone: counted[zone] for zone in ("nominal", "watch", "alert")}


_UNCOMPUTED = {"cost": "no_actual_cost", "schedule": "no_planned_value"}
"""Why the indices of the first quarter are not computable: nothing was spent nor planned yet."""


def _drift(quarter: str, index: str, today: Decimal, *, last: bool) -> JsonObject:
    if quarter == _QUARTERS[0]:
        return {"is_computable": False, "value": None, "reason": _UNCOMPUTED[index]}
    value = today if last else today + Decimal(draw(f"quarter/{index}/{quarter}", -8, 8)) / 100
    return {"is_computable": True, "value": decimal(value), "reason": None}


_LABOR_SHARE, _NON_LABOR_SHARE = Decimal("0.55"), Decimal("0.35")
_REMAINING_LABOR_SHARE, _REMAINING_NON_LABOR_SHARE = Decimal("0.5"), Decimal("0.4")
"""How the budgets and the remaining to commit of the portfolio part by nature."""


def portfolio_cost_structure(rows: list[JsonObject]) -> JsonObject:
    """Return the answer of getPortfolioCostStructure over the projects in progress (WF-PTF-0080).

    The budget and the remaining to commit part between the three natures of the universe, the
    provisions taking what is left, so that the parts sum to their totals; the labour is that of
    the one node of organisation the roles of the universe come under.
    """
    sums = _progressing(rows)
    budget = sum((each.budget for each in sums), Decimal(0))
    remaining = sum((each.remaining for each in sums), Decimal(0))
    natures = [(nature["cost_type_id"], nature["label"]) for nature in fixture("cost_types")]
    budgets = _parts(budget, (_LABOR_SHARE, _NON_LABOR_SHARE))
    org_node = fixture("resource_roles")[0]["org_node_id"]
    label = next(node["label"] for node in fixture("org_nodes") if node["org_node_id"] == org_node)
    return {
        "scope": _scope(rows, ["in_progress"], period=False),
        "budget_by_cost_type": _by_key(natures, budgets, budget),
        "remaining_by_cost_type": _by_key(
            natures,
            _parts(remaining, (_REMAINING_LABOR_SHARE, _REMAINING_NON_LABOR_SHARE)),
            remaining,
        ),
        "labor_by_org_node": _by_key([(org_node, label)], budgets[:1], budgets[0]),
    }


def _parts(total: Decimal, shares: tuple[Decimal, Decimal]) -> list[Decimal]:
    first, second = ((total * share).quantize(CENT) for share in shares)
    return [first, second, total - first - second]


def _by_key(keys: list[tuple[str, str]], amounts: list[Decimal], total: Decimal) -> list[JsonValue]:
    return [
        {"key": key, "label": label, "amount": money(amount), "share": _ratio(amount, total)}
        for (key, label), amount in zip(keys, amounts, strict=True)
    ]


@dataclass(frozen=True)
class Risk:
    """An identified risk of a project in progress of the portfolio, in its cell of the matrix."""

    row: JsonObject
    risk_id: str
    label: str
    probability: Decimal
    severity: Decimal
    provision: Decimal
    cell: tuple[int, int]


_MOST_LIKELY, _HEAVIEST = Decimal("0.9"), Decimal("0.2")
"""The upper bounds drawn in the last level of each axis of the matrix, which has none."""


def _bounds(level: JsonObject, last: Decimal) -> tuple[Decimal, Decimal]:
    upper = level["upper"]
    lower = Decimal(cast("str", level["lower"]))
    return lower, last if upper is None else Decimal(cast("str", upper))


def _within(key: str, level: JsonObject, last: Decimal) -> Decimal:
    """Draw a ratio within the bounds of a level of the matrix, by thousandths, bounds excluded."""
    lower, upper = _bounds(level, last)
    return Decimal(draw(key, int(lower * 1000) + 1, int(upper * 1000) - 1)) / 1000


def identified_risks(rows: list[JsonObject]) -> list[Risk]:
    """Return the identified risks of the projects in progress of the portfolio.

    The witness project brings those of its register. Every other project in progress has up to
    three: each drawn in a cell of the matrix first, then its probability and its severity — a
    part of the budget of its project — within the bounds of the levels of that cell
    (`risk_matrix`), and its provision the severity weighted by the probability (WF-RIS-0010).
    The register and the matrix are read in memory (``mockhistory``), never from the files the
    same command writes.
    """
    witness = fixture("project")["project_id"]
    read = mockhistory.readings()
    register = cast("list[dict[str, Any]]", cast("dict[str, Any]", read["risks"])["items"])
    matrix = cast("dict[str, Any]", read["risk_matrix"])
    levels = {"probability": matrix["probability_levels"], "severity": matrix["severity_levels"]}
    risks: list[Risk] = []
    for row in rows:
        if row["state"] != "in_progress":
            continue
        if row["project_id"] == witness:
            risks.extend(
                Risk(
                    row=row,
                    risk_id=risk["risk_id"],
                    label=risk["label"],
                    probability=Decimal(risk["probability"]),
                    severity=Decimal(risk["severity"]),
                    provision=Decimal(risk["provision_amount"]),
                    cell=(
                        risk["matrix_cell"]["probability_level"],
                        risk["matrix_cell"]["severity_level"],
                    ),
                )
                for risk in register
                if risk["state"] == "identified"
            )
            continue
        budget = Decimal(cast("str", row["reference_budget"]))
        for rank in range(draw(f"risks/{row['project_id']}", 0, 3)):
            key = f"risk/{row['project_id']}/{rank}"
            cell = (draw(f"{key}/probability", 1, 4), draw(f"{key}/severity", 1, 4))
            probability = _within(f"{key}/chance", levels["probability"][cell[0] - 1], _MOST_LIKELY)
            severity = (
                budget * _within(f"{key}/weight", levels["severity"][cell[1] - 1], _HEAVIEST)
            ).quantize(CENT)
            risks.append(
                Risk(
                    row=row,
                    risk_id=identifier(RISKS, len(risks) + 1),
                    label=_RISK_SUBJECTS[draw(f"{key}/subject", 0, len(_RISK_SUBJECTS) - 1)],
                    probability=probability,
                    severity=severity,
                    provision=(severity * probability).quantize(CENT),
                    cell=cell,
                )
            )
    return risks


def portfolio_risks(rows: list[JsonObject]) -> JsonObject:
    """Return the answer of getPortfolioRisks over the projects in progress (WF-PTF-0090).

    The total, the heaviest and the matrix are those of the identified risks
    (`identified_risks`); the risks that occurred or were dismissed over the period are the
    witness project's and a drawn sum.
    """
    read = mockhistory.readings()
    register = cast("list[dict[str, Any]]", cast("dict[str, Any]", read["risks"])["items"])
    risks = identified_risks(rows)
    total = sum((risk.provision for risk in risks), Decimal(0))
    heaviest = sorted(risks, key=lambda risk: -risk.provision)[:10]
    matrix = cast("dict[str, Any]", read["risk_matrix"])
    counted = Counter(risk.cell for risk in risks)
    occurred = sum(
        (Decimal(risk["provision_amount"]) for risk in register if risk["state"] == "occurred"),
        Decimal(draw("risks/occurred", 2_000, 9_000) * 1_000),
    )
    dismissed = sum(
        (Decimal(risk["provision_amount"]) for risk in register if risk["state"] == "dismissed"),
        Decimal(draw("risks/dismissed", 2_000, 9_000) * 1_000),
    )
    # The coverage of the risks (WF-RIS-0050), summed over the projects in progress: the
    # witness brings its own, the others a drawn reserve that their identified provisions and
    # the reestimated cost of their occurred risks eat into (WF-PTF-0090).
    coverage = cast("dict[str, Any]", read["risk_coverage"])
    reserve = Decimal(coverage["reserve"]) + Decimal(draw("risks/reserve", 95_000, 125_000) * 1_000)
    remaining = total
    occurred_cost = Decimal(coverage["occurred_cost"]) + Decimal(
        draw("risks/occurred_cost", 500, 2_500) * 1_000
    )
    return {
        "scope": _scope(rows, ["in_progress"], period=True),
        "identified_total": money(total),
        "heaviest": [
            {
                "risk_id": risk.risk_id,
                "label": risk.label,
                "project_id": risk.row["project_id"],
                "project_label": risk.row["label"],
                "can_open": risk.row["can_open"],
                "provision_amount": money(risk.provision),
            }
            for risk in heaviest
        ],
        "matrix": {
            "probability_levels": matrix["probability_levels"],
            "severity_levels": matrix["severity_levels"],
            "cells": [
                cell | {"count": counted[cell["probability_level"], cell["severity_level"]]}
                for cell in matrix["cells"]
            ],
            "totals": {
                "identified": money(total),
                "occurred": money(occurred),
                "dismissed": money(dismissed),
                "total": money(total + occurred + dismissed),
                "reserve": money(reserve),
            },
        },
        "coverage": {
            "reserve": money(reserve),
            "remaining_provisions": money(remaining),
            "occurred_cost": money(occurred_cost),
            "coverage_variance": money(reserve - remaining - occurred_cost),
        },
        "period_outcome": {
            "occurred_provisions": money(occurred),
            "dismissed_provisions": money(dismissed),
        },
    }
