# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the trial of the chart holds while the API goes from one instance to three (US-2800/L2)."""

import json
import threading
from typing import TYPE_CHECKING, Any

import pytest

from wftools import chartload
from wftools.chartload import Tally
from wftools.charttrial import Tools, Trial, TrialError
from wftools.production import Answer, Browser, Platform, ProductionError, Send

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

pytestmark = [pytest.mark.requirement("WF-ARC-0050-A"), pytest.mark.story("US-2800")]

PLATFORM = Platform("waterfall.localhost", 41443, 0)
EMAIL = "administrateur@waterfall.test"


def named(status: int = 200, email: str = EMAIL) -> Answer:
    return Answer(status, (), f"<main>{email.replace('@', '&#64;')}</main>")


def test_a_request_that_ends_on_the_account_of_the_administrator_is_not_a_failure() -> None:
    def send(_method: str, _url: str, _body: object, headers: Mapping[str, str]) -> Answer:
        assert headers["Cookie"] == "session=abc"
        return named()

    assert chartload.request_once(send, {"session": "abc"}, PLATFORM, EMAIL) is None


@pytest.mark.parametrize(
    ("answer", "said"),
    [
        (Answer(502, (), "bad gateway"), "answered 502"),
        (Answer(503, (), ""), "answered 503"),
        (Answer(200, (), "<main>somebody else</main>"), "does not name the first administrator"),
    ],
    ids=["502", "503", "another account"],
)
def test_a_request_that_does_not_end_on_the_account_is_a_failure_that_says_why(
    answer: Answer, said: str
) -> None:
    def send(*_: object) -> Answer:
        return answer

    failure = chartload.request_once(send, {}, PLATFORM, EMAIL)
    assert failure is not None
    assert said in failure


def test_a_connection_that_does_not_answer_is_a_failure_not_an_exception() -> None:
    def send(*_: object) -> Answer:
        message = "GET /account did not answer: refused"
        raise ProductionError(message)

    assert (
        chartload.request_once(send, {}, PLATFORM, EMAIL) == "GET /account did not answer: refused"
    )


def test_requests_are_held_by_several_threads_until_the_block_ends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(chartload, "PAUSE", 0.001)
    seen: set[int] = set()
    lock = threading.Lock()

    def send(*_: object) -> Answer:
        with lock:
            seen.add(threading.get_ident())
        return named()

    with chartload.requests_held(send, Browser(send, {"s": "1"}), PLATFORM, EMAIL, 3) as tally:
        while tally.sent < 30:
            threading.Event().wait(0.001)
    sent = tally.sent
    assert sent >= 30
    assert len(seen) == 3
    assert tally.failed == []
    # The threads are joined: nothing is sent once the block has ended.
    threading.Event().wait(0.02)
    assert tally.sent == sent


def test_a_request_that_fails_while_the_block_runs_is_kept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(chartload, "PAUSE", 0.001)
    calls = iter(range(10**6))

    def send(*_: object) -> Answer:
        return named(502) if next(calls) == 7 else named()

    with chartload.requests_held(send, Browser(send), PLATFORM, EMAIL, 1) as tally:
        while tally.sent < 20:
            threading.Event().wait(0.001)
    assert tally.failed == ["the account answered 502"]


def test_the_passage_is_uninterrupted_when_enough_requests_were_held_and_none_failed() -> None:
    chartload.check_uninterrupted(Tally(sent=chartload.LEAST))


def test_a_passage_with_a_failed_request_is_refused_naming_the_first() -> None:
    tally = Tally(sent=200, failed=["the account answered 502", "the account answered 503"])
    with pytest.raises(ProductionError, match=r"2 of 200 requests failed.*answered 502"):
        chartload.check_uninterrupted(tally)


def test_a_passage_under_too_few_requests_is_refused_as_untried() -> None:
    with pytest.raises(ProductionError, match=r"only 3 requests were held"):
        chartload.check_uninterrupted(Tally(sent=3))


def pod(name: str, owner: str, phase: str = "Running", restarts: int = 0) -> dict[str, Any]:
    return {
        "metadata": {
            "name": name,
            "uid": f"uid-{name}",
            "ownerReferences": [{"kind": owner}],
        },
        "status": {"phase": phase, "containerStatuses": [{"restartCount": restarts}] * 2},
    }


def test_the_pods_that_run_are_those_of_deployments_and_statefulsets_not_of_jobs() -> None:
    listing = {
        "items": [
            pod("api-1", "ReplicaSet", restarts=1),
            pod("postgres-0", "StatefulSet"),
            pod("migrate-x", "Job"),
            pod("purge-y", "Job", phase="Succeeded"),
            pod("front-2", "ReplicaSet", phase="Pending"),
            {
                "metadata": {"name": "bare", "uid": "u"},
                "status": {"phase": "Running"},
            },
        ]
    }
    assert chartload.pods_of(listing) == {
        "api-1": ("uid-api-1", 2),
        "postgres-0": ("uid-postgres-0", 0),
    }


def test_a_pod_there_was_and_is_still_there_unrestarted_passes_beside_new_ones() -> None:
    before = {"api-1": ("a", 0), "postgres-0": ("p", 0)}
    chartload.check_untouched(before, {**before, "api-2": ("b", 0), "api-3": ("c", 0)})


@pytest.mark.parametrize(
    ("after", "said"),
    [
        ({"api-1": ("a", 0)}, "the pod postgres-0 is gone"),
        ({"api-1": ("a", 0), "postgres-0": ("p2", 0)}, "the pod postgres-0 was restarted"),
        ({"api-1": ("a", 0), "postgres-0": ("p", 1)}, "the pod postgres-0 was restarted"),
        ({"postgres-0": ("p", 0), "api-1": ("z", 0)}, "the pod api-1 was restarted"),
    ],
    ids=["gone", "replaced", "restarted", "api replaced"],
)
def test_a_pod_replaced_or_restarted_by_the_passage_is_refused(
    after: dict[str, tuple[str, int]], said: str
) -> None:
    before = {"api-1": ("a", 0), "postgres-0": ("p", 0)}
    with pytest.raises(ProductionError, match=said):
        chartload.check_untouched(before, after)


@pytest.mark.parametrize(
    ("done", "started", "passes"),
    [
        ("2026-11-20T10:00:05Z", "2026-11-20T10:00:09Z", True),
        ("2026-11-20T10:00:09Z", "2026-11-20T10:00:09Z", True),
        ("2026-11-20T10:00:12Z", "2026-11-20T10:00:09Z", False),
        ("", "2026-11-20T10:00:09Z", False),
        ("2026-11-20T10:00:05Z", "", False),
    ],
    ids=["before", "the same second", "after", "never ended", "never began"],
)
def test_the_migrations_must_end_before_the_installation_begins(
    done: str, started: str, passes: bool
) -> None:
    if passes:
        chartload.check_before(done, started)
        return
    with pytest.raises(ProductionError, match="the migrations ended at"):
        chartload.check_before(done, started)


def _sender_of(send: Send) -> Callable[[Trial], Send]:
    def sender(_trial: Trial) -> Send:
        return send

    return sender


def _trial(tmp_path: Path, answers: dict[str, str], ran: list[list[str]]) -> Trial:
    def run(command: list[str]) -> int:
        ran.append(command)
        return 0

    def read(command: list[str]) -> tuple[int, str]:
        ran.append(command)
        return 0, next((out for key, out in answers.items() if key in " ".join(command)), "")

    return Trial(Tools(["kind"], ["kubectl"], ["helm"]), run, read, tmp_path, PLATFORM)


def test_the_chart_is_upgraded_with_the_same_values_but_the_replicas_of_the_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ran: list[list[str]] = []
    listing = json.dumps({"items": [pod("api-1", "ReplicaSet")]})
    trial = _trial(tmp_path, {"get pods": listing, "readyReplicas": "3"}, ran)
    monkeypatch.setattr(chartload, "PAUSE", 0.001)
    monkeypatch.setattr(chartload, "LEAST", 1)

    def send(*_: object) -> Answer:
        return named()

    monkeypatch.setattr(Trial, "sender", _sender_of(send))
    values = {"images": {"tag": "abc"}, "api": {"processes": 2}}
    trial.scale(values, Browser(send), EMAIL, 3)
    (upgrade,) = [command for command in ran if "upgrade" in command]
    assert upgrade[:3] == ["helm", "upgrade", "waterfall"]
    assert "--wait" in upgrade
    given = (tmp_path / "values.json").read_text(encoding="utf-8")
    assert '"api": {"processes": 2, "replicas": 3}' in given
    assert '"images": {"tag": "abc"}' in given


def test_an_upgrade_that_leaves_fewer_instances_ready_than_asked_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ran: list[list[str]] = []
    trial = _trial(tmp_path, {"get pods": '{"items": []}', "readyReplicas": "2"}, ran)
    monkeypatch.setattr(chartload, "PAUSE", 0.001)
    monkeypatch.setattr(chartload, "LEAST", 1)

    def send(*_: object) -> Answer:
        return named()

    monkeypatch.setattr(Trial, "sender", _sender_of(send))
    with pytest.raises(TrialError, match="2 instances of the API are ready, not 3"):
        trial.scale({}, Browser(send), EMAIL, 3)


def test_an_upgrade_under_which_a_request_fails_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ran: list[list[str]] = []
    trial = _trial(tmp_path, {"get pods": '{"items": []}', "readyReplicas": "3"}, ran)
    monkeypatch.setattr(chartload, "PAUSE", 0.001)
    monkeypatch.setattr(chartload, "LEAST", 1)

    def send(*_: object) -> Answer:
        return named(503)

    monkeypatch.setattr(Trial, "sender", _sender_of(send))
    with pytest.raises(ProductionError, match=r"requests failed during the passage"):
        trial.scale({}, Browser(send), EMAIL, 3)
