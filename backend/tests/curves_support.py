# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the curves share (US-1690/L2): a project priced over three months, and reads.

Two tasks of the reference start on the Monday ``DAY``, 2 November 2026, on the calendar of eight
hours from Monday to Friday: the studies, 400 over 30 working days, ending on 11 December, and the
wiring, 600 over 60, ending on 25 January. The studies are completed on the Friday of the week,
``DAY + 4``, and 100 of cost are dated the Wednesday, ``DAY + 3``; the clock is set on the Friday
of the week after, ``DAY + 11``, 13 November. A budget of 1 000 is thus spread 490 in November
(21 days of 30 of the studies, 21 of 60 of the wiring), 350 in December and 160 in January; the 600
of the wiring left from 16 November are 132, 276 and 192 (11, 23 and 16 days of 50, at 12 a day).
"""

from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from costs_support import load_import
from day_indicators_support import Planned, completed, dated, priced
from planning_support import DAY
from projects_support import PROJECTS

if TYPE_CHECKING:
    from day_indicators_support import Priced
    from indicators_support import Clock
    from projects_support import Scene
    from support import ContractClient

COST_CURVE, EARNED_VALUE_CURVES = "cost-curve", "earned-value-curves"
# The day of the reading of the scenario: the Friday of the week after the start.
TODAY = DAY + timedelta(days=11)


def curve_answer(api: ContractClient, stage: Scene, name: str, query: str = "") -> Any:
    """Ask for a curve of the project of the stage, the query said; give the answer."""
    return api.get(
        f"{PROJECTS}/{stage.project['project_id']}/indicators/{name}{query}",
        headers=stage.manager.headers,
    )


def curve(api: ContractClient, stage: Scene, name: str, query: str = "") -> dict[str, Any]:
    """Read a curve of the project of the stage, which must be served."""
    answer = curve_answer(api, stage, name, query)
    assert answer.status_code == 200, answer.text
    return answer.json()


def series(body: dict[str, Any], name: str) -> list[tuple[str, str]]:
    """Give the points of a series of a curve, each as its day and its amount."""
    found = next(each for each in body["series"] if each["name"] == name)
    return [(point["date"], point["amount"]) for point in found["points"]]


def over_three_months(
    api: ContractClient,
    stage: Scene,
    clock: Clock,
    *,
    subproject_id: str | None = None,
    payment_delay_days: int = 0,
) -> Priced:
    """Write the project of the module, its two tasks borne by a subproject or by none.

    The studies completed on ``DAY + 4``, 100 of cost loaded for the project alone, dated
    ``DAY + 3``; the clock set at ``TODAY``.
    """
    found = priced(
        api,
        stage,
        [
            Planned("Études", "400", subproject_id, "30", payment_delay_days),
            Planned("Câblage", "600", subproject_id, "60", payment_delay_days),
        ],
    )
    completed(found.tree, "Études", DAY + timedelta(days=4))
    cost = dated("FA-1", None, "100.00", DAY + timedelta(days=3))
    load_import(stage, UUID(stage.project["project_id"]), [cost])
    clock(TODAY)
    return found
