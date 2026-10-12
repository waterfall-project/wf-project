# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The backup and the restoration the trial of the production platform asks of its API (US-0440).

The platform is played: the realm that gives the front its code and its token, the API that the
container of the API is asked, the liveness probe. These tests hold what the trial concludes from
what they answer; the platform itself is backed up and restored by ``make production-trial`` in the
chain, once the service of the restoration is started there (#948, point 2).
"""

import base64
import hashlib
import json
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest

from wftools.production import Answer
from wftools.restoration_trial import (
    API_CALL,
    Administrator,
    Api,
    Clock,
    RestorationTrial,
    TrialError,
    access_token,
    probe_of,
    wanted,
)

ADDRESS = "https://waterfall.localhost"
CALLBACK = f"{ADDRESS}/auth/callback"
FRONT_CLIENT = "chain-only-front-client"
COMPOSE = ["docker", "compose"]
BACKUP = {
    "backup_id": "01926f3a-7c00-7000-8000-000000000501",
    "taken_at": "2026-06-02T01:00:00Z",
    "verification": "passed",
}


@dataclass(slots=True)
class Realm:
    """The realm, a session of Keycloak open or not: it gives a code, then a token for it."""

    signed_in: bool = True
    state: str | None = None
    token_status: int = 200
    asked: list[dict[str, str]] = field(default_factory=list[dict[str, str]])
    challenge: str = ""

    def request(self, method: str, url: str) -> Answer:
        assert method == "GET"
        query = {key: values[0] for key, values in parse_qs(urlsplit(url).query).items()}
        assert urlsplit(url).path == "/auth/realms/waterfall/protocol/openid-connect/auth"
        assert (query["client_id"], query["redirect_uri"]) == ("waterfall-front", CALLBACK)
        assert query["code_challenge_method"] == "S256"
        self.challenge = query["code_challenge"]
        if not self.signed_in:
            return Answer(200, (), "<form>")
        state = query["state"] if self.state is None else self.state
        return Answer(302, (("Location", f"{CALLBACK}?state={state}&code=c0de"),), "")

    def send(self, method: str, url: str, body: bytes | None, headers: Mapping[str, str]) -> Answer:
        assert (method, urlsplit(url).path) == (
            "POST",
            "/auth/realms/waterfall/protocol/openid-connect/token",
        )
        assert "Cookie" not in headers
        form = {key: values[0] for key, values in parse_qs((body or b"").decode()).items()}
        self.asked.append(form)
        if self.token_status != 200:
            return Answer(self.token_status, (), '{"error": "invalid_grant"}')
        return Answer(200, (), json.dumps({"access_token": f"token-{len(self.asked)}"}))


def test_a_token_is_taken_as_the_front_takes_it_by_its_code_its_proof_and_its_secret() -> None:
    realm = Realm()
    assert access_token(realm, realm.send, ADDRESS, FRONT_CLIENT) == "token-1"
    (form,) = realm.asked
    assert form["grant_type"] == "authorization_code"
    assert (form["code"], form["redirect_uri"]) == ("c0de", CALLBACK)
    assert (form["client_id"], form["client_secret"]) == ("waterfall-front", FRONT_CLIENT)
    proof = hashlib.sha256(form["code_verifier"].encode()).digest()
    assert base64.urlsafe_b64encode(proof).decode().rstrip("=") == realm.challenge


def test_a_token_is_refused_without_a_session_the_state_given_or_a_token_issued() -> None:
    for realm, said in (
        (Realm(signed_in=False), "no session of Keycloak"),
        (Realm(state="another"), "without the code or the state"),
        (Realm(token_status=400), re.escape("issued no token for the code (400)")),
    ):
        with pytest.raises(TrialError, match=said):
            access_token(realm, realm.send, ADDRESS, FRONT_CLIENT)


def test_the_trial_asks_for_the_backup_and_its_restoration_by_one_variable() -> None:
    assert wanted({"WATERFALL_TRIAL_RESTORATION": "1"})
    assert not wanted({})
    assert not wanted({"WATERFALL_TRIAL_RESTORATION": "0"})


type Said = tuple[int, Any]


class FakeApi:
    """The container of the API: each operation answers in turn what the test gives it."""

    def __init__(self, answers: Mapping[str, list[Said]]) -> None:
        self.answers = {key: iter(said) for key, said in answers.items()}
        self.asked: list[dict[str, Any]] = []
        self.commands: list[list[str]] = []

    def ask(self, command: list[str], given: str) -> tuple[int, str]:
        self.commands.append(command)
        asked = json.loads(given)
        self.asked.append(asked)
        status, body = next(self.answers[f"{asked['method']} {asked['path']}"])
        text = body if isinstance(body, str) else json.dumps(body)
        return 0, json.dumps({"status": status, "body": text})

    def calls(self) -> list[tuple[str, str]]:
        return [(asked["method"], asked["path"]) for asked in self.asked]


@dataclass(slots=True)
class FakeClock:
    """A clock that moves only when the trial pauses."""

    time: float = 0.0
    pauses: int = 0

    def now(self) -> float:
        return self.time

    def pause(self, seconds: float) -> None:
        self.pauses += 1
        self.time += seconds


def probes(*said: str) -> Iterator[str]:
    """Answer the liveness probe in turn."""
    return iter(said)


def trial_of(api: FakeApi, said: Iterator[str], clock: FakeClock | None = None) -> RestorationTrial:
    # Each sign-in opens a session of its own; the realm issues token-1, token-2, and so on.
    administrator = Administrator(Realm, Realm().send, ADDRESS, FRONT_CLIENT)
    timed = clock or FakeClock()
    return RestorationTrial(
        Api(COMPOSE, api.ask), administrator, lambda: next(said), Clock(timed.now, timed.pause)
    )


ANSWERS: dict[str, list[Said]] = {
    "POST /backups": [(202, {"task_id": "b"})],
    "GET /tasks/b": [(200, {"status": "running"}), (200, {"status": "succeeded"})],
    "GET /backups?limit=1": [(200, {"items": [BACKUP], "meta": {"total": 1}})],
    "POST /restores": [(202, {"task_id": "r"})],
    "GET /tasks/r": [
        (200, {"status": "queued"}),
        (401, {"code": "SESSION_REVOKED"}),
        (200, {"status": "succeeded"}),
    ],
}


@pytest.mark.requirement("WF-ADM-0160-A")
def test_a_backup_asked_of_the_api_is_restored_and_the_platform_comes_back_from_maintenance(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # #948, point 2: the backup asked for, waited for and listed verified; its restoration asked
    # for with its date confirmed, followed by the probe through the maintenance to ok, the
    # administrator signed in again once the restoration closed their session.
    api = FakeApi(ANSWERS)
    trial_of(api, probes("ok", "maintenance", "ok", "ok")).run()
    assert api.calls() == [
        ("POST", "/backups"),
        ("GET", "/tasks/b"),
        ("GET", "/tasks/b"),
        ("GET", "/backups?limit=1"),
        ("POST", "/restores"),
        ("GET", "/tasks/r"),
        ("GET", "/tasks/r"),
        ("GET", "/tasks/r"),
    ]
    assert api.asked[4]["body"] == {
        "backup_id": BACKUP["backup_id"],
        "confirmed": True,
        "acknowledged_backup_taken_at": BACKUP["taken_at"],
    }
    assert [asked["token"] for asked in api.asked] == [
        *["token-1"] * 5,
        "token-2",
        "token-2",
        "token-3",
    ]
    for command in api.commands:
        assert command == [*COMPOSE, "exec", "-T", "api", "python", "-c", API_CALL]
        assert not any("token" in word for word in command[:-1])
    said = capsys.readouterr().out
    assert f"listed verified: {BACKUP['backup_id']}" in said
    assert "the probe said the maintenance, then ok, the administrator back" in said


def test_a_task_that_fails_or_does_not_end_fails_the_trial() -> None:
    failed = {**ANSWERS, "GET /tasks/b": [(200, {"status": "failed", "problem": {"code": "X"}})]}
    with pytest.raises(TrialError, match=re.escape("failed: {'code': 'X'}")):
        trial_of(FakeApi(failed), probes()).run()
    endless = {**ANSWERS, "GET /tasks/b": [(200, {"status": "running"})] * 400}
    with pytest.raises(TrialError, match="did not end in 600 s"):
        trial_of(FakeApi(endless), probes()).run()
    unread = {**ANSWERS, "GET /tasks/b": [(404, {"code": "NOT_FOUND"})]}
    with pytest.raises(TrialError, match="does not read \\(404\\)"):
        trial_of(FakeApi(unread), probes()).run()


def test_a_backup_refused_or_listed_unverified_fails_the_trial() -> None:
    refused = {**ANSWERS, "POST /backups": [(403, {"code": "PERMISSION_DENIED"})]}
    with pytest.raises(TrialError, match="POST /backups answered 403, not 202"):
        trial_of(FakeApi(refused), probes()).run()
    unverified = {**BACKUP, "verification": "failed"}
    listed = {**ANSWERS, "GET /backups?limit=1": [(200, {"items": [unverified]})]}
    with pytest.raises(TrialError, match="listed unverified"):
        trial_of(FakeApi(listed), probes()).run()
    nothing: list[Any] = []
    empty = {**ANSWERS, "GET /backups?limit=1": [(200, {"items": nothing})]}
    with pytest.raises(TrialError, match="holds none"):
        trial_of(FakeApi(empty), probes()).run()


def test_a_restoration_that_fails_or_never_lifts_the_maintenance_fails_the_trial() -> None:
    failed = {**ANSWERS, "GET /tasks/r": [(200, {"status": "failed", "problem": {"code": "Y"}})]}
    with pytest.raises(TrialError, match=re.escape("failed: {'code': 'Y'}")):
        trial_of(FakeApi(failed), probes("ok")).run()
    clock = FakeClock()
    with pytest.raises(TrialError, match="the restoration did not end in 600 s"):
        trial_of(FakeApi(ANSWERS), probes(*["maintenance"] * 400), clock).run()
    # One pause for the backup still running, then one for each look in maintenance.
    assert clock.pauses == 1 + 300
    refused = {**ANSWERS, "GET /tasks/r": [(500, {"code": "INTERNAL_ERROR"})]}
    with pytest.raises(TrialError, match="does not read \\(500\\)"):
        trial_of(FakeApi(refused), probes("ok")).run()


def test_the_api_is_asked_in_its_container_and_what_it_says_is_read() -> None:
    def failing(_command: list[str], _given: str) -> tuple[int, str]:
        return 1, ""

    with pytest.raises(TrialError, match="could not be asked GET /backups \\(1\\)"):
        Api(COMPOSE, failing).call("GET", "/backups", "t")

    def garbled(_command: list[str], _given: str) -> tuple[int, str]:
        return 0, "Traceback"

    with pytest.raises(TrialError, match="does not read: 'Traceback'"):
        Api(COMPOSE, garbled).call("GET", "/backups", "t")

    def plain(_command: list[str], _given: str) -> tuple[int, str]:
        return 0, json.dumps({"status": 502, "body": "Bad gateway"})

    assert Api(COMPOSE, plain).call("GET", "/backups", "t") == (502, "Bad gateway")


def test_the_liveness_probe_says_ok_or_maintenance_and_nothing_else() -> None:
    command = [*COMPOSE, "exec", "-T", "api", "python", "-c", "probe"]
    for output, said in (('{"status": "ok"}', "ok"), ('{"status": "maintenance"}', "maintenance")):
        assert probe_of(lambda _asked, output=output: (0, output), command)() == said
    for code, output in ((0, '{"status": "down"}'), (0, "Traceback"), (1, '{"status": "ok"}')):
        with pytest.raises(TrialError, match="the liveness probe of the API says"):
            probe_of(lambda _asked, code=code, output=output: (code, output), command)()
