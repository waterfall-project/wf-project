# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The current day of an instant: the one function every module takes it from (US-1380/L4).

A dated entry proposes the current day by default — the state of a task started or completed
(WF-PLA-0130), the review date of an export of the remaining to commit (WF-INTF-0130), the planning
start of a structure created — and the day is that of the time zone of the installation
(WF-EXP-0020, WF-DAT-0100). The back has no such time zone yet: the day is taken in universal time
until EP-07 gives the installation its own and plugs it here (#2527), its callers unchanged.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date, datetime


def current_day(at: datetime) -> date:
    """Give the day an instant of the service falls on: in universal time, for now (#2527).

    ``at`` is aware, as every instant of the service is (``UtcDateTime``): the clock is read by
    the caller, never here.
    """
    return at.date()
