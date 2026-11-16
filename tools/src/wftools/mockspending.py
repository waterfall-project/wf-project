# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The projection of spending of the witness, by nature of cost and by month (US-2040/L1, #3511).

The amounts of the lines of a revision — but the provisions — spread over the months of their task
pro rata of its hours of work, as the workload spreads their hours (WF-DEV-0100): on the reference
budget, each over the whole of its task; on the remaining to commit, the remaining of each over the
part of its task after the day of the calculation, whole at that day when the task is past its
finish (``mockcurves.ahead``, WF-IND-0100). Each line by its parts rounded to the cent, which sum to
its amount (``mockcurves.parts``); a category sums the parts of its lines, a nature its categories,
a month its natures. On request, each part shifted by the payment delay of its line: the
disbursements. Nothing is kept at a marking: a marked revision is read on what it froze.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockcategories, mockhistory, mocktext
from wftools.mockcurves import REMAINING, ahead, monthly_totals, parts, summed
from wftools.mockindicators import PROJECT, context, over, remaining_of
from wftools.mockstructure import CENT, money
from wftools.mockwitness import SUBPROJECT_CONTROL, TODAY, fixture

if TYPE_CHECKING:
    from wftools import mockcore
    from wftools.mockindicators import Reading
    from wftools.mockstructure import JsonObject, JsonValue


def amounts_of(
    reading: Reading, line: mockcore.Row, basis: str, *, delays: bool
) -> dict[str, Decimal]:
    """Return the amount of a line by month, on the basis asked, its parts rounded to the cent."""
    delay = reading.delays[line.number] if delays else 0
    if basis in REMAINING:
        amount = remaining_of(reading, line)
        flow = ahead(reading, line, amount, delay)
    else:
        amount = line.amounts.budgeted
        flow = over(reading.bearer(line), amount, delay)
    return parts(flow, CENT, ROUND_HALF_UP) if amount else {}


def _ranks() -> dict[str, int]:
    """Return the rank of each category under its nature: the order of its code (``ACH-001``)."""
    return {
        category: rank
        for entries, _, _, _ in mockcategories.groups()
        for rank, (category, _) in enumerate(entries)
    }


def _objs(value: JsonValue) -> list[JsonObject]:
    return cast("list[JsonObject]", value)


def _months(months: dict[str, Decimal]) -> list[JsonValue]:
    return [{"month": month, "amount": money(amount)} for month, amount in months.items()]


def spending(
    reading: Reading, basis: str, *, delays: bool = False, scope: str = PROJECT
) -> JsonObject:
    """Return the projection of spending of the project (`SpendingProjection`, WF-DEV-0100).

    The natures in the order of the reference — their code —, each with its categories in the same
    order, those that carry an amount alone; their months the months they load alone (#3096); the
    total of each month from the first to the last without a gap, nought where nothing is spent.
    Of a subproject, or of what belongs to none, the lines of that scope alone (WF-IND-0020).
    """
    by_category: dict[str, list[dict[str, Decimal]]] = {}
    labels: dict[str, str] = {}
    for line in reading.lines:
        if mockhistory.is_provision(line) or not reading.in_scope(line, scope):
            continue
        months = amounts_of(reading, line, basis, delays=delays)
        if not months:
            continue
        facet = reading.facet(line)
        category = cast("str", facet["cost_category_id"])
        labels[category] = cast("str", facet["cost_category_label"])
        by_category.setdefault(category, []).append(months)
    ranks = _ranks()
    natures: list[JsonValue] = []
    natures_read = sorted(
        fixture("cost_types")["items"], key=lambda each: (each["code"], each["cost_type_id"])
    )
    for nature in natures_read:
        held = sorted(
            (
                category
                for category in by_category
                if mockcategories.nature_of(category)["cost_type_id"] == nature["cost_type_id"]
            ),
            key=lambda category: (ranks[category], category),
        )
        categories = [(category, summed(by_category[category])) for category in held]
        categories = [(category, months) for category, months in categories if months]
        if not categories:
            continue
        months = summed(each for _, each in categories)
        natures.append(
            {
                "cost_type_id": nature["cost_type_id"],
                "label": nature["label"],
                "total": money(sum(months.values(), Decimal(0))),
                "months": _months(months),
                "categories": [
                    {
                        "cost_category_id": category,
                        "label": labels[category],
                        "total": money(sum(each.values(), Decimal(0))),
                        "months": _months(each),
                    }
                    for category, each in categories
                ],
            }
        )
    totals = monthly_totals(cast("list[JsonObject]", natures), "amount")
    marked = basis == "marked_remaining"
    return {
        # Computed when read, never kept by a marking (#3182); a marked revision at its marking.
        "context": context(reading, at=reading.at if marked else TODAY, scope=scope),
        "basis": basis,
        "payment_delays": delays,
        "total": money(
            sum((Decimal(cast("str", each["total"])) for each in _objs(natures)), Decimal(0))
        ),
        "monthly_totals": totals,
        "cost_types": natures,
    }


# --- The examples ---------------------------------------------------------------------------------


def values(today: Reading, reference: Reading) -> dict[str, JsonValue]:
    """Return the values of the examples of `getProjectSpending`, by name.

    The remaining to commit of the current revision today, first; the budget of the reference,
    whose months before the day of the calculation are shown; the remaining of the reference at
    its marking; the disbursements of today; and the subproject of the control (WF-DEV-0100).
    """
    return {
        "spending": spending(today, "current_remaining"),
        "spending_reference_budget": spending(reference, "reference_budget"),
        "spending_marked_remaining": spending(reference, "marked_remaining"),
        "spending_payment_delays": spending(today, "current_remaining", delays=True),
        "spending_subproject": spending(today, "current_remaining", scope=SUBPROJECT_CONTROL),
    }


def _month(value: JsonValue) -> str:
    """Write a month of the contract as French does: juin 2026."""
    year, month = cast("str", value).split("-")
    return mocktext.day(date(int(year), int(month), 1)).removeprefix("1er ")


def _money(value: JsonValue) -> str:
    return mocktext.amount(Decimal(cast("str", value)))


def _said(projection: JsonObject) -> str:
    """Say a projection: each nature and its categories, its total, the span of its months."""
    natures = [
        f"« {nature['label']} », {_money(nature['total'])} ("
        + ", ".join(
            f"« {category['label']} » {_money(category['total'])}"
            for category in _objs(nature["categories"])
        )
        + ")"
        for nature in _objs(projection["cost_types"])
    ]
    totals = _objs(projection["monthly_totals"])
    return (
        f"{' ; '.join(natures)} ; au total {_money(projection['total'])}, de "
        f"{_month(totals[0]['month'])} à {_month(totals[-1]['month'])}, le total de chaque mois "
        f"sans trou (monthly_totals)"
    )


def summaries(found: dict[str, JsonValue]) -> dict[str, str]:
    """Return the summary of each example of `getProjectSpending`, by name."""

    def said(name: str) -> str:
        return _said(cast("JsonObject", found[name]))

    today = mocktext.day(TODAY.date())
    subproject = next(
        entry["label"]
        for entry in fixture("subprojects")
        if entry["subproject_id"] == SUBPROJECT_CONTROL
    )
    return {
        "spending": (
            f"La projection de dépenses du projet sur le reste à engager de la révision en cours, "
            f"au {today} : par nature de coût dans l'ordre du référentiel, puis par catégorie, "
            f"mois par mois, le reste à engager de chaque ligne hors provision étalé sur les "
            f"heures ouvrées de sa tâche après la date de calcul — aucun mois passé —, ses parts "
            f"arrondies au centime de façon que leur somme soit son montant : {said('spending')} "
            f"(WF-DEV-0100)."
        ),
        "spending_reference_budget": (
            f"La même projection sur les montants budgétés de la révision de référence, chaque "
            f"ligne étalée sur toute la durée de sa tâche, les mois antérieurs à la date de calcul "
            f"compris : {said('spending_reference_budget')} (WF-DEV-0100)."
        ),
        "spending_marked_remaining": (
            f"La même projection sur les montants réestimés de la révision marquée « Référence », "
            f"nommée par revision_id, calculée à la lecture à sa date de marquage, rien n'en étant "
            f"conservé : {said('spending_marked_remaining')} (WF-DEV-0100)."
        ),
        "spending_payment_delays": (
            f"La même projection que la première, en décaissements (payment_delays) : chaque part "
            f"décalée du délai de paiement de sa ligne : {said('spending_payment_delays')} "
            f"(WF-DEV-0100)."
        ),
        "spending_subproject": (
            f"La même projection que la première, restreinte au sous-projet « {subproject} » "
            f"(subproject_id), ses seules lignes : {said('spending_subproject')} (WF-DEV-0100, "
            f"WF-IND-0020)."
        ),
    }
