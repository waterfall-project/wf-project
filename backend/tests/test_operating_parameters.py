# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The operating parameters a process reads from its environment, and where it reaches Prometheus.

Each is set at the deployment, at its shipped value when not given (§4.5.1, WF-ARC-0050); a value
out of its bounds stops the process, naming the variable. Prometheus is reached in HTTPS, its
certificate checked against the root of the platform when the settings give it (TFX-14, US-2840).
"""

import os
import ssl
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from prometheus_support import TestPrometheus
from support import PLATFORM_ADDRESSES, PLATFORM_SECRETS

from waterfall.platform import authority
from waterfall.platform.prometheus import USED, Prometheus, PrometheusError
from waterfall.platform.settings import (
    InstallationSettings,
    OperatingParameters,
    SettingsError,
    load_api_settings,
    load_installation_settings,
)

if TYPE_CHECKING:
    from pathlib import Path

INSTALLATION = {
    "WATERFALL_INSTALLATION_CLIENT_SECRET": "installation-test-only",
    "WATERFALL_ADMIN_EMAIL": "admin@example.org",
    "WATERFALL_DEFAULT_LANGUAGE": "fr",
    "WATERFALL_CURRENCY": "EUR",
    "WATERFALL_COMPANY_NAME": "Delmas Automatismes",
}


@pytest.fixture
def environment(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Give the process the variables of the test platform, to which a test adds its own."""
    for name, value in {**PLATFORM_SECRETS, **PLATFORM_ADDRESSES, **INSTALLATION}.items():
        monkeypatch.setenv(name, value)
    return monkeypatch


@pytest.mark.story("US-2890")
def test_the_operating_parameters_are_shipped_at_the_values_of_the_specification(
    environment: pytest.MonkeyPatch,
) -> None:
    # Proper to US-2890: ten minutes, thirty days, fifteen minutes, 85 %, 5 % over five minutes;
    # and an avatar of 512 KB, which the bootstrap writes (#3965).
    del environment
    assert load_api_settings().operating_parameters() == OperatingParameters(
        cache_validity_seconds=600,
        background_task_retention_days=30,
        task_queue_age_threshold_seconds=900,
        storage_usage_threshold=Decimal("0.85"),
        error_rate_threshold=Decimal("0.05"),
        error_rate_window_seconds=300,
    )
    assert load_installation_settings().avatar_max_bytes == 512 * 1024
    assert load_api_settings().prometheus_address is None


@pytest.mark.story("US-2890")
def test_each_operating_parameter_is_read_from_its_variable(
    environment: pytest.MonkeyPatch,
) -> None:
    # Proper to US-2890: the value the deployment sets is the one in force.
    for name, value in {
        "WATERFALL_INDICATORS_CACHE_TTL": "30",
        "WATERFALL_BACKGROUND_TASK_RETENTION_DAYS": "7",
        "WATERFALL_TASK_QUEUE_AGE_THRESHOLD_SECONDS": "600",
        "WATERFALL_STORAGE_USAGE_THRESHOLD": "0.9",
        "WATERFALL_ERROR_RATE_THRESHOLD": "0.1",
        "WATERFALL_ERROR_RATE_WINDOW_SECONDS": "120",
        "WATERFALL_AVATAR_MAX_BYTES": "2097152",
    }.items():
        environment.setenv(name, value)
    assert load_api_settings().operating_parameters() == OperatingParameters(
        30, 7, 600, Decimal("0.9"), Decimal("0.1"), 120
    )
    assert load_installation_settings().avatar_max_bytes == 2 * 1024**2


@pytest.mark.story("US-2890")
@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("WATERFALL_STORAGE_USAGE_THRESHOLD", "0"),
        ("WATERFALL_ERROR_RATE_THRESHOLD", "1.5"),
        ("WATERFALL_TASK_QUEUE_AGE_THRESHOLD_SECONDS", "0"),
        ("WATERFALL_PROMETHEUS_ADDRESS", "prometheus:9090"),
    ],
)
def test_an_operating_parameter_out_of_its_bounds_stops_the_api_naming_it(
    environment: pytest.MonkeyPatch, name: str, value: str
) -> None:
    environment.setenv(name, value)
    with pytest.raises(SettingsError, match=name):
        load_api_settings()


@pytest.mark.story("US-2890")
@pytest.mark.parametrize("value", ["0", str(8 * 1024**2 + 1)])
def test_an_avatar_bound_out_of_its_bounds_stops_the_bootstrap_naming_it(
    environment: pytest.MonkeyPatch, value: str
) -> None:
    # Proper to US-2890: the bound of the installation, at most 8 MiB, as its table says.
    environment.setenv("WATERFALL_AVATAR_MAX_BYTES", value)
    with pytest.raises(SettingsError, match="WATERFALL_AVATAR_MAX_BYTES"):
        load_installation_settings()
    assert InstallationSettings.model_fields["avatar_max_bytes"].default == 524288


@pytest.mark.story("US-2880")
def test_prometheus_in_the_clear_is_refused_when_the_root_of_the_platform_is_given(
    environment: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Proper to US-2880: TFX-14 is in HTTPS; given the root, an address in the clear stops the API.
    root = rooted(tmp_path)[0]
    environment.setenv("WATERFALL_TLS_AUTHORITY", str(root))
    for name, value in ENCRYPTED.items():
        environment.setenv(name, value)
    environment.setenv("WATERFALL_PROMETHEUS_ADDRESS", "http://prometheus:9090")
    with pytest.raises(SettingsError, match="WATERFALL_PROMETHEUS_ADDRESS must be in https://"):
        load_api_settings()
    environment.setenv("WATERFALL_PROMETHEUS_ADDRESS", "https://prometheus:9090")
    assert load_api_settings().prometheus_address == "https://prometheus:9090"


# The addresses of a process given the root of the platform, each encrypted.
VERIFIED = "sslmode=verify-full&sslrootcert=/trust/root.crt"
ENCRYPTED = {
    "WATERFALL_DATABASE_URL": f"{PLATFORM_SECRETS['WATERFALL_DATABASE_URL']}?{VERIFIED}",
    "WATERFALL_REDIS_URL": PLATFORM_SECRETS["WATERFALL_REDIS_URL"].replace("redis:", "rediss:", 1),
    "WATERFALL_KEYCLOAK_BACKCHANNEL": "https://keycloak:8443/auth",
    "WATERFALL_STORAGE_ADDRESS": "https://storage:3900",
}


def rooted(folder: Path) -> tuple[Path, ssl.SSLContext]:
    """Give the root of a platform, and a server context with the certificate it signs."""
    provided = folder / "provided"
    provided.mkdir(parents=True)
    served = [authority.Served("localhost", os.getuid(), os.getgid())]
    authority.run(provided, folder / "kept", folder / "trust", folder / "certificates", served)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    certificates = folder / "certificates" / "localhost"
    context.load_cert_chain(certificates / "tls.crt", certificates / "tls.key")
    return folder / "trust" / "root.crt", context


@pytest.mark.story("US-2880")
def test_prometheus_is_reached_in_tls_its_certificate_checked_against_the_root(
    tmp_path: Path,
) -> None:
    # Proper to US-2880: the usual roots do not vouch for the platform's Prometheus; its root does.
    root, context = rooted(tmp_path)
    served = TestPrometheus(context)
    address = served.address.replace("http://127.0.0.1", "https://localhost")
    served.holds(USED, [({"component": "database"}, 1.0)])
    usual, platform = Prometheus(address), Prometheus(address, str(root))
    try:
        with pytest.raises(PrometheusError):
            usual.query(USED)
        assert platform.query(USED) == [({"component": "database"}, 1.0)]
    finally:
        usual.close()
        platform.close()
        served.stop()
