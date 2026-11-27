# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Start the production platform on the images of a commit, bootstrap it, and hold it (US-0430).

Usage: ``python -m wftools.production``.

The platform of ``deploy/compose/compose.prod.yaml`` is started on the images tagged
``WATERFALL_IMAGE_TAG`` — the commit of the checkout unless it names another —, which the chain
either just built (``make check-production``) or just published (``images.yml``), each designated by
its digest, as the Compose designates them (#3726): the three ``WATERFALL_DIGEST_<NAME>`` the
publication wrote — the images of ghcr.io —, or else, for images built here and never pushed, those
the pushes of the three to a registry of the trial say, which the Compose reads them from
(``wftools.trialregistry``, ``WATERFALL_REGISTRY``). The platform runs under a local
name, ``WATERFALL_DOMAIN`` (``waterfall.localhost`` by default), with ``compose.prod.local.yaml``:
Caddy makes its certificate from its own authority, whose root this tool alone trusts. Its secrets
come from the environment, as the chain gives them; no file holds them. Then it holds that:

- the bootstrap, ``docker compose run --rm install``, writes the link of the first administrator;
- the API answers its liveness probe, ``status`` ``ok``;
- the owner of the tables, ``waterfall``, is no superuser, and can create neither a role nor a
  database: the administrator of the server is ``postgres``, the services' of initialisation alone;
- PostgreSQL, Redis, the API, Keycloak, the object storage and Prometheus refuse a connection in the
  clear and serve in TLS, and nothing else of them is reached from the network of the platform
  (``wftools.transport``, US-2840, WF-SEC-0010);
- the platform answers in HTTP by sending to the same page in HTTPS, at its published address
  (WF-SEC-0010); in HTTPS, with the headers that keep the browser there and its pages to
  themselves, HSTS first;
- the console of Keycloak and its realm master are not served (404);
- the first administrator sets their password by the link, signs in through the front, at the root
  of the domain, and Keycloak under ``/auth``, and the front opens the session: its cookie set, a
  page of the front that names them;
- asked for by ``WATERFALL_TRIAL_RESTORATION=1``, as the chain does, a backup and its restoration by
  the API, which the service of the restoration runs, followed by the liveness probe to its end
  (``wftools.restoration_trial``, US-0440, #948), and the test of a restoration under Compose
  (``deploy/compose/restore-test.sh``) on a backup the schedule took, which leaves nothing of its
  ephemeral platform behind (``wftools.restoretest_trial``, US-2930);
- no component, Keycloak and the supervision included, tried to reach a server outside the
  platform: it runs on networks without a way out, its users let in by a door
  (``compose.isolated.yaml``), and every name its services asked that is not the platform's, which
  the sink of its names writes down, fails the trial, naming the service that asked
  (``wftools.egress``, US-3010, WF-CMP-0030).

Given ``WATERFALL_PRODUCTION_CGROUP_PARENT`` (a slice of the cgroups of the host, which the
chain bounds to four cores and eight gigabytes before it starts the trial, ``production.yml``),
every container of the platform, and of the ephemeral platform of the test of a restoration, runs
under it, by the override ``wftools.bounded`` writes: the platform holds all of the above on a
machine of those characteristics, data components and supervision included (WF-CMP-0020-A,
US-2810).

Every request reaches the platform at the loopback, under the name of the domain, which no resolver
is asked for. The platform is removed at the end, its volumes with it, whatever the outcome; what
its services said is printed first when it fails. The project of Compose is
``WATERFALL_PRODUCTION_PROJECT`` (``waterfall-production-trial``), so that a workstation tries it
beside its other platforms.
"""

import http.client
import json
import os
import re
import secrets
import socket
import ssl
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path
from typing import cast
from urllib.parse import urlencode, urljoin, urlsplit

from wftools import REPOSITORY, bounded, egress, transport, trialregistry
from wftools.images import DIGEST, IMAGES, digest_variable
from wftools.restoration_trial import (
    API_REACHED,
    Administrator,
    Api,
    Ask,
    Restoration,
    RestorationTrial,
    TrialError,
    probe_of,
    wanted,
)
from wftools.restoretest_trial import GRACE, Run, restore_test, scheduled_backup
from wftools.transport import SERVED, TransportError, check_clear_refused
from wftools.trialregistry import RegistryError

COMPOSE = REPOSITORY / "deploy" / "compose"
FILES = (
    COMPOSE / "compose.prod.yaml",
    COMPOSE / "compose.prod.local.yaml",
    COMPOSE / "compose.isolated.yaml",
)
SINK = "egress-sink"
"""The service of ``compose.isolated.yaml`` that writes down every name asked from inside."""
ENDED = (
    "authority",
    "door-authority",
    "postgres-volume",
    "waterfall-database",
    "components",
    "migrate",
    "service-database-role",
    "backup-database-role",
    "keycloak-database",
    "install",
    "storage-buckets",
)
"""The services that run once and leave, by the order of their fixed address, from ``.0.101``.

Docker no longer lists them when the trial reads the names asked, so ``compose.isolated.yaml``
gives each an address of its own, and the request of a service that has ended is named by it."""
FIRST_ENDED = 101
DOMAIN = "waterfall.localhost"
PROJECT = "waterfall-production-trial"
ADMIN = "administrateur@waterfall.test"
# The currency and the name of the company a local trial installs, unless the environment says
# others: those of the witness (EP-05).
CURRENCY = "EUR"
COMPANY_NAME = "Delmas Automatismes"
# The capacity a local trial declares of each space, unless the environment says another: 10 GiB.
CAPACITY = str(10 * 1024**3)
AUTHORITY = "caddy:/data/caddy/pki/authorities/local/root.crt"
LIVENESS = (
    f"import urllib.request; {API_REACHED}"
    "print(urllib.request.urlopen(API + '/api/v1/health', timeout=5, context=TRUSTED)"
    ".read().decode())"
)
OWNER_RIGHTS = (
    "SELECT rolsuper, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname = 'waterfall'"
)
"""What the owner of the tables may do on the server, asked as its administrator."""
SESSION_COOKIE = "__Host-wf_session"
HTTPS_PORT = 443
HTTP_PORT = 80
PARENT = "WATERFALL_PRODUCTION_CGROUP_PARENT"
"""The slice of the cgroups the containers of the platform run under, when it is bounded."""
OVERRIDE = "WATERFALL_PRODUCTION_OVERRIDE"
"""The file of Compose that puts the production under that slice, which ``main`` writes."""
REDIRECTIONS = frozenset({301, 302, 303, 307, 308})
MOST_REDIRECTIONS = 20
OK = 200
NOT_FOUND = 404
NOT_FOUND_CODE = "NOT_FOUND"
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "SAMEORIGIN",
}
"""The headers Caddy sets on every answer in HTTPS (Caddyfile.prod)."""
HIDDEN = ("/auth/admin/", "/auth/realms/master/")
"""The console of Keycloak and its realm master, which Caddy does not serve."""
METRICS = ("/metrics", "/api/v1/metrics")
"""The point of metrics of the front, and `getMetrics` under the prefix of the API: the public door
answers 404 to both, the metrics being served on a port of their own inside the network (TFX-09)."""
TIMEOUT = 30.0
_LINK = re.compile(r"^https://\S+$", re.MULTILINE)
_FORM_ACTION = re.compile(r'<form[^>]*\baction="([^"]*)"')
_CONFIRMATION = re.compile(r'href="([^"]*login-actions/action-token[^"]*)"')

Read = Callable[[list[str]], tuple[int, str]]


class ProductionError(Exception):
    """What the production platform does not do as it must."""


@dataclass(frozen=True, slots=True)
class Answer:
    """What the platform answered a request: its status, its headers, its body."""

    status: int
    headers: tuple[tuple[str, str], ...]
    body: str

    def header(self, name: str) -> str | None:
        """Return the first value of a header, by its name in any case."""
        return next((value for key, value in self.headers if key.lower() == name.lower()), None)

    def cookies(self) -> list[tuple[str, str, bool]]:
        """Return each cookie the answer sets: its name, its value, and whether it is removed."""
        found: list[tuple[str, str, bool]] = []
        for key, value in self.headers:
            if key.lower() != "set-cookie":
                continue
            pair, _, attributes = value.partition(";")
            name, _, kept = pair.strip().partition("=")
            removed = re.search(r"max-age=0\b", attributes, re.IGNORECASE) is not None
            found.append((name, kept, removed or not kept))
        return found


Send = Callable[[str, str, bytes | None, Mapping[str, str]], Answer]
"""Send a request — method, address, body, headers — to the platform, and give its answer."""


@dataclass(frozen=True, slots=True)
class Platform:
    """Where the trial reaches the platform: its domain and its two ports on the loopback."""

    domain: str
    https_port: int
    http_port: int

    @property
    def address(self) -> str:
        """Return the address the browser reaches the platform at."""
        port = "" if self.https_port == HTTPS_PORT else f":{self.https_port}"
        return f"https://{self.domain}{port}"


@dataclass(slots=True)
class Browser:
    """Follow the pages of the platform as a browser does, with the cookies of its session.

    The cookies are those of one host, sent back on every path: the front's and Keycloak's do not
    share a name.
    """

    send: Send
    cookies: dict[str, str] = field(default_factory=dict[str, str])

    def request(self, method: str, url: str, form: Mapping[str, str] | None = None) -> Answer:
        """Send one request, the cookies held with it, and keep those its answer sets."""
        headers = {"Accept": "text/html"}
        if self.cookies:
            headers["Cookie"] = "; ".join(f"{name}={value}" for name, value in self.cookies.items())
        body = None
        if form is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            body = urlencode(form).encode()
        answer = self.send(method, url, body, headers)
        for name, value, removed in answer.cookies():
            if removed:
                self.cookies.pop(name, None)
            else:
                self.cookies[name] = value
        return answer

    def follow(self, answer: Answer, url: str) -> tuple[Answer, str]:
        """Follow the redirections of an answer; give the last answer and its address."""
        for _ in range(MOST_REDIRECTIONS):
            location = answer.header("Location")
            if answer.status not in REDIRECTIONS or location is None:
                return answer, url
            url = urljoin(url, location)
            answer = self.request("GET", url)
        message = f"more than {MOST_REDIRECTIONS} redirections from {url}"
        raise ProductionError(message)

    def open(self, url: str) -> tuple[Answer, str]:
        """Open a page, following its redirections."""
        return self.follow(self.request("GET", url), url)

    def submit(self, page: Answer, url: str, fields: Mapping[str, str]) -> tuple[Answer, str]:
        """Submit the one form of a page, following the redirections of its answer."""
        action = _FORM_ACTION.search(page.body)
        if action is None:
            message = f"no form on {urlsplit(url).path} ({page.status})"
            raise ProductionError(message)
        target = urljoin(url, unescape(action.group(1)))
        return self.follow(self.request("POST", target, fields), target)


def installation_link(output: str, platform: Platform) -> str:
    """Return the link the bootstrap wrote, under the address of the platform."""
    links = _LINK.findall(output)
    if len(links) != 1 or not links[0].startswith(f"{platform.address}/auth/"):
        message = f"the bootstrap wrote no link under {platform.address}/auth: {output.strip()!r}"
        raise ProductionError(message)
    return links[0]


def check_liveness(output: str) -> None:
    """Hold the answer of the liveness probe of the API: ``status`` ``ok``."""
    try:
        status = json.loads(output)["status"]
    except (ValueError, KeyError, TypeError) as error:
        message = f"the liveness probe of the API does not read: {output.strip()!r}"
        raise ProductionError(message) from error
    if status != "ok":
        message = f"the liveness probe of the API says {status!r}"
        raise ProductionError(message)


def check_owner(output: str) -> None:
    """Hold that the owner of the tables is no superuser, and creates neither a role nor a base."""
    if output.strip() != "f|f|f":
        message = (
            "the owner of the tables, waterfall, is a superuser, creates a role or a database: "
            f"{output.strip()!r} (rolsuper|rolcreaterole|rolcreatedb)"
        )
        raise ProductionError(message)


def check_https_alone(browser: Browser, platform: Platform) -> None:
    """Hold that the platform answers in HTTP by sending to the same page at its HTTPS address."""
    plain = f"http://{platform.domain}:{platform.http_port}/login"
    answer = browser.request("GET", plain)
    location = answer.header("Location")
    expected = f"{platform.address}/login"
    if answer.status not in REDIRECTIONS or location != expected:
        message = f"HTTP answered {answer.status} to {location!r}, not a redirection to {expected}"
        raise ProductionError(message)


def check_security_headers(browser: Browser, platform: Platform) -> None:
    """Hold that an answer in HTTPS carries the headers of Caddy, HSTS first."""
    answer = browser.request("GET", f"{platform.address}/login")
    for name, value in SECURITY_HEADERS.items():
        if (said := answer.header(name)) != value:
            message = f"/login answered {name}: {said!r} in HTTPS, not {value!r}"
            raise ProductionError(message)


def check_console_answers_not_found(browser: Browser, platform: Platform) -> None:
    """Hold that Caddy answers 404, at the first request, to the console and the realm master.

    Not ``wftools.charttrial.check_console_not_served``, which follows the redirection of the front
    and admits its screen "not found": behind Caddy the front is never reached.
    """
    for path in HIDDEN:
        answer = browser.request("GET", f"{platform.address}{path}")
        if answer.status != NOT_FOUND:
            message = f"{path} answered {answer.status}, not {NOT_FOUND}: it is served"
            raise ProductionError(message)


def _code(body: str) -> object:
    """Return the ``code`` of the error envelope in a body, or None when it is not one."""
    try:
        envelope: object = json.loads(body)
    except ValueError:
        return None
    if not isinstance(envelope, dict):
        return None
    return cast("dict[str, object]", envelope).get("code")


def check_metrics_hidden(browser: Browser, platform: Platform) -> None:
    """Hold that the public door answers 404 to the point of metrics, at both of its addresses."""
    for path in METRICS:
        answer = browser.request("GET", f"{platform.address}{path}")
        if answer.status != NOT_FOUND:
            message = f"{path} answered {answer.status}, not {NOT_FOUND}: the metrics are served"
            raise ProductionError(message)
        if _code(answer.body) != NOT_FOUND_CODE:
            message = f"{path} answered {NOT_FOUND} without the NOT_FOUND of the contract"
            raise ProductionError(message)


def set_password(browser: Browser, link: str, password: str) -> None:
    """Open the link of the bootstrap, confirm it, and set the password in the form it opens."""
    confirmation, url = browser.open(link)
    target = _CONFIRMATION.search(confirmation.body)
    if target is None:
        message = f"the link of the bootstrap opens no confirmation ({confirmation.status})"
        raise ProductionError(message)
    form, url = browser.open(urljoin(url, unescape(target.group(1))))
    if 'name="password-new"' not in form.body:
        message = f"the link of the bootstrap opens no form of a password ({form.status})"
        raise ProductionError(message)
    done, _ = browser.submit(form, url, {"password-new": password, "password-confirm": password})
    if done.status != OK:
        message = f"the password of the first administrator is not set ({done.status})"
        raise ProductionError(message)


def sign_in(browser: Browser, platform: Platform, email: str, password: str) -> Answer:
    """Sign in through the front and Keycloak; give the page of the front it ends on."""
    page, url = browser.open(f"{platform.address}/login")
    if not urlsplit(url).path.startswith("/auth/realms/waterfall/"):
        message = f"the front does not send to the realm under /auth: {urlsplit(url).path}"
        raise ProductionError(message)
    landed, url = browser.submit(page, url, {"username": email, "password": password})
    path = urlsplit(url).path
    if landed.status != OK or path.startswith(("/auth/", "/login")):
        message = f"the first administrator is not signed in: {path} answered {landed.status}"
        raise ProductionError(message)
    if SESSION_COOKIE not in browser.cookies:
        message = f"the front opened no session ({SESSION_COOKIE})"
        raise ProductionError(message)
    return landed


def check_signed_in(browser: Browser, platform: Platform, email: str) -> None:
    """Hold that the front names the first administrator on their own account."""
    account, url = browser.open(f"{platform.address}/account")
    if account.status != OK or email not in unescape(account.body):
        path = urlsplit(url).path
        message = f"the account of the first administrator does not name them: {path}"
        raise ProductionError(message)


def compose_command(project: str, override: Path | None = None) -> list[str]:
    """Return the command of Compose on the production platform under a local name.

    ``override`` is a file added after the others: the bound of its resources.
    """
    files = [
        word
        for path in (*FILES, *([override] if override else []))
        for word in ("--file", str(path))
    ]
    return ["docker", "compose", "--project-name", project, *files]


def _output(read: Read, command: list[str]) -> str:
    """Run a command that must succeed, and return what it wrote on its standard output."""
    code, output = read(command)
    if code != 0:
        message = f"{' '.join(command[:2])} … {' '.join(command[-3:])} failed ({code})"
        raise ProductionError(message)
    return output


def check_bounded(compose: list[str], read: Read, parent: str) -> None:
    """Fail unless the containers the platform started run under the slice ``parent``.

    A file of Compose the platform did not read, or a runner that did not make the slice, would
    leave it unbounded, and the trial would pass holding nothing of WF-CMP-0020-A.
    """
    names = _output(read, [*compose, "ps", "--all", "--quiet"]).split()
    if not names:
        message = f"no container of the platform to run under {parent}"
        raise ProductionError(message)
    inspect = ["docker", "inspect", "--format", "{{.Name}} {{.HostConfig.CgroupParent}}", *names]
    out = [line.split() for line in _output(read, inspect).splitlines() if line.strip()]
    loose = [line[0].lstrip("/") for line in out if line[1:] != [parent]]
    if loose or len(out) != len(names):
        message = f"containers outside the slice {parent}: {', '.join(loose) or 'unread'}"
        raise ProductionError(message)
    print(f"  the {len(names)} containers of the platform run under {parent}")


def trial(
    compose: list[str], read: Read, platform: Platform, email: str, send: Callable[[Path], Send]
) -> tuple[Callable[[], Browser], Send]:
    """Bootstrap the started platform and hold it.

    Give how to sign the first administrator in again, in a browser of their own, and the sender
    of the requests to the platform.
    """
    link = installation_link(
        _output(read, [*compose, "run", "--rm", "--no-TTY", "install"]), platform
    )
    print("  the bootstrap wrote the link of the first administrator")
    check_liveness(_output(read, liveness_command(compose)))
    print("  the API answers its liveness probe: ok")
    psql = [*compose, "exec", "-T", "postgres", "psql", "--username=postgres", "--no-psqlrc"]
    rights = [*psql, "--tuples-only", "--no-align", f"--command={OWNER_RIGHTS}"]
    check_owner(_output(read, rights))
    print("  the owner of the tables, waterfall, is no superuser")
    try:
        check_clear_refused(_output(read, transport_command(compose)))
    except TransportError as error:
        raise ProductionError(str(error)) from error
    print(f"  {', '.join(SERVED)} refuse a connection in the clear, and serve in TLS")
    with tempfile.TemporaryDirectory(prefix="waterfall-production-") as folder:
        authority = Path(folder) / "root.crt"
        _output(read, [*compose, "cp", AUTHORITY, str(authority)])
        sent = send(authority)
        check_https_alone(Browser(sent), platform)
        print(f"  HTTP sends to {platform.address}")
        check_security_headers(Browser(sent), platform)
        print(f"  HTTPS answers with {', '.join(SECURITY_HEADERS)}")
        check_console_answers_not_found(Browser(sent), platform)
        print(f"  {' and '.join(HIDDEN)} answer {NOT_FOUND}")
        check_metrics_hidden(Browser(sent), platform)
        print(f"  {' and '.join(METRICS)} answer {NOT_FOUND}")
        browser = Browser(sent)
        password = f"Trial-{secrets.token_urlsafe(18)}"
        set_password(browser, link, password)
        print("  the first administrator sets their password by the link")
        sign_in(browser, platform, email, password)
        check_signed_in(browser, platform, email)
        print(f"  the first administrator signs in at {platform.address}, and the front names them")

    def signed_in() -> Browser:
        again = Browser(sent)
        sign_in(again, platform, email, password)
        return again

    return signed_in, sent


def check_no_egress(compose: list[str], read: Read, project: str, domain: str) -> None:
    """Fail if a service asked a name outside the platform, naming it and the service."""
    log = _output(read, [*compose, "logs", "--no-color", "--no-log-prefix", SINK])
    found = egress.attempts(log, domain)
    if not found:
        print("  no component asked for a server outside the platform")
        return
    networks = [f"{project}_default", f"{project}_storage"]
    inspected = _output(
        read, ["docker", "network", "inspect", *networks, "--format", "{{json .Containers}}"]
    )
    named = containers_of(inspected)
    said = "; ".join(f"{who(named, attempt.client)} asked for {attempt.name}" for attempt in found)
    message = f"a component tried to leave the network of the platform: {said}"
    raise ProductionError(message)


def who(named: dict[str, str], client: str) -> str:
    """Name the client of a request: a container still on the networks, or a service that ended."""
    if client in named:
        return named[client]
    host = client.rsplit(".", 1)[-1]
    if client.split(".")[2:3] == ["0"] and host.isdigit():
        place = int(host) - FIRST_ENDED
        if 0 <= place < len(ENDED):
            return f"{ENDED[place]} (ended)"
    return client


def containers_of(inspected: str) -> dict[str, str]:
    """Read the containers of the networks inspected, one JSON object a line, by their address."""
    named: dict[str, str] = {}
    for written in inspected.splitlines():
        if not written.strip():
            continue
        containers = cast("dict[str, dict[str, str]]", json.loads(written) or {})
        for container in containers.values():
            address = container.get("IPv4Address", "").partition("/")[0]
            if address:
                named[address] = container.get("Name", address)
    return named


def liveness_command(compose: list[str]) -> list[str]:
    """Return the command that asks the API its liveness probe, inside its container."""
    return [*compose, "exec", "-T", "api", "python", "-c", LIVENESS]


def transport_command(compose: list[str]) -> list[str]:
    """Return the command that tries every server in the clear, inside the container of the API."""
    return [*compose, "exec", "-T", "api", *transport.COMPOSE.command()]


def back_up_and_restore(
    compose: list[str],
    read: Read,
    platform: Platform,
    signed: tuple[Callable[[], Browser], Send],
    restoration: Restoration,
) -> None:
    """Back the platform up by its API, and restore it (``wftools.restoration_trial``)."""
    signed_in, sent = signed
    administrator = Administrator(
        signed_in,
        sent,
        platform.address,
        restoration.client_secret,
        (ProductionError, TrialError, OSError),
    )
    api = Api(compose, restoration.ask)
    probe = probe_of(read, liveness_command(compose))
    RestorationTrial(api, administrator, probe, restoration.clock).run()


class _Loopback(http.client.HTTPSConnection):
    """A connection in HTTPS to a name, made at the loopback: no resolver is asked for it."""

    def __init__(self, host: str, port: int, tls: ssl.SSLContext) -> None:
        super().__init__(host, port, context=tls, timeout=TIMEOUT)
        self.tls = tls

    def connect(self) -> None:
        """Connect at the loopback, and check the certificate for the name."""
        plain = socket.create_connection(("127.0.0.1", self.port), self.timeout)
        self.sock = self.tls.wrap_socket(plain, server_hostname=self.host)


def sender(platform: Platform) -> Callable[[Path], Send]:
    """Make the sender of the requests to the platform, trusting the root of its authority alone."""

    def make(authority: Path) -> Send:
        tls = ssl.create_default_context(cafile=str(authority))

        def send(method: str, url: str, body: bytes | None, headers: Mapping[str, str]) -> Answer:
            parts = urlsplit(url)
            if parts.hostname != platform.domain:
                message = f"a page sent away from the platform, to {parts.hostname}"
                raise ProductionError(message)
            if parts.scheme == "https":
                connection: http.client.HTTPConnection = _Loopback(
                    platform.domain, parts.port or HTTPS_PORT, tls
                )
            else:
                connection = http.client.HTTPConnection(
                    "127.0.0.1", parts.port or HTTP_PORT, timeout=TIMEOUT
                )
            target = parts.path or "/"
            if parts.query:
                target = f"{target}?{parts.query}"
            sent = dict(headers)
            sent["Host"] = parts.netloc
            try:
                connection.request(method, target, body, sent)
                response = connection.getresponse()
                text = response.read().decode(errors="replace")
                return Answer(response.status, tuple(response.getheaders()), text)
            except (OSError, http.client.HTTPException) as error:
                message = f"{method} {parts.path} did not answer: {error}"
                raise ProductionError(message) from error
            finally:
                connection.close()

        return send

    return make


def platform_of(environment: Mapping[str, str]) -> Platform:
    """Read where the platform is published from the environment the trial is given."""
    domain = environment.get("WATERFALL_DOMAIN") or DOMAIN
    try:
        https_port = int(environment.get("WATERFALL_HTTPS_PORT") or HTTPS_PORT)
        http_port = int(environment.get("WATERFALL_HTTP_PORT") or HTTP_PORT)
    except ValueError as error:
        message = f"a port of the platform is not a number: {error}"
        raise ProductionError(message) from error
    return Platform(domain, https_port, http_port)


def digests_of(environment: Mapping[str, str], pushed: Mapping[str, str]) -> dict[str, str]:
    """Return the variable that designates each image by its digest: the three given, or none.

    Given, they are the publication's; none given, those of the images the trial pushed to its own
    registry, by name of image. Two of three would run images of two origins.
    """
    given = {digest_variable(image): environment.get(digest_variable(image)) for image in IMAGES}
    if any(given.values()) and not all(given.values()):
        message = f"give the digests of the three images, or none: {', '.join(given)}"
        raise ProductionError(message)
    found = {
        variable: value or pushed.get(image.name, "")
        for (variable, value), image in zip(given.items(), IMAGES, strict=True)
    }
    for variable, value in found.items():
        if not DIGEST.fullmatch(value):
            message = f"{variable} is not the digest of an image (sha256:…): {value!r}"
            raise ProductionError(message)
    return found


def environment_of(
    environment: Mapping[str, str], platform: Platform, pushed: Mapping[str, str]
) -> dict[str, str]:
    """Return the environment Compose starts the platform with: what is given, and the defaults.

    Each image by its digest, as given or as the trial pushed it (``digests_of``).
    """
    email = environment.get("WATERFALL_ADMIN_EMAIL") or ADMIN
    return {
        **environment,
        **digests_of(environment, pushed),
        "WATERFALL_DOMAIN": platform.domain,
        "WATERFALL_ADMIN_EMAIL": email,
        "WATERFALL_ACME_EMAIL": environment.get("WATERFALL_ACME_EMAIL") or email,
        "WATERFALL_CURRENCY": environment.get("WATERFALL_CURRENCY") or CURRENCY,
        "WATERFALL_COMPANY_NAME": environment.get("WATERFALL_COMPANY_NAME") or COMPANY_NAME,
        **{
            name: environment.get(name) or CAPACITY
            for name in ("WATERFALL_DATABASE_CAPACITY_BYTES", "WATERFALL_STORAGE_CAPACITY_BYTES")
        },
    }


def local_images(
    given: Mapping[str, str], tag: str, run: Run, read: Read
) -> tuple[dict[str, str], dict[str, str]]:
    """Return what the trial adds to its environment, and the digest of each image it pushed.

    Digests given: nothing is added, they are those of ghcr.io's. None: the images of the tag,
    built here, are pushed to a registry of the trial (``trialregistry``), which Compose reads them
    from by the digests the pushes said.
    """
    if any(given.get(digest_variable(image)) for image in IMAGES):
        return {}, {}
    address = trialregistry.start(run, read)
    try:
        digests = trialregistry.publish(tag, address, read)
    except RegistryError:
        trialregistry.stop(run)
        raise
    return {"WATERFALL_REGISTRY": trialregistry.location(address)}, digests


def main(
    environment: Mapping[str, str] | None = None,
    run: Run | None = None,
    read: Read | None = None,
    send: Callable[[Platform], Callable[[Path], Send]] = sender,
    ask: Ask | None = None,
) -> int:
    """Start the platform, hold it, and remove it; fail naming what it does not do."""
    given = dict(os.environ if environment is None else environment)
    registry: list[str] = []
    try:
        platform = platform_of(given)
        tag = given.get("WATERFALL_IMAGE_TAG") or _head()
        added, pushed = local_images(given, tag, run or runner(given), read or _reader(given))
        registry = list(added)
        started = environment_of({**given, **added}, platform, pushed)
        with tempfile.TemporaryDirectory(prefix="waterfall-production-") as folder:
            started = {**started, **bounded.environment(started.get(PARENT), Path(folder))}
            commands = (run or runner(started), read or _reader(started))
            return hold(started, tag, platform, commands, (send, ask))
    except (ProductionError, RegistryError, OSError, subprocess.CalledProcessError) as error:
        print(f"wftools.production: {error}", file=sys.stderr)
        return 1
    finally:
        if registry:
            trialregistry.stop(run or runner(given))


def hold(
    started: Mapping[str, str],
    tag: str,
    platform: Platform,
    commands: tuple[Run, Read],
    extras: tuple[Callable[[Platform], Callable[[Path], Send]], Ask | None],
) -> int:
    """Start the platform on the environment made, hold it, and remove it."""
    run, read = commands
    send, ask = extras
    restoration = None
    if wanted(started):
        secret = started.get("WATERFALL_FRONT_CLIENT_SECRET", "")
        restoration = Restoration(ask or _asker(started), secret)
    project = started.get("WATERFALL_PRODUCTION_PROJECT") or PROJECT
    given = started.get(OVERRIDE)
    compose = compose_command(project, Path(given) if given else None)
    up = [*compose, "up", "--detach", "--wait", "--quiet-pull"]
    print(f"  the images {tag}, at {platform.address}", flush=True)
    failed = True
    try:
        if code := run(up):
            return code
        if parent := started.get(PARENT):
            check_bounded(compose, read, parent)
        email = started["WATERFALL_ADMIN_EMAIL"]
        signed = trial(compose, read, platform, email, send(platform))
        if restoration is None:
            print("  the backup and its restoration are left out (WATERFALL_TRIAL_RESTORATION)")
        else:
            scheduled_backup(compose, read)
            back_up_and_restore(compose, read, platform, signed, restoration)
            restore_test(compose, run, read, project)
        check_no_egress(compose, read, project, platform.domain)
        failed = False
    except (ProductionError, TrialError) as error:
        print(f"wftools.production: {error}", file=sys.stderr)
        return 1
    finally:
        if failed:
            run([*compose, "--profile", "install", "logs", "--no-color", "--tail", "200"])
        run([*compose, "--profile", "install", "down", "--volumes"])
    return 0


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY, capture_output=True, text=True, check=True
    ).stdout.strip()


def runner(environment: Mapping[str, str]) -> Run:
    """Return the function that runs a command, bounded by its ``limit`` if it has one."""

    def run(command: list[str], limit: float | None = None) -> int:
        with subprocess.Popen(command, cwd=REPOSITORY, env=dict(environment)) as process:
            try:
                return process.wait(timeout=limit)
            except subprocess.TimeoutExpired:
                # TERM, not KILL: the script removes its platform in a trap. ``command`` is
                # ``env ... sh script``, and ``env`` executes: the process is the shell itself.
                process.terminate()
                try:
                    process.wait(timeout=GRACE)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise

    return run


def _reader(environment: Mapping[str, str]) -> Read:
    def read(command: list[str]) -> tuple[int, str]:
        done = subprocess.run(
            command,
            cwd=REPOSITORY,
            env=dict(environment),
            capture_output=True,
            text=True,
            check=False,
        )
        if done.returncode != 0:
            print(done.stderr, file=sys.stderr)
        return done.returncode, done.stdout

    return read


def _asker(environment: Mapping[str, str]) -> Ask:
    def ask(command: list[str], given: str) -> tuple[int, str]:
        done = subprocess.run(
            command,
            cwd=REPOSITORY,
            env=dict(environment),
            input=given,
            capture_output=True,
            text=True,
            check=False,
        )
        if done.returncode != 0:
            print(done.stderr, file=sys.stderr)
        return done.returncode, done.stdout

    return ask


if __name__ == "__main__":
    sys.exit(main())
