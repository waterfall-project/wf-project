# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the trial of the chart holds of services that keep no state (US-2820, WF-ARC-0080-A).

On a chart of three instances of the API and two of the worker, it holds that:

- the same user, with the same token and no session of an instance, is answered the same by each
  instance of the API: what one wrote, the others read, without signing in again. Each instance is
  asked inside its own pod, so that which one served is not left to the Service;
- a worker killed in the middle of a marking — held there by a lock of the table of the revisions,
  taken by the administrator of the server — leaves the database as it was, and the other worker
  claims the entry the killed one left unacknowledged (``XAUTOCLAIM``, after its delay) and runs
  the task again from its start: the revision is marked, the task attempted twice.

What no service reads of what it wrote on its own disk is held by a test of the back
(``backend/tests/test_stateless_files.py``), which needs no cluster.
"""

import json
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, cast
from uuid import UUID

from wftools.production import ProductionError
from wftools.restoration_trial import ACCEPTED, CREATED, OK, Api, Ask, Clock, as_object

RELEASE = "waterfall"
STREAM = "waterfall:tasks"
GROUP = "workers"
PATIENCE = 300.0
"""How long, in seconds, the other worker may take to claim the entry the killed one left: the
delay of its claim is thirty seconds."""
PAUSE = 1.0
LEAST_INSTANCES = 2
"""The fewest instances of the API, or of the worker, the trial is held on."""
SETTLED = "draft|t|t"
"""A revision unmarked and current, as ``HELD_REVISION`` reads it: its status, whether its moment of
marking is absent, whether its project still has it as its current revision."""
LOCK = "BEGIN; LOCK TABLE revision IN SHARE ROW EXCLUSIVE MODE; SELECT pg_sleep(900);"
"""What holds up every write of the table of the revisions and no read: the marking blocks at its
first write of a revision, having read, and written elsewhere, before."""
WHERE_LOCKED = (
    "FROM pg_locks l JOIN pg_class c ON c.oid = l.relation "
    "WHERE c.relname = 'revision' AND l.mode = 'ShareRowExclusiveLock' AND l.granted"
)
LOCK_HELD = f"SELECT count(*) {WHERE_LOCKED}"
LOCK_RELEASED = f"SELECT count(pg_terminate_backend(l.pid)) {WHERE_LOCKED}"
WHERE_WAITING = (
    "FROM pg_stat_activity WHERE datname = 'waterfall' "
    "AND wait_event_type = 'Lock' AND usename <> 'postgres'"
)
WAITING = f"SELECT count(*) {WHERE_WAITING}"
WAITING_ENDED = f"SELECT count(pg_terminate_backend(pid)) {WHERE_WAITING}"
HELD_REVISION = (
    "SELECT r.status, r.marked_at IS NULL, p.current_revision_id = r.id "
    "FROM revision r JOIN project p ON p.id = r.project_id WHERE r.id = :id"
)
TASK = "SELECT status, attempts FROM background_task WHERE id = :id"

PERMISSIONS = (
    {"project_create", "revision_mark"},
    {"cost_settings.write", "resource_settings.write"},
)
"""What the roles the first administrator is given hold, between them."""

Start = Callable[[list[str]], Callable[[], None]]
"""Start a command that runs until it is stopped; give what stops it."""
Read = Callable[[list[str]], tuple[int, str]]


def pending_consumers(output: str) -> dict[str, str]:
    """Read ``XPENDING`` as ``redis-cli --raw`` writes it: an entry to its consumer.

    Four lines an entry: its identifier, its consumer, how long it has been idle, and how many
    times it was delivered.
    """
    lines = [line for line in output.splitlines() if line.strip()]
    return {lines[index]: lines[index + 1] for index in range(0, len(lines) - 3, 4)}


def check_same_answers(answers: Mapping[str, tuple[int, Any]], project_id: str) -> None:
    """Hold that every instance answered, and answered the same, the project one wrote."""
    if len(answers) < LEAST_INSTANCES:
        message = f"{len(answers)} instance of the API answered: two at least are asked"
        raise ProductionError(message)
    for pod, (status, body) in answers.items():
        if status != OK:
            message = f"the instance {pod} answered {status}: {body!r}"
            raise ProductionError(message)
        if as_object(body).get("project_id") != project_id:
            said = json.dumps(body)[:300]
            message = f"the instance {pod} does not read the project another instance made: {said}"
            raise ProductionError(message)
    first = next(iter(answers))
    for pod, answer in answers.items():
        if answer != answers[first]:
            message = f"the instance {pod} answered otherwise than {first}"
            raise ProductionError(message)


def check_unchanged(row: str) -> None:
    """Hold that the revision is still current, a draft, unmarked."""
    if row.strip() != SETTLED:
        message = f"the worker killed in a marking changed the database: {row.strip()!r}"
        raise ProductionError(message)


def check_attempted_once(row: str) -> None:
    """Hold that a task, as psql writes ``status|attempts``, was attempted once and not ended."""
    status, _, made = row.strip().partition("|")
    if made != "1" or status in {"succeeded", "failed"}:
        message = f"the task is {row.strip()!r} after its worker was killed: one attempt, not ended"
        raise ProductionError(message)


def found(body: Any, key: str, having: Mapping[str, Any] | None = None) -> str:
    """Find the first ``key`` of an object, anywhere in a body, that has all of ``having``.

    The body lists or nests objects; fail when none has it.
    """
    wanted = having or {}
    pending = [body]
    while pending:
        item = pending.pop(0)
        if isinstance(item, dict):
            node = cast("dict[str, Any]", item)
            if key in node and all(node.get(name) == value for name, value in wanted.items()):
                return str(node[key])
            pending.extend(node.values())
        elif isinstance(item, list):
            pending.extend(cast("list[Any]", item))
    message = f"no {key} in what the platform listed, among {sorted(wanted)}"
    raise ProductionError(message)


def asked(query: str, identifier: str) -> str:
    """Give a query with its ``:id`` replaced by a UUID the platform made, checked to be one."""
    return query.replace(":id", f"'{UUID(identifier)}'")


@dataclass(slots=True)
class Stateless:
    """The platform of the trial, asked in its pods: kubectl on its namespace, what runs there."""

    kubectl: list[str]
    read: Read
    ask: Ask
    start: Start
    clock: Clock = field(default_factory=Clock)

    def output(self, command: list[str], what: str) -> str:
        """Run a command that must succeed and give what it wrote."""
        code, output = self.read(command)
        if code != 0:
            message = f"{what} failed ({code})"
            raise ProductionError(message)
        return output

    def pods(self, component: str) -> list[str]:
        """Give the pods of a component, as ``pod/<name>``, sorted."""
        selector = f"app.kubernetes.io/instance={RELEASE},app.kubernetes.io/component={component}"
        listed = self.output(
            [*self.kubectl, "get", "pods", "--selector", selector, "--output", "name"],
            f"list the pods of the {component}",
        )
        return sorted(listed.split())

    def api_on(self, pod: str) -> Api:
        """Return the API of one instance, asked inside its pod."""
        return Api(self.kubectl, self.ask, ("exec", "-i", pod, "--"))

    def psql(self) -> list[str]:
        """Return psql on the database of the platform, as the administrator of the server."""
        return [
            *self.kubectl,
            "exec",
            f"statefulset/{RELEASE}-postgres",
            "--",
            "psql",
            "--username=postgres",
            "--dbname=waterfall",
            "--no-psqlrc",
            "--tuples-only",
            "--no-align",
            "--set=ON_ERROR_STOP=1",
        ]

    def sql(self, query: str, what: str) -> str:
        """Run a query as the administrator of the server and give its rows."""
        return self.output([*self.psql(), f"--command={query}"], what).strip()

    def expect(self, api: Api, call: tuple[str, str, str], status: int, body: Any = None) -> Any:
        """Ask one operation (method, path, token) that must answer ``status``; give its body."""
        method, path, token = call
        got, answered = api.call(method, path, token, body)
        if got != status:
            message = f"{method} {path} answered {got}, not {status}: {answered!r}"
            raise ProductionError(message)
        return answered

    def give_the_roles(self, api: Api, token: str) -> None:
        """Give the first administrator the roles that make and mark projects, besides their own.

        The administrator of the platform holds no permission of the trade: a role that creates
        and marks projects (``project_create``, ``revision_mark``), and one that writes the
        reference (``cost_settings.write``, ``resource_settings.write``), as the predefined roles
        have. The change applies at once, with no sign-in again (WF-ADM-0090).
        """
        me = as_object(self.expect(api, ("GET", "/me", token), OK))
        # The list of the roles is the whole list, a bare array: the contract paginates none.
        roles = cast("list[Any]", self.expect(api, ("GET", "/access-roles", token), OK))
        given = cast("list[str]", me["access_role_ids"])
        for wanted in PERMISSIONS:
            found = [
                str(as_object(role)["access_role_id"])
                for role in roles
                if wanted <= set(cast("list[str]", as_object(role).get("permissions", [])))
            ]
            if not found:
                message = f"no role of the platform holds {sorted(wanted)}"
                raise ProductionError(message)
            given = [*given, found[0]]
        body = {"access_role_ids": list(dict.fromkeys(given)), "lock_version": me["lock_version"]}
        self.expect(api, ("PUT", f"/users/{me['user_id']}/access-roles", token), OK, body)

    def make_the_reference(self, api: Api, token: str) -> None:
        """Make a labour category and a role of the reference, as a project needs (WF-CYC-0120)."""
        types = self.expect(api, ("GET", "/reference/cost-types", token), OK)
        try:
            labour = found(types, "cost_type_id", {"kind": "labor", "is_active": True})
        except ProductionError:
            # A new installation holds only the cost type of the risk provision.
            kind = {"code": "ESS", "label": "Essai sans état", "kind": "labor"}
            made = self.expect(api, ("POST", "/reference/cost-types", token), CREATED, kind)
            labour = str(as_object(made)["cost_type_id"])
        category = {
            "code": "ESS",
            "label": "Essai sans état",
            "cost_type_id": labour,
            "accounting_code": "ESS",
        }
        path = "/reference/cost-categories"
        made = self.expect(api, ("POST", path, token), CREATED, category)
        nodes = self.expect(api, ("GET", "/reference/org-nodes", token), OK)
        try:
            node = found(nodes, "org_node_id", {"is_active": True})
        except ProductionError:
            # A new installation holds no department.
            root = {"code": "ESS", "label": "Essai sans état"}
            made_node = self.expect(api, ("POST", "/reference/org-nodes", token), CREATED, root)
            node = str(as_object(made_node)["org_node_id"])
        calendars = self.expect(api, ("GET", "/reference/calendars", token), OK)
        role = {
            "code": "ESS",
            "label": "Essai sans état",
            "org_node_id": node,
            "cost_category_id": as_object(made)["cost_category_id"],
            "calendar_id": found(calendars, "calendar_id", {"is_active": True}),
            "capacity": {"headcount": "1"},
        }
        self.expect(api, ("POST", "/reference/resource-roles", token), CREATED, role)

    def hold_the_same_answer(self, token: str) -> tuple[str, str]:
        """Hold that each instance of the API answers the same to the same token.

        A project is made by the first, and read by every instance. Give its identifier and the
        revision opened in it, for the marking.
        """
        pods = self.pods("api")
        first = self.api_on(pods[0])
        self.give_the_roles(first, token)
        self.make_the_reference(first, token)
        label = {"label": "Essai sans état"}
        made = self.expect(first, ("POST", "/projects", token), CREATED, label)
        project_id = str(as_object(made)["project_id"])
        path = f"/projects/{project_id}/revisions"
        opened = self.expect(first, ("POST", path, token), CREATED, {})
        answers = {
            pod: self.api_on(pod).call("GET", f"/projects/{project_id}", token) for pod in pods
        }
        check_same_answers(answers, project_id)
        print(
            f"  {len(pods)} instances of the API, asked one by one with one token, answer the "
            "same: each reads the project the first made",
            flush=True,
        )
        return project_id, str(as_object(opened)["revision_id"])

    def entry_held(self) -> str:
        """Wait until a worker holds an entry the lock keeps from ending; give its consumer."""
        redis = [*self.kubectl, "exec", f"deployment/{RELEASE}-redis", "--", "redis-cli", "--raw"]
        deadline = self.clock.now() + PATIENCE
        while self.clock.now() < deadline:
            waiting = self.sql(WAITING, "look for a worker held up by the lock")
            command = [*redis, "XPENDING", STREAM, GROUP, "-", "+", "10"]
            consumers = pending_consumers(self.output(command, "read the pending entries"))
            if waiting != "0" and len(consumers) == 1:
                return next(iter(consumers.values()))
            self.clock.pause(PAUSE)
        message = "no worker is held in a marking by the lock of the revisions"
        raise ProductionError(message)

    def hold_the_task_taken_again(self, token: str, project_id: str, revision_id: str) -> None:
        """Kill a worker in the middle of a marking, and hold that the other one marks.

        The lock keeps the marking from its first write of a revision. The worker is killed with no
        warning (a pod removed with no grace), the sessions it leaves are ended, and the database
        read while the lock is still held; then the lock is released, and the other worker, which
        claims the entry, marks.
        """
        api = self.api_on(self.pods("api")[0])
        stop = self.start([*self.psql(), f"--command={LOCK}"])
        try:
            self.locked()
            path = f"/projects/{project_id}/revisions/{revision_id}"
            read = self.expect(api, ("GET", path, token), OK)
            lock_version = as_object(read)["lock_version"]
            body = {"version_name": "v1.0", "lock_version": lock_version}
            marking = self.expect(api, ("POST", f"{path}/mark", token), ACCEPTED, body)
            task_id = str(as_object(marking)["task_id"])
            worker = self.entry_held()
            if f"pod/{worker}" not in self.pods("worker"):
                message = f"the entry is held by {worker}, which is no worker of the platform"
                raise ProductionError(message)
            self.output(
                [*self.kubectl, "delete", f"pod/{worker}", "--grace-period=0", "--force"],
                f"kill the worker {worker}",
            )
            self.sql(WAITING_ENDED, "end the sessions of the worker killed")
            check_unchanged(self.sql(asked(HELD_REVISION, revision_id), "read the revision"))
            check_attempted_once(self.sql(asked(TASK, task_id), "read the task"))
            print(
                f"  the worker {worker} killed in the middle of a marking leaves the revision a "
                "draft, still the current one: the database is as it was",
                flush=True,
            )
        finally:
            self.sql(LOCK_RELEASED, "release the lock of the revisions")
            stop()
        self.marked_by_another(task_id, worker, revision_id)

    def locked(self) -> None:
        """Wait until the lock of the revisions is held."""
        deadline = self.clock.now() + PATIENCE
        while self.clock.now() < deadline:
            if self.sql(LOCK_HELD, "look for the lock of the revisions") == "1":
                return
            self.clock.pause(PAUSE)
        message = "the lock of the table of the revisions was not taken"
        raise ProductionError(message)

    def marked_by_another(self, task_id: str, killed: str, revision_id: str) -> None:
        """Wait for the task to succeed on its second attempt, and for the revision to be marked."""
        deadline = self.clock.now() + PATIENCE
        row = ""
        while self.clock.now() < deadline:
            row = self.sql(asked(TASK, task_id), "read the task")
            if row.startswith(("succeeded", "failed")):
                break
            self.clock.pause(PAUSE)
        if row != "succeeded|2":
            message = f"the task of the worker {killed}, killed, is {row!r}, not 'succeeded|2'"
            raise ProductionError(message)
        marked = self.sql(asked(HELD_REVISION, revision_id), "read the revision")
        if not marked.startswith("marked|f"):
            message = f"the revision is {marked!r} after the task succeeded: not marked"
            raise ProductionError(message)
        print(
            f"  the task was run again from its start and succeeded, by another worker than "
            f"{killed}: attempted twice, the revision marked",
            flush=True,
        )

    def hold(self, token: str) -> None:
        """Hold both: the same answers of every instance of the API, then the worker killed."""
        project_id, revision_id = self.hold_the_same_answer(token)
        if len(self.pods("worker")) < LEAST_INSTANCES:
            message = "the worker has fewer than two instances: none to take the task again"
            raise ProductionError(message)
        self.hold_the_task_taken_again(token, project_id, revision_id)


def started(command: list[str]) -> Callable[[], None]:
    """Start a command in the background; give what stops it and waits for it."""
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

    def stop() -> None:
        process.terminate()
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    return stop
