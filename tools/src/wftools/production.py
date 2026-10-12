# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Start the production platform on the images of a commit, bootstrap it, and hold it (US-0430).

Usage: ``python -m wftools.production``.

The platform of ``deploy/compose/compose.prod.yaml`` is started on the images tagged
``WATERFALL_IMAGE_TAG`` — the commit of the checkout unless it names another —, which the chain
either just built (``make check-production``) or just published (``images.yml``), under a local
name, ``WATERFALL_DOMAIN`` (``waterfall.localhost`` by default), with ``compose.prod.local.yaml``:
Caddy makes its certificate from its own authority, whose root this tool alone trusts. Its secrets
come from the environment, as the chain gives them; no file holds them. Then it holds that:

- the bootstrap, ``docker compose run --rm install``, writes the link of the first administrator;
- the API answers its liveness probe, ``status`` ``ok``;
- the owner of the tables, ``waterfall``, is no superuser, and can create neither a role nor a
  database: the administrator of the server is ``postgres``, the services' of initialisation alone;
- the platform answers in HTTP by sending to the same page in HTTPS, at its published address
  (WF-SEC-0010); in HTTPS, with the headers that keep the browser there and its pages to
  themselves, HSTS first;
- the console of Keycloak and its realm master are not served (404);
- the first administrator sets their password by the link, signs in through the front, at the root
  of the domain, and Keycloak under ``/auth``, and the front opens the session: its cookie set, a
  page of the front that names them;
- asked for by ``WATERFALL_TRIAL_RESTORATION=1``, a backup and its restoration by the API, the
  restoration followed by the liveness probe to its end (``wftools.restoration_trial``, US-0440,
  #948): left out until the chain starts the service of the restoration.

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
from urllib.parse import urlencode, urljoin, urlsplit

from wftools import REPOSITORY
from wftools.restoration_trial import (
    Administrator,
    Api,
    Ask,
    Restoration,
    RestorationTrial,
    TrialError,
    probe_of,
    wanted,
)

COMPOSE = REPOSITORY / "deploy" / "compose"
FILES = (COMPOSE / "compose.prod.yaml", COMPOSE / "compose.prod.local.yaml")
DOMAIN = "waterfall.localhost"
PROJECT = "waterfall-production-trial"
ADMIN = "administrateur@waterfall.test"
AUTHORITY = "caddy:/data/caddy/pki/authorities/local/root.crt"
LIVENESS = (
    "import urllib.request; "
    "print(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=5)"
    ".read().decode())"
)
OWNER_RIGHTS = (
    "SELECT rolsuper, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname = 'waterfall'"
)
"""What the owner of the tables may do on the server, asked as its administrator."""
SESSION_COOKIE = "__Host-wf_session"
HTTPS_PORT = 443
HTTP_PORT = 80
REDIRECTIONS = frozenset({301, 302, 303, 307, 308})
MOST_REDIRECTIONS = 20
OK = 200
NOT_FOUND = 404
SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "SAMEORIGIN",
}
"""The headers Caddy sets on every answer in HTTPS (Caddyfile.prod)."""
HIDDEN = ("/auth/admin/", "/auth/realms/master/")
"""The console of Keycloak and its realm master, which Caddy does not serve."""
TIMEOUT = 30.0
_LINK = re.compile(r"^https://\S+$", re.MULTILINE)
_FORM_ACTION = re.compile(r'<form[^>]*\baction="([^"]*)"')
_CONFIRMATION = re.compile(r'href="([^"]*login-actions/action-token[^"]*)"')

Run = Callable[[list[str]], int]
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


def check_console_hidden(browser: Browser, platform: Platform) -> None:
    """Hold that the console of Keycloak and its realm master are not served."""
    for path in HIDDEN:
        answer = browser.request("GET", f"{platform.address}{path}")
        if answer.status != NOT_FOUND:
            message = f"{path} answered {answer.status}, not {NOT_FOUND}: it is served"
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


def compose_command(project: str) -> list[str]:
    """Return the command of Compose on the production platform under a local name."""
    files = [word for path in FILES for word in ("--file", str(path))]
    return ["docker", "compose", "--project-name", project, *files]


def _output(read: Read, command: list[str]) -> str:
    """Run a command that must succeed, and return what it wrote on its standard output."""
    code, output = read(command)
    if code != 0:
        message = f"{' '.join(command[:2])} … {' '.join(command[-3:])} failed ({code})"
        raise ProductionError(message)
    return output


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
    with tempfile.TemporaryDirectory(prefix="waterfall-production-") as folder:
        authority = Path(folder) / "root.crt"
        _output(read, [*compose, "cp", AUTHORITY, str(authority)])
        sent = send(authority)
        check_https_alone(Browser(sent), platform)
        print(f"  HTTP sends to {platform.address}")
        check_security_headers(Browser(sent), platform)
        print(f"  HTTPS answers with {', '.join(SECURITY_HEADERS)}")
        check_console_hidden(Browser(sent), platform)
        print(f"  {' and '.join(HIDDEN)} answer {NOT_FOUND}")
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


def liveness_command(compose: list[str]) -> list[str]:
    """Return the command that asks the API its liveness probe, inside its container."""
    return [*compose, "exec", "-T", "api", "python", "-c", LIVENESS]


def back_up_and_restore(
    compose: list[str],
    read: Read,
    platform: Platform,
    signed: tuple[Callable[[], Browser], Send],
    restoration: Restoration,
) -> None:
    """Back the platform up by its API, and restore it (``wftools.restoration_trial``)."""
    signed_in, sent = signed
    administrator = Administrator(signed_in, sent, platform.address, restoration.client_secret)
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


def environment_of(environment: Mapping[str, str], tag: str, platform: Platform) -> dict[str, str]:
    """Return the environment Compose starts the platform with: what is given, and the defaults."""
    email = environment.get("WATERFALL_ADMIN_EMAIL") or ADMIN
    return {
        **environment,
        "WATERFALL_IMAGE_TAG": tag,
        "WATERFALL_DOMAIN": platform.domain,
        "WATERFALL_ADMIN_EMAIL": email,
        "WATERFALL_ACME_EMAIL": environment.get("WATERFALL_ACME_EMAIL") or email,
    }


def main(
    environment: Mapping[str, str] | None = None,
    run: Run | None = None,
    read: Read | None = None,
    send: Callable[[Platform], Callable[[Path], Send]] = sender,
    ask: Ask | None = None,
) -> int:
    """Start the platform, hold it, and remove it; fail naming what it does not do."""
    given = dict(os.environ if environment is None else environment)
    try:
        platform = platform_of(given)
        tag = given.get("WATERFALL_IMAGE_TAG") or _head()
        started = environment_of(given, tag, platform)
    except (ProductionError, OSError, subprocess.CalledProcessError) as error:
        print(f"wftools.production: {error}", file=sys.stderr)
        return 1
    run = run or _runner(started)
    read = read or _reader(started)
    restoration = None
    if wanted(given):
        secret = given.get("WATERFALL_FRONT_CLIENT_SECRET", "")
        restoration = Restoration(ask or _asker(started), secret)
    compose = compose_command(given.get("WATERFALL_PRODUCTION_PROJECT") or PROJECT)
    up = [*compose, "up", "--detach", "--wait", "--quiet-pull"]
    print(f"  the images {tag}, at {platform.address}", flush=True)
    failed = True
    try:
        if code := run(up):
            return code
        email = started["WATERFALL_ADMIN_EMAIL"]
        signed = trial(compose, read, platform, email, send(platform))
        if restoration is None:
            print("  the backup and its restoration are left out (WATERFALL_TRIAL_RESTORATION)")
        else:
            back_up_and_restore(compose, read, platform, signed, restoration)
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


def _runner(environment: Mapping[str, str]) -> Run:
    def run(command: list[str]) -> int:
        return subprocess.run(
            command, cwd=REPOSITORY, env=dict(environment), check=False
        ).returncode

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
