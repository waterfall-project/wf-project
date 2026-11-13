# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The precision of a decimal the service keeps in a ``numeric`` column without precision.

Such a column refuses more than 16 383 decimals or 131 072 digits before the point: a value that
reached it so would be a failure of the database, a 500 that names no field. A threshold of an
index or a bound of the matrix of risks is refused before, at its field, beyond ten decimals or ten
digits before the point (#2234): ten decimals as an hour is kept (``Hours``, a ten-billionth),
enough for a percentage entered at three decimals. The decimals are counted as written, a final
zero included — the column keeps them —; the digits before the point, from the first that is not
zero.

This departs from ``RATIO_DECIMALS`` (``core/projects/interface/projects.py``), which counts the
decimals of the value normalised, a final zero dropped: ``0.1`` followed by 20 000 zeros is worth
``0.1`` there, but written as is it would overflow the ``numeric`` column of a threshold or a
bound, which keeps them. Here the count is that of the text, so that no such value gets through.

The same rule bounds the other decimals the service writes (#2875, US-1980): the constants of the
units of duration, the durations and the lags of the planning (``numeric`` without precision, ten
digits before the point), the quantity (``numeric(14, 4)``, ten) and the unit disbursement
(``numeric(14, 2)``, twelve) of an estimate line.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal

MOST_DECIMALS = 10
MOST_WHOLE_DIGITS = 10


def exceeds_precision(value: Decimal, whole_digits: int = MOST_WHOLE_DIGITS) -> bool:
    """Tell a decimal of more than ten decimals, or of more digits before the point than allowed.

    ``0.1234567890`` and ``1234567890.5`` are kept; ``0.12345678901`` and ``12345678901`` are not.
    A column with a precision (``numeric(14, 2)``) passes the digits it keeps before the point
    (``whole_digits=12``): a figure that crossed it would be a ``numeric field overflow``.
    """
    exponent = value.as_tuple().exponent
    decimals = -exponent if isinstance(exponent, int) and exponent < 0 else 0
    before_point = max(value.adjusted() + 1, 0)
    return decimals > MOST_DECIMALS or before_point > whole_digits
