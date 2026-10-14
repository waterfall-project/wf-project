# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The task ``restore``: both databases replaced whole by a backup, nothing partial (WF-ADM-0160).

The archive is read from the bucket of the backups, its manifest read and each dump checked against
its digest; one of a newer version than the installation, or one that does not read back whole, is
refused before anything changes (``waterfall.worker.restore``). Then, in this order (#981):

1. the platform is held in maintenance, and every session closed, of the identity provider and of
   the front; the runs of the tasks the worker started before are waited for;
2. what the restoration keeps — the journal of audit, the backups, a few tasks, the rights of the
   role of the service — is copied aside, once (``keep_for_restoration``);
3. the token of the client of the bootstrap is taken, and each database made again from its dump,
   as its owner (#701); the migrations that follow the backup are applied;
4. what was kept is written back, the tasks restored pending fail, and the accounts anonymised since
   the backup are anonymised again (``write_back_after_restoration``, #892, #893, #894, #987, #988);
5. the caches of Keycloak are cleared, which the maintenance keeps first, and its realm, that of
   the installation, applied again over the database restored (#954, #955, #991); the local
   accounts anonymised again leave it;
6. every session is closed again, and the restoration inscribed in the journal, the last of its
   inscriptions; what runs it ends the task, then lifts the maintenance.

Taken up after an interruption, it starts again from the beginning, the maintenance held
(WF-ARC-0090): what it reads of the task and of who asked for it, the maintenance keeps. So does it
keep that the caches of Keycloak were asked cleared: Keycloak may then serve the realm of the
backup, whose secrets refuse the service account and the client of the bootstrap, and the attempt
taken up first has the realm of the installation applied again, which gives them theirs back. If
that fails, the log says what the operator does — restart ``keycloak``, then ``keycloak-realm``,
which applies the realm of the installation at its start — and the attempt goes on.
"""

import dataclasses
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import Engine, inspect, select
from sqlalchemy.orm import Session

from waterfall.core.backups.interface import (
    NOT_FOUND,
    inscribe_restoration,
    keep_for_restoration,
    write_back_after_restoration,
)
from waterfall.core.users.interface import inscribed_actor
from waterfall.platform.audit import AuditActor
from waterfall.platform.database import create_database_engine, utc_now
from waterfall.platform.errors import NotFoundError
from waterfall.platform.logs import get_logger
from waterfall.platform.maintenance import Maintenance, Restoring
from waterfall.platform.storage import Bucket, MissingObjectError
from waterfall.platform.tasks import PENDING, BackgroundTask, Task
from waterfall.restore.provider import IdentityProvider, RealmNotAppliedError
from waterfall.worker.backup import DATABASES
from waterfall.worker.restore import extracted, replace
from waterfall.worker.runner import await_run

# What the operator does when the realm of the installation cannot be applied again.
GIVE_THE_REALM_BACK = "restart keycloak, then keycloak-realm"

logger = get_logger(__name__)


class RestoreTask:
    """Restore a backup of the two databases, as the service runs a task of the kind ``restore``."""

    def __init__(
        self,
        databases: Mapping[str, str],
        bucket: Bucket,
        maintenance: Maintenance,
        provider: IdentityProvider,
        migrate: Callable[[Engine], None],
    ) -> None:
        """Restore into ``databases``, as their owners, from ``bucket``.

        ``migrate`` brings the database of Waterfall to the revision of the installation.
        """
        self.databases = databases
        self.bucket = bucket
        self.maintenance = maintenance
        self.provider = provider
        self.migrate = migrate

    def __call__(self, session: Session, task: Task) -> dict[str, Any]:
        """Read the archive, hold the maintenance, keep, replace, migrate, write back, renew.

        ``session`` is the transaction that ends the task: it inscribes the restoration, once all is
        done. It holds no lock on a table while the databases are replaced, which would hold up
        the replacement.
        """
        backup_id = UUID(task.payload["backup_id"])
        with tempfile.TemporaryDirectory(prefix="waterfall-restore-") as work:
            folder = Path(work)
            archive = folder / "restored.tar"
            try:
                self.bucket.download(task.payload["object_key"], archive)
            except MissingObjectError:
                raise NotFoundError(NOT_FOUND) from None
            dumps = extracted(archive, folder)
            owner = create_database_engine(self.databases["waterfall"])
            try:
                taken_up = self.taken_up(task)
                actor = self.requester(owner, task, taken_up)
                held = self.hold(task, actor, taken_up)
                if taken_up is not None and taken_up.caches_cleared:
                    self.give_the_realm_back(task)
                self.close_sessions()
                await_runs(owner, task.task_id)
                with owner.begin() as kept:
                    keep_for_restoration(kept, task.task_id)
                self.provider.prepare()
                for name in DATABASES:
                    replace(name, dumps[name], self.databases[name], folder)
                self.migrate(owner)
                with owner.begin() as written:
                    subjects = write_back_after_restoration(written, task.task_id, utc_now())
            finally:
                owner.dispose()
        self.maintenance.hold(dataclasses.replace(held, caches_cleared=True))
        self.provider.clear_caches()
        self.provider.apply_realm(f"{task.task_id}-{task.attempt}")
        self.provider.remove(subjects)
        self.close_sessions()
        inscribe_restoration(session, backup_id, actor, utc_now())
        logger.info("restore.done", backup_id=str(backup_id))
        return {"backup_id": str(backup_id)}

    def taken_up(self, task: Task) -> Restoring | None:
        """Give what the maintenance keeps of an attempt of this restoration before, if it does."""
        held = self.maintenance.current()
        return held if held is not None and held.task_id == task.task_id else None

    @staticmethod
    def requester(owner: Engine, task: Task, taken_up: Restoring | None) -> AuditActor | None:
        """Name who asked for the restoration, as they were when they asked.

        As the maintenance keeps them: the database restored may not hold their account, and an
        attempt taken up reads a database already replaced.
        """
        if taken_up is not None and "actor" in taken_up.payload:
            named = taken_up.payload["actor"]
            return None if named is None else AuditActor(UUID(named[0]), named[1])
        with Session(owner) as reading, reading.begin():
            return inscribed_actor(reading, task.requested_by)

    def hold(self, task: Task, actor: AuditActor | None, taken_up: Restoring | None) -> Restoring:
        """Hold the platform in maintenance, the requester named; give what it holds.

        Whether an attempt before asked for the caches cleared is kept.
        """
        kept = None if actor is None else [str(actor.user_id), actor.display_name]
        held = Restoring(
            task.task_id,
            {**task.payload, "actor": kept},
            task.requested_by,
            task.correlation_id,
            task.attempt,
            caches_cleared=taken_up is not None and taken_up.caches_cleared,
        )
        self.maintenance.hold(held)
        return held

    def give_the_realm_back(self, task: Task) -> None:
        """Have the realm of the installation applied again, which Keycloak may no longer serve.

        If it is not, the operator is told what to do, and the attempt goes on: Keycloak may still
        serve the realm of the installation, its caches not cleared before the interruption.
        """
        try:
            self.provider.apply_realm(f"{task.task_id}-{task.attempt}-taken-up")
        except RealmNotAppliedError:
            logger.exception("restore.realm_not_given_back", action=GIVE_THE_REALM_BACK)
        else:
            logger.info("restore.realm_given_back")

    def close_sessions(self) -> None:
        """Close every session: the identity provider's, then the front's, which Redis keeps."""
        self.provider.close_sessions()
        closed = self.maintenance.close_front_sessions()
        logger.info("restore.sessions_closed", front_keys=closed)


def await_runs(owner: Engine, restoration: UUID) -> None:
    """Wait for the end of each run of a task the worker started before the maintenance.

    The worker runs nothing once it reads the maintenance, but a task it started before goes on,
    and writes the database the restoration keeps: the lock of its run says when it has ended. A
    database replaced already, its tables not made again, holds no task.
    """
    with Session(owner) as session, session.begin():
        if not inspect(session.connection()).has_table(BackgroundTask.__tablename__):
            return
        pending = BackgroundTask.status.in_(PENDING) & (BackgroundTask.id != restoration)
        for task_id in session.scalars(select(BackgroundTask.id).where(pending)).all():
            await_run(session, task_id)
