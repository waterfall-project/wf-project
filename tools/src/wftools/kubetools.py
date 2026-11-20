# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Install Helm, kind, kubectl, promtool and amtool at the versions the chain pins (US-2800).

Usage: ``python -m wftools.kubetools``.

promtool and amtool are those of the releases of Prometheus and of Alertmanager the platform runs
(US-2880): the tests check their configurations by them and play the rules of alert by promtool.
PyPI holds none of the five, as it holds actionlint, hadolint and shellcheck, which the tools take
as their packages: each is downloaded once from where its project publishes it, checked against the
digest written here, and kept under the cache of the user — ``$XDG_CACHE_HOME/waterfall/bin``,
``~/.cache/waterfall/bin`` by default —, a folder per version, which the worktrees share. A download
whose digest is not the one written is refused and removed: raise a version here, with its digest,
and nowhere else. For Linux on x86-64 alone, the workstation's and the runners' of the chain.
"""

import hashlib
import http.client
import io
import os
import platform
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlsplit

TOOL = "wftools.kubetools"
TIMEOUT = 120.0
MACHINE = "x86_64"
OK = 200
MOVED = frozenset({301, 302, 303, 307, 308})
REDIRECTIONS = 5


class ToolError(Exception):
    """What keeps a tool from being installed."""


@dataclass(frozen=True, slots=True)
class Binary:
    """A tool the chain pins: where its release is, its digest, and its path in an archive."""

    name: str
    version: str
    url: str
    sha256: str
    member: str | None = None
    """Its path in the archive of the release, or None when the release is the binary itself."""


BINARIES = {
    binary.name: binary
    for binary in (
        Binary(
            "helm",
            "4.3.2",
            "https://get.helm.sh/helm-v4.3.2-linux-amd64.tar.gz",
            "d1c0278d46beab79582d7e50f5b3dc206944ba8e577cde618513fd07daa53983",
            "linux-amd64/helm",
        ),
        Binary(
            "kind",
            "0.33.0",
            "https://github.com/kubernetes-sigs/kind/releases/download/v0.33.0/kind-linux-amd64",
            "aee6151561422756b764a4ae28e7f44cda5af5a9eead3cc9985112b1de8d8e0d",
        ),
        # The version of Kubernetes the node of kind runs (wftools.charttrial).
        Binary(
            "kubectl",
            "1.37.2",
            "https://dl.k8s.io/release/v1.37.2/bin/linux/amd64/kubectl",
            "c04487523e7aa7d1493f7808174c899db93d7a9cf57531420cd76b9bd415f8f4",
        ),
        # The version of Prometheus the Compose and the chart run (prom/prometheus).
        Binary(
            "promtool",
            "3.16.0",
            "https://github.com/prometheus/prometheus/releases/download/v3.16.0/prometheus-3.16.0.linux-amd64.tar.gz",
            "68727009472a2c02e1ff7f062fd5b3e637285bffc8fc2d340c76fb449d6e0f34",
            "prometheus-3.16.0.linux-amd64/promtool",
        ),
        # The version of Alertmanager the Compose and the chart run: its configuration is checked.
        Binary(
            "amtool",
            "0.35.0",
            "https://github.com/prometheus/alertmanager/releases/download/v0.35.0/alertmanager-0.35.0.linux-amd64.tar.gz",
            "6c7752a903c40c8a749e0b29df9240437e4fbb8228068d0af8807377db32addd",
            "alertmanager-0.35.0.linux-amd64/amtool",
        ),
    )
}


def cache(environment: dict[str, str] | None = None) -> Path:
    """Return the folder the tools are kept in."""
    given = os.environ if environment is None else environment
    root = given.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(root) / "waterfall" / "bin"


def location(binary: Binary, folder: Path) -> Path:
    """Return where a tool lives once installed: a folder per version."""
    return folder / f"{binary.name}-{binary.version}" / binary.name


def extracted(binary: Binary, payload: bytes) -> bytes:
    """Check the digest of a download, and return the binary it is or that its archive holds."""
    digest = hashlib.sha256(payload).hexdigest()
    if digest != binary.sha256:
        message = (
            f"{binary.url} has the digest {digest}, not the one pinned, {binary.sha256}: refused"
        )
        raise ToolError(message)
    if binary.member is None:
        return payload
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        member = archive.extractfile(binary.member)
        if member is None:
            message = f"{binary.url} holds no {binary.member}"
            raise ToolError(message)
        return member.read()


def _download(url: str) -> bytes:
    """Download a release over HTTPS alone, following the redirections of its host."""
    for _ in range(REDIRECTIONS):
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname:
            message = f"{url} is not an address in HTTPS"
            raise ToolError(message)
        connection = http.client.HTTPSConnection(parts.hostname, timeout=TIMEOUT)
        try:
            target = f"{parts.path}?{parts.query}" if parts.query else parts.path
            connection.request("GET", target, headers={"User-Agent": TOOL})
            answer = connection.getresponse()
            if answer.status in MOVED and (moved := answer.getheader("Location")):
                url = urljoin(url, moved)
                continue
            if answer.status != OK:
                message = f"{url} answered {answer.status}"
                raise ToolError(message)
            return answer.read()
        finally:
            connection.close()
    message = f"more than {REDIRECTIONS} redirections from {url}"
    raise ToolError(message)


def installed(name: str, folder: Path | None = None) -> Path:
    """Return the path of a tool, installing it first if it is not."""
    binary = BINARIES[name]
    path = location(binary, folder or cache())
    if path.exists():
        return path
    if sys.platform != "linux" or platform.machine() != MACHINE:
        message = f"{name} is pinned for Linux on {MACHINE} alone"
        raise ToolError(message)
    content = extracted(binary, _download(binary.url))
    path.parent.mkdir(parents=True, exist_ok=True)
    # Written beside, then renamed: two runs at once never read half a binary.
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as written:
        written.write(content)
    Path(written.name).chmod(0o755)
    Path(written.name).replace(path)
    return path


def main() -> int:
    """Install every tool, and say where each is."""
    try:
        for name, binary in BINARIES.items():
            print(f"  {name} {binary.version}: {installed(name)}")
    except (ToolError, OSError) as error:
        print(f"{TOOL}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
