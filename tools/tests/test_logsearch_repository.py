# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the search of the secrets known in the repository (US-2840, WF-SEC-0010).

The same search as that of the logs (US-2900), on every file git tracks, by the values of the
secrets alone. A repository of each test is made in its folder.
"""

import re
import subprocess
from typing import TYPE_CHECKING

import pytest
import yaml

from wftools import REPOSITORY, logsearch

if TYPE_CHECKING:
    from pathlib import Path

JWT = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.c2lnbmF0dXJlLW9mLXRoZS10b2tlbg"
MAKEFILE = (REPOSITORY / "Makefile").read_text(encoding="utf-8")


def _repository(root: Path, files: dict[str, str]) -> None:
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "--all"], check=True)


@pytest.mark.requirement("WF-SEC-0010-A")
def test_a_secret_written_in_a_file_the_repository_tracks_is_found_naming_the_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    value = "a-secret-of-the-chain-42"
    _repository(
        tmp_path,
        {"deploy/values.yaml": f"password: {value}\n", "README.md": "nothing here\n"},
    )
    # Written after the files were added: a file git does not track is not read.
    (tmp_path / "untracked.txt").write_text(value, encoding="utf-8")
    assert logsearch.search_repository({"WATERFALL_REDIS_PASSWORD": value}, tmp_path) == 1
    said = capsys.readouterr().err
    assert "found in deploy/values.yaml: WATERFALL_REDIS_PASSWORD" in said
    assert "untracked.txt" not in said
    assert value not in said


@pytest.mark.requirement("WF-SEC-0010-A")
def test_a_secret_quoted_as_a_url_writes_it_is_found_too(tmp_path: Path) -> None:
    _repository(tmp_path, {"a.env": "URL=redis://:a%2Fsecret%2Bvalue@redis/0\n"})
    secrets = {"WATERFALL_REDIS_PASSWORD": "a/secret+value"}
    assert logsearch.search_repository(secrets, tmp_path) == 1


@pytest.mark.requirement("WF-SEC-0010-A")
def test_a_repository_without_the_secrets_passes_and_tokens_written_in_tests_are_not_sought(
    tmp_path: Path,
) -> None:
    _repository(tmp_path, {"tests/test_tokens.py": f'JWT = "{JWT}"\n'})
    assert logsearch.search_repository({"WATERFALL_REDIS_PASSWORD": "not-written-x"}, tmp_path) == 0


@pytest.mark.requirement("WF-SEC-0010-A")
def test_the_search_of_the_repository_reaches_the_secrets_the_chain_draws_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Its reach (guide, « Un parcours de bout en bout »): the values of SECRET_VARIABLES, each
    # found in a tracked file; the password of the paths, a constant of the repository written in
    # realm.ts, is not one of them.
    drawn = {
        name: f"drawn-{index}-for-{name.lower()}"
        for index, name in enumerate(logsearch.SECRET_VARIABLES)
    }
    (constant,) = logsearch.FIXED_SECRETS.values()
    _repository(tmp_path, {"realm.ts": f'const LOCAL_PASSWORD = "{constant}";\n'})
    assert logsearch.search_repository(drawn, tmp_path) == 0
    for name, value in drawn.items():
        (tmp_path / "leak.env").write_text(f"X={value}\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(tmp_path), "add", "leak.env"], check=True)
        assert logsearch.search_repository(drawn, tmp_path) == 1, name
        assert f"found in leak.env: {name}" in capsys.readouterr().err


@pytest.mark.requirement("WF-SEC-0010-A")
def test_a_value_a_workflow_sets_in_clear_is_not_sought_and_a_value_of_a_platform_still_is(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Under the chain, the secrets of the platform are values a workflow writes in clear, public
    # and named as such (keycloak.yml, INSTALL.md): found in the workflow and wherever the files
    # reuse them, they are no secret of a platform. A value of a platform, set by no workflow and
    # written in a tracked file, is still found.
    chain = "chain-only-storage-secret"
    workflow = (
        "jobs:\n  paths:\n    env:\n"
        f"      WATERFALL_STORAGE_SECRET: {chain}\n"
        "      WATERFALL_REDIS_PASSWORD: ${{ secrets.REDIS }}\n"
    )
    _repository(
        tmp_path,
        {".github/workflows/service.yml": workflow, "compose.test.yaml": f"KEY: {chain}\n"},
    )
    drawn = "drawn-at-run-time-for-redis"
    environment = {"WATERFALL_STORAGE_SECRET": chain, "WATERFALL_REDIS_PASSWORD": drawn}
    assert logsearch.search_repository(environment, tmp_path) == 0
    said = capsys.readouterr()
    assert "values a workflow of the chain sets: WATERFALL_STORAGE_SECRET" in said.err
    assert "searched 1 secrets" in said.out
    # The expression of GitHub is no value of the file: the value it gives is still sought.
    (tmp_path / "leak.env").write_text(f"X={drawn}\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "leak.env"], check=True)
    assert logsearch.search_repository(environment, tmp_path) == 1
    said = capsys.readouterr()
    assert "found in leak.env: WATERFALL_REDIS_PASSWORD" in said.err
    assert "found in compose.test.yaml" not in said.err
    assert "found in .github" not in said.err
    assert drawn not in said.err + said.out


@pytest.mark.requirement("WF-SEC-0010-A")
def test_every_secret_a_value_of_the_chain_passes_saying_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _repository(
        tmp_path, {".github/workflows/a.yaml": "env:\n  WATERFALL_REDIS_PASSWORD: chainonlyredis\n"}
    )
    environment = {"WATERFALL_REDIS_PASSWORD": "chainonlyredis"}
    assert logsearch.search_repository(environment, tmp_path) == 0
    assert "none of a platform to look for" in capsys.readouterr().out


@pytest.mark.requirement("WF-SEC-0010-A")
def test_the_search_of_the_repository_passes_with_the_secrets_the_paths_of_the_chain_hold() -> None:
    # The conditions of the chain: the environment of the job that plays e2e-service, on this
    # repository, whose workflows and files write those values (#4782, run 45109501025).
    workflow = REPOSITORY / ".github" / "workflows" / "service.yml"
    environment = yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"]["paths"]["env"]
    assert set(logsearch.SECRET_VARIABLES) <= set(environment)
    assert logsearch.search_repository(environment) == 0


@pytest.mark.requirement("WF-SEC-0010-A")
def test_the_search_of_the_repository_without_any_secret_known_fails(tmp_path: Path) -> None:
    _repository(tmp_path, {"a.txt": "text\n"})
    assert logsearch.search_repository({}, tmp_path) == 2


@pytest.mark.requirement("WF-SEC-0010-A")
def test_the_paths_of_the_chain_search_the_repository_with_the_secrets_of_their_platform() -> None:
    # e2e-service, which the chain plays with the secrets of the platform of service, searches the
    # repository for them, and fails if it finds one, as it does for the logs.
    played = re.search(r"^e2e-service: install-front.*?\n((?:\t.*\n)+)", MAKEFILE, re.MULTILINE)
    assert played
    # The end of the recipe, which e2e-service and e2e-reference share, is a macro (US-2950/L3).
    shared = re.search(r"^service-harness-play = (.*?)\n(?!\t)", MAKEFILE, re.MULTILINE | re.DOTALL)
    assert shared
    recipe = played[1] + shared[1]
    assert "$(repository-secrets); written=$$?;" in recipe
    assert "if [ $$written -ne 0 ]; then exit $$written; fi;" in recipe
    defined = re.search(r"^repository-secrets = (.*)$", MAKEFILE, re.MULTILINE)
    assert defined
    assert "logsearch repository" in defined[1]
