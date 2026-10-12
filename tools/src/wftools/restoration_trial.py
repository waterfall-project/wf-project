# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A backup, then its restoration, asked of the production platform by its API (US-0440, #948).

The trial of the production platform (``wftools.production``) holds, once its first administrator
has signed in, that:

- a backup asked for by the API (``startBackup``) is taken, and listed verified;
- a role made after it (``createAccessRole``) marks what the restoration must take away;
- its restoration asked for by the API (``startRestore``), its date confirmed, puts the platform in
  maintenance, which the liveness probe must say, and ends: the probe says ``ok`` again, the
  administrator signs in again — the restoration closed every session —, the task of the
  restoration has succeeded, and the role made after the backup is no more (404).

The API is not published: Caddy serves the front and Keycloak alone. It is asked inside its
container, at the loopback, as the front asks it, with a token of the first administrator: the
trial takes one from the realm as the front does — the code of the flow of the front, its proof
(PKCE) and the secret of its client —, on the session of Keycloak the sign-in opened. The token
goes to the container on its standard input, never on a command line.

The restoration needs the service that runs it, which US-0440/L2b brings (#953, #985); until the
chain starts it, the step is asked for by ``WATERFALL_TRIAL_RESTORATION=1``, and left out otherwise.
"""

import base64
import hashlib
import json
import secrets
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, cast
from urllib.parse import parse_qs, urlencode, urlsplit

GUARD = "WATERFALL_TRIAL_RESTORATION"
"""The variable that asks the trial for the backup and its restoration: ``1``."""
CLIENT = "waterfall-front"
REALM = "/auth/realms/waterfall/protocol/openid-connect"
OK = 200
CREATED = 201
ACCEPTED = 202
NOT_FOUND = 404
REDIRECTIONS = frozenset({301, 302, 303, 307, 308})
UNAUTHORIZED = 401
UNAVAILABLE = 503
PATIENCE = 600.0
"""How long, in seconds, a backup or a restoration may take on the platform of the trial."""
PAUSE = 2.0
MARKER = "Essai de restauration : fait après la sauvegarde"
"""The label of the role made after the backup, which its restoration takes away."""
API_CALL = """
import json, sys, urllib.error, urllib.request
asked = json.load(sys.stdin)
body = None if asked["body"] is None else json.dumps(asked["body"]).encode()
headers = {"Authorization": "Bearer " + asked["token"], "Accept": "application/json"}
if body is not None:
    headers["Content-Type"] = "application/json"
request = urllib.request.Request(
    "http://127.0.0.1:8000/api/v1" + asked["path"], body, headers, method=asked["method"]
)
try:
    with urllib.request.urlopen(request, timeout=30) as response:
        status, text = response.status, response.read().decode()
except urllib.error.HTTPError as error:
    status, text = error.code, error.read().decode()
print(json.dumps({"status": status, "body": text}))
"""
"""What the container of the API runs to ask it one operation, read on its standard input."""

Ask = Callable[[list[str], str], tuple[int, str]]
"""Run a command with what it reads on its standard input; give its code and its output."""
Read = Callable[[list[str]], tuple[int, str]]


class TrialError(Exception):
    """What the backup or the restoration of the platform does not do as it must."""


class Page(Protocol):
    """What the platform answered a request: its status, its headers, its body."""

    @property
    def status(self) -> int:
        """The status of the answer."""
        ...

    @property
    def body(self) -> str:
        """The body of the answer."""
        ...

    def header(self, name: str) -> str | None:
        """Return the first value of a header, by its name in any case."""
        ...


class Session(Protocol):
    """A browser on the platform, with the cookies of its session."""

    def request(self, method: str, url: str) -> Page:
        """Send one request, the cookies held with it."""
        ...


Post = Callable[[str, str, bytes | None, Mapping[str, str]], Page]
"""Send a request — method, address, body, headers — to the platform, without cookies."""


def wanted(environment: Mapping[str, str]) -> bool:
    """Tell whether the trial is asked for the backup and its restoration."""
    return environment.get(GUARD) == "1"


@dataclass(frozen=True, slots=True)
class Api:
    """The API of the platform, asked inside its container."""

    compose: list[str]
    ask: Ask

    def call(
        self, method: str, path: str, token: str, body: Mapping[str, Any] | None = None
    ) -> tuple[int, Any]:
        """Ask one operation; give its status and its body, read as JSON when it is."""
        command = [*self.compose, "exec", "-T", "api", "python", "-c", API_CALL]
        asked = json.dumps({"method": method, "path": path, "token": token, "body": body})
        code, output = self.ask(command, asked)
        if code != 0:
            message = f"the API could not be asked {method} {path} ({code})"
            raise TrialError(message)
        try:
            said = cast("dict[str, Any]", json.loads(output))
            status, text = int(said["status"]), str(said["body"])
        except (ValueError, KeyError, TypeError) as error:
            message = f"the API answered {method} {path} with what does not read: {output!r}"
            raise TrialError(message) from error
        try:
            return status, json.loads(text)
        except ValueError:
            return status, text


def access_token(browser: Session, send: Post, address: str, client_secret: str) -> str:
    """Take a token of the account signed in, from the realm, as the front does (code and PKCE).

    ``address`` is that of the platform, which the realm sends back to; the code is exchanged by
    ``send``, without the cookies of the browser.
    """
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
    state = secrets.token_urlsafe(16)
    callback = f"{address}/auth/callback"
    asked = {
        "client_id": CLIENT,
        "redirect_uri": callback,
        "response_type": "code",
        "scope": "openid",
        "state": state,
        "code_challenge": challenge.decode().rstrip("="),
        "code_challenge_method": "S256",
    }
    answer = browser.request("GET", f"{address}{REALM}/auth?{urlencode(asked)}")
    location = answer.header("Location") or ""
    given = parse_qs(urlsplit(location).query)
    if answer.status not in REDIRECTIONS or not location.startswith(f"{callback}?"):
        message = f"the realm gave no code to the front ({answer.status}): no session of Keycloak"
        raise TrialError(message)
    if given.get("state") != [state] or "code" not in given:
        message = "the realm sent back to the front without the code or the state it was given"
        raise TrialError(message)
    form = {
        "grant_type": "authorization_code",
        "code": given["code"][0],
        "redirect_uri": callback,
        "client_id": CLIENT,
        "client_secret": client_secret,
        "code_verifier": verifier,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    issued = send("POST", f"{address}{REALM}/token", urlencode(form).encode(), headers)
    try:
        token = cast("dict[str, Any]", json.loads(issued.body))["access_token"]
    except (ValueError, KeyError, TypeError) as error:
        message = f"the realm issued no token for the code ({issued.status})"
        raise TrialError(message) from error
    return str(token)


@dataclass(frozen=True, slots=True)
class Administrator:
    """The first administrator: how to sign them in again, and take a token of theirs."""

    signed_in: Callable[[], Session]
    send: Post
    address: str
    client_secret: str

    def token(self) -> str:
        """Sign in in a new browser, and take a token from the session it opens."""
        return access_token(self.signed_in(), self.send, self.address, self.client_secret)


@dataclass(slots=True)
class Clock:
    """The time of the trial, and its pause between two looks at a task."""

    now: Callable[[], float] = time.monotonic
    pause: Callable[[float], None] = time.sleep


def as_object(value: Any) -> dict[str, Any]:
    """Read a JSON value as an object, an empty one if it is not."""
    return cast("dict[str, Any]", value) if isinstance(value, dict) else {}


@dataclass(frozen=True, slots=True)
class Restoration:
    """What the trial needs to ask for a restoration: the API, the secret of the front, a clock."""

    ask: Ask
    client_secret: str
    clock: Clock = field(default_factory=Clock)


@dataclass(frozen=True, slots=True)
class RestorationTrial:
    """The backup and its restoration, asked of the API by the first administrator."""

    api: Api
    administrator: Administrator
    probe: Callable[[], str]
    clock: Clock

    def run(self) -> None:
        """Back up by the API, restore what was backed up, and hold that the platform came back."""
        token = self.administrator.token()
        backing_up = self.accepted("/backups", token)
        self.ended(token, backing_up)
        backup = self.latest_backup(token)
        print(f"  a backup asked of the API is taken and listed verified: {backup['backup_id']}")
        marker = self.marked(token)
        confirmed = {
            "backup_id": backup["backup_id"],
            "confirmed": True,
            "acknowledged_backup_taken_at": backup["taken_at"],
        }
        restoring = self.accepted("/restores", token, confirmed)
        self.forgotten(self.restored(restoring), marker)
        print(
            "  its restoration asked of the API has ended: the probe said the maintenance, then ok,"
            " the administrator back, the role made after the backup gone"
        )

    def marked(self, token: str) -> str:
        """Make a role after the backup, which its restoration must take away; give its id."""
        made: dict[str, Any] = {"label": MARKER, "permissions": []}
        status, role = self.api.call("POST", "/access-roles", token, made)
        if status != CREATED or "access_role_id" not in as_object(role):
            message = f"POST /access-roles answered {status}, not {CREATED}: {role!r}"
            raise TrialError(message)
        return str(as_object(role)["access_role_id"])

    def forgotten(self, token: str, marker: str) -> None:
        """Hold that the role made after the backup is no more once it is restored (404)."""
        status, role = self.api.call("GET", f"/access-roles/{marker}", token)
        if status != NOT_FOUND:
            message = (
                f"the role {marker} made after the backup reads after its restoration "
                f"({status}), not {NOT_FOUND}: {role!r}"
            )
            raise TrialError(message)

    def accepted(self, path: str, token: str, body: Mapping[str, Any] | None = None) -> str:
        """Ask for a task; give its identifier, or fail if it is not accepted (202)."""
        status, task = self.api.call("POST", path, token, body)
        if status != ACCEPTED or "task_id" not in as_object(task):
            message = f"POST {path} answered {status}, not {ACCEPTED}: {task!r}"
            raise TrialError(message)
        return str(as_object(task)["task_id"])

    def ended(self, token: str, task_id: str) -> None:
        """Wait for a task to succeed; fail when it fails, or outlasts the patience."""
        deadline = self.clock.now() + PATIENCE
        while self.clock.now() < deadline:
            status, task = self.api.call("GET", f"/tasks/{task_id}", token)
            if status != OK:
                message = f"the task {task_id} does not read ({status}): {task!r}"
                raise TrialError(message)
            if self.finished(as_object(task)):
                return
            self.clock.pause(PAUSE)
        message = f"the task {task_id} did not end in {PATIENCE:.0f} s"
        raise TrialError(message)

    @staticmethod
    def finished(task: Mapping[str, Any]) -> bool:
        """Tell whether a task has succeeded; fail if it has failed."""
        if task.get("status") == "failed":
            message = f"the task {task.get('task_id')} failed: {task.get('problem')!r}"
            raise TrialError(message)
        return task.get("status") == "succeeded"

    def latest_backup(self, token: str) -> dict[str, Any]:
        """Read the latest backup of the list; fail unless its verification passed."""
        status, page = self.api.call("GET", "/backups?limit=1", token)
        items = as_object(page).get("items") if status == OK else None
        if not isinstance(items, list) or not items:
            message = f"the list of the backups holds none ({status}): {page!r}"
            raise TrialError(message)
        backup = as_object(cast("list[Any]", items)[0])
        if backup.get("verification") != "passed":
            message = f"the backup {backup.get('backup_id')} is listed unverified"
            raise TrialError(message)
        return backup

    def restored(self, task_id: str) -> str:
        """Follow a restoration to its end, through the maintenance; give a token taken after it.

        The probe must say the maintenance, in which the API answers 503; until it does, the
        restoration has not begun. The restoration closes every session before it lifts the
        maintenance: the administrator signs in again at the first ``ok`` after it, and again,
        after a pause, if the token is refused (401). It has ended when its task has succeeded.
        """
        seen = False
        token: str | None = None
        deadline = self.clock.now() + PATIENCE
        while self.clock.now() < deadline:
            if self.probe() == "maintenance":
                seen = True
            elif seen:
                token = token or self.administrator.token()
                status, task = self.api.call("GET", f"/tasks/{task_id}", token)
                if status == UNAUTHORIZED:
                    token = None
                elif status == OK and self.finished(as_object(task)):
                    return token
                elif status not in {OK, UNAVAILABLE}:
                    message = f"the task of the restoration does not read ({status}): {task!r}"
                    raise TrialError(message)
            self.clock.pause(PAUSE)
        if not seen:
            message = f"the liveness probe did not say the maintenance in {PATIENCE:.0f} s"
            raise TrialError(message)
        message = f"the restoration did not end in {PATIENCE:.0f} s"
        raise TrialError(message)


def probe_of(read: Read, command: list[str]) -> Callable[[], str]:
    """Make the look at the liveness probe of the API, by its command: ``ok`` or ``maintenance``."""

    def probe() -> str:
        code, output = read(command)
        said = as_object(_json(output)).get("status") if code == 0 else None
        if said not in {"ok", "maintenance"}:
            message = f"the liveness probe of the API says {output.strip()!r} ({code})"
            raise TrialError(message)
        return str(said)

    return probe


def _json(text: str) -> Any:
    try:
        return json.loads(text)
    except ValueError:
        return None
