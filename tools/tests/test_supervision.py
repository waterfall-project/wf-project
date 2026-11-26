# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The supervision of the production platform under Compose (US-2880, WF-OBS-0030, #4229).

Prometheus is a service of compose.prod.yaml, which collects the front, the API and the worker and
evaluates the rules of the alerts, written at its start with the thresholds of .env
(prometheus.sh). What it needs of the other services is held here: the API declares the capacities
of the spaces, without which the alert of a full storage could never appear, and the worker serves
its metrics where Prometheus reaches it. The rules themselves are played by promtool, with the chart
(tools/tests/test_alerts.py, test_chartprometheus.py).
"""

import ipaddress
import os
import re
import subprocess
from typing import TYPE_CHECKING, Any, cast

import pytest
import yaml

from wftools import REPOSITORY, production
from wftools.images import IMAGES

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

COMPOSE = REPOSITORY / "deploy" / "compose"
PRODUCTION = COMPOSE / "compose.prod.yaml"
LOCAL = COMPOSE / "compose.prod.local.yaml"
SERVICE = COMPOSE / "compose.service.yaml"
TEMPLATE = COMPOSE / "production.env.example"
START = COMPOSE / "prometheus.sh"
MOUNTED = ("prometheus.sh", "prometheus.yml", "prometheus-alerts.yml")
TLS = ("prometheus-web.yml", "prometheus-client.yml")
# The thresholds WF-OBS-0030 ships: fifteen minutes, 85 %, 5 % over five minutes.
SHIPPED = {
    "WATERFALL_TASK_QUEUE_AGE_THRESHOLD_SECONDS": "900",
    "WATERFALL_STORAGE_USAGE_THRESHOLD": "0.85",
    "WATERFALL_ERROR_RATE_THRESHOLD": "0.05",
    "WATERFALL_ERROR_RATE_WINDOW_SECONDS": "300",
}
CAPACITIES = ("WATERFALL_DATABASE_CAPACITY_BYTES", "WATERFALL_STORAGE_CAPACITY_BYTES")
DEFAULTED = re.compile(r"^\$\{(WATERFALL_[A-Z0-9_]+):-([^}]*)\}$")


def services(path: Path = PRODUCTION) -> dict[str, Any]:
    """Read the services of a Compose file."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))["services"]


def environment(service: str, path: Path = PRODUCTION) -> dict[str, str]:
    """Read the environment of a service, its anchors merged."""
    return {name: str(value) for name, value in services(path)[service]["environment"].items()}


def defaults(variables: dict[str, str]) -> dict[str, str]:
    """Give the value each variable takes when .env does not set it."""
    found = {name: DEFAULTED.fullmatch(value) for name, value in variables.items()}
    return {name: match.group(2) for name, match in found.items() if match and match[1] == name}


@pytest.mark.requirement("WF-OBS-0030-A")
def test_the_api_does_not_start_without_the_capacities_of_the_spaces() -> None:
    # #4229: without a capacity, the metrics say no space left, and the alert of a storage at 85 %
    # could never appear, without a word. Compose refuses to start the API without them, naming
    # each; the model of .env names them.
    api = environment("api")
    for name in CAPACITIES:
        assert api[name] == f"${{{name}:?set {name} in .env}}", name
    template = TEMPLATE.read_text(encoding="utf-8")
    assert all(re.search(rf"^{name}=$", template, re.MULTILINE) for name in CAPACITIES)


@pytest.mark.requirement("WF-OBS-0030-A")
def test_the_worker_serves_its_metrics_on_every_interface_on_the_port_of_the_front() -> None:
    # #4229: the worker listens on the loopback alone unless told otherwise, where Prometheus would
    # not reach it; its port is the variable the front reads, and Prometheus collects both on it.
    worker = environment("worker")
    assert ipaddress.ip_address(worker["WATERFALL_HOST"]).is_unspecified
    port = "${WATERFALL_METRICS_PORT:-9100}"
    assert (
        worker["WATERFALL_METRICS_PORT"] == environment("front")["WATERFALL_METRICS_PORT"] == port
    )
    assert environment("prometheus")["WATERFALL_METRICS_PORT"] == port


@pytest.mark.story("US-2880")
def test_prometheus_is_a_service_of_the_platform_its_series_kept_in_a_volume() -> None:
    # Proper to US-2880: the platform delivers Prometheus, which collects and evaluates the rules,
    # by the Compose as by the chart; inside the network of the platform, published nowhere.
    prometheus = services()["prometheus"]
    assert prometheus["entrypoint"] == ["/bin/sh", "/etc/waterfall/prometheus.sh"]
    assert "ports" not in prometheus
    assert prometheus["restart"] == "unless-stopped"
    mounts = [str(volume) for volume in prometheus["volumes"]]
    read = [f"./{name}:/etc/waterfall/{name}:ro" for name in MOUNTED]
    # In TLS, with the certificate the authority issues it, and its health checked so (US-2840).
    in_tls = [f"./{name}:/etc/waterfall/{name}:ro" for name in TLS]
    assert mounts == [
        *read,
        *in_tls,
        "prometheus-data:/prometheus",
        "certificates-prometheus:/tls:ro",
    ]
    # The service platform runs the same image, on the same files, for the tests that read it; in
    # TLS too, with the certificate of the authority of its supervision.
    beside = services(SERVICE)["prometheus"]
    assert beside["image"] == prometheus["image"]
    assert beside["profiles"] == ["supervision"]
    assert [str(volume) for volume in beside["volumes"]] == [
        *read,
        *in_tls,
        "supervision-certificates-prometheus:/tls:ro",
    ]
    assert beside["command"] == [
        "--storage.tsdb.path=/prometheus",
        "--web.config.file=/etc/waterfall/prometheus-web.yml",
    ]


@pytest.mark.requirement("WF-OBS-0030-A")
def test_the_thresholds_are_settings_of_the_file_shipped_at_the_values_of_the_requirement() -> None:
    # « Les trois seuils sont des paramètres d'exploitation, livrés à quinze minutes, 85 % et 5 %
    # sur cinq minutes. » : read from .env, whose model gives the same values, as the service
    # platform.
    assert defaults(environment("prometheus")) == {**SHIPPED, "WATERFALL_METRICS_PORT": "9100"}
    assert defaults(environment("prometheus", SERVICE)) == SHIPPED
    template = TEMPLATE.read_text(encoding="utf-8")
    for name, value in SHIPPED.items():
        assert re.search(rf"^{name}={re.escape(value)}$", template, re.MULTILINE), name


@pytest.mark.requirement("WF-ADM-0130-A")
def test_the_api_presents_the_values_the_rules_and_the_worker_are_given() -> None:
    # #4636: the status screen presents the operating parameters in force, the thresholds the rules
    # of Prometheus are written with and the retention the purge of the worker applies, which the
    # API reads from the same variables, at the same defaults; it reads Prometheus in HTTPS
    # (TFX-14). The bootstrap writes the largest avatar, shipped at 512 KiB.
    api = environment("api")
    prometheus = environment("prometheus")
    for name in SHIPPED:
        assert api[name] == prometheus[name], name
    retention = "WATERFALL_BACKGROUND_TASK_RETENTION_DAYS"
    assert api[retention] == environment("worker")[retention] == f"${{{retention}:-30}}"
    assert api["WATERFALL_PROMETHEUS_ADDRESS"] == "https://prometheus:9090"
    avatar = "WATERFALL_AVATAR_MAX_BYTES"
    assert environment("install")[avatar] == f"${{{avatar}:-{512 * 1024}}}"
    assert re.search(
        rf"^# {avatar}={512 * 1024}$", TEMPLATE.read_text(encoding="utf-8"), re.MULTILINE
    )


def started(folder: Path, **given: str) -> subprocess.CompletedProcess[str]:
    """Start Prometheus as the Compose does, the thresholds shipped and those given, on nothing."""
    variables = {
        "PATH": os.environ["PATH"],
        "MODELS": str(COMPOSE),
        "RENDERED": str(folder),
        "PROMETHEUS": "echo",
        "WATERFALL_METRICS_PORT": "9100",
        **SHIPPED,
        **given,
    }
    return subprocess.run(
        ["sh", str(START), "--storage.tsdb.path=/prometheus"],
        env=variables,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.requirement("WF-OBS-0030-A")
def test_the_start_writes_the_thresholds_and_the_port_in_place_then_hands_over(
    tmp_path: Path,
) -> None:
    done = started(tmp_path, WATERFALL_METRICS_PORT="9200", WATERFALL_STORAGE_USAGE_THRESHOLD="0.9")
    assert done.returncode == 0, done.stderr
    configuration = tmp_path / "prometheus.yml"
    assert done.stdout.split() == [
        f"--config.file={configuration}",
        "--storage.tsdb.path=/prometheus",
    ]
    collected = yaml.safe_load(configuration.read_text(encoding="utf-8"))
    ports = {
        job["job_name"]: job["dns_sd_configs"][0]["port"] for job in collected["scrape_configs"]
    }
    assert ports == {"front": 9200, "api": 8000, "worker": 9200}
    rules = (tmp_path / "alerts.yml").read_text(encoding="utf-8")
    assert "${" not in rules
    assert ">= 0.9\n" in rules
    assert "> 900\n" in rules


@pytest.mark.requirement("WF-OBS-0030-A")
@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("WATERFALL_TASK_QUEUE_AGE_THRESHOLD_SECONDS", "15m"),
        ("WATERFALL_TASK_QUEUE_AGE_THRESHOLD_SECONDS", "0"),
        ("WATERFALL_ERROR_RATE_WINDOW_SECONDS", "-300"),
        ("WATERFALL_STORAGE_USAGE_THRESHOLD", "85"),
        ("WATERFALL_STORAGE_USAGE_THRESHOLD", "0"),
        ("WATERFALL_ERROR_RATE_THRESHOLD", "1.5"),
        ("WATERFALL_ERROR_RATE_THRESHOLD", ""),
        ("WATERFALL_ERROR_RATE_THRESHOLD", "0.05|g;s|x"),
        ("WATERFALL_ERROR_RATE_THRESHOLD", "0.05\nx|g;s|y"),
        ("WATERFALL_TASK_QUEUE_AGE_THRESHOLD_SECONDS", "900\n"),
        ("WATERFALL_METRICS_PORT", "70000"),
    ],
)
def test_a_threshold_that_is_not_one_stops_the_start_naming_it(
    tmp_path: Path, name: str, value: str
) -> None:
    done = started(tmp_path, **{name: value})
    assert done.returncode == 2
    assert name in done.stderr
    assert done.stdout == ""


@pytest.mark.parametrize("ratio", ["1", "1.0", "0.5", ".05", "0.001"])
def test_a_ratio_above_zero_and_at_most_one_is_a_threshold(tmp_path: Path, ratio: str) -> None:
    done = started(tmp_path, WATERFALL_ERROR_RATE_THRESHOLD=ratio)
    assert done.returncode == 0, done.stderr


def test_the_environment_of_compose_takes_the_defaults_of_a_local_trial() -> None:
    # The local trial of the platform declares a capacity of 10 GiB for each space, unless the
    # environment says another; it designates each image by its digest (#3726).
    platform = production.Platform("waterfall.localhost", 443, 80)
    email = "administrateur@waterfall.test"
    given = {"X": "y", "WATERFALL_STORAGE_CAPACITY_BYTES": "5"}
    pushed = {image.name: f"sha256:{index:064x}" for index, image in enumerate(IMAGES, start=1)}
    assert production.environment_of(given, platform, pushed) == {
        **given,
        **{f"WATERFALL_DIGEST_{name.upper()}": value for name, value in pushed.items()},
        "WATERFALL_DOMAIN": "waterfall.localhost",
        "WATERFALL_ADMIN_EMAIL": email,
        "WATERFALL_ACME_EMAIL": email,
        "WATERFALL_CURRENCY": "EUR",
        "WATERFALL_COMPANY_NAME": "Delmas Automatismes",
        "WATERFALL_DATABASE_CAPACITY_BYTES": "10737418240",
    }
    command = production.compose_command("p")
    assert command[-4:] == ["--file", str(PRODUCTION), "--file", str(LOCAL)]


TAG = "0123456789abcdef0123456789abcdef01234567"
GIVEN_DIGESTS = {
    f"WATERFALL_DIGEST_{image.name.upper()}": f"sha256:{index:064x}"
    for index, image in enumerate(IMAGES, start=1)
}
PUSHED = {image.name: "sha256:" + f"{index:x}" * 64 for index, image in enumerate(IMAGES, start=7)}


@pytest.mark.story("US-2800")
def test_the_trial_designates_each_image_by_the_digests_given_before_those_it_pushed() -> None:
    # The publication's digests, given, prevail: the trial of images.yml runs what it published.
    assert production.digests_of(GIVEN_DIGESTS, PUSHED) == GIVEN_DIGESTS


@pytest.mark.story("US-2800")
def test_the_trial_designates_each_image_by_the_digest_its_push_said_when_none_is_given() -> None:
    found = production.digests_of({}, PUSHED)
    assert found == {f"WATERFALL_DIGEST_{name.upper()}": PUSHED[name] for name in PUSHED}


@pytest.mark.story("US-2800")
def test_the_trial_refuses_two_digests_of_three_which_would_run_images_of_two_origins() -> None:
    given = {"WATERFALL_DIGEST_FRONT": GIVEN_DIGESTS["WATERFALL_DIGEST_FRONT"]}
    with pytest.raises(production.ProductionError, match=r"give the digests of the three images"):
        production.digests_of(given, PUSHED)


@pytest.mark.story("US-2800")
def test_the_trial_refuses_an_image_designated_otherwise_than_by_a_digest() -> None:
    given = {**GIVEN_DIGESTS, "WATERFALL_DIGEST_KEYCLOAK": "0.3.0"}
    with pytest.raises(
        production.ProductionError, match=r"WATERFALL_DIGEST_KEYCLOAK is not the digest"
    ):
        production.digests_of(given, PUSHED)


# A file of configuration that names a root to trust: Prometheus's ca_file, Grafana's $__file{}.
ROOT_FILE = re.compile(r"\$__file\{([^}]+)\}")
BIND = re.compile(r"^(?P<source>\./[^:]+):(?P<target>/[^:]*)(?::\w+)?$")
NAMED = re.compile(r"^(?P<source>[^./][^:]*):(?P<target>/[^:]*)(?::\w+)?$")


def roots_read(configuration: Any) -> Iterator[str]:
    """Give each root a file of configuration reads, wherever it names it."""
    if isinstance(configuration, dict):
        for key, value in cast("dict[str, Any]", configuration).items():
            if key == "ca_file" and isinstance(value, str):
                yield value
            else:
                yield from roots_read(value)
    elif isinstance(configuration, list):
        for value in cast("list[Any]", configuration):
            yield from roots_read(value)
    elif isinstance(configuration, str):
        yield from ROOT_FILE.findall(configuration)


def mounted(root: str, targets: list[str]) -> bool:
    """Tell whether a file is in one of the mounts of a service."""
    return any(root == target or root.startswith(f"{target.rstrip('/')}/") for target in targets)


def unmounted_roots(found: dict[str, Any], folder: Path = COMPOSE) -> list[str]:
    """Name each service that mounts a configuration whose root it does not mount."""
    faults: list[str] = []
    for name, service in found.items():
        volumes = [str(volume) for volume in service.get("volumes", [])]
        targets = [match["target"] for v in volumes if (match := BIND.match(v) or NAMED.match(v))]
        for volume in volumes:
            bound = BIND.match(volume)
            if bound is None or not bound["source"].endswith((".yml", ".yaml")):
                continue
            source = bound["source"]
            configuration = yaml.safe_load((folder / source).read_text(encoding="utf-8"))
            faults.extend(
                f"{name} reads {root} ({source}), which it does not mount"
                for root in roots_read(configuration)
                if not mounted(root, targets)
            )
    return faults


@pytest.mark.requirement("WF-SEC-0010-A")
@pytest.mark.parametrize("path", sorted(COMPOSE.glob("compose.*.yaml")), ids=lambda path: path.name)
def test_every_root_a_mounted_configuration_reads_is_mounted_too(path: Path) -> None:
    # A profile that mounts the configuration of the production, whose roots it does not mount,
    # does not start (US-2840): Prometheus checks Alertmanager against /tls/ca.crt, Grafana
    # Prometheus against /trust/root.crt.
    assert unmounted_roots(services(path)) == []


@pytest.mark.story("US-2840")
def test_a_configuration_mounted_without_its_root_is_named() -> None:
    found = services(SERVICE)
    taken = {
        "prometheus": {
            **found["prometheus"],
            "volumes": [v for v in found["prometheus"]["volumes"] if not v.endswith(":/tls:ro")],
        },
        "grafana": {
            **found["grafana"],
            "volumes": [v for v in found["grafana"]["volumes"] if not v.endswith(":/trust:ro")],
        },
    }
    assert unmounted_roots(taken) == [
        "prometheus reads /tls/ca.crt (./prometheus.yml), which it does not mount",
        "prometheus reads /tls/ca.crt (./prometheus-client.yml), which it does not mount",
        "grafana reads /trust/root.crt (./grafana-datasource.yml), which it does not mount",
    ]
