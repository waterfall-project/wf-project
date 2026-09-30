# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The files whose line endings matter are checked out with LF (#171, #175).

A tool writes its files with LF, and its check compares them with what it would write; Prettier
checks the front with LF. Checked out in CRLF, as ``core.autocrlf`` does on Windows, they would
look outdated while nothing changed: ``.gitattributes`` fixes their line endings, and this test
holds it to every generated path the declaration lists, to the front and to the examples — and
to the shell scripts, which bash no longer parses in CRLF (#175).
"""

import subprocess

from wftools import REPOSITORY, paths

# Besides the generated paths: formatted with LF by Prettier, and read by the generators; the
# originals of the copies the front compares byte for byte (`src/theme/brand.test.ts`); and the
# shell scripts, which bash fails to parse in CRLF (#175).
LF_ONLY = ("frontend/**", "fixtures/**", "docs/assets/*.svg", "**/*.sh")


def git(*arguments: str, given: str = "") -> str:
    """Run git in the repository, and return what it prints."""
    return subprocess.run(
        ["git", *arguments], cwd=REPOSITORY, input=given, capture_output=True, text=True, check=True
    ).stdout


def lf_files() -> list[str]:
    """Return the tracked files that must be checked out with LF."""
    declaration = paths.read()
    patterns = [pattern for entry in declaration.generated for pattern in entry.paths]
    tracked = git("ls-files", "-z").split("\0")
    return [path for path in tracked if path and paths.matches(path, (*patterns, *LF_ONLY))]


def attributes(files: list[str]) -> dict[str, dict[str, str]]:
    """Return the ``text`` and ``eol`` attributes git gives each file, by file."""
    found: dict[str, dict[str, str]] = {}
    listing = git("check-attr", "-z", "--stdin", "text", "eol", given="\0".join(files))
    fields = listing.split("\0")
    for path, name, value in zip(fields[0::3], fields[1::3], fields[2::3], strict=False):
        found.setdefault(path, {})[name] = value
    return found


def test_the_lf_files_include_each_kind_whose_line_endings_matter() -> None:
    files = lf_files()
    assert "fixtures/api/volume/nodes_thousand.json" in files
    assert "fixtures/examples.json" in files
    assert "frontend/src/api/generated/schema.d.ts" in files
    assert "frontend/messages/fr.json" in files
    assert "docs/spec/waterfall-spec.md" in files
    assert "docs/assets/waterfall_logo.svg" in files
    assert "docs/spec/build.sh" in files


def test_every_lf_file_is_checked_out_with_lf() -> None:
    files = lf_files()
    found = attributes(files)
    wrong = {
        path: found.get(path, {})
        for path in files
        if found.get(path, {}).get("eol") != "lf" or found.get(path, {}).get("text") == "unset"
    }
    assert wrong == {}
