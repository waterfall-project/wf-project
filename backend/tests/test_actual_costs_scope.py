# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A line of the actual costs excluded from the scope tracked, and reinstated (US-1620/L1).

``setActualCostTrackedScope``: the state aimed at and the reason written, idempotent and without a
counter, the totals of the list that follow at once, the exclusion kept by a later import, the
inscription in the journal of audit and no entry in the history that can be undone; the conditions
of the command ``exclude_cost_lines`` in their order, the rights, two exclusions of a line at once
and an exclusion that waits for the lock of the project; and the exclusion the witness loads. Every
answer is checked against the contract.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from costs_support import cost, load_import
from nodes_support import refusal
from projects_support import PROJECTS, Scene, contribute, person, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from support import wait_for_a_lock

from waterfall.api.contract.models import AuditParams
from waterfall.core.costs.interface import load_exclusion
from waterfall.core.costs.tables import CostLine
from waterfall.core.history.tables import UndoEntry
from waterfall.core.projects.interface import lock_project
from waterfall.core.projects.tables import Project
from waterfall.platform.audit import Act, AuditEntry
from waterfall.platform.database import utc_now
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

STATE = "STATE_FORBIDS_OPERATION"
REASON = "Câbles d'un autre projet, à réimputer"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform and its project In progress, with two lines of cost loaded: FA-1 and FA-2."""
    stage = make_scene(api, owner, database, realm)
    put_in_state(owner, stage.project["project_id"], "in_progress")
    load_import(
        stage,
        UUID(stage.project["project_id"]),
        [cost("FA-1", None, "100.00", "10"), cost("FA-2", None, "40.00")],
    )
    return stage


def line_of(stage: Scene, number: str) -> UUID:
    """Give the identifier of the line of a document of the project of the stage."""
    with stage.database.transaction() as session:
        return session.scalars(select(CostLine.id).where(CostLine.document_number == number)).one()


def stored(stage: Scene, number: str) -> CostLine:
    """Read the line of a document, as the base holds it."""
    with stage.database.transaction() as session:
        found = session.scalars(select(CostLine).where(CostLine.document_number == number)).one()
        session.expunge(found)
        return found


def scope_path(stage: Scene, number: str) -> str:
    """Give the path of the tracked scope of the line of a document."""
    base = f"{PROJECTS}/{stage.project['project_id']}/actual-costs"
    return f"{base}/{line_of(stage, number)}/tracked-scope"


def put(api: ContractClient, stage: Scene, number: str, who: Any = None, **body: Any) -> Any:
    """Send the state aimed at for a line, as the manager does unless said; give the answer."""
    headers = (who or stage.manager).headers
    return api.put(scope_path(stage, number), headers=headers, json=body)


def totals(api: ContractClient, stage: Scene) -> dict[str, str]:
    """Read the three totals of the list of the actual costs."""
    answer = api.get(
        f"{PROJECTS}/{stage.project['project_id']}/actual-costs", headers=stage.manager.headers
    )
    assert answer.status_code == 200, answer.text
    return answer.json()["totals"]


def journal(stage: Scene) -> list[AuditEntry]:
    """Read the inscriptions of the journal of audit, in the order they were made."""
    with stage.database.transaction() as session:
        found = session.scalars(select(AuditEntry).order_by(AuditEntry.occurred_at)).all()
        session.expunge_all()
        return [each for each in found if each.object_kind == "cost_line"]


@pytest.mark.requirement("WF-CRE-0040-A")
def test_the_exclusion_of_a_line_moves_its_amount_from_the_tracked_total_to_the_excluded_one(
    api: ContractClient, stage: Scene
) -> None:
    # « L'exclusion d'une ligne depuis la liste modifie immédiatement les deux premiers totaux. »
    assert totals(api, stage) == {"tracked": "140.00", "excluded": "0.00", "overall": "140.00"}
    answer = put(api, stage, "FA-1", is_in_tracked_scope=False, reason=REASON)
    assert answer.status_code == 200, answer.text
    excluded = answer.json()
    assert (excluded["is_in_tracked_scope"], excluded["excluded_reason"]) == (False, REASON)
    assert (excluded["document_number"], excluded["document_item"]) == ("FA-1", "10")
    assert excluded["audit"]["updated_by"]["user_id"] == str(stage.manager.user_id)
    assert totals(api, stage) == {"tracked": "40.00", "excluded": "100.00", "overall": "140.00"}


@pytest.mark.requirement("WF-CRE-0030-A")
def test_a_line_reinstated_is_tracked_again_and_carries_no_reason(
    api: ContractClient, stage: Scene
) -> None:
    put(api, stage, "FA-1", is_in_tracked_scope=False, reason=REASON)
    # The reason sent with a reinstatement is not kept: a tracked line never has one.
    answer = put(api, stage, "FA-1", is_in_tracked_scope=True, reason="ignorée")
    assert answer.status_code == 200, answer.text
    assert (answer.json()["is_in_tracked_scope"], answer.json()["excluded_reason"]) == (True, None)
    assert totals(api, stage) == {"tracked": "140.00", "excluded": "0.00", "overall": "140.00"}
    without = put(api, stage, "FA-2", is_in_tracked_scope=False)
    assert (without.status_code, without.json()["excluded_reason"]) == (200, None)


@pytest.mark.requirement("WF-CRE-0030-A")
def test_an_exclusion_is_kept_by_a_second_import_of_the_same_period(
    api: ContractClient, stage: Scene
) -> None:
    # « Après un second import couvrant la même période, elle est toujours exclue. » : the import
    # writes the line on its document and item again, and leaves the exclusion as it is.
    put(api, stage, "FA-1", is_in_tracked_scope=False, reason=REASON)
    load_import(stage, UUID(stage.project["project_id"]), [cost("FA-1", None, "120.00", "10")])
    again = stored(stage, "FA-1")
    assert (again.is_in_tracked_scope, again.excluded_reason) == (False, REASON)
    assert str(again.amount) == "120.00"
    assert totals(api, stage) == {"tracked": "40.00", "excluded": "120.00", "overall": "160.00"}


@pytest.mark.requirement("WF-CRE-0030-A")
def test_a_request_for_the_state_the_line_has_changes_and_inscribes_nothing(
    api: ContractClient, stage: Scene
) -> None:
    # Idempotent, without a counter: the same state with the same reason, replayed, is a no-op.
    first = put(api, stage, "FA-1", is_in_tracked_scope=False, reason=REASON)
    before = stored(stage, "FA-1")
    replay = put(api, stage, "FA-1", is_in_tracked_scope=False, reason=REASON)
    assert replay.status_code == 200, replay.text
    assert replay.json() == first.json()
    assert stored(stage, "FA-1").updated_at == before.updated_at
    tracked = stored(stage, "FA-2")
    assert put(api, stage, "FA-2", is_in_tracked_scope=True).status_code == 200
    assert stored(stage, "FA-2").updated_at == tracked.updated_at
    assert [entry.action for entry in journal(stage)] == ["cost_line_exclude"]
    # Another reason for the same state is a change, and is inscribed.
    changed = put(api, stage, "FA-1", is_in_tracked_scope=False, reason="Autre motif")
    assert changed.json()["excluded_reason"] == "Autre motif"
    assert [entry.action for entry in journal(stage)] == ["cost_line_exclude"] * 2


@pytest.mark.requirement("WF-SEC-0030-A")
def test_an_exclusion_and_a_reinstatement_are_inscribed_in_the_journal_of_audit(
    api: ContractClient, stage: Scene
) -> None:
    put(api, stage, "FA-1", is_in_tracked_scope=False, reason=REASON)
    put(api, stage, "FA-1", is_in_tracked_scope=True)
    excluding, reinstating = journal(stage)
    identifier = line_of(stage, "FA-1")
    assert (excluding.action, reinstating.action) == ("cost_line_exclude", "cost_line_reinstate")
    for entry in (excluding, reinstating):
        assert (entry.object_kind, entry.object_id) == ("cost_line", identifier)
        assert entry.object_label == "FA-1 / 10"
        assert str(entry.project_id) == stage.project["project_id"]
        assert entry.actor_user_id == stage.manager.user_id
        assert AuditParams.model_validate(entry.params).model_dump(exclude_unset=True) == {}


@pytest.mark.requirement("WF-IHM-0110-A")
def test_an_exclusion_does_not_enter_the_history_that_can_be_undone(
    api: ContractClient, stage: Scene
) -> None:
    put(api, stage, "FA-1", is_in_tracked_scope=False, reason=REASON)
    put(api, stage, "FA-1", is_in_tracked_scope=True)
    with stage.database.transaction() as session:
        assert session.scalars(select(UndoEntry)).all() == []


@pytest.mark.requirement("WF-CYC-0100-A")
@pytest.mark.parametrize("state", ["completed", "lost", "abandoned"])
def test_the_exclusion_is_refused_on_a_terminal_project_and_writes_nothing(
    api: ContractClient, stage: Scene, state: str
) -> None:
    put_in_state(stage.owner, stage.project["project_id"], state)
    answer = put(api, stage, "FA-1", is_in_tracked_scope=False, reason=REASON)
    assert refusal(answer) == (409, STATE, {"missing_condition": "project_not_terminal"})
    assert stored(stage, "FA-1").is_in_tracked_scope
    assert journal(stage) == []


@pytest.mark.requirement("WF-CRE-0030-A")
@pytest.mark.parametrize("state", ["created", "pricing"])
def test_the_exclusion_is_refused_before_the_project_is_in_progress(
    api: ContractClient, stage: Scene, state: str
) -> None:
    put_in_state(stage.owner, stage.project["project_id"], state)
    answer = put(api, stage, "FA-1", is_in_tracked_scope=False)
    assert refusal(answer) == (409, STATE, {"missing_condition": "project_in_progress"})
    assert stored(stage, "FA-1").is_in_tracked_scope
    assert journal(stage) == []


@pytest.mark.requirement("WF-CRE-0030-A")
def test_a_line_that_the_project_does_not_have_is_unknown(
    api: ContractClient, stage: Scene
) -> None:
    base = f"{PROJECTS}/{stage.project['project_id']}/actual-costs"
    unknown = api.put(
        f"{base}/{uuid4()}/tracked-scope",
        headers=stage.manager.headers,
        json={"is_in_tracked_scope": False},
    )
    assert refusal(unknown)[:2] == (404, "NOT_FOUND")
    # A line of another project is none of this one, whatever its identifier is.
    other = api.post(PROJECTS, headers=stage.manager.headers, json={"label": "Autre projet"})
    assert other.status_code == 201, other.text
    put_in_state(stage.owner, other.json()["project_id"], "in_progress")
    foreign = f"{PROJECTS}/{other.json()['project_id']}/actual-costs"
    elsewhere = api.put(
        f"{foreign}/{line_of(stage, 'FA-1')}/tracked-scope",
        headers=stage.manager.headers,
        json={"is_in_tracked_scope": False},
    )
    assert refusal(elsewhere)[:2] == (404, "NOT_FOUND")
    assert stored(stage, "FA-1").is_in_tracked_scope


@pytest.mark.requirement("WF-ADM-0110-A")
def test_the_exclusion_asks_for_its_permission_and_the_quality_of_contributor(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    sent = {"is_in_tracked_scope": False}
    reading = person(stage.database, realm, "actual_costs.read")
    contribute(stage.database, stage.project["project_id"], reading, "contributor")
    denied = put(api, stage, "FA-1", reading, **sent)
    assert refusal(denied) == (
        403,
        "PERMISSION_MISSING",
        {"missing_permission": "cost_line_exclude"},
    )
    holding = person(stage.database, realm, "actual_costs.read", "cost_line_exclude")
    assert refusal(put(api, stage, "FA-1", holding, **sent))[:2] == (404, "NOT_FOUND")
    seeing = person(
        stage.database, realm, "actual_costs.read", "cost_line_exclude", "all_projects_read"
    )
    assert refusal(put(api, stage, "FA-1", seeing, **sent))[:2] == (403, "NOT_CONTRIBUTOR")
    contributing = put(api, stage, "FA-1", stage.participant, **sent)
    assert contributing.status_code == 200, contributing.text
    assert journal(stage)[0].actor_user_id == stage.participant.user_id


@pytest.mark.requirement("WF-CRE-0030-A")
def test_a_body_without_the_state_aimed_at_is_refused(api: ContractClient, stage: Scene) -> None:
    answer = put(api, stage, "FA-1", reason=REASON)
    assert answer.status_code in {400, 422}, answer.text
    assert stored(stage, "FA-1").is_in_tracked_scope


@pytest.mark.requirement("WF-CRE-0030-A")
def test_two_exclusions_of_a_line_at_once_are_written_one_after_the_other(
    api: ContractClient, stage: Scene
) -> None:
    # Under the lock of the project, the second request finds the line excluded: one inscription,
    # not two, and the totals are those of one exclusion.
    with ThreadPoolExecutor(2) as pool:
        pending = [
            pool.submit(put, api, stage, "FA-1", is_in_tracked_scope=False, reason=REASON)
            for _ in range(2)
        ]
        answers = [each.result() for each in pending]
    assert [answer.status_code for answer in answers] == [200, 200]
    assert answers[0].json() == answers[1].json()
    assert [entry.action for entry in journal(stage)] == ["cost_line_exclude"]
    assert totals(api, stage) == {"tracked": "40.00", "excluded": "100.00", "overall": "140.00"}


@pytest.mark.requirement("WF-CRE-0030-A")
def test_an_exclusion_waits_for_the_lock_of_the_project_and_judges_the_state_it_finds(
    api: ContractClient, stage: Scene, database: Database
) -> None:
    # An import applied (or any writer of the project) holds the lock: the exclusion waits for it,
    # and when the project has become terminal meanwhile, it is refused on that state.
    with ThreadPoolExecutor(1) as others, Session(database.engine) as holding:
        lock_project(holding, UUID(stage.project["project_id"]))
        waiting = others.submit(put, api, stage, "FA-1", is_in_tracked_scope=False)
        wait_for_a_lock(database, 1)
        assert not waiting.done()
        holding.execute(
            update(Project)
            .where(Project.id == UUID(stage.project["project_id"]))
            .values(state="completed")
        )
        holding.commit()
        answer = waiting.result(timeout=20)
    assert refusal(answer) == (409, STATE, {"missing_condition": "project_not_terminal"})
    assert stored(stage, "FA-1").is_in_tracked_scope


@pytest.mark.requirement("WF-CRE-0030-A")
def test_the_witness_excludes_a_line_at_its_instant_whatever_the_state_of_the_project(
    stage: Scene,
) -> None:
    # ``load_exclusion``: as the service excludes, the journal included, but the conditions of the
    # command are not judged — the witness writes a past that the project may have left.
    put_in_state(stage.owner, stage.project["project_id"], "completed")
    at = utc_now().replace(year=2026, month=4, day=6, hour=9, minute=15)
    with logging_context(correlation_id="witness"), stage.database.transaction() as session:
        load_exclusion(
            session,
            UUID(stage.project["project_id"]),
            line_of(stage, "FA-1"),
            REASON,
            Act(stage.manager.user_id, at),
        )
    loaded = stored(stage, "FA-1")
    assert (loaded.is_in_tracked_scope, loaded.excluded_reason) == (False, REASON)
    assert (loaded.updated_at, loaded.updated_by) == (at, stage.manager.user_id)
    [entry] = journal(stage)
    assert (entry.action, entry.occurred_at) == ("cost_line_exclude", at)
    assert date(2026, 4, 6) == loaded.updated_at.date()
