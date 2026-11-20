# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the risks of the portfolio are made of, without a database (US-2730).

The pure part of ``getPortfolioRisks``: the risks held by the documents of the projects, placed in
the matrix on the bounds of the day and the base of their own project, the ten heaviest, the
provision totals, the sums of the coverages and of the outcomes. The tests of the service
(``test_portfolio_risks``) read them through the API.
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest

from waterfall.core.cost_settings.interface import RiskMatrix
from waterfall.core.estimate.interface import Coverage
from waterfall.core.portfolio.risking import (
    HEAVIEST,
    HeldRisk,
    coverage_document,
    heaviest_document,
    held_risks,
    identified_of,
    matrix_document,
    outcome_document,
    place,
)
from waterfall.core.risks.interface import RiskOutcome

if TYPE_CHECKING:
    from waterfall.core.indicators.interface import Document

D = Decimal
# The fields of a risk held that are amounts, given as text by the tests.
AMOUNTS = {"probability", "severity", "provision", "base"}
# The bounds of a new installation (WF-EXP-0020): 25, 50 and 75 % of probability, 1, 5 and 10 % of
# severity; a zone of each cell, the alert zone at the corner.
MATRIX = RiskMatrix(
    probability_bounds=(D("0.25"), D("0.5"), D("0.75")),
    severity_bounds=(D("0.01"), D("0.05"), D("0.1")),
    zones=(
        *("nominal", "nominal", "nominal", "watch"),
        *("nominal", "nominal", "watch", "watch"),
        *("nominal", "watch", "watch", "alert"),
        *("watch", "watch", "alert", "alert"),
    ),
)


def identifier(number: int) -> UUID:
    """Give an identifier from a number."""
    return UUID(int=number)


def risk(number: int, **changes: Any) -> HeldRisk:
    """Give a risk of a project, held as its document keeps it, with the fields changed.

    By default identified, of project 1 at 30 % and 100 of severity on a base of 1 000.
    """
    project = changes.pop("project", 1)
    held = HeldRisk(
        project_id=identifier(project),
        project_label=f"Projet {project}",
        can_open=True,
        risk_id=identifier(number),
        label="Un risque",
        probability=D("0.3"),
        severity=D("100.00"),
        provision=D("30.00"),
        state="identified",
        base=D("1000.00"),
    )
    return replace(
        held,
        **{name: D(value) if name in AMOUNTS else value for name, value in changes.items()},
    )


def document(base: str, risks: list[dict[str, Any]]) -> Document:
    """Give a document ``portfolio_risks`` as a marking keeps it."""
    return {"base": base, "risks": risks}


def cell(body: Document, row: int, column: int) -> Document:
    """Give a cell of a matrix document."""
    (found,) = (
        each
        for each in body["cells"]
        if (each["probability_level"], each["severity_level"]) == (row, column)
    )
    return found


@pytest.mark.requirement("WF-PTF-0090-A")
def test_the_risks_of_a_document_are_read_in_the_order_of_their_declaration() -> None:
    # « … pour chaque risque, sa probabilité, sa gravité, sa provision et son état » : read from the
    # document of a marking, each risk with the base of its project and its project's label.
    kept = document(
        "2500.00",
        [
            {
                "risk_id": str(identifier(2)),
                "label": "Panne de la grue",
                "probability": "0.4000",
                "severity": "300.00",
                "provision_amount": "120.00",
                "state": "identified",
                "occurrence_cost": None,
                "occurred_reestimated_amount": None,
            },
            {
                "risk_id": str(identifier(1)),
                "label": "Gel des sols",
                "probability": "0.2000",
                "severity": "50.00",
                "provision_amount": "0.00",
                "state": "dismissed",
                "occurrence_cost": None,
                "occurred_reestimated_amount": None,
            },
        ],
    )
    found = held_risks(identifier(7), "Grue", can_open=False, document=kept)
    assert [(each.risk_id, each.label, each.state) for each in found] == [
        (identifier(2), "Panne de la grue", "identified"),
        (identifier(1), "Gel des sols", "dismissed"),
    ]
    assert found[0].probability == D("0.4")
    assert (found[0].severity, found[0].provision, found[0].base) == (
        D("300.00"),
        D("120.00"),
        D("2500.00"),
    )
    assert (found[0].project_id, found[0].project_label, found[0].can_open) == (
        identifier(7),
        "Grue",
        False,
    )
    assert identified_of(found) == [found[0]]


@pytest.mark.requirement("WF-PTF-0090-A")
def test_a_risk_is_placed_on_the_base_of_its_own_project_in_the_cell_of_its_levels() -> None:
    # « La matrice compte chaque risque identifié une fois. » : the same severity, 100, is at 10 %
    # of a base of 1 000 — the fourth level, from 10 % — and at 5 % of a base of 2 000, the third:
    # each project is judged on its own base. A bound is of the level it opens (WF-REF-0160).
    heavy = place(risk(1, severity="100.00", base="1000.00", probability="0.3"), MATRIX)
    light = place(risk(2, severity="100.00", base="2000.00", probability="0.3"), MATRIX)
    assert (heavy.probability_level, heavy.severity_level, heavy.zone) == (2, 4, "watch")
    assert (light.probability_level, light.severity_level, light.zone) == (2, 3, "watch")
    # The bounds of probability: 0.25 is the second level, 0.75 the fourth.
    assert place(risk(3, probability="0.25"), MATRIX).probability_level == 2
    assert place(risk(4, probability="0.75"), MATRIX).probability_level == 4
    assert place(risk(5, probability="0.2499"), MATRIX).probability_level == 1


@pytest.mark.requirement("WF-PTF-0090-A")
def test_on_a_base_of_nought_the_lowest_level_and_a_share_not_computable() -> None:
    # A project whose estimate carries only provisions has no base: the severity relates to
    # nothing (#1240) — the lowest level, no share, and the reason the register gives.
    placed = place(risk(1, severity="100.00", base="0.00", probability="0.8"), MATRIX)
    assert (placed.probability_level, placed.severity_level, placed.zone) == (4, 1, "watch")
    assert placed.severity_ratio.value is None
    assert placed.severity_ratio.reason == "no_reference_budget"
    shown = place(risk(2, severity="18.34", base="100.00"), MATRIX).severity_ratio
    assert shown.value == D("0.1834")


@pytest.mark.requirement("WF-PTF-0090-A")
def test_the_matrix_counts_each_identified_risk_once_and_its_points_are_those_risks() -> None:
    # « La matrice compte chaque risque identifié une fois. » : of five risks held, three are
    # identified — two in the same cell, one in another —; an occurred and a dismissed one stay
    # out of the cells and the points, and are counted in the totals, each in its own state.
    risks = [
        risk(1, probability="0.3", severity="100.00", provision="30.00"),
        risk(2, probability="0.3", severity="120.00", provision="36.00"),
        risk(3, probability="0.9", severity="5.00", provision="4.50", project=2, base="100.00"),
        risk(4, state="occurred", provision="60.00"),
        risk(5, state="dismissed", provision="25.00"),
    ]
    body = matrix_document(MATRIX, risks, D("90.00"))
    assert sum(each["count"] for each in body["cells"]) == 3
    assert cell(body, 2, 4)["count"] == 2
    assert cell(body, 4, 3)["count"] == 1
    assert cell(body, 1, 1)["count"] == 0
    assert [each["risk_id"] for each in body["points"]] == [
        str(identifier(number)) for number in (1, 2, 3)
    ]
    assert {each["state"] for each in body["points"]} == {"identified"}
    # A point names its project and says whether the reader opens it, the three together.
    assert [(each["project_id"], each["project_label"]) for each in body["points"]][-1] == (
        str(identifier(2)),
        "Projet 2",
    )
    assert body["totals"] == {
        "identified": "70.50",
        "occurred": "60.00",
        "dismissed": "25.00",
        "total": "155.50",
        "reserve": "90.00",
    }


@pytest.mark.requirement("WF-PTF-0090-A")
def test_the_matrix_writes_its_levels_and_a_point_as_the_contract_does() -> None:
    body = matrix_document(
        MATRIX, [risk(1, probability="0.4", severity="18.34", base="100.00")], D(0)
    )
    assert [
        (each["level"], each["lower"], each["upper"]) for each in body["probability_levels"]
    ] == [
        (1, "0", "0.25"),
        (2, "0.25", "0.5"),
        (3, "0.5", "0.75"),
        (4, "0.75", None),
    ]
    assert [(each["lower"], each["upper"]) for each in body["severity_levels"]] == [
        ("0", "0.01"),
        ("0.01", "0.05"),
        ("0.05", "0.1"),
        ("0.1", None),
    ]
    assert len(body["cells"]) == 16
    (point,) = body["points"]
    assert point == {
        "risk_id": str(identifier(1)),
        "label": "Un risque",
        "probability": "0.4",
        "severity_amount": "18.34",
        "severity_ratio": {"is_computable": True, "value": "0.1834", "reason": None},
        "provision_amount": "30.00",
        "state": "identified",
        "zone": "watch",
        "project_id": str(identifier(1)),
        "project_label": "Projet 1",
        "can_open": True,
    }
    # With no risk, the sixteen cells stay, empty, and the totals are nought.
    empty = matrix_document(MATRIX, [], D(0))
    assert (empty["points"], sum(each["count"] for each in empty["cells"])) == ([], 0)
    assert empty["totals"]["total"] == "0.00"


@pytest.mark.requirement("WF-PTF-0090-A")
def test_the_heaviest_are_the_ten_identified_risks_of_greatest_provision() -> None:
    # « … les risques identifiés les plus lourds, tous projets confondus, classés par montant de
    # provision, avec leur projet » : twelve identified risks of three projects, the first ten by
    # provision; an occurred risk heavier than all of them is not among them; a tie is broken by
    # the project's label, then the risk's.
    risks = [
        risk(number, project=1 + number % 3, provision=f"{number * 10}.00", can_open=number != 11)
        for number in range(1, 13)
    ]
    risks.append(risk(99, state="occurred", provision="5000.00"))
    risks.append(risk(98, project=2, label="A égalité", provision="30.00"))
    found = heaviest_document(risks)
    assert HEAVIEST == 10
    assert len(found) == 10
    assert [each["provision_amount"] for each in found] == [
        f"{amount}.00" for amount in (120, 110, 100, 90, 80, 70, 60, 50, 40, 30)
    ]
    assert str(identifier(99)) not in {each["risk_id"] for each in found}
    # The tie at 30: the risk 3, of the project 1, and the risk 98, of the project 2: the project
    # whose label comes first is kept.
    assert found[-1]["risk_id"] == str(identifier(3))
    eleventh = next(each for each in found if each["risk_id"] == str(identifier(11)))
    assert (eleventh["project_id"], eleventh["project_label"], eleventh["can_open"]) == (
        str(identifier(3)),
        "Projet 3",
        False,
    )
    assert set(found[0]) == {
        "risk_id",
        "label",
        "project_id",
        "project_label",
        "can_open",
        "provision_amount",
    }


@pytest.mark.requirement("WF-PTF-0090-A")
def test_the_coverage_is_the_sum_of_the_coverages_and_its_variance_that_of_the_sums() -> None:
    # « La réserve agrégée est la somme des réserves […], et l'écart de couverture agrégé la
    # différence des sommes. » : two projects, reserves 850 and 100, provisions left 500 and 20,
    # costs at occurrence 200 and 0 — the variance of the sums, 230, is the sum of the variances,
    # 150 and 80.
    first = Coverage(D("850.00"), D("500.00"), D("200.00"), D("260.00"), D("150.00"))
    second = Coverage(D("100.00"), D("20.00"), D("0.00"), D("0.00"), D("80.00"))
    body = coverage_document([first, second])
    assert body == {
        "reserve": "950.00",
        "remaining_provisions": "520.00",
        "occurred_cost": "200.00",
        "occurred_reestimated": "260.00",
        "coverage_variance": "230.00",
    }
    # No project, no coverage: every figure at nought.
    assert set(coverage_document([]).values()) == {"0.00"}


@pytest.mark.requirement("WF-PTF-0090-A")
@pytest.mark.story("US-2730")
def test_the_reestimated_amount_is_summed_beside_the_cost_of_the_occurred_risks() -> None:
    # Propre à l'US : « la couverture rend, à côté du coût des survenus, la somme des réestimés des
    # lignes qui en sont issues » (#2002) : a project whose occurred risk cost 200 at its
    # occurrence and whose lines are re-estimated at 260 — the cost stays 200, the re-estimated 260
    # — and a second whose lines were re-estimated at 150 for a cost of 180; the variance counts
    # the costs alone: 1 000 - (300 + 380) = 320.
    first = Coverage(D("600.00"), D("100.00"), D("200.00"), D("260.00"), D("300.00"))
    second = Coverage(D("400.00"), D("200.00"), D("180.00"), D("150.00"), D("20.00"))
    body = coverage_document([first, second])
    assert body["occurred_cost"] == "380.00"
    assert body["occurred_reestimated"] == "410.00"
    assert body["coverage_variance"] == "320.00"


@pytest.mark.requirement("WF-PTF-0090-A")
@pytest.mark.story("US-2730")
def test_the_outcomes_of_the_period_sum_the_occurred_and_the_dismissed_provisions() -> None:
    # Propre à l'US : « period_outcome somme, sur la période, les provisions des risques survenus
    # et celles des risques écartés » : two occurred, one dismissed; none at all gives nought.
    moved = [
        RiskOutcome(identifier(1), identifier(10), date(2026, 5, 1), "occurred", D("60.00")),
        RiskOutcome(identifier(1), identifier(11), date(2026, 5, 2), "dismissed", D("25.00")),
        RiskOutcome(identifier(2), identifier(12), date(2026, 5, 3), "occurred", D("40.50")),
    ]
    assert outcome_document(moved) == {
        "occurred_provisions": "100.50",
        "dismissed_provisions": "25.00",
    }
    assert outcome_document([]) == {
        "occurred_provisions": "0.00",
        "dismissed_provisions": "0.00",
    }
