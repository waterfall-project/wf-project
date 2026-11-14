# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The amount of an estimate line and its projection onto the years it is consumed (US-1490/L2).

Pure: numbers in, numbers out, without a database, a setting or a clock. Every amount is a
``Decimal`` rounded to the cent once, half away from zero as ``Money`` of the contract says (#2618),
so that a sum of amounts does not depend on the order it is made in (WF-DAT-0100); a share is never
rounded before it is summed.

The re-estimated amount starts from the unrounded products, not from the rounded base amount: it
may therefore differ by one cent from the rounded base amount times the inflation factor.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

CENT = Decimal("0.01")

# Wide enough for any product of quantities, hourly rates and inflation factors to stay exact.
_PRECISION = 60


class Amount(StrEnum):
    """The amounts of a line that the server computes and nobody enters (WF-DEV-0020)."""

    BASE = "base_amount"
    BUDGETED = "budgeted_amount"
    REESTIMATED = "reestimated_amount"


@dataclass(frozen=True, slots=True)
class Share:
    """The part of a line's base amount consumed in one year, before projection and rounding.

    It is cut from the unrounded product (``unrounded_*_amount``), so the re-estimated amount may
    differ by one cent from the rounded base amount times the factor: rounding comes once, last.
    """

    year: int
    amount: Decimal


def round_to_cent(value: Decimal) -> Decimal:
    """Round to the cent, half away from zero: the only rounding of an amount.

    ``Money`` of the contract rounds so, and the generator of the witness with it (#2618): 75.705
    gives 75.71.
    """
    with localcontext() as context:
        context.prec = _PRECISION
        return value.quantize(CENT, rounding=ROUND_HALF_UP)


def labour_base_amount(quantity: Decimal, effort: Decimal, hourly_rate: Decimal) -> Decimal:
    """Return the base amount of a labour line: quantity x effort x hourly rate (WF-DEV-0020)."""
    return round_to_cent(unrounded_labour_amount(quantity, effort, hourly_rate))


def disbursement_base_amount(quantity: Decimal, unit_disbursement: Decimal) -> Decimal:
    """Return the base amount of a non-labour line: quantity x unit disbursement (WF-DEV-0020)."""
    return round_to_cent(unrounded_disbursement_amount(quantity, unit_disbursement))


def unrounded_labour_amount(quantity: Decimal, effort: Decimal, hourly_rate: Decimal) -> Decimal:
    """Return the product of a labour line, which the shares are cut from.

    Not rounded: the re-estimated amount starts from it, so it may differ by one cent from the
    rounded base amount times the inflation factor.
    """
    with localcontext() as context:
        context.prec = _PRECISION
        return quantity * effort * hourly_rate


def unrounded_disbursement_amount(quantity: Decimal, unit_disbursement: Decimal) -> Decimal:
    """Return the product of a non-labour line, which the shares are cut from.

    Not rounded, like ``unrounded_labour_amount``: the re-estimated amount may differ by one cent
    from the rounded base amount times the inflation factor.
    """
    with localcontext() as context:
        context.prec = _PRECISION
        return quantity * unit_disbursement


def inflation_factor(inflation_rate: Decimal, reference_year: int, year: int) -> Decimal:
    """Return the factor of one share: (1 + rate) once per year elapsed since the reference year.

    A year before the reference one has no year elapsed, hence a factor of one: nothing deflates.
    WF-DEV-0030-A fixes this factor: a share consumed the year before the reference year is worth
    its base amount, whatever the inflation rate.
    """
    with localcontext() as context:
        context.prec = _PRECISION
        return (1 + inflation_rate) ** max(year - reference_year, 0)


def projected_amount(
    shares: Iterable[Share],
    reference_year: int,
    inflation_rate: Decimal,
    *,
    provision: bool = False,
) -> Decimal:
    """Return the amount of a line over its shares, projected, rounded to the cent once.

    The sum of the projected shares is rounded, never a sum of rounded shares, so that a line
    spread over two years obeys WF-DAT-0100. A provision line is not projected (WF-DEV-0030): its
    shares are summed as they are.
    """
    with localcontext() as context:
        context.prec = _PRECISION
        total = Decimal(0)
        for share in shares:
            factor = (
                Decimal(1)
                if provision
                else inflation_factor(inflation_rate, reference_year, share.year)
            )
            total += share.amount * factor
        return round_to_cent(total)


def sum_amounts(amounts: Iterable[Decimal]) -> Decimal:
    """Return the exact sum of amounts already rounded to the cent; an empty sum is 0.00.

    An amount that is not to the cent is refused rather than rounded: it was passed by mistake,
    and its rounding here would hide it (#2548).
    """
    with localcontext() as context:
        context.prec = _PRECISION
        total = Decimal(0)
        for amount in amounts:
            if amount != round_to_cent(amount):
                msg = f"an amount summed is not to the cent: {amount}"
                raise ValueError(msg)
            total += amount
        return round_to_cent(total)


def dependencies_of(amount: Amount, *, labour: bool, provision: bool = False) -> tuple[str, ...]:
    """Return what ``getComputedValueDependencies`` names for an amount of a line.

    The base amount comes from the hourly rate of a labour line, from the unit disbursement of
    another; the budgeted one is set by the reference revision, the re-estimated one tracked by the
    reviews of the remaining to commit; both are projected at the inflation rate (WF-DEV-0020,
    WF-DEV-0030).

    A provision line follows the contract (``ComputedDependency`` in ``revisions.yaml``: ``risk``
    is "the figures, the subproject and the amount of a provision line"): its base and
    re-estimated amounts depend on ``risk``, its budgeted one, fixed like every line's by the
    reference revision, on ``reference_revision``. It is not projected, so never ``inflation``.
    """
    if provision:
        return ("reference_revision",) if amount is Amount.BUDGETED else ("risk",)
    match amount:
        case Amount.BASE:
            return ("hourly_rate",) if labour else ("unit_disbursement",)
        case Amount.BUDGETED:
            return ("reference_revision", "inflation")
        case Amount.REESTIMATED:
            return ("remaining_reviews", "inflation")
