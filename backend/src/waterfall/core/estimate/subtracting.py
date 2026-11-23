# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The differences of a modified node of a comparison, private to the module (EP-27, US-2340).

Pure: of the values of a node that differ from its base, those that are a date, a duration or an
amount bear a difference, the revision read less the base (``NodeDeltas``, WF-IHM-0150), written
as the node writes its values, by their name in the node (``task.finish``): a date in calendar
days, the date alone of a start or a finish (``WorkInstant``); a duration in the unit of the one
read, in working time, both converted into hours by the constants of the installation when their
units differ (``Duration.less``, WF-PLA-0160); an amount to the cent. A difference is null when
one of its two values is, which only the values that may be null are.
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from waterfall.core.planning.interface import Duration

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from waterfall.core.planning.interface import DurationUnit, UnitConstants

CENT = Decimal("0.01")
# The values that bear a difference, by kind (``TaskDeltas``, ``EstimateLineDeltas``).
DATES = frozenset({"task.start", "task.finish", "task.started_on", "task.completed_on"})
DURATIONS = frozenset({"task.duration"})
AMOUNTS = frozenset(
    {
        *(
            f"{facet}.{amount}"
            for facet in ("task", "estimate_line")
            for amount in ("base_amount", "budgeted_amount", "reestimated_amount")
        ),
        "estimate_line.unit_disbursement",
        "estimate_line.previous_unit_disbursement",
        "estimate_line.previous_reestimated_amount",
    }
)


def _value(values: Mapping[str, Any], name: str) -> Any:
    """Give a value of a node written whole by its name in it, ``task.finish`` in its facet."""
    facet, _, key = name.partition(".")
    held: Mapping[str, Any] = values.get(facet) or {}
    return held.get(key)


def _day(value: Any) -> date:
    """Give the day of a date, or of an instant of work (``WorkInstant``), as a node writes it."""
    written = cast("Mapping[str, str] | str", value)
    return date.fromisoformat(written if isinstance(written, str) else written["date"])


def _duration(value: Mapping[str, Any]) -> Duration:
    """Give a duration as a node writes it (``Duration``): its value, its unit."""
    return Duration(Decimal(value["value"]), cast("DurationUnit", value["unit"]))


def _difference(name: str, now: Any, then: Any, constants: UnitConstants) -> Any:
    """Give the difference of a value, the revision read less the base; null if either is."""
    if now is None or then is None:
        return None
    if name in DATES:
        return (_day(now) - _day(then)).days
    if name in DURATIONS:
        found = _duration(now).less(_duration(then), constants)
        return {"value": format(found.value.normalize(), "f"), "unit": found.unit}
    return format((Decimal(now) - Decimal(then)).quantize(CENT), "f")


def deltas_of(
    names: Iterable[str],
    then: Mapping[str, Any],
    now: Mapping[str, Any],
    constants: UnitConstants,
) -> dict[str, Any]:
    """Give the differences of the values named that are a date, a duration or an amount.

    ``names`` the values of the node that differ, ``then`` and ``now`` the node written whole in
    the base and in the revision read; ``constants`` those of the units of the installation.
    """
    return {
        name: _difference(name, _value(now, name), _value(then, name), constants)
        for name in names
        if name in DATES or name in DURATIONS or name in AMOUNTS
    }
