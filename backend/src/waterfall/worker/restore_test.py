# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The test of a restoration under Kubernetes: the schedule makes its Job (US-2930).

Once a month, the schedule (``waterfall.worker.schedule``) makes, in the namespace of the
installation, the Job the chart describes — a file it mounts, ``restore_test_job`` — and writes the
task ``restore_test``, ended, which says when the test was started and names its Job. Its one pod
holds the PostgreSQL, the Keycloak and the API of the test, which listen on its loopback alone; no
Service selects it, a NetworkPolicy closes it to every other pod, and it is deleted with its volumes
once the test has ended (``ttlSecondsAfterFinished``): the only place out of the production where a
copy not anonymised exists (WF-EXP-0010, WF-EXP-0060). It runs ``waterfall-restore test``, which
inscribes its outcome in the production itself.

The schedule reaches the API of Kubernetes as its service account, which may create Jobs in its
namespace, nothing else (the Role of the chart): the one process that holds that right runs a fixed
command and reads no file a user gave — the worker, which reads the imports, holds no right of the
cluster. It does not wait for the test, which lasts as long as a restoration. A Job the cluster
refuses, or one that cannot be asked, leaves no task: the test stays due, and the next schedule,
five minutes later, asks again. No task is ever taken again, as a worker takes a task again: the
Job is deleted as soon as its test has ended, and no second attempt can find it gone and make it
anew. A schedule that fails once the Job is made, before its task is written, leaves the test due:
the next makes a second Job, under another name, which tests and is deleted as the first. Its name
ends with the beginning of its task's identifier; a name the cluster already holds (409) is taken
as made.
"""

import json
import ssl
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import httpx2

from waterfall.platform.identifiers import new_id
from waterfall.platform.logs import get_logger
from waterfall.platform.tasks import record_ran

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

# Where Kubernetes mounts the token, the authority and the namespace of the service account of a
# pod, and the address of its API inside the cluster.
SERVICE_ACCOUNT = Path("/var/run/secrets/kubernetes.io/serviceaccount")
API = "https://kubernetes.default.svc"
CREATED = 201
EXISTS = 409
# How long a request to the API of Kubernetes waits, in seconds.
TIMEOUT = 10.0
# The characters of the identifier of the task the name of its Job ends with.
SUFFIX = 8

logger = get_logger(__name__)


class KubernetesError(Exception):
    """The API of Kubernetes refused the Job: no task is written, the reason in the journal."""


@dataclass(frozen=True, slots=True)
class Jobs:
    """The Jobs of a namespace, as its service account creates them.

    ``send`` posts a body at a path of the API and gives the status it answered.
    """

    namespace: str
    send: Callable[[str, Mapping[str, Any]], int]

    @classmethod
    def in_cluster(cls, account: Path = SERVICE_ACCOUNT, address: str = API) -> Jobs:
        """Reach the API of the cluster the pod runs in, as the service account it mounts.

        The token is read at each request: Kubernetes renews the file before the token expires.
        """
        namespace = (account / "namespace").read_text(encoding="utf-8").strip()
        roots = ssl.create_default_context(cafile=str(account / "ca.crt"))

        def send(path: str, body: Mapping[str, Any]) -> int:
            token = (account / "token").read_text(encoding="utf-8").strip()
            headers = {"Authorization": f"Bearer {token}"}
            with httpx2.Client(
                base_url=address, verify=roots, timeout=TIMEOUT, headers=headers
            ) as http:
                return http.post(path, json=body).status_code

        return cls(namespace, send)

    def create(self, job: Mapping[str, Any]) -> bool:
        """Make a Job; tell whether it is new, ``False`` if one of its name was already made."""
        status = self.send(f"/apis/batch/v1/namespaces/{self.namespace}/jobs", job)
        if status == CREATED:
            return True
        if status == EXISTS:
            return False
        message = f"the API of Kubernetes answered {status} to the creation of a Job"
        raise KubernetesError(message)


def named(manifest: Mapping[str, Any], task_id: UUID) -> dict[str, Any]:
    """Give the Job of the manifest named after a task: its name, and the task's beginning."""
    metadata = cast("dict[str, Any]", manifest["metadata"])
    name = f"{metadata['name']}-{task_id.hex[:SUFFIX]}"
    return {**manifest, "metadata": {**metadata, "name": name}}


@dataclass(frozen=True, slots=True)
class RestoreTestJob:
    """Make the Job of the test of a restoration, as ``manifest`` describes it, by ``jobs``."""

    manifest: Mapping[str, Any]
    jobs: Jobs

    @classmethod
    def of(cls, path: str, account: Path = SERVICE_ACCOUNT, address: str = API) -> RestoreTestJob:
        """Make the Job the file at ``path`` describes, in the namespace of the schedule's pod."""
        manifest = cast("dict[str, Any]", json.loads(Path(path).read_text(encoding="utf-8")))
        return cls(manifest, Jobs.in_cluster(account, address))

    def start(self, session: Session) -> UUID:
        """Make the Job of a new task, then write the task, ended; give it.

        The test inscribes its outcome itself.
        """
        task_id = new_id()
        job = named(self.manifest, task_id)
        name = job["metadata"]["name"]
        made = self.jobs.create(job)
        record_ran(session, task_id, "restore_test", {"job": name})
        logger.info(
            "restore_test.job_made" if made else "restore_test.job_already_made",
            job=name,
            task_id=str(task_id),
        )
        return task_id


def start_restore_test(
    session: Session, path: str, account: Path = SERVICE_ACCOUNT, address: str = API
) -> UUID | None:
    """Start the test the file at ``path`` describes; give its task, ``None`` if it did not start.

    A file, an account or an API that does not answer as it should is said in the journal, and
    leaves the other tasks of the schedule deposited: the test stays due.
    """
    try:
        return RestoreTestJob.of(path, account, address).start(session)
    except (OSError, ValueError, KubernetesError, httpx2.HTTPError):
        logger.exception("restore_test.job_not_made")
        return None
