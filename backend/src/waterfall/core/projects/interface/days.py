# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The current day of an instant: the one function every module takes it from (US-1380/L4).

A dated entry proposes the current day by default — the state of a task started or completed
(WF-PLA-0130), the review date of an export of the remaining to commit (WF-INTF-0130), the planning
start of a structure created — and the day is that of the time zone of the installation
(WF-EXP-0020, WF-DAT-0100), which the bootstrap fixes and the process reads once (US-2200, #2527).
"""

from typing import TYPE_CHECKING

from waterfall.platform.installation import TIME_ZONE

if TYPE_CHECKING:
    from datetime import date, datetime


def current_day(at: datetime) -> date:
    """Give the day an instant of the service falls on, in the time zone of the installation.

    ``at`` is aware, as every instant of the service is (``UtcDateTime``): the clock is read by
    the caller, never here. The time zone is the process's (``TIME_ZONE``): at 23:30 in universal
    time, an installation in Paris is already on the next day.
    """
    return at.astimezone(TIME_ZONE.zone()).date()
