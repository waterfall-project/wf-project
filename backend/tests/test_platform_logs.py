# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The logs are structured, say who did what, and keep the secrets out (WF-OBS-0020)."""

import logging

import pytest
from support import (
    BEARER_JWT,
    DB_CREDENTIAL,
    PLATFORM_SECRETS,
    REDIS_CREDENTIAL,
    SESSION_COOKIE,
    Logs,
    found_in,
)

from waterfall.platform.logs import drop_secrets, get_logger, logging_context
from waterfall.platform.settings import load_settings


def test_a_record_is_a_json_line_with_its_severity_its_time_and_its_author(logs: Logs) -> None:
    get_logger("test").warning("something.happened", count=3)
    (record,) = logs.records
    assert record["event"] == "something.happened"
    assert record["level"] == "warning"
    assert record["count"] == 3
    assert record["actor"] == "platform"
    assert record["timestamp"].endswith("Z")


def test_the_context_is_bound_to_every_record_written_inside_it(logs: Logs) -> None:
    with logging_context(correlation_id="abc-123", actor="someone"):
        get_logger("test").info("inside")
    get_logger("test").info("outside")
    inside, outside = logs.records
    assert (inside["correlation_id"], inside["actor"]) == ("abc-123", "someone")
    assert "correlation_id" not in outside
    assert outside["actor"] == "platform"


def test_the_records_of_the_libraries_are_written_the_same_way(logs: Logs) -> None:
    logging.getLogger("uvicorn.error").error("library failure")
    (record,) = logs.records
    assert (record["event"], record["level"], record["logger"]) == (
        "library failure",
        "error",
        "uvicorn.error",
    )


@pytest.mark.parametrize(
    "name", ["password", "access_token", "client_secret", "Authorization", "set-cookie", "TOKEN"]
)
def test_a_field_whose_name_evokes_a_secret_is_removed(name: str) -> None:
    cleaned = drop_secrets(None, "info", {"event": "login", name: "value", "user": "ada"})
    assert cleaned == {"event": "login", "user": "ada"}


def test_a_secret_nested_in_a_field_is_removed_too() -> None:
    event = {"event": "call", "request": {"headers": [{"authorization": "x", "host": "h"}]}}
    cleaned = drop_secrets(None, "info", event)
    assert cleaned == {"event": "call", "request": {"headers": [{"host": "h"}]}}


@pytest.mark.requirement("WF-OBS-0020-A")
def test_the_secrets_and_tokens_of_the_test_platform_are_not_in_the_logs(
    platform_environment: dict[str, str], logs: Logs
) -> None:
    assert platform_environment
    settings = load_settings()
    logger = get_logger("test")
    logger.info("settings.loaded", settings=settings)
    logger.info("login", password=DB_CREDENTIAL, token=BEARER_JWT, cookie=SESSION_COOKIE)
    logger.info("call", headers={"Authorization": f"Bearer {BEARER_JWT}", "Cookie": SESSION_COOKIE})
    logging.getLogger("library").info("connect", extra={"password": REDIS_CREDENTIAL})
    assert logs.text
    assert found_in(logs.text) == []


def test_the_search_finds_a_secret_that_a_record_carries_under_an_innocent_name(
    logs: Logs,
) -> None:
    get_logger("test").info("careless", dsn=PLATFORM_SECRETS["WATERFALL_REDIS_URL"])
    assert REDIS_CREDENTIAL in found_in(logs.text)
