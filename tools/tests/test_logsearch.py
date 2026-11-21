# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the search of the secrets in the logs, and of the story of one identifier (US-2900)."""

import json
from typing import TYPE_CHECKING

import pytest

from wftools import logsearch

if TYPE_CHECKING:
    from pathlib import Path

SECRETS = {"DATABASE": "pa$$w0rd-of-the-base", "CLIENT": 'sec"ret/client+value'}
JWT = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.c2lnbmF0dXJlLW9mLXRoZS10b2tlbg"


@pytest.mark.requirement("WF-OBS-0020-A")
def test_a_secret_is_found_as_it_is_written_as_json_escapes_it_and_as_a_url_quotes_it() -> None:
    for text in (
        f"connect {SECRETS['DATABASE']}",
        json.dumps({"event": SECRETS["CLIENT"]}),
        "postgresql://u:" + "sec%22ret%2Fclient%2Bvalue" + "@host/db",
        "q=sec%22ret%2Fclient%2Bvalue",
    ):
        assert logsearch.find_secrets(text, SECRETS)


@pytest.mark.requirement("WF-OBS-0020-A")
def test_the_search_names_what_it_found_and_never_gives_its_value() -> None:
    found = logsearch.find_secrets(f"x {SECRETS['CLIENT']} y", SECRETS)
    assert found == ["CLIENT"]
    assert not any(value in found for value in SECRETS.values())


@pytest.mark.requirement("WF-OBS-0020-A")
def test_a_text_that_holds_no_secret_finds_none() -> None:
    assert (
        logsearch.find_secrets('{"event": "request.completed", "path": "/api/v1"}', SECRETS) == []
    )


@pytest.mark.requirement("WF-OBS-0020-A")
@pytest.mark.parametrize("text", [f"token {JWT}", f"Authorization: Bearer {'a' * 30}"])
def test_a_token_is_found_by_its_shape_whatever_its_value(text: str) -> None:
    assert logsearch.find_secrets(text, {})


def test_a_masked_value_is_not_a_token() -> None:
    assert logsearch.find_secrets('{"authorization": "Bearer ***"}', {}) == []


def test_the_secrets_come_from_the_environment_by_name_and_a_short_value_is_left_out() -> None:
    environment = {"WATERFALL_REDIS_PASSWORD": "long-enough-value", "WATERFALL_STORAGE_SECRET": "x"}
    assert logsearch.secrets_from(environment) == {"WATERFALL_REDIS_PASSWORD": "long-enough-value"}


def record(event: str, correlation_id: str, **fields: str) -> str:
    """Write a record as a service of Compose does, under the name of the service."""
    body = json.dumps({"event": event, "correlation_id": correlation_id, **fields})
    return f"api-1  | {body}"


@pytest.mark.requirement("WF-OBS-0020-A")
def test_the_story_of_an_identifier_holds_the_deposit_its_import_opened_on_and_the_task() -> None:
    lines = [
        record("upload.deposited", "c-upload", upload_id="u1"),
        record("upload.deposited", "c-other", upload_id="u2"),
        record("import.opened", "c-open", upload_id="u1", import_id="i1", task_id="t1"),
        "worker-1  | not a record, a line of another kind",
        record("task.started", "c-open", task_id="t1"),
        record("task.failed", "c-open", task_id="t1"),
        record("task.failed", "c-elsewhere", task_id="t2"),
    ]
    story = logsearch.follow(lines, "c-open")
    assert story == [lines[0], lines[2], lines[4], lines[5]]


def test_a_line_that_is_no_record_is_kept_when_it_holds_the_identifier() -> None:
    lines = ["keycloak-1  | WARN login c-open", "keycloak-1  | WARN login c-other"]
    assert logsearch.follow(lines, "c-open") == [lines[0]]


def test_the_command_ends_with_1_on_a_secret_found_and_names_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("WATERFALL_REDIS_PASSWORD", "long-enough-value")
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "api.log").write_text("connect redis://:long-enough-value@redis\n")
    assert logsearch.main(["secrets", str(logs)]) == 1
    assert "WATERFALL_REDIS_PASSWORD" in capsys.readouterr().err
    (logs / "api.log").write_text("connect redis://:***@redis\n")
    assert logsearch.main(["secrets", str(logs)]) == 0


def test_a_search_with_no_secret_known_fails_instead_of_passing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in logsearch.SECRET_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    (tmp_path / "a.log").write_text("anything")
    assert logsearch.main(["secrets", str(tmp_path)]) == 2


@pytest.mark.story("US-2900")
def test_a_line_that_is_no_record_or_lacks_a_field_is_reported() -> None:
    whole = '{"event": "e", "correlation_id": "c", "actor": "platform", "level": "info"}'
    lines = [
        f"api-1  | {whole}",
        "",
        "api-1  | Traceback (most recent call last):",
        'api-1  | {"event": "e", "correlation_id": "c", "level": "info"}',
    ]
    assert logsearch.lacking(lines) == [lines[2], lines[3]]


@pytest.mark.story("US-2900")
def test_the_fields_command_ends_with_1_on_a_line_that_lacks_one(tmp_path: Path) -> None:
    log = tmp_path / "api.log"
    log.write_text('{"event": "e", "correlation_id": "c", "actor": "a", "level": "info"}\n')
    assert logsearch.main(["fields", str(log)]) == 0
    log.write_text('{"event": "e"}\n')
    assert logsearch.main(["fields", str(log)]) == 1
