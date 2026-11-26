# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The production platform on a network without a way out, and its images from a registry inside.

US-3010 (WF-CMP-0030): the trial of the production Compose runs it on networks that have no route
out, each service resolving through the sink of the names, and fails on any name asked that is not
the platform's (``compose.isolated.yaml``, ``wftools.egress``). The registry of the images is a
setting of the Compose and a value of the chart, which every image follows; the documentation of the
operation names each image to copy into it. The Compose files are read as Compose resolves them.
"""

import json
import os
import re
import shutil
import subprocess
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from test_supervision import services

from wftools import REPOSITORY, chart, production
from wftools.production import ProductionError

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.story("US-3010")

COMPOSE = REPOSITORY / "deploy" / "compose"
PRODUCTION = COMPOSE / "compose.prod.yaml"
LOCAL = COMPOSE / "compose.prod.local.yaml"
ISOLATED = COMPOSE / "compose.isolated.yaml"
RESTORE_TEST = COMPOSE / "compose.restore-test.yaml"
DOCUMENTATION = REPOSITORY / "docs" / "exploitation" / "reseau-isole.md"
ZERO = "sha256:" + "0" * 64
# The variables the Compose files require, as ``make lint-compose`` stands them in.
STAND_IN = {
    "WATERFALL_DOMAIN": "waterfall.localhost",
    "WATERFALL_ACME_EMAIL": "stand-in",
    "WATERFALL_DIGEST_FRONT": ZERO,
    "WATERFALL_DIGEST_WATERFALL": ZERO,
    "WATERFALL_DIGEST_KEYCLOAK": ZERO,
    "WATERFALL_ADMIN_EMAIL": "stand-in",
    "WATERFALL_SERVER_ACTIONS_KEY": "stand-in",
    "WATERFALL_CURRENCY": "EUR",
    "WATERFALL_COMPANY_NAME": "stand-in",
    "WATERFALL_DATABASE_CAPACITY_BYTES": "1",
    "WATERFALL_STORAGE_CAPACITY_BYTES": "1",
    "WATERFALL_RESTORE_TEST_PASSWORD": "stand-in",
    **{
        f"WATERFALL_{name}": "stand-in"
        for name in (
            "POSTGRES_ADMIN_PASSWORD",
            "POSTGRES_PASSWORD",
            "SERVICE_DATABASE_PASSWORD",
            "BACKUP_DATABASE_PASSWORD",
            "REDIS_PASSWORD",
            "KEYCLOAK_DATABASE_PASSWORD",
            "KEYCLOAK_ADMIN_PASSWORD",
            "FRONT_CLIENT_SECRET",
            "SERVICE_CLIENT_SECRET",
            "INSTALLATION_CLIENT_SECRET",
            "STORAGE_SECRET",
            "STORAGE_RPC_SECRET",
            "GRAFANA_ADMIN_PASSWORD",
        )
    },
}
INSIDE = "registre.interne:5000"
SETTINGS = {"WATERFALL_REGISTRY": f"{INSIDE}/waterfall", "WATERFALL_MIRROR": f"{INSIDE}/hub/"}
SINK = "egress-sink"
DOOR = "door"
NO_DOCKER = pytest.mark.skipif(shutil.which("docker") is None, reason="docker is not installed")
UNEXECUTED = pytest.mark.unexecuted("skipped where docker is not installed")
MIRRORED = re.compile(r"^\$\{WATERFALL_MIRROR:-\}(\S+@sha256:[0-9a-f]{64})$")
PINNED_LINE = re.compile(r"^[\w./-]+:[\w.-]+@sha256:[0-9a-f]{64}$", re.MULTILINE)


def compose(*files: Path, given: dict[str, str] | None = None, images: bool = False) -> Any:
    """Resolve Compose files as Compose reads them: the configuration, or the images it pulls."""
    command = ["docker", "compose", *(word for path in files for word in ("-f", str(path)))]
    asked = ["--images"] if images else ["--format", "json"]
    done = subprocess.run(
        [*command, "--profile", "install", "--profile", "restore-test", "config", *asked],
        env={**os.environ, **STAND_IN, **(given or {})},
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return done.stdout.split() if images else json.loads(done.stdout)


@pytest.fixture(scope="module")
def isolated() -> dict[str, Any]:
    return compose(PRODUCTION, LOCAL, ISOLATED)


@NO_DOCKER
@UNEXECUTED
def test_every_network_of_the_platform_is_internal_but_the_door_s_which_it_alone_joins(
    isolated: dict[str, Any],
) -> None:
    networks = isolated["networks"]
    assert {name for name, network in networks.items() if not network.get("internal")} == {DOOR}
    joined = {name for name, service in isolated["services"].items() if DOOR in service["networks"]}
    assert joined == {DOOR}


@NO_DOCKER
@UNEXECUTED
def test_the_door_alone_publishes_and_relays_http_and_https_to_caddy(
    isolated: dict[str, Any],
) -> None:
    services = isolated["services"]
    published = {name for name, service in services.items() if service.get("ports")}
    assert published == {DOOR}
    door = services[DOOR]
    assert [(port["published"], port["target"]) for port in door["ports"]] == [
        ("80", 8080),
        ("443", 8443),
    ]
    assert door["command"][-2:] == ["8080:caddy:80", "8443:caddy:443"]
    # The door stands for the firewall: it runs nothing of Waterfall, and the sink nothing either.
    for name in (DOOR, SINK):
        assert "waterfall" not in services[name]["image"], name


@NO_DOCKER
@UNEXECUTED
def test_every_service_resolves_through_the_sink_and_waits_for_it(
    isolated: dict[str, Any],
) -> None:
    services = isolated["services"]
    sink = services[SINK]["networks"]
    addresses = {network: joined["ipv4_address"] for network, joined in sink.items()}
    assert set(addresses) == set(isolated["networks"]) - {DOOR, "front"}
    resolved: set[str] = set()
    for name, service in services.items():
        if name in {SINK, DOOR}:
            continue
        reachable = {addresses[network] for network in service["networks"] if network in addresses}
        assert service.get("dns", [None])[0] in reachable, name
        assert service["depends_on"][SINK]["condition"] == "service_healthy", name
        resolved.add(name)
    # Keycloak and the supervision included, and every service the production defines.
    assert {"keycloak", "keycloak-realm", "prometheus", "alertmanager", "grafana"} <= resolved
    assert set(compose(PRODUCTION, LOCAL)["services"]) <= resolved


@NO_DOCKER
@UNEXECUTED
def test_every_service_that_resolves_has_no_search_domain_to_add_after_a_name(
    isolated: dict[str, Any],
) -> None:
    # The host's search domain, a runner's, would follow a name not found — keycloak while it
    # restarts — and the sink would name keycloak.<domain>, a server outside that was never asked.
    services = isolated["services"]
    for name, service in services.items():
        if name not in {SINK, DOOR}:
            assert service.get("dns_search") == ["."], name


def test_the_trial_runs_the_platform_isolated() -> None:
    # Proper to US-3010: « la chaîne échoue sur toute tentative de connexion au-dehors ».
    assert production.FILES[-1] == ISOLATED
    command = production.compose_command("trial")
    assert command[-2:] == ["--file", str(ISOLATED)]
    assert production.SINK in services(ISOLATED)


class Logs:
    """What the trial reads at its end: the lines of the sink, and the networks of the platform."""

    def __init__(self, written: str) -> None:
        self.written = written
        self.asked: list[list[str]] = []

    def read(self, command: list[str]) -> tuple[int, str]:
        self.asked.append(command)
        if command[:3] == ["docker", "network", "inspect"]:
            containers = {"a1": {"Name": "trial-grafana-1", "IPv4Address": "10.213.0.7/24"}}
            return 0, f"{json.dumps(containers)}\n{json.dumps(None)}\n"
        return 0, self.written


def test_the_trial_passes_when_no_name_out_of_the_platform_was_asked(
    capsys: pytest.CaptureFixture[str],
) -> None:
    logs = Logs("the sink answers on 53\nquery 10.213.0.9 1 keycloak\n")
    production.check_no_egress(["compose"], logs.read, "trial", "waterfall.localhost")
    assert logs.asked == [["compose", "logs", "--no-color", "--no-log-prefix", SINK]]
    assert "no component asked for a server outside the platform" in capsys.readouterr().out


def test_the_trial_fails_on_a_name_out_of_the_platform_naming_the_service() -> None:
    # Proper to US-3010: « la chaîne échoue sur toute tentative de connexion au-dehors ».
    logs = Logs(
        "query 10.213.0.7 1 grafana.com\nquery 10.213.0.8 28 pool.ntp.org\n"
        "query 10.213.0.7 1 waterfall.localhost\n"
    )
    with pytest.raises(ProductionError) as raised:
        production.check_no_egress(["compose"], logs.read, "trial", "waterfall.localhost")
    assert str(raised.value) == (
        "a component tried to leave the network of the platform: "
        "trial-grafana-1 asked for grafana.com; 10.213.0.8 asked for pool.ntp.org"
    )
    assert logs.asked[1][3:5] == ["trial_default", "trial_storage"]


def test_the_trial_names_a_service_that_ended_before_the_networks_were_read() -> None:
    # Proper to US-3010: « la chaîne échoue sur toute tentative de connexion au-dehors ».
    # migrate left the networks at the end of the trial: only its fixed address names it.
    address = f"10.213.0.{production.FIRST_ENDED + production.ENDED.index('migrate')}"
    logs = Logs(f"query {address} 28 pool.ntp.org\nquery 10.213.0.250 1 elsewhere.org\n")
    with pytest.raises(ProductionError) as raised:
        production.check_no_egress(["compose"], logs.read, "trial", "waterfall.localhost")
    assert str(raised.value) == (
        "a component tried to leave the network of the platform: "
        "migrate (ended) asked for pool.ntp.org; 10.213.0.250 asked for elsewhere.org"
    )


@NO_DOCKER
@UNEXECUTED
def test_every_service_that_runs_once_keeps_the_fixed_address_that_names_it() -> None:
    services = compose(PRODUCTION, LOCAL, ISOLATED)["services"]
    once = {name for name, service in services.items() if service.get("restart") == "no"}
    assert once == set(production.ENDED)
    for place, name in enumerate(production.ENDED):
        address = services[name]["networks"]["default"]["ipv4_address"]
        assert address == f"10.213.0.{production.FIRST_ENDED + place}", name


@NO_DOCKER
@UNEXECUTED
@pytest.mark.parametrize(
    "files", [(PRODUCTION, LOCAL), (RESTORE_TEST,)], ids=["production", "restore-test"]
)
def test_every_image_of_the_compose_is_read_from_the_registry_its_settings_name(
    files: tuple[Path, ...],
) -> None:
    # Proper to US-3010: « le registre des images est une valeur … du Compose ».
    images = compose(*files, given=SETTINGS, images=True)
    assert images
    assert [image for image in images if not image.startswith(f"{INSIDE}/")] == []
    assert {image.split("@")[0] for image in images} >= {f"{INSIDE}/waterfall/waterfall"}


def pod_images(document: dict[str, Any]) -> list[str]:
    """Give the image of every container of an object that runs pods, initialisation included."""
    spec = document.get("spec", {})
    template = spec.get("jobTemplate", {}).get("spec", spec).get("template", {}).get("spec", {})
    return [
        container["image"]
        for kind in ("initContainers", "containers")
        for container in template.get(kind, [])
    ]


@pytest.mark.chart
def test_every_image_of_the_chart_is_read_from_the_registry_its_values_name() -> None:
    # Proper to US-3010: « le registre des images est une valeur du chart ».
    values = {"images": {"registry": f"{INSIDE}/waterfall", "mirror": f"{INSIDE}/hub/"}}
    documents = [each for each in yaml.safe_load_all(chart.render(values)) if each]
    images = [image for document in documents for image in pod_images(document)]
    assert images
    assert [image for image in images if not image.startswith(f"{INSIDE}/")] == []
    named = {image.split("@")[0] for image in images}
    assert {f"{INSIDE}/waterfall/{name}" for name in ("front", "waterfall", "keycloak")} <= named


def third_parties() -> set[str]:
    """Give every image of a third party the production pulls, under Compose or the chart."""
    found: set[str] = set()
    for path in (PRODUCTION, LOCAL, RESTORE_TEST):
        text = path.read_text(encoding="utf-8")
        found |= {
            matched.group(1)
            for word in re.findall(r"\$\{WATERFALL_MIRROR:-\}\S+", text)
            if (matched := MIRRORED.match(word))
        }
    values = chart.defaults()
    found |= set(re.findall(r"[\w./-]+:[\w.-]+@sha256:[0-9a-f]{64}", yaml.safe_dump(values)))
    return found


def test_the_documentation_names_every_image_of_a_third_party_to_copy_and_no_other() -> None:
    # Proper to US-3010: « la documentation d'exploitation dit comment y charger les images ».
    text = DOCUMENTATION.read_text(encoding="utf-8")
    block = text.split("```text\n", 1)[1].split("```", 1)[0]
    assert set(PINNED_LINE.findall(block)) == third_parties()
    for setting in ("WATERFALL_REGISTRY", "WATERFALL_MIRROR", "images.registry", "images.mirror"):
        assert setting in text, setting


def test_the_documentation_names_the_mail_server_the_authority_and_the_time_server() -> None:
    # Proper to US-3010: « … le serveur de messagerie, l'autorité et le serveur de temps internes ».
    text = DOCUMENTATION.read_text(encoding="utf-8")
    headings = re.findall(r"^## (.+)$", text, re.MULTILINE)
    assert headings == [
        "Charger les images dans un registre interne",
        "Le serveur de messagerie interne",
        "L'autorité de certification interne",
        "Le serveur de temps interne",
        "Ce que la chaîne vérifie",
    ]
    for named in (
        "WATERFALL_ALERT_SMTP_HOST",
        "alertmanager.smtp",
        "WF-ADM-0140",
        "WATERFALL_AUTHORITY_DIRECTORY",
        "transport.authority",
        "ingress.tlsSecret",
        "chrony",
    ):
        assert named in text, named
