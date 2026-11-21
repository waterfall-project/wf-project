# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The task ``restore_test``: the worker makes the Job of the test of a restoration (US-2930).

Under Kubernetes, the schedule deposits the task once a month (``waterfall.worker.schedule``), and
the worker makes, in the namespace of the installation, the Job the chart describes — a file it
mounts, ``restore_test_job``. Its one pod holds the PostgreSQL, the Keycloak and the API of the
test, which listen on its loopback alone; no Service selects it, a NetworkPolicy closes it to every
other pod, and it is deleted with its volumes once the test has ended (``ttlSecondsAfterFinished``):
the only place out of the production where a copy not anonymised exists (WF-EXP-0010, WF-EXP-0060).
It runs ``waterfall-restore test``, which inscribes its outcome in the production itself.

The worker does not wait for the test, which lasts as long as a restoration: it would hold a worker
that long. Each Job is named after its task: a task taken again by another worker does not make a
second one, Kubernetes refusing the name (409), which the worker takes as made. It reaches the API
of Kubernetes as its service account, which may create Jobs in its namespace, nothing else (the
Role of the chart).
"""

import json
import ssl
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import httpx2

from waterfall.platform.logs import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.tasks import Task

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
    """The API of Kubernetes refused to make the Job: the task fails, the reason in the journal."""


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
    def of(cls, path: str, account: Path = SERVICE_ACCOUNT) -> RestoreTestJob:
        """Make the Job the file at ``path`` describes, in the namespace of the worker's pod."""
        manifest = cast("dict[str, Any]", json.loads(Path(path).read_text(encoding="utf-8")))
        return cls(manifest, Jobs.in_cluster(account))

    def __call__(self, _session: Session, task: Task) -> Mapping[str, Any]:
        """Make the Job of the test; say its name. The test inscribes its outcome itself."""
        job = named(self.manifest, task.task_id)
        name = job["metadata"]["name"]
        if self.jobs.create(job):
            logger.info("restore_test.job_made", job=name)
        else:
            logger.info("restore_test.job_already_made", job=name)
        return {"job": name}
