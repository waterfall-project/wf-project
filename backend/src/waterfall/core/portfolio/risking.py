# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the risks of the portfolio are made of, from the documents of the projects (US-2730).

The view of the risks (``getPortfolioRisks``, WF-PTF-0090) is formed here of the documents
``portfolio_risks`` and ``remaining`` its projects contribute, and of the outcomes of the period;
it reads no risk itself. Without weighting: a risk counts for its provision whatever the state of
its project — an offer In pricing included (WF-PTF-0020) —, and every sum is that of the
aggregation (``total_of``, ``count_by_key``, ``ratio_of``), none rewritten here (#4037).

- the risks are held as the marking kept them: probability, severity, provision and state, with the
  base of their project; each identified one is classed at the reading, once, in the cell of its
  levels on the bounds of that day — its severity as a share of the base of its own project —, so
  that a change of the bounds moves a past reading too (EP-11, "Ce que le cadrage décide");
- the total, the ten heaviest and the points of the matrix are those of the identified risks; the
  three totals of the matrix count each risk once, in the state it is held in;
- the coverage is the sum of that of the projects In progress and Completed, a project In pricing
  having no reference; the variance is the difference of the sums, and the re-estimated amount of
  the lines that came from the occurred risks is summed beside their cost, never in its place;
- the outcomes of the period are those ``outcomes_between`` gives, summed by state.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from waterfall.core.estimate.interface import Coverage
from waterfall.core.indicators.interface import NO_REFERENCE_BUDGET
from waterfall.core.portfolio.aggregation import count_by_key, ratio_of, total_of
from waterfall.core.portfolio.shaping import computable, money, percent
from waterfall.core.portfolio.states import PRICING
from waterfall.core.risk_settings.interface import LEVELS, level_of, zone_of
from waterfall.core.risks.interface import kept_coverage, levels_of, risk_coverage_of

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from sqlalchemy.orm import Session

    from waterfall.core.cost_settings.interface import RiskMatrix
    from waterfall.core.indicators.interface import Computable, Document, IndicatorKind
    from waterfall.core.portfolio.documents import Documents
    from waterfall.core.portfolio.interface.scope import ResolvedScope
    from waterfall.core.risks.interface import RiskOutcome, RiskState

# The heaviest risks the view gives: the first ten by provision.
HEAVIEST = 10
IDENTIFIED: RiskState = "identified"
OCCURRED: RiskState = "occurred"
DISMISSED: RiskState = "dismissed"
REMAINING: IndicatorKind = "remaining"
NOUGHT = Decimal(0)
# The figures of a coverage a marking keeps, which the view sums.
COVERAGE_FIGURES = (
    "reserve",
    "remaining_provisions",
    "occurred_cost",
    "occurred_reestimated",
    "coverage_variance",
)


@dataclass(frozen=True, slots=True)
class HeldRisk:
    """A risk of a project as its document keeps it, with its project and the base it relates to.

    ``base`` is what the matrix relates the severity to (WF-REF-0160): the budget of the reference,
    or before one the total of the estimate, provisions left out.
    """

    project_id: UUID
    project_label: str
    can_open: bool
    risk_id: UUID
    label: str
    probability: Decimal
    severity: Decimal
    provision: Decimal
    state: RiskState
    base: Decimal


@dataclass(frozen=True, slots=True)
class PlacedRisk:
    """An identified risk placed in the matrix: its levels, its cell's zone, its severity share.

    The cell is that of the exact share, the share shown is rounded to four places and not
    computable on a base of nought (#1240).
    """

    risk: HeldRisk
    probability_level: int
    severity_level: int
    zone: str
    severity_ratio: Computable


def held_risks(
    project_id: UUID, project_label: str, *, can_open: bool, document: Document
) -> list[HeldRisk]:
    """Read the risks of a document ``portfolio_risks``, in the order of their declaration."""
    base = Decimal(document["base"])
    return [
        HeldRisk(
            project_id,
            project_label,
            can_open,
            UUID(each["risk_id"]),
            each["label"],
            Decimal(each["probability"]),
            Decimal(each["severity"]),
            Decimal(each["provision_amount"]),
            each["state"],
            base,
        )
        for each in document["risks"]
    ]


def place(risk: HeldRisk, matrix: RiskMatrix) -> PlacedRisk:
    """Place a risk in the matrix of the reference settings, on the base of its own project.

    The severity as a share of the base, on a base of nought the lowest level, as the register of
    the project places it (WF-REF-0160, WF-RIS-0040).
    """
    share = risk.severity / risk.base if risk.base > 0 else NOUGHT
    probability_level = level_of(risk.probability, matrix.probability_bounds)
    severity_level = level_of(share, matrix.severity_bounds)
    return PlacedRisk(
        risk,
        probability_level,
        severity_level,
        zone_of(matrix, risk.probability, share),
        ratio_of(risk.severity, risk.base, NO_REFERENCE_BUDGET),
    )


def identified_of(risks: Iterable[HeldRisk]) -> list[HeldRisk]:
    """Keep the identified risks, in the order given."""
    return [each for each in risks if each.state == IDENTIFIED]


def identified_total(risks: Iterable[HeldRisk]) -> Decimal:
    """Give the total of the provisions of the identified risks, each as it is, unweighted."""
    return total_of(each.provision for each in identified_of(risks))


def heaviest_of(risks: Iterable[HeldRisk]) -> list[HeldRisk]:
    """Give the ten identified risks of greatest provision, all projects together.

    The heavier first; on equal provisions the project by its label then its identifier, then the
    risk by its label then its identifier, so that two readings of the same documents agree.
    """
    ordered = sorted(
        identified_of(risks),
        key=lambda each: (
            -each.provision,
            each.project_label,
            str(each.project_id),
            each.label,
            str(each.risk_id),
        ),
    )
    return ordered[:HEAVIEST]


def _levels(bounds: Sequence[Decimal]) -> list[Document]:
    """Write the levels of an axis, as the matrix of a project gives them (``levels_of``)."""
    return [
        {"level": each.level, "lower": percent(each.lower), "upper": percent(each.upper)}
        for each in levels_of(bounds)
    ]


def _point(placed: PlacedRisk) -> Document:
    """Write a risk the matrix places, with its project (``RiskMatrixPoint``)."""
    risk = placed.risk
    return {
        "risk_id": str(risk.risk_id),
        "label": risk.label,
        "probability": percent(risk.probability),
        "severity_amount": money(risk.severity),
        "severity_ratio": computable(placed.severity_ratio),
        "provision_amount": money(risk.provision),
        "state": risk.state,
        "zone": placed.zone,
        "project_id": str(risk.project_id),
        "project_label": risk.project_label,
        "can_open": risk.can_open,
    }


def matrix_document(matrix: RiskMatrix, risks: Sequence[HeldRisk], reserve: Decimal) -> Document:
    """Write the matrix of the portfolio (``RiskMatrix``): the identified risks, each counted once.

    The sixteen cells count the identified risks of their levels, and the points are those same
    risks; the provision totals count every risk held once, each in its own state — a risk
    dismissed after the marking is still identified in the document that kept it —, with the reserve
    of the coverage beside them. The bounds are the current ones.
    """
    placed = [place(each, matrix) for each in identified_of(risks)]
    counts = count_by_key((each.probability_level, each.severity_level) for each in placed)
    by_state = {
        state: total_of(each.provision for each in risks if each.state == state)
        for state in (IDENTIFIED, OCCURRED, DISMISSED)
    }
    return {
        "probability_levels": _levels(matrix.probability_bounds),
        "severity_levels": _levels(matrix.severity_bounds),
        "cells": [
            {
                "probability_level": row,
                "severity_level": column,
                "count": counts.get((row, column), 0),
                "zone": matrix.zones[LEVELS * (row - 1) + (column - 1)],
            }
            for row in range(1, LEVELS + 1)
            for column in range(1, LEVELS + 1)
        ],
        "points": [_point(each) for each in placed],
        "totals": {
            "identified": money(by_state[IDENTIFIED]),
            "occurred": money(by_state[OCCURRED]),
            "dismissed": money(by_state[DISMISSED]),
            "total": money(total_of(by_state.values())),
            "reserve": money(reserve),
        },
    }


def heaviest_document(risks: Iterable[HeldRisk]) -> list[Document]:
    """Write the ten heaviest identified risks, each with its project and ``can_open``."""
    return [
        {
            "risk_id": str(each.risk_id),
            "label": each.label,
            "project_id": str(each.project_id),
            "project_label": each.project_label,
            "can_open": each.can_open,
            "provision_amount": money(each.provision),
        }
        for each in heaviest_of(risks)
    ]


def _kept(held: Mapping[str, str]) -> Coverage | None:
    """Read the coverage a marking kept, none when a figure of it is missing or is no number."""
    try:
        figures = [Decimal(held[name]) for name in COVERAGE_FIGURES]
    except KeyError, TypeError, ArithmeticError:
        return None
    return Coverage(*figures) if all(each.is_finite() for each in figures) else None


def project_coverage(
    session: Session, project_id: UUID, revision_id: UUID, documents: Documents | None
) -> Coverage | None:
    """Give the coverage of a project that is In progress or Completed, or none that is known.

    On the current day (``documents`` is none) it is the coverage of the revision of the day,
    computed as ``getRemainingIndicators`` gives it. At a past date it is the one the document
    ``remaining`` of the last revision marked kept, with the reserve the reference conserves
    (``kept_coverage``); a coverage kept incomplete, or a revision that kept no document
    ``remaining`` — marked before EP-10 —, adds none: no past view reads a line of the estimate nor
    computes anew (WF-DAT-0040; EP-11, "La contribution d'un projet").
    """
    if documents is None:
        return risk_coverage_of(session, project_id, revision_id)
    remaining = documents.get(REMAINING)
    if remaining is None:
        return None
    conserved = kept_coverage(session, project_id, remaining.get("coverage"))
    return _kept(conserved) if conserved is not None else None


def coverages_of(
    session: Session, resolved: ResolvedScope, documents: Mapping[UUID, Documents]
) -> list[Coverage]:
    """Give the coverage of each project of the scope that is In progress or Completed.

    A project In pricing has no reference, so no reserve to cover (WF-PTF-0090); one with no
    revision to contribute by adds none.
    """
    found: list[Coverage] = []
    for project_id, retained in resolved.projects.items():
        if retained.state == PRICING or retained.revision_id is None:
            continue
        held = None if resolved.on_current_day else documents.get(project_id, {})
        covered = project_coverage(session, project_id, retained.revision_id, held)
        if covered is not None:
            found.append(covered)
    return found


def coverage_document(found: Iterable[Coverage]) -> Document:
    """Write the sums of the coverages (``RiskCoverageTotals``): the variance of the sums.

    The re-estimated amount is the sum of that of the projects, beside the cost at occurrence and
    outside the variance (#1761, #2002).
    """
    parts = list(found)
    reserve = total_of(each.reserve for each in parts)
    left = total_of(each.remaining_provisions for each in parts)
    cost = total_of(each.occurred_cost for each in parts)
    reestimated = total_of(each.occurred_reestimated for each in parts)
    return {
        "reserve": money(reserve),
        "remaining_provisions": money(left),
        "occurred_cost": money(cost),
        "occurred_reestimated": money(reestimated),
        "coverage_variance": money(reserve - (left + cost)),
    }


def reserve_of(found: Iterable[Coverage]) -> Decimal:
    """Give the aggregated reserve, the sum of the reserves of the coverages."""
    return total_of(each.reserve for each in found)


def outcome_document(outcomes: Iterable[RiskOutcome]) -> Document:
    """Write the provisions of the risks occurred and dismissed in the period, each by state."""
    moved = list(outcomes)
    return {
        "occurred_provisions": money(
            total_of(each.provision_amount for each in moved if each.state == OCCURRED)
        ),
        "dismissed_provisions": money(
            total_of(each.provision_amount for each in moved if each.state == DISMISSED)
        ),
    }
