# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The risks and the costs of the health of the control, on the project of the risks (US-2750).

The project of ``occurrence_support``, moved In progress: a risk identified in its first revision,
marked and designated the reference, its second opened. The reviews and the markings it writes carry
the instant of their writing, which is the current day: the interval between the marking before the
last and the last is the one the sentence under test lays down, the markings and the reviews written
in the order of the story. Every answer is validated against the contract by the client of the
tests; the chronology of 2026 and the reading of a past date are in ``test_portfolio_pilot_health``.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from costs_support import load_import
from estimate_support import costing
from nodes_support import mark
from occurrence_support import Occurring, occurring
from portfolio_listing_support import served
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from risks_support import costed
from sqlalchemy import event

from waterfall.core.costs.interface import last_imports
from waterfall.core.risks.interface import ReviewWindow, not_reviewed_since
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

REQUIREMENT = "WF-PTF-0110-A"
RISKS_NOT_REVIEWED = "risks_not_reviewed"
NO_COST = "no_actual_cost_since_last_review"


@pytest.fixture
def ready(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Occurring:
    """Give the risk identified in the second revision of the project, moved In progress."""
    stage: Scene = make_scene(api, owner, database, realm)
    ready = occurring(api, costed(api, stage, costing(stage.database)))
    path = f"{PROJECTS}/{ready.project.project_id}"
    counter = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    coded = api.patch(
        path, headers=stage.manager.headers, json={"code": "PRJ-2750", "lock_version": counter}
    )
    assert (coded.status_code, coded.json()["state"]) == (200, "in_progress"), coded.text
    return ready


def codes(ready: Occurring) -> list[str]:
    """Read the health as the reader of every project does; give the codes of the signals."""
    body = served(ready.api, ready.project.stage.reader, "pilot-health", "")
    assert body["scope"]["project_count"] == 1
    assert {each["project_id"] for each in body["signals"]} <= {str(ready.project.project_id)}
    return [each["code"] for each in body["signals"]]


def imported(ready: Occurring) -> None:
    """Load an import applied now on the project, as the witness loads one."""
    load_import(ready.project.stage, ready.project.project_id, [], at=utc_now())


@pytest.mark.requirement(REQUIREMENT)
def test_a_project_whose_review_marked_today_re_examined_every_risk_and_imported_costs_has_neither(
    ready: Occurring,
) -> None:
    # « Un projet dont la revue marquée ce jour a réexaminé chaque risque et importé des coûts
    # n'apparaît pour aucun de ces deux signaux » : the first revision was marked before the
    # project passed In progress, it is its reference and no review: until a review is marked
    # after the passage, neither signal is raised (``review_overdue`` says its delay). The first
    # review after the passage judged from the passage: the risk it did not re-examine and the
    # cost it did not import are both signalled; re-examined and imported, neither remains.
    assert codes(ready) == []
    mark(ready.project.stage, ready.revision, "v2.0")
    assert codes(ready) == [RISKS_NOT_REVIEWED, NO_COST]
    third = ready.risks.revision()
    ready.risks.reviewed(ready.read())
    imported(ready)
    mark(ready.project.stage, third, "v3.0")
    assert codes(ready) == []


@pytest.mark.requirement(REQUIREMENT)
def test_a_risk_not_re_examined_between_the_two_last_markings_signals_the_project_until_it_is(
    ready: Occurring,
) -> None:
    # « …un risque identifié n'a pas été réexaminé entre l'avant-dernière et la dernière révision
    # marquée » : the second revision marked as it is, a third opened and marked without the risk
    # reviewed nor a cost imported, both signals are back; reviewed in a fourth, with an import,
    # they leave; the review that follows the marking does not count for it.
    stage = ready.project.stage
    ready.risks.reviewed(ready.read())
    imported(ready)
    mark(stage, ready.revision, "v2.0")
    third = ready.risks.revision()
    mark(stage, third, "v3.0")
    assert codes(ready) == [RISKS_NOT_REVIEWED, NO_COST]
    fourth = ready.risks.revision()
    ready.risks.reviewed(ready.read())
    imported(ready)
    assert codes(ready) == [RISKS_NOT_REVIEWED, NO_COST]
    mark(stage, fourth, "v4.0")
    assert codes(ready) == []


@pytest.mark.story("US-2750")
def test_a_risk_that_is_not_identified_is_not_one_to_re_examine(ready: Occurring) -> None:
    # Propre à l'US : « un risque identifié » — a risk dismissed in the revision read does not
    # signal its project, whatever the reviews before it; the cost signal stays on its own.
    stage = ready.project.stage
    ready.risks.reviewed(ready.read(), state="dismissed")
    mark(stage, ready.revision, "v2.0")
    third = ready.risks.revision()
    mark(stage, third, "v3.0")
    assert codes(ready) == [NO_COST]


@pytest.mark.story("US-2750")
def test_the_risks_not_re_examined_of_many_projects_are_read_in_a_fixed_number_of_statements(
    ready: Occurring, database: Database
) -> None:
    # #4294 point 1 : one project, then that project with others, the same statements — the
    # marked revisions of all, one query, and the risks of all, one more — whatever the number of
    # projects, and none a read of ``portfolio_risks`` project by project.
    project_id = ready.project.project_id
    revision = UUID(ready.first["revision_id"])
    since = utc_now()
    sent: list[str] = []

    def heard(*arguments: Any) -> None:
        sent.append(str(arguments[2]))

    def measure(count: int) -> int:
        windows = {project_id: ReviewWindow(revision, since)}
        windows |= {uuid4(): ReviewWindow(uuid4(), since) for _ in range(count)}
        sent.clear()
        event.listen(database.engine, "before_cursor_execute", heard)
        try:
            with database.transaction() as session:
                found = not_reviewed_since(session, windows)
                last_imports(session, dict.fromkeys(windows, since))
        finally:
            event.remove(database.engine, "before_cursor_execute", heard)
        assert found == {project_id: {UUID(ready.risk["risk_id"])}}
        return len(sent)

    few = measure(0)
    many = measure(40)
    assert 0 < few <= 4
    assert many == few
