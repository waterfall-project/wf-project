# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The production platform: its Compose, its settings, and the trial the chain runs (US-0430).

What the files say is held here: the platform is made of the images the chain publishes, Caddy is
its only door, its data live in named volumes, every secret comes from the file of settings the
operator fills, and the backups pass by their own role. The platform itself is started, bootstrapped
and signed in by ``make production-trial`` in the chain (production.yml, images.yml); these tests
hold what the trial concludes from what Compose and the platform answer.
"""

import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
import yaml

from wftools import REPOSITORY, images, paths, production
from wftools.production import Answer, Browser, Platform, ProductionError

COMPOSE = REPOSITORY / "deploy" / "compose"
PRODUCTION = COMPOSE / "compose.prod.yaml"
LOCAL = COMPOSE / "compose.prod.local.yaml"
SERVICE = COMPOSE / "compose.service.yaml"
TEMPLATE = COMPOSE / "production.env.example"
CADDYFILE = COMPOSE / "Caddyfile.prod"
WORKFLOWS = REPOSITORY / ".github" / "workflows"
PUBLISHED = re.compile(r"ghcr\.io/waterfall-project/(\w+):\$\{WATERFALL_IMAGE_TAG:\?[^}]*\}")
PINNED = re.compile(r"[\w./-]+:[\w.-]+@sha256:[0-9a-f]{64}")
VARIABLE = re.compile(r"\$\{(WATERFALL_[A-Z0-9_]+)")
DEFAULTED = re.compile(r"\$\{(WATERFALL_[A-Z0-9_]+)(:?-)")
SECRET = re.compile(r"PASSWORD|SECRET|_KEY$")
PLATFORM = Platform("waterfall.localhost", 443, 80)
ADDRESS = PLATFORM.address
EMAIL = "administrateur@waterfall.test"
LINK = f"{ADDRESS}/auth/realms/waterfall/login-actions/action-token?key=abc"


def compose(path: Path = PRODUCTION) -> dict[str, Any]:
    """Read a Compose file."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def services() -> dict[str, Any]:
    """Read the services of the production platform."""
    return compose()["services"]


def template() -> dict[str, str]:
    """Read the variables the model of the file of settings names, with their values."""
    lines = TEMPLATE.read_text(encoding="utf-8").splitlines()
    pairs = (line.partition("=") for line in lines if re.match(r"#? ?WATERFALL_\w+=", line))
    return {name.lstrip("# "): value for name, _, value in pairs}


def required(name: str) -> str:
    """Return how the production Compose reads a variable it does not start without."""
    return f"${{{name}:?set {name} in .env}}"


def environment(service: str) -> dict[str, str]:
    """Read the environment of a service, its anchors merged."""
    return dict(services()[service].get("environment", {}))


@pytest.mark.requirement("WF-ARC-0050-A")
def test_the_platform_runs_the_three_images_the_chain_publishes_and_builds_nothing() -> None:
    # « Le fichier Compose démarre une plateforme complète sur une machine seule, à partir des
    # mêmes images que le chart » : those of ghcr.io/waterfall-project, under the tag the operator
    # names, every other image pinned by its digest.
    text = PRODUCTION.read_text(encoding="utf-8")
    assert set(PUBLISHED.findall(text)) == {image.name for image in images.IMAGES}
    for name, service in services().items():
        assert "build" not in service, name
        image = str(service["image"])
        assert PUBLISHED.fullmatch(image) or PINNED.fullmatch(image), (name, image)


@pytest.mark.requirement("WF-ARC-0050-A")
def test_the_platform_is_complete_on_one_machine_its_data_in_named_volumes() -> None:
    # Proper to US-0430: the TLS front end, the front, the API, the worker, the schedule,
    # PostgreSQL, Redis, the object storage and its buckets, Keycloak and its configuration.
    found = services()
    assert {
        "caddy",
        "front",
        "api",
        "worker",
        "scheduler",
        "postgres",
        "redis",
        "storage",
        "storage-buckets",
        "keycloak",
        "keycloak-realm",
        "migrate",
        "install",
    } <= set(found)
    assert environment("storage-buckets")["STORAGE_BUCKETS"].split() == ["backups", "imports"]
    assert set(compose()["volumes"]) == {
        "caddy-data",
        "caddy-config",
        "postgres-data",
        "storage-data",
    }
    for name, kept in {
        "postgres": "/var/lib/postgresql/data",
        "storage": "/var/lib/garage",
        "caddy": "/data",
    }.items():
        mounts = [str(volume) for volume in found[name]["volumes"]]
        assert any(re.fullmatch(rf"[\w-]+:{kept}", mount) for mount in mounts), name


@pytest.mark.requirement("WF-ARC-0050-A")
def test_caddy_is_the_only_door_and_serves_the_front_at_the_root_and_keycloak_under_auth() -> None:
    published = {name for name, service in services().items() if "ports" in service}
    assert published == {"caddy"}
    assert services()["caddy"]["ports"] == [
        "${WATERFALL_HTTP_PORT:-80}:80",
        "${WATERFALL_HTTPS_PORT:-443}:443",
    ]
    caddyfile = CADDYFILE.read_text(encoding="utf-8")
    assert re.search(r"^\{\$WATERFALL_DOMAIN\} \{$", caddyfile, re.MULTILINE)
    assert "email {$WATERFALL_ACME_EMAIL}" in caddyfile
    assert re.search(r"handle /auth/\* \{\s*reverse_proxy keycloak:8080\s*\}", caddyfile)
    assert re.search(r"handle \{\s*reverse_proxy front:3000\s*\}", caddyfile)


def site(caddyfile: str, address: str) -> str:
    """Return the body of the block of a site of the Caddyfile, without its comments."""
    block = rf"^{re.escape(address)} \{{\n(.*?)^\}}$"
    found = re.search(block, caddyfile, re.MULTILINE | re.DOTALL)
    assert found is not None, address
    return "\n".join(
        line.strip() for line in found.group(1).splitlines() if not line.strip().startswith("#")
    )


@pytest.mark.requirement("WF-SEC-0010-A")
def test_every_answer_in_https_keeps_the_browser_in_https_and_its_pages_to_themselves() -> None:
    # The browser speaks HTTPS alone, and comes back in HTTPS alone (HSTS); the headers of Caddy
    # replace those of the services, on every answer. SAMEORIGIN, not DENY: Keycloak frames its own
    # pages, under /auth. Between the services, the encryption is EP-13's.
    served = site(CADDYFILE.read_text(encoding="utf-8"), "{$WATERFALL_DOMAIN}")
    headers = re.search(r"^header \{\n(.*?)\n\}$", served, re.MULTILINE | re.DOTALL)
    assert headers is not None
    assert headers.group(1).splitlines() == [
        'Strict-Transport-Security "max-age=31536000"',
        "X-Content-Type-Options nosniff",
        "Referrer-Policy strict-origin-when-cross-origin",
        "X-Frame-Options SAMEORIGIN",
        "defer",
    ]
    assert {
        name: value.strip('"')
        for name, _, value in (line.partition(" ") for line in headers.group(1).splitlines()[:-1])
    } == production.SECURITY_HEADERS


@pytest.mark.requirement("WF-SEC-0010-A")
def test_http_sends_to_the_published_address_its_port_included() -> None:
    plain = site(CADDYFILE.read_text(encoding="utf-8"), "http://{$WATERFALL_DOMAIN}")
    assert plain == "redir {$WATERFALL_ADDRESS}{uri} 308"
    caddy = environment("caddy")
    assert caddy["WATERFALL_ADDRESS"] == environment("front")["WATERFALL_FRONT_ADDRESS"]
    assert caddy["WATERFALL_ADDRESS"].endswith("${WATERFALL_HTTPS_PORT:+:${WATERFALL_HTTPS_PORT}}")


def test_the_console_of_keycloak_and_its_realm_master_are_not_served() -> None:
    # Their administrator holds every realm: reached on the machine alone (README.md). The 404 is
    # handled before Keycloak's /auth/*, which would serve them.
    served = site(CADDYFILE.read_text(encoding="utf-8"), "{$WATERFALL_DOMAIN}")
    hidden = "/auth/admin /auth/admin/* /auth/realms/master /auth/realms/master/*"
    assert f"@keycloak-admin path {hidden}" in served
    refused = served.index("handle @keycloak-admin {\nrespond 404\n}")
    assert refused < served.index("handle /auth/* {")
    for path in production.HIDDEN:
        assert any(path.rstrip("/") == kept.removesuffix("/*") for kept in hidden.split()), path


def test_every_route_of_the_front_under_auth_is_served_to_it_or_kept_inside_the_platform() -> None:
    # Keycloak is under /auth, and so are three routes of the front: those the browser opens pass
    # to the front; its back channel, which Keycloak reaches at front:3000, is not served (#731).
    routes = {path.name for path in (REPOSITORY / "frontend/src/app/auth").iterdir()}
    served = re.search(r"@front path ([^\n]+)", CADDYFILE.read_text(encoding="utf-8"))
    assert served is not None
    assert {path.removeprefix("/auth/") for path in served.group(1).split()} == routes - {
        "backchannel-logout"
    }
    realm = environment("keycloak-realm")
    assert realm["WATERFALL_FRONT_BACKCHANNEL"] == "http://front:3000"


@pytest.mark.requirement("WF-SEC-0010-A")
def test_every_secret_comes_from_the_file_of_settings_and_none_has_a_default() -> None:
    # « Le démarrage d'un service sans les secrets attendus échoue en le disant, plutôt que de
    # démarrer sans. » : Compose refuses to start a service whose secret the file lacks, naming it.
    text = PRODUCTION.read_text(encoding="utf-8")
    secrets = {name for name in VARIABLE.findall(text) if SECRET.search(name)}
    assert secrets
    defaulted = {name for name, _ in DEFAULTED.findall(text)}
    # The identifier of the key of the storage is no secret.
    assert secrets & defaulted == {"WATERFALL_STORAGE_ACCESS_KEY"}
    for name in secrets - defaulted:
        assert required(name) in text


@pytest.mark.requirement("WF-SEC-0010-A")
def test_the_model_of_the_file_of_settings_names_every_variable_and_holds_no_secret() -> None:
    named = template()
    read = set(VARIABLE.findall(PRODUCTION.read_text(encoding="utf-8")))
    assert set(named) == read
    for name, value in named.items():
        if SECRET.search(name) and name != "WATERFALL_STORAGE_ACCESS_KEY":
            assert value == "", name
    assert ".env" in (REPOSITORY / ".gitignore").read_text(encoding="utf-8")


@pytest.mark.requirement("WF-SEC-0010-A")
def test_nothing_of_the_development_enters_the_production_platform() -> None:
    values = set(images.development_values().values())
    for path in (PRODUCTION, LOCAL, TEMPLATE, CADDYFILE):
        text = path.read_text(encoding="utf-8")
        assert not [value for value in values if value in text], path
        assert "keycloak/development" not in text
        assert "mailpit" not in text
        assert "openldap" not in text


def test_the_third_party_images_are_those_of_the_service_platform() -> None:
    pinned = set(PINNED.findall(PRODUCTION.read_text(encoding="utf-8")))
    assert pinned <= set(PINNED.findall(SERVICE.read_text(encoding="utf-8")))


def test_the_worker_backs_up_as_the_role_of_the_backup_and_the_owner_migrates_alone() -> None:
    # #701, #895: the API, the worker and the schedule connect as the role of the service; the
    # worker dumps the databases as the role of the backup, a member of pg_read_all_data; the owner
    # of the tables migrates and bootstraps, and nothing else holds its password.
    owner = "postgresql://waterfall:"
    worker = environment("worker")
    for name in ("WATERFALL_BACKUP_DATABASE_URL", "WATERFALL_KEYCLOAK_DATABASE_URL"):
        assert worker[name].startswith("postgresql://waterfall_backup:"), name
    for name, service in services().items():
        held = [str(value) for value in dict(service.get("environment", {})).values()]
        if any(value.startswith(owner) for value in held):
            assert name in {"migrate", "install"}, name
    for name in ("api", "worker", "scheduler"):
        assert environment(name)["WATERFALL_DATABASE_URL"].startswith(
            "postgresql://waterfall_service:"
        )
    script = (COMPOSE / "backup-database-role.sql").read_text(encoding="utf-8")
    assert "GRANT pg_read_all_data TO waterfall_backup;" in script
    assert "NOSUPERUSER" in script


def test_the_owner_of_the_tables_is_no_superuser_and_the_administrator_initialises_alone() -> None:
    # #701, #895: postgres is the administrator of the server; waterfall owns the database and its
    # tables, and can create neither a role nor a database. The password of the administrator is
    # held by the server and the services that create the roles and the databases, then stop.
    assert environment("postgres")["POSTGRES_USER"] == "postgres"
    assert "POSTGRES_DB" not in environment("postgres")
    administrator = required("WATERFALL_POSTGRES_ADMIN_PASSWORD")
    initialising = {
        "waterfall-database",
        "service-database-role",
        "backup-database-role",
        "keycloak-database",
    }
    holders = {
        name
        for name, service in services().items()
        if administrator in [str(value) for value in dict(service.get("environment", {})).values()]
    }
    assert holders == {"postgres", *initialising}
    for name in initialising:
        assert services()[name]["restart"] == "no", name
        assert environment(name)["PGUSER"] == "postgres", name
    script = (COMPOSE / "waterfall-database.sql").read_text(encoding="utf-8")
    assert (
        "ALTER ROLE waterfall LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
        in script
    )
    assert "CREATE DATABASE waterfall OWNER waterfall" in script
    assert "CREATE ROLE waterfall_service NOLOGIN" in script
    owner = required("WATERFALL_POSTGRES_PASSWORD")
    assert environment("waterfall-database")["OWNER_DATABASE_PASSWORD"] == owner
    assert f"postgresql://waterfall:{owner}@" in environment("migrate")["WATERFALL_DATABASE_URL"]
    assert services()["migrate"]["depends_on"] == {
        "waterfall-database": {"condition": "service_completed_successfully"}
    }


@pytest.mark.requirement("WF-ARC-0050-A")
def test_the_bootstrap_is_a_service_of_its_own_never_started_by_up() -> None:
    # The bootstrap holds the secret of its client alone (#652), as the owner of the tables (#701):
    # `docker compose run --rm install`.
    install = services()["install"]
    assert install["profiles"] == ["install"]
    assert install["command"] == ["waterfall-api", "install"]
    # Run alone, it waits for the schema migrated and for the realm whose client it uses.
    done = {"condition": "service_completed_successfully"}
    healthy = {"condition": "service_healthy"}
    assert install["depends_on"] == {
        "postgres": healthy,
        "migrate": done,
        "keycloak": healthy,
        "keycloak-realm": done,
    }
    holders = [
        name
        for name, service in services().items()
        if "WATERFALL_INSTALLATION_CLIENT_SECRET" in dict(service.get("environment", {}))
        and name != "keycloak-realm"
    ]
    assert holders == ["install"]


def test_a_local_name_makes_the_front_trust_the_authority_of_caddy() -> None:
    front = compose(LOCAL)["services"]["front"]
    assert front["environment"]["NODE_EXTRA_CA_CERTS"] == "/authority/root.crt"
    assert "authority:/authority:ro" in front["volumes"]


def test_the_chain_tries_the_platform_in_the_full_tier_and_on_the_images_published() -> None:
    chain = yaml.safe_load((WORKFLOWS / "ci.yml").read_text(encoding="utf-8"))["jobs"]
    assert "production" in chain["gate"]["needs"]
    assert chain["production"]["uses"] == "./.github/workflows/production.yml"
    assert "tier == 'full'" in chain["production"]["if"]
    trial = yaml.safe_load((WORKFLOWS / "production.yml").read_text(encoding="utf-8"))
    step = trial["jobs"]["trial"]["steps"][-1]
    assert (step["run"], step["env"]) == ("make check-production", {"TIER": "full"})
    published = yaml.safe_load((WORKFLOWS / "images.yml").read_text(encoding="utf-8"))
    job = published["jobs"]["trial"]
    assert job["needs"] == "publish"
    assert job["steps"][-1] == {
        "env": {"WATERFALL_IMAGE_TAG": "${{ github.sha }}"},
        "run": "make production-trial",
    }
    assert set(job["env"]) == set(trial["jobs"]["trial"]["env"])


def test_a_change_of_the_platform_or_of_its_trial_wakes_the_production_family() -> None:
    declaration = paths.read()
    mounted = [
        f"deploy/compose/{Path(volume.split(':')[0]).name}"
        for service in services().values()
        for volume in service.get("volumes", [])
        if str(volume).startswith("./")
    ]
    for changed in (
        "deploy/compose/compose.prod.yaml",
        "deploy/compose/compose.prod.local.yaml",
        "deploy/compose/production.env.example",
        "tools/src/wftools/production.py",
        *mounted,
    ):
        assert "production" in {family.name for family in declaration.touched([changed])}, changed


def test_the_address_carries_the_port_of_https_unless_it_is_443() -> None:
    assert PLATFORM.address == "https://waterfall.localhost"
    assert Platform("demo.example", 44443, 44080).address == "https://demo.example:44443"
    assert production.platform_of({"WATERFALL_HTTPS_PORT": "8443"}).https_port == 8443
    with pytest.raises(ProductionError, match="not a number"):
        production.platform_of({"WATERFALL_HTTP_PORT": "eighty"})


def test_the_link_of_the_bootstrap_is_read_alone_under_the_address_of_the_platform() -> None:
    assert production.installation_link(f"{LINK}\n", PLATFORM) == LINK
    for output in ("", f"{LINK}\n{LINK}\n", "https://elsewhere.example/auth/x\n"):
        with pytest.raises(ProductionError, match="no link"):
            production.installation_link(output, PLATFORM)


def test_the_liveness_probe_must_say_ok() -> None:
    production.check_liveness('{"status": "ok"}\n')
    with pytest.raises(ProductionError, match="says 'down'"):
        production.check_liveness('{"status": "down"}')
    with pytest.raises(ProductionError, match="does not read"):
        production.check_liveness("Traceback")


def answer(status: int, body: str = "", **headers: str | list[str]) -> Answer:
    """Make an answer, each header given once, or several times by a list."""
    pairs = [
        (name.replace("_", "-"), value)
        for name, values in headers.items()
        for value in ([values] if isinstance(values, str) else values)
    ]
    return Answer(status, tuple(pairs), body)


@dataclass(frozen=True, slots=True)
class Asked:
    """A request the fake platform receives: its method, its query, its form, its cookies."""

    method: str
    query: str
    form: dict[str, str]
    cookie: str


type Route = Callable[[Asked], Answer]


def fixed(status: int, body: str = "", **headers: str | list[str]) -> Route:
    """Make a route that answers every request the same."""

    def route(_asked: Asked) -> Answer:
        return answer(status, body, **headers)

    return route


class FakePlatform:
    """Caddy, the front and Keycloak as a test plays them, by path; it records each request.

    Caddy sends HTTP to the same page at ``address``, sets ``secured`` on every answer in HTTPS,
    and answers 404 for the console of Keycloak and its realm master, unless a route serves them.
    """

    def __init__(
        self,
        routes: Mapping[str, Route],
        *,
        address: str = ADDRESS,
        secured: Mapping[str, str] = production.SECURITY_HEADERS,
    ) -> None:
        self.routes = routes
        self.address = address
        self.secured = secured
        self.requests: list[tuple[str, str, dict[str, str]]] = []

    def send(self, method: str, url: str, body: bytes | None, headers: Mapping[str, str]) -> Answer:
        parts = urlsplit(url)
        if parts.scheme == "http":
            return answer(308, Location=f"{self.address}{parts.path}")
        if parts.path in production.HIDDEN and parts.path not in self.routes:
            return self.secure(answer(404))
        form = {key: values[0] for key, values in parse_qs((body or b"").decode()).items()}
        self.requests.append((method, parts.path, dict(headers)))
        asked = Asked(method, parts.query, form, headers.get("Cookie", ""))
        return self.secure(self.routes[parts.path](asked))

    def secure(self, given: Answer) -> Answer:
        """Add the headers Caddy sets on every answer in HTTPS."""
        return Answer(given.status, (*given.headers, *self.secured.items()), given.body)


LOGIN = f"{ADDRESS}/auth/realms/waterfall/protocol/openid-connect/auth?client_id=waterfall-front"
SESSION = "__Host-wf_session=opaque; Path=/; Secure; HttpOnly; SameSite=Lax"
CONFIRMATION = '<a href="/auth/realms/waterfall/login-actions/action-token?key=abc&amp;go=1">'
CHOOSING_FORM = '<form action="/auth/realms/waterfall/password"><input name="password-new">'


def action_token(asked: Asked) -> Answer:
    """Open the link of the bootstrap: its confirmation, then the form of the password."""
    return answer(200, CHOOSING_FORM if "go=1" in asked.query else CONFIRMATION)


def realm_authorization(asked: Asked) -> Answer:
    """Open the form of the realm; give the front its code at once on a session already open."""
    query = parse_qs(asked.query)
    if "AUTH_SESSION_ID" in asked.cookie and "state" in query:
        location = f"{ADDRESS}/auth/callback?code=c&state={query['state'][0]}"
        return answer(302, Location=location)
    return answer(
        200,
        '<form id="kc-form-login" action="/auth/realms/waterfall/authenticate?x=1&amp;y=2">',
        Set_Cookie=["KC_RESTART=r; Path=/auth/realms/waterfall/", "AUTH_SESSION_ID=a; Path=/"],
    )


def realm_routes(*, signed_in: bool = True, named: bool = True) -> dict[str, Route]:
    """Play the link of the bootstrap, the sign-in through the realm, the account of the front."""
    callback = f"{ADDRESS}/auth/callback?code=c&state=s"
    return {
        "/": lambda asked: answer(
            200 if "wf_session" in asked.cookie else 307, "home", Location="/login"
        ),
        "/login": fixed(307, Location=LOGIN, Set_Cookie="wf_pending=p; Path=/"),
        "/auth/realms/waterfall/login-actions/action-token": action_token,
        "/auth/realms/waterfall/password": lambda asked: answer(
            200 if asked.form["password-new"] == asked.form["password-confirm"] else 400
        ),
        "/auth/realms/waterfall/protocol/openid-connect/auth": realm_authorization,
        "/auth/realms/waterfall/protocol/openid-connect/token": fixed(200, '{"access_token": "t"}'),
        "/auth/realms/waterfall/authenticate": lambda asked: answer(
            302 if signed_in and asked.form["username"] == EMAIL else 200, Location=callback
        ),
        "/auth/callback": fixed(
            303, Location="/", Set_Cookie=[SESSION, "wf_pending=; Path=/; Max-Age=0"]
        ),
        "/account": fixed(200, f"<p>{EMAIL if named else 'someone'}</p>"),
    }


def test_a_browser_keeps_the_cookies_of_the_platform_and_forgets_those_it_removes() -> None:
    platform = FakePlatform(realm_routes())
    browser = Browser(platform.send)
    browser.open(f"{ADDRESS}/login")
    assert browser.cookies == {"wf_pending": "p", "KC_RESTART": "r", "AUTH_SESSION_ID": "a"}
    browser.request("GET", f"{ADDRESS}/auth/callback")
    assert "wf_pending" not in browser.cookies
    assert browser.cookies["__Host-wf_session"] == "opaque"


def test_a_page_that_redirects_without_end_is_refused() -> None:
    loop = FakePlatform({"/": fixed(302, Location="/")})
    with pytest.raises(ProductionError, match="more than 20 redirections"):
        Browser(loop.send).open(f"{ADDRESS}/")


def test_a_page_without_a_form_cannot_be_submitted() -> None:
    with pytest.raises(ProductionError, match="no form on /x"):
        Browser(FakePlatform({}).send).submit(answer(200, "<p>"), f"{ADDRESS}/x", {})


@pytest.mark.requirement("WF-ARC-0050-A")
def test_the_first_administrator_sets_their_password_signs_in_and_is_named_by_the_front() -> None:
    # « … et les tests de la chaîne CI/CD s'exécutent contre elle. » : the trial follows the link of
    # the bootstrap, then the sign-in from the front to Keycloak under /auth and back.
    platform = FakePlatform(realm_routes())
    browser = Browser(platform.send)
    production.set_password(browser, LINK, "Trial-password")
    landed = production.sign_in(browser, PLATFORM, EMAIL, "Trial-password")
    production.check_signed_in(browser, PLATFORM, EMAIL)
    assert landed.body == "home"
    posted = [(path, headers) for method, path, headers in platform.requests if method == "POST"]
    assert [path for path, _ in posted] == [
        "/auth/realms/waterfall/password",
        "/auth/realms/waterfall/authenticate",
    ]
    assert all(h["Content-Type"] == "application/x-www-form-urlencoded" for _, h in posted)


def test_a_link_that_opens_no_confirmation_or_no_form_is_refused() -> None:
    spent = {"/auth/realms/waterfall/login-actions/action-token": fixed(400, "x")}
    with pytest.raises(ProductionError, match="opens no confirmation"):
        production.set_password(Browser(FakePlatform(spent).send), LINK, "p")
    again = {"/auth/realms/waterfall/login-actions/action-token": fixed(200, CONFIRMATION)}
    with pytest.raises(ProductionError, match="no form of a password"):
        production.set_password(Browser(FakePlatform(again).send), LINK, "p")


def test_a_refused_password_fails_the_trial() -> None:
    routes = {**realm_routes(), "/auth/realms/waterfall/password": fixed(400)}
    with pytest.raises(ProductionError, match="password of the first administrator is not set"):
        production.set_password(Browser(FakePlatform(routes).send), LINK, "p")


@pytest.mark.parametrize(
    ("routes", "said"),
    [
        (realm_routes(signed_in=False), "is not signed in: /auth/realms/waterfall/authenticate"),
        (
            {**realm_routes(), "/login": fixed(200, "<form action='/x'>")},
            "does not send to the realm under /auth",
        ),
        (
            {**realm_routes(), "/auth/callback": fixed(303, Location="/account")},
            "opened no session",
        ),
    ],
    ids=["refused", "elsewhere", "no-session"],
)
def test_a_sign_in_that_does_not_open_a_session_on_the_front_fails(
    routes: dict[str, Route], said: str
) -> None:
    with pytest.raises(ProductionError, match=said):
        production.sign_in(Browser(FakePlatform(routes).send), PLATFORM, EMAIL, "p")


def test_an_account_that_does_not_name_the_administrator_fails() -> None:
    browser = Browser(FakePlatform(realm_routes(named=False)).send)
    with pytest.raises(ProductionError, match="does not name them: /account"):
        production.check_signed_in(browser, PLATFORM, EMAIL)


@pytest.mark.requirement("WF-SEC-0010-A")
def test_http_must_send_to_the_same_page_at_the_published_address() -> None:
    production.check_https_alone(Browser(FakePlatform({}).send), PLATFORM)
    moved = Platform("waterfall.localhost", 44443, 44080)
    sent = FakePlatform({}, address=moved.address)
    production.check_https_alone(Browser(sent.send), moved)

    def clear(_method: str, _url: str, _body: bytes | None, _headers: Mapping[str, str]) -> Answer:
        return answer(200, "the front in clear")

    with pytest.raises(ProductionError, match="HTTP answered 200"):
        production.check_https_alone(Browser(clear), PLATFORM)


def test_a_redirection_to_https_that_leaves_out_the_published_port_fails() -> None:
    # Caddy's own redirection names the port of the container, 443: the browser would knock on a
    # port the machine does not publish.
    moved = Platform("waterfall.localhost", 44443, 44080)
    portless = FakePlatform({}, address="https://waterfall.localhost")
    with pytest.raises(
        ProductionError,
        match=r"to 'https://waterfall.localhost/login', not a redirection to "
        r"https://waterfall.localhost:44443/login",
    ):
        production.check_https_alone(Browser(portless.send), moved)


@pytest.mark.requirement("WF-SEC-0010-A")
def test_an_answer_in_https_carries_hsts_and_the_headers_of_caddy() -> None:
    production.check_security_headers(Browser(FakePlatform(realm_routes()).send), PLATFORM)


@pytest.mark.parametrize(
    ("secured", "said"),
    [
        ({}, "Strict-Transport-Security: None"),
        (
            {**production.SECURITY_HEADERS, "Strict-Transport-Security": "max-age=0"},
            "Strict-Transport-Security: 'max-age=0'",
        ),
        (
            {**production.SECURITY_HEADERS, "X-Frame-Options": "ALLOWALL"},
            "X-Frame-Options: 'ALLOWALL'",
        ),
    ],
    ids=["no-hsts", "hsts-off", "framed"],
)
def test_an_answer_in_https_without_hsts_or_a_header_of_caddy_fails(
    secured: dict[str, str], said: str
) -> None:
    fake = FakePlatform(realm_routes(), secured=secured)
    with pytest.raises(ProductionError, match=f"/login answered {said} in HTTPS"):
        production.check_security_headers(Browser(fake.send), PLATFORM)


def test_the_console_of_keycloak_and_its_realm_master_must_not_be_served() -> None:
    production.check_console_hidden(Browser(FakePlatform({}).send), PLATFORM)
    served = FakePlatform({path: fixed(200) for path in production.HIDDEN})
    with pytest.raises(ProductionError, match="/auth/admin/ answered 200, not 404"):
        production.check_console_hidden(Browser(served.send), PLATFORM)


class Docker:
    """A Compose that answers as a test tells it, and records what it is asked."""

    def __init__(
        self,
        *,
        up: int = 0,
        installed: str = f"{LINK}\n",
        live: str = '{"status": "ok"}',
        rights: str = "f|f|f\n",
        failing: bool = False,
    ) -> None:
        self.failing = failing
        self.rights = rights
        self.up = up
        self.installed = installed
        self.live = live
        self.ran: list[list[str]] = []

    def run(self, command: list[str]) -> int:
        self.ran.append(command)
        return self.up if "up" in command else 0

    def read(self, command: list[str]) -> tuple[int, str]:
        self.ran.append(command)
        if self.failing:
            return 1, ""
        if "install" in command:
            return 0, self.installed
        if "exec" in command:
            return 0, self.rights if "postgres" in command else self.live
        if "cp" in command:
            Path(command[-1]).write_text("root", encoding="utf-8")
        return 0, ""

    def verbs(self) -> list[str]:
        known = ("up", "run", "exec", "cp", "logs", "down")
        return [next(word for word in command if word in known) for command in self.ran]


def platform_sender(fake: FakePlatform) -> Callable[[Platform], Callable[[Path], production.Send]]:
    """Give the trial a sender that reaches the fake platform, the root of its authority read."""

    def make(_platform: Platform) -> Callable[[Path], production.Send]:
        def trusted(authority: Path) -> production.Send:
            assert authority.read_text(encoding="utf-8") == "root"
            return fake.send

        return trusted

    return make


TAG = "0123456789abcdef0123456789abcdef01234567"
GIVEN = {"WATERFALL_IMAGE_TAG": TAG, "WATERFALL_PRODUCTION_PROJECT": "trial-a3"}


@pytest.mark.requirement("WF-ARC-0050-A")
def test_the_trial_starts_bootstraps_holds_and_removes_the_platform(
    capsys: pytest.CaptureFixture[str],
) -> None:
    docker = Docker()
    fake = FakePlatform(realm_routes())
    assert production.main(GIVEN, docker.run, docker.read, platform_sender(fake)) == 0
    assert docker.verbs() == ["up", "run", "exec", "exec", "cp", "down"]
    assert docker.ran[0][:5] == ["docker", "compose", "--project-name", "trial-a3", "--file"]
    assert docker.ran[0][-4:] == ["up", "--detach", "--wait", "--quiet-pull"]
    assert docker.ran[-1][-2:] == ["down", "--volumes"]
    said = capsys.readouterr().out
    assert f"the images {TAG}, at https://waterfall.localhost" in said
    assert "HTTP sends to https://waterfall.localhost\n" in said
    assert "HTTPS answers with Strict-Transport-Security, X-Content-Type-Options" in said
    assert "/auth/admin/ and /auth/realms/master/ answer 404" in said
    assert "signs in at https://waterfall.localhost, and the front names them" in said
    assert "the backup and its restoration are left out (WATERFALL_TRIAL_RESTORATION)" in said


class Container:
    """The container of the API, asked by the trial: a backup, then its restoration, succeed."""

    def __init__(self) -> None:
        self.asked: list[tuple[str, str]] = []

    def ask(self, command: list[str], given: str) -> tuple[int, str]:
        assert command[-3:-1] == ["python", "-c"]
        asked = json.loads(given)
        self.asked.append((asked["method"], asked["path"]))
        backup = {"backup_id": "b1", "taken_at": "2026-06-02T01:00:00Z", "verification": "passed"}
        bodies: dict[str, tuple[int, object]] = {
            "/backups": (202, {"task_id": "b"}),
            "/backups?limit=1": (200, {"items": [backup]}),
            "/restores": (202, {"task_id": "r"}),
        }
        status, body = bodies.get(asked["path"], (200, {"status": "succeeded"}))
        return 0, json.dumps({"status": status, "body": json.dumps(body)})


@pytest.mark.requirement("WF-ARC-0050-A")
def test_the_trial_backs_up_and_restores_by_the_api_when_asked_to(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # #948, point 2: asked for by its variable until the chain starts the service of the
    # restoration, the trial backs the platform up by its API and restores it.
    docker = Docker()
    container = Container()
    fake = FakePlatform(realm_routes())
    given = {**GIVEN, "WATERFALL_TRIAL_RESTORATION": "1"}
    sender = platform_sender(fake)
    assert production.main(given, docker.run, docker.read, sender, container.ask) == 0
    assert container.asked == [
        ("POST", "/backups"),
        ("GET", "/tasks/b"),
        ("GET", "/backups?limit=1"),
        ("POST", "/restores"),
        ("GET", "/tasks/r"),
    ]
    said = capsys.readouterr().out
    assert "its restoration asked of the API has ended: the probe says ok" in said
    assert docker.verbs()[-2:] == ["exec", "down"]


def test_the_owner_of_the_tables_must_be_no_superuser(capsys: pytest.CaptureFixture[str]) -> None:
    production.check_owner("f|f|f\n")
    for rights in ("t|f|f", "f|t|f", "f|f|t", ""):
        with pytest.raises(ProductionError, match="waterfall, is a superuser"):
            production.check_owner(rights)
    docker = Docker(rights="t|t|t\n")
    fake = FakePlatform(realm_routes())
    assert production.main(GIVEN, docker.run, docker.read, platform_sender(fake)) == 1
    asked = docker.ran[3]
    assert asked[asked.index("exec") :][:6] == [
        "exec",
        "-T",
        "postgres",
        "psql",
        "--username=postgres",
        "--no-psqlrc",
    ]
    assert f"--command={production.OWNER_RIGHTS}" in asked
    assert "is a superuser" in capsys.readouterr().err


def test_a_platform_that_does_not_start_is_said_and_removed() -> None:
    docker = Docker(up=1)
    fake = FakePlatform({})
    assert production.main(GIVEN, docker.run, docker.read, platform_sender(fake)) == 1
    assert docker.verbs() == ["up", "logs", "down"]


def test_a_bootstrap_that_writes_no_link_fails_the_trial_and_removes_the_platform(
    capsys: pytest.CaptureFixture[str],
) -> None:
    docker = Docker(installed="nothing\n")
    assert production.main(GIVEN, docker.run, docker.read, platform_sender(FakePlatform({}))) == 1
    assert docker.verbs() == ["up", "run", "logs", "down"]
    assert "the bootstrap wrote no link" in capsys.readouterr().err


def test_a_command_of_compose_that_fails_fails_the_trial(
    capsys: pytest.CaptureFixture[str],
) -> None:
    docker = Docker(failing=True)
    assert production.main(GIVEN, docker.run, docker.read, platform_sender(FakePlatform({}))) == 1
    assert docker.verbs() == ["up", "run", "logs", "down"]
    assert "install failed (1)" in capsys.readouterr().err


def test_the_environment_of_compose_takes_the_defaults_of_a_local_trial() -> None:
    started = production.environment_of({"X": "y"}, TAG, PLATFORM)
    assert started == {
        "X": "y",
        "WATERFALL_IMAGE_TAG": TAG,
        "WATERFALL_DOMAIN": "waterfall.localhost",
        "WATERFALL_ADMIN_EMAIL": EMAIL,
        "WATERFALL_ACME_EMAIL": EMAIL,
    }
    command = production.compose_command("p")
    assert command[-4:] == ["--file", str(PRODUCTION), "--file", str(LOCAL)]
