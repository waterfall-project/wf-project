# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rules of the thresholds of the indices and of the delay between two reviews.

Each threshold is a decimal strictly between 0 and 1, and the threshold of alert of each index is
strictly below its threshold of watch (WF-REF-0170); the delay is from 1 to 104 weeks
(WF-REF-0180). The form of a threshold is judged first, its range then, its precision last — ten
decimals at most, which the database keeps (#2234) —, and the order of two thresholds only between
thresholds in range and kept. An index is in the zone its thresholds give it:
nominal from the watch on, in watch from the alert on, in alert below. Pure functions: the
settings are read by the interface of ``cost_settings``, which keeps them.
"""

import re
from dataclasses import dataclass
from decimal import Decimal

from waterfall.core.cost_settings.interface import IndexThresholds
from waterfall.platform.decimals import exceeds_precision
from waterfall.platform.errors import VALIDATION_FAILED, FieldError, json_pointer

NUMBER_INVALID = "NUMBER_INVALID"
THRESHOLD_NOT_BETWEEN_ZERO_AND_ONE = "THRESHOLD_NOT_BETWEEN_ZERO_AND_ONE"
THRESHOLD_NOT_BELOW_WATCH = "THRESHOLD_NOT_BELOW_WATCH"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
# The form of a decimal, as the contract writes it (``Decimal``): ASCII digits, a point.
DECIMAL = re.compile(r"-?[0-9]+(\.[0-9]+)?")
# The delay between two reviews, in weeks (WF-REF-0180).
FEWEST_WEEKS = 1
MOST_WEEKS = 104
# The zones of an index, as the contract says them (``AlertZone``).
NOMINAL, WATCH, ALERT = "nominal", "watch", "alert"


@dataclass(frozen=True, slots=True)
class ThresholdTexts:
    """The four thresholds as a writing sends them, before their form is judged."""

    cost_watch: str
    cost_alert: str
    schedule_watch: str
    schedule_alert: str


def _in_range(name: str, text: str) -> tuple[Decimal | None, FieldError | None]:
    """Read a threshold, or refuse its form, then its range, then its precision, at its pointer."""
    pointer = json_pointer("index_thresholds", name)
    if DECIMAL.fullmatch(text) is None:
        return None, FieldError(pointer, NUMBER_INVALID)
    value = Decimal(text)
    if not 0 < value < 1:
        return None, FieldError(pointer, THRESHOLD_NOT_BETWEEN_ZERO_AND_ONE)
    if exceeds_precision(value):
        return None, FieldError(pointer, VALIDATION_FAILED)
    return value, None


def read_thresholds(texts: ThresholdTexts) -> tuple[IndexThresholds | None, list[FieldError]]:
    """Read the four thresholds, or give each fault in the order of the fields (WF-REF-0170).

    A threshold that is no decimal is ``NUMBER_INVALID``, a decimal out of ]0, 1[
    ``THRESHOLD_NOT_BETWEEN_ZERO_AND_ONE``, a decimal in range of more than ten decimals
    ``VALIDATION_FAILED``; an alert that is not below its watch, both in range and kept,
    ``THRESHOLD_NOT_BELOW_WATCH`` at the alert.
    """
    faults: list[FieldError] = []
    values: dict[str, Decimal] = {}
    for index in ("cost", "schedule"):
        watch_name, alert_name = f"{index}_watch", f"{index}_alert"
        watch, watch_fault = _in_range(watch_name, getattr(texts, watch_name))
        alert, alert_fault = _in_range(alert_name, getattr(texts, alert_name))
        faults.extend(fault for fault in (watch_fault, alert_fault) if fault is not None)
        if watch is None or alert is None:
            continue
        if alert >= watch:
            pointer = json_pointer("index_thresholds", alert_name)
            faults.append(FieldError(pointer, THRESHOLD_NOT_BELOW_WATCH))
        values[watch_name], values[alert_name] = watch, alert
    if faults:
        return None, faults
    return IndexThresholds(**values), []


def delay_faults(weeks: int) -> list[FieldError]:
    """Refuse a delay out of 1 to 104 weeks, naming the one bound it crosses (WF-REF-0180)."""
    pointer = "/max_weeks_between_reviews"
    if weeks < FEWEST_WEEKS:
        return [FieldError(pointer, VALUE_OUT_OF_RANGE, {"minimum": FEWEST_WEEKS})]
    if weeks > MOST_WEEKS:
        return [FieldError(pointer, VALUE_OUT_OF_RANGE, {"maximum": MOST_WEEKS})]
    return []


def index_zone(value: Decimal, watch: Decimal, alert: Decimal) -> str:
    """Give the zone of an index: nominal from its watch on, in watch from its alert on (EP-10).

    With thresholds at 0.9 and 0.8, an index of 0.9 is nominal, one of 0.8 in watch (WF-REF-0170).
    """
    if value >= watch:
        return NOMINAL
    if value >= alert:
        return WATCH
    return ALERT
