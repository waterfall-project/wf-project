# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The settings and the secrets are read at start, and a missing secret stops the process."""

import subprocess
import sys

import pytest
from pydantic import SecretStr
from support import (
    DB_CREDENTIAL,
    DECODED_CREDENTIAL,
    ENCODED_CREDENTIAL,
    PLATFORM_SECRETS,
    PLUS_CREDENTIAL,
)

from waterfall.platform.settings import Settings, SettingsError, load_settings


def start_api(environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Start the API as a process with only the given environment."""
    return subprocess.run(
        [sys.executable, "-m", "waterfall.api.main"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@pytest.mark.requirement("WF-SEC-0010-A")
def test_a_service_started_without_its_secrets_fails_and_names_them() -> None:
    result = start_api({})
    assert result.returncode != 0
    assert "WATERFALL_DATABASE_URL: is missing" in result.stderr
    assert "WATERFALL_REDIS_URL: is missing" in result.stderr
    assert result.stdout == ""


@pytest.mark.requirement("WF-SEC-0010-A")
def test_a_service_started_without_one_secret_names_that_one_only() -> None:
    present = {"WATERFALL_REDIS_URL": PLATFORM_SECRETS["WATERFALL_REDIS_URL"]}
    result = start_api(present)
    assert result.returncode != 0
    assert "WATERFALL_DATABASE_URL: is missing" in result.stderr
    assert "WATERFALL_REDIS_URL" not in result.stderr


@pytest.mark.requirement("WF-SEC-0010-A")
@pytest.mark.usefixtures("platform_environment")
def test_a_secret_that_is_empty_is_a_secret_that_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WATERFALL_REDIS_URL", "")
    with pytest.raises(SettingsError, match="WATERFALL_REDIS_URL"):
        load_settings()


def test_the_settings_read_the_secrets_of_the_environment(
    platform_environment: dict[str, str],
) -> None:
    settings = load_settings()
    assert (
        settings.database_url.get_secret_value() == platform_environment["WATERFALL_DATABASE_URL"]
    )
    assert (settings.host, settings.port, settings.log_level) == ("127.0.0.1", 8000, "INFO")


@pytest.mark.usefixtures("platform_environment")
def test_the_settings_show_no_secret_when_printed() -> None:
    assert DB_CREDENTIAL not in repr(load_settings())


@pytest.mark.usefixtures("platform_environment")
def test_an_invalid_setting_is_named_without_its_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WATERFALL_PORT", "not-a-port")
    with pytest.raises(SettingsError) as raised:
        load_settings()
    assert "WATERFALL_PORT" in str(raised.value)
    assert "not-a-port" not in str(raised.value)


@pytest.mark.requirement("WF-OBS-0020-A")
def test_the_secrets_of_a_url_that_urlsplit_refuses_are_still_given() -> None:
    settings = Settings(
        database_url=SecretStr("postgresql://u:pa[ss@db/x"),
        redis_url=SecretStr(PLATFORM_SECRETS["WATERFALL_REDIS_URL"]),
    )
    assert {"postgresql://u:pa[ss@db/x", "pa[ss"} <= set(settings.secret_values())


@pytest.mark.requirement("WF-OBS-0020-A")
def test_the_decoded_password_of_a_url_is_a_secret() -> None:
    settings = Settings(
        database_url=SecretStr(f"postgresql://u:{ENCODED_CREDENTIAL}@db/x"),
        redis_url=SecretStr(PLATFORM_SECRETS["WATERFALL_REDIS_URL"]),
    )
    assert {ENCODED_CREDENTIAL, DECODED_CREDENTIAL} <= set(settings.secret_values())


def settings_for(database_url: str) -> Settings:
    return Settings(
        database_url=SecretStr(database_url),
        redis_url=SecretStr(PLATFORM_SECRETS["WATERFALL_REDIS_URL"]),
    )


@pytest.mark.requirement("WF-OBS-0020-A")
def test_both_decodings_of_a_password_with_a_plus_are_secrets() -> None:
    values = settings_for(f"postgresql://u:{PLUS_CREDENTIAL}@db/x").secret_values()
    assert {PLUS_CREDENTIAL, "a+b@", "a b@"} <= set(values)


@pytest.mark.requirement("WF-OBS-0020-A")
def test_a_decoded_form_shorter_than_four_characters_is_not_a_secret() -> None:
    url = "postgresql://u:%20@db/x"
    values = settings_for(url).secret_values()
    assert {url, "%20"} <= set(values)
    assert " " not in values


@pytest.mark.requirement("WF-OBS-0020-A")
@pytest.mark.parametrize(
    ("url", "password"),
    [
        ("postgresql://u:p#ss@db/x", "p#ss"),
        ("postgresql://u:p/ss@db/x", "p/ss"),
        ("postgresql://u:p?ss@db/x", "p?ss"),
        ("postgresql://u:pa[ss@db/x", "pa[ss"),
    ],
)
def test_the_password_is_read_before_the_url_is_split(url: str, password: str) -> None:
    assert {url, password} <= set(settings_for(url).secret_values())
