# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of what the search of the logs holds of the platform of service (US-2900).

The secrets it looks for, the profiles of Compose it reads the logs under, and what it does of a
text that is empty or of a variable it leaves out.
"""

import re
from pathlib import Path

import pytest

from wftools import logsearch

REPOSITORY = Path(__file__).resolve().parents[2]
COMPOSE = (REPOSITORY / "deploy" / "compose" / "compose.service.yaml").read_text(encoding="utf-8")
MAKEFILE = (REPOSITORY / "Makefile").read_text(encoding="utf-8")
LOCAL_PASSWORD = re.compile(r'LOCAL_PASSWORD = "([^"]+)"')


@pytest.mark.requirement("WF-OBS-0020-A")
def test_the_secrets_searched_are_those_the_compose_file_of_the_service_reads() -> None:
    read = set(re.findall(r"\$\{(WATERFALL_[A-Z_]*(?:SECRET|PASSWORD|_KEY)(?![A-Z]))", COMPOSE))
    assert read
    assert read - set(logsearch.IDENTIFIERS) <= set(logsearch.SECRET_VARIABLES)
    assert not set(logsearch.IDENTIFIERS) & set(logsearch.SECRET_VARIABLES)


@pytest.mark.requirement("WF-OBS-0020-A")
def test_the_password_of_the_accounts_of_the_paths_is_searched_as_the_paths_set_it() -> None:
    realm = (REPOSITORY / "frontend" / "e2e" / "service" / "realm.ts").read_text(encoding="utf-8")
    set_by_the_paths = LOCAL_PASSWORD.search(realm)
    assert set_by_the_paths
    assert logsearch.FIXED_SECRETS["E2E_LOCAL_PASSWORD"] == set_by_the_paths[1]


@pytest.mark.requirement("WF-OBS-0020-A")
def test_a_variable_absent_or_too_short_is_named_as_left_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    environment = {"WATERFALL_REDIS_PASSWORD": "long-enough-value", "WATERFALL_STORAGE_SECRET": "x"}
    left = logsearch.left_out(environment)
    assert "WATERFALL_STORAGE_SECRET" in left
    assert "WATERFALL_POSTGRES_PASSWORD" in left
    assert "WATERFALL_REDIS_PASSWORD" not in left
    for name in logsearch.SECRET_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("WATERFALL_REDIS_PASSWORD", "long-enough-value")
    (tmp_path / "a.log").write_text("anything")
    assert logsearch.main(["secrets", str(tmp_path)]) == 0
    said = capsys.readouterr().err
    assert "WATERFALL_POSTGRES_PASSWORD" in said
    # An identifier that holds no secret is never named as left out: it is not looked for.
    assert "WATERFALL_STORAGE_ACCESS_KEY" not in said


@pytest.mark.requirement("WF-OBS-0020-A")
@pytest.mark.parametrize("command", ["secrets", "fields"])
def test_an_empty_text_fails_instead_of_passing(
    command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WATERFALL_REDIS_PASSWORD", "long-enough-value")
    (tmp_path / "a.log").write_text("\n  \n")
    assert logsearch.main([command, str(tmp_path)]) == 2


@pytest.mark.requirement("WF-OBS-0020-A")
def test_the_search_reads_the_logs_under_every_profile_service_down_knows() -> None:
    down = re.search(r"^service-down:.*\n\t@(.*)$", MAKEFILE, re.MULTILINE)
    assert down
    assert "$(COMPOSE_SERVICE_ALL)" in down[1]
    profiles = re.search(r"^SERVICE_PROFILES = (.*)$", MAKEFILE, re.MULTILINE)
    assert profiles
    # The supervision profile is the chain's, not this platform's: nothing here starts it.
    assert set(profiles[1].split()) >= set(re.findall(r"profiles: \[(\w+)\]", COMPOSE)) - {
        "supervision"
    }
    reads = [
        line
        for line in MAKEFILE.splitlines()
        # The reading of the one service of the volume (postgres-volume), on a failure, is named.
        if re.search(r"\$\(COMPOSE_SERVICE(?:_ALL)?\)", line)
        and "logs --no-color" in line
        and "postgres-volume" not in line
    ]
    assert reads
    assert all("$(COMPOSE_SERVICE_ALL)" in line for line in reads)


@pytest.mark.requirement("WF-OBS-0020-A")
@pytest.mark.requirement("WF-SEC-0010-A")
def test_the_search_reads_the_logs_of_the_services_run_once_by_the_paths() -> None:
    # install and witness run by `run --rm`: their containers go with their logs, which the search
    # reads from the files e2e-service keeps them in (#4395) — install's log alone, its standard
    # output being the link of the first administrator.
    variables = dict(re.findall(r"^([\w-]+) = (.*)$", MAKEFILE, re.MULTILINE))
    logs = variables["RUN_LOGS"].split()
    assert logs == ["$(INSTALL_LOG)", "$(WITNESS_LOG)"]
    assert "for each in $(RUN_LOGS)" in variables["service-logs-text"]
    played = re.search(r"^e2e-service: install-front.*?\n((?:\t.*\n)+)", MAKEFILE, re.MULTILINE)
    assert played
    # The end of the recipe, which e2e-service and e2e-reference share, is a macro (US-2950/L3).
    shared = re.search(r"^service-harness-play = (.*?)\n(?!\t)", MAKEFILE, re.MULTILINE | re.DOTALL)
    assert shared
    recipe = played[1] + shared[1]
    assert "$(call run-logged,install,$(INSTALL_LOG),2> $(INSTALL_LOG))" in recipe
    assert "$(call run-logged,witness,$(WITNESS_LOG),> $(WITNESS_LOG) 2>&1)" in recipe
    assert "run --rm --no-TTY install)" not in recipe
    assert recipe.index("run-logged,witness") < recipe.index("$(service-logs-secrets)")
