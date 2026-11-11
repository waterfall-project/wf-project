# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A format of the tests, which tries the whole mechanics of the imports before any real format.

Its file is a head, ``WF-TRIAL``, then one label of a task per line, which its preparation reads.
Its analysis reports each line as a task added, and a line that reads ``REFUSE`` rejects the whole
file; its application writes each task, at the root of the structure aimed at, after the tasks
there. What it does besides — a condition of its kind refused, an analysis or an application that
refuses, breaks, or is stopped — a test asks of it by its attributes (#1790, EP-06, "Les tests du
back"). It stands in for the format a module registered for a kind (``stand_in``). And what the
tests of the imports share: the platform, its client, its worker, the deposit and the opening of a
file.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, get_protocol_members
from uuid import UUID

from planning_support import insert_task
from sqlalchemy import delete, func, select

from waterfall.core.access_roles.tables import AccessRolePermission, Permission, UserAccessRole
from waterfall.core.exchanges.interface import Format, formats
from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.planning.tables import Node
from waterfall.platform.errors import ConflictError, UnprocessableError
from waterfall.worker.exchanges import ImportTasks
from waterfall.worker.marking import mark
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from collections.abc import Mapping

    import pytest
    from projects_support import Person, Scene
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.core.exchanges.interface import ExchangeKind, ImportScope, ImportTarget
    from waterfall.platform.audit import Act
    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.storage import Bucket

HEAD = b"WF-TRIAL\n"
AT_ONCE = Timing(claim_after=0, block=0.01, redeposit_every=0)
ROWS = ("Câblage", "Essais")
STATE = "STATE_FORBIDS_OPERATION"
UNREADABLE = "FILE_FORMAT_UNREADABLE"
UPLOADS = "/api/v1/file-uploads"
PROJECTS = "/api/v1/projects"


class Stopped(BaseException):
    """A worker stopped during a task, as ``SIGTERM`` stops it: nothing of the task is kept."""


@dataclass
class TrialFormat:
    """The format of the tests, as the exchanges ask a format (``Format``).

    ``condition`` a condition of the kind the import lacks (409); ``analysis`` and ``application``
    what their step does besides: ``None``, nothing; ``refuse``, a refusal; ``break``, an error;
    ``stop``, the worker stopped once its writes are done (``application`` alone). ``preparation``
    ``refuse`` refuses the file as unreadable (422), ``break`` breaks on it (``ValueError``).
    """

    scope: ImportScope = "structure"
    permission: str = "remaining.write"
    header_length: int = len(HEAD)
    judged_first: bool = False
    condition: str | None = None
    analysis: str | None = None
    preparation: str | None = None
    application: str | None = None
    seen: list[ImportTarget] = field(default_factory=list[Any])

    def read_header(self, session: Session, head: bytes) -> None:
        """Refuse a head that is not the trial's, naming the format and the version expected."""
        del session
        if head != HEAD:
            expected = {"expected_format": "remaining", "expected_version": "1"}
            raise UnprocessableError(UNREADABLE, expected)

    def judge(self, session: Session, target: ImportTarget) -> None:
        """Refuse an import whose kind lacks the condition the test names."""
        del session
        self.seen.append(target)
        if self.condition is not None:
            raise ConflictError(STATE, {"missing_condition": self.condition})

    def analyse(self, session: Session, target: ImportTarget, content: bytes) -> Mapping[str, Any]:
        """Report each line as a task added; ``REFUSE`` rejects the whole file."""
        del session, target
        self._besides(self.analysis)
        labels = labels_of(content)
        horizon: dict[str, Any] = {"code": "PROJECT_HORIZON_EXCEEDED", "params": {}}
        refusals = [horizon] if "REFUSE" in labels else []
        return {
            "format_version": "1",
            "read_count": len(labels),
            "unchanged_count": 0,
            "rejected": [
                {"sheet": None, "row": 2, "code": "UNKNOWN_TASK", "params": {"value": "Inconnue"}}
            ],
            "refusals": refusals,
            "differences": [
                {
                    "change": "added",
                    "target": "task",
                    "lineage_id": None,
                    "label": label,
                    "fields": [],
                }
                for label in labels
            ],
            "ignored": [],
            "completed_tasks": [],
            "date_mismatches": [],
            "signals": [],
            "requires_confirmation_reasons": [],
            "unit_constants": None,
        }

    def prepare(self, content: bytes) -> list[str]:
        """Read the labels of a trial file, before the application takes any lock."""
        if self.preparation == "refuse":
            expected = {"expected_format": "remaining", "expected_version": "1"}
            raise UnprocessableError(UNREADABLE, expected)
        if self.preparation == "break":
            msg = "the preparation breaks"
            raise ValueError(msg)
        return labels_of(content)

    def apply(
        self,
        session: Session,
        target: ImportTarget,
        prepared: list[str],
        report: Mapping[str, Any],
        act: Act,
    ) -> None:
        """Write each task the report adds at the root of the structure, then do what is asked."""
        del act
        if self.scope == "project":
            # An import of the project writes no node: what it was given is on ``seen``.
            self._besides(self.application)
            return
        assert target.revision_id is not None
        assert target.structure_id is not None
        connection = session.connection()
        rank = connection.scalar(
            select(func.count()).where(
                Node.structure_id == target.structure_id, Node.parent_id.is_(None)
            )
        )
        for offset, difference in enumerate(report["differences"], start=(rank or 0) + 1):
            insert_task(
                connection,
                target.project_id,
                target.revision_id,
                target.structure_id,
                rank=offset,
                label=difference["label"],
            )
        assert prepared
        self._besides(self.application)

    @staticmethod
    def _besides(what: str | None) -> None:
        if what == "refuse":
            raise ConflictError(STATE, {"missing_condition": "task_not_started"})
        if what == "break":
            msg = "the format broke"
            raise RuntimeError(msg)
        if what == "stop":
            raise Stopped


# What the exchanges read of a format, which the format of the tests stands in for: every member of
# the protocol, so that one added to ``Format`` leaves no part of the real format acting.
FORMAT_PARTS = tuple(sorted(get_protocol_members(Format)))


def stand_in[Trial: TrialFormat](
    monkeypatch: pytest.MonkeyPatch, kind: ExchangeKind, form: Trial
) -> Trial:
    """Make the format a module registered for a kind act as ``form`` for the test; give ``form``.

    Every kind has its format from the socle of EP-09 on (US-1580/L1), and a kind holds one at most:
    the format of the tests takes the place of the one registered — what the exchanges read of it —,
    the end of the test giving it back, as ``test_exports.py`` stands in for an exporter.
    """
    held = formats()[kind]
    for part in FORMAT_PARTS:
        monkeypatch.setattr(held, part, getattr(form, part))
    return form


def labels_of(content: bytes) -> list[str]:
    """Read the labels of a trial file, its head apart."""
    return [line for line in content.removeprefix(HEAD).decode().splitlines() if line]


def trial_file(*labels: str) -> bytes:
    """Write a trial file of the labels given."""
    return HEAD + "".join(f"{label}\n" for label in labels).encode()


def upload(
    api: ContractClient,
    who: Person,
    content: bytes,
    *,
    filename: str = "planning-essai.wft",
    purpose: str = "import",
) -> Any:
    """Deposit a file for an import as ``who`` does; give the answer."""
    return api.post(
        UPLOADS,
        headers=who.headers,
        files={"file": (filename, content, "application/octet-stream")},
        data={"purpose": purpose},
    )


def deposited(api: ContractClient, who: Person, content: bytes) -> str:
    """Deposit a file for an import as ``who`` does; give its deposit."""
    response = upload(api, who, content)
    assert response.status_code == 201, response.text
    return response.json()["upload_id"]


def open_import(
    api: ContractClient, who: Person, project_id: str, upload_id: str, **body: Any
) -> Any:
    """Open an import of a deposit as ``who`` does; give the answer."""
    return api.post(
        f"{PROJECTS}/{project_id}/imports",
        headers=who.headers,
        json={"kind": "remaining", "upload_id": upload_id, **body},
    )


def nodes(database: Database) -> list[tuple[UUID, UUID, str]]:
    """Read every node of the platform: its revision, its structure and its kind."""
    with database.transaction() as session:
        return sorted(
            (row[0], row[1], row[2])
            for row in session.execute(select(Node.revision_id, Node.structure_id, Node.kind))
        )


def withdraw(database: Database, who: Person, permission: str) -> None:
    """Withdraw a permission from every role an account holds, around the service."""
    with database.transaction() as session:
        roles = select(UserAccessRole.access_role_id).where(
            UserAccessRole.user_account_id == who.user_id
        )
        granted = select(Permission.id).where(Permission.code == permission)
        session.execute(
            delete(AccessRolePermission).where(
                AccessRolePermission.access_role_id.in_(roles),
                AccessRolePermission.permission_id.in_(granted),
            )
        )


def import_worker(database: Database, queue: TaskQueue, bucket: Bucket) -> Worker:
    """Give a worker on the queue of a test: the imports, by the platform's handlers, and marks."""
    queue.prepare()
    tasks = ImportTasks(bucket)
    handlers = {
        "import_analysis": tasks.analyse,
        "import_apply": tasks.apply,
        "revision_mark": mark,
    }
    return Worker(database, queue, handlers, "worker", AT_ONCE)


def run(worker: Worker) -> None:
    """Run every task deposited until the queue is empty."""
    while worker.step():
        pass


def path(stage: Scene, import_id: str = "") -> str:
    """Give the address of the imports of the project of the stage, or of one of them."""
    base = f"{PROJECTS}/{stage.project['project_id']}/imports"
    return f"{base}/{import_id}" if import_id else base


def read(api: ContractClient, stage: Scene, import_id: str) -> dict[str, Any]:
    """Read an import as its manager does."""
    response = api.get(path(stage, import_id), headers=stage.manager.headers)
    assert response.status_code == 200, response.text
    return response.json()


def opened(api: ContractClient, stage: Scene, *labels: str, **body: Any) -> dict[str, Any]:
    """Deposit a trial file and open its import as the manager does; give the import."""
    upload_id = deposited(api, stage.manager, trial_file(*labels))
    response = open_import(api, stage.manager, stage.project["project_id"], upload_id, **body)
    assert response.status_code == 202, response.text
    return response.json()


def analysed(api: ContractClient, stage: Scene, worker: Worker, *labels: str) -> dict[str, Any]:
    """Open an import of a trial file and run its analysis; give the import analysed."""
    import_id = opened(api, stage, *(labels or ROWS))["import_id"]
    run(worker)
    found = read(api, stage, import_id)
    assert found["status"] == "analysed", found
    return found


def apply(api: ContractClient, stage: Scene, import_id: str, who: Any = None) -> Any:
    """Confirm the application of an import; give the answer."""
    headers = (who or stage.manager).headers
    return api.post(f"{path(stage, import_id)}/apply", headers=headers, json={"confirmed": True})


def stored(database: Database, import_id: str) -> ImportReport:
    """Read the row of an import as the database keeps it."""
    with database.transaction() as session:
        row = session.get_one(ImportReport, UUID(import_id))
        session.expunge(row)
        return row


def refusal(response: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("params", {})


def commands(found: dict[str, Any]) -> dict[str, list[str]]:
    """Give the conditions each command of an import lacks, by command."""
    return {each["command"]: each["missing_conditions"] for each in found["available_commands"]}
