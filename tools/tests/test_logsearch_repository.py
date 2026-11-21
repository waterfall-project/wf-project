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
def test_the_search_of_the_repository_without_any_secret_known_fails(tmp_path: Path) -> None:
    _repository(tmp_path, {"a.txt": "text\n"})
    assert logsearch.search_repository({}, tmp_path) == 2


@pytest.mark.requirement("WF-SEC-0010-A")
def test_the_paths_of_the_chain_search_the_repository_with_the_secrets_of_their_platform() -> None:
    # e2e-service, which the chain plays with the secrets of the platform of service, searches the
    # repository for them, and fails if it finds one, as it does for the logs.
    played = re.search(r"^e2e-service: install-front.*?\n((?:\t.*\n)+)", MAKEFILE, re.MULTILINE)
    assert played
    recipe = played[1]
    assert "$(repository-secrets); written=$$?;" in recipe
    assert "if [ $$written -ne 0 ]; then exit $$written; fi;" in recipe
    defined = re.search(r"^repository-secrets = (.*)$", MAKEFILE, re.MULTILINE)
    assert defined
    assert "logsearch repository" in defined[1]
