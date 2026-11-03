# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tracking table of an epic's issue, changed under a lock (US-1120).

The tool runs as the Makefile runs it, ``python -m wftools.tracking``, with a fake ``gh`` first on
the ``PATH``: an executable that keeps the body of the issue in a file. No test touches a real
issue, and ``XDG_RUNTIME_DIR`` is a temporary directory.
"""

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from wftools import REPOSITORY, tracking

# View: the body, or the title and state of a finding, as JSON. Edit: waits the delay between
# the reading of the body and its writing, which makes the race real without the lock.
FAKE_GH = """\
#!{python}
import json, os, sys, time
directory = os.environ["FAKE_GH_DIR"]
arguments = sys.argv[1:]
number = arguments[2]
with open(os.path.join(directory, "calls"), "a") as calls:
    calls.write(" ".join(arguments) + "\\n")
if arguments[:2] == ["issue", "view"] and arguments[4] == "body":
    with open(os.path.join(directory, "body"), newline="") as body:
        print(json.dumps({{"body": body.read()}}))
elif arguments[:2] == ["issue", "view"]:
    with open(os.path.join(directory, f"issue-{{number}}.json")) as issue:
        print(issue.read())
elif arguments[:2] == ["issue", "edit"]:
    new = sys.stdin.read()
    time.sleep(float(os.environ.get("FAKE_GH_DELAY", "0")))
    with open(os.path.join(directory, "body"), "w", newline="") as body:
        body.write(new)
else:
    sys.exit("unexpected call")
"""

BODY = """\
## Ordre de réalisation

| # | US | Statut | Lot | Dépend de | Pas avec | État du lot | PR | Modèle |
|---|---|---|---|---|---|---|---|---|
| 1 | US-1080 #1882 | fini | lot unique | — | — | fusionné | #1894 | opus |
| 2 | US-1090 #1883 | fini | lot unique | — | US-1120/L1 #1887 | fusionné | #1898 | sonnet |
| 5 | US-1120 #1886 | à faire | L1 #1887 | — | US-1090 #1883 | à faire | — | sonnet |
|   |   |   | L2 #1888 | US-1120/L1 #1887 | — | à faire | — | sonnet |

Six lots.

## Constats ouverts

| Constat | Rattaché à | Décision |
|---|---|---|
| #1890 outil : formes d'arrêt | US-1080 #1882 | **à trancher** |
| #1903 outil : agents | US-1120/L2 #1888 | corrigé par US-1120/L2 #1888 |

Aucun constat n'est repris au cadrage.

### Before opening

- [x] prêt
"""

LOT_ROW = "| 2 | US-1090 #1883 | fini | lot unique | — | US-1120/L1 #1887 | {} | {} | sonnet |\n"
US_ROW = "| 5 | US-1120 #1886 | {} | L1 #1887 | — | US-1090 #1883 | à faire | — | sonnet |\n"

NO_FINDINGS = "## Constats ouverts\n\nAucun constat n'est ouvert.\n\n### Before opening\n"


class Issue:
    """The fake ``gh`` of a test, and the issue it holds."""

    def __init__(self, directory: Path, body: str) -> None:
        self.directory = directory
        self.bin = directory / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(FAKE_GH.format(python=sys.executable))
        gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
        self.set_body(body)

    def set_body(self, body: str) -> None:
        """Replace the body, byte for byte."""
        (self.directory / "body").write_bytes(body.encode())

    @property
    def body(self) -> str:
        """Return the body the issue holds."""
        return (self.directory / "body").read_bytes().decode()

    def finding(self, number: int, title: str, state: str) -> None:
        """Give the issue of a finding."""
        data = {"title": title, "state": state}
        (self.directory / f"issue-{number}.json").write_text(json.dumps(data))

    @property
    def writes(self) -> int:
        """Return how many times the body was written."""
        calls = self.directory / "calls"
        if not calls.exists():
            return 0
        return sum(1 for line in calls.read_text().splitlines() if line.startswith("issue edit"))

    def start(self, arguments: list[str], delay: str = "0") -> subprocess.Popen[str]:
        """Start the tool on an issue of number 7."""
        environment = {
            **os.environ,
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "XDG_RUNTIME_DIR": str(self.directory),
            "FAKE_GH_DIR": str(self.directory),
            "FAKE_GH_DELAY": delay,
        }
        return subprocess.Popen(
            [sys.executable, "-m", "wftools.tracking", "--issue", "7", *arguments],
            env=environment,
            cwd=REPOSITORY / "tools",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def run(self, *arguments: str) -> tuple[int, str]:
        """Run the tool; return its code and what it wrote on its error output."""
        process = self.start(list(arguments))
        _, error = process.communicate(timeout=60)
        return process.returncode, error


@pytest.fixture
def issue(tmp_path: Path) -> Issue:
    return Issue(tmp_path, BODY)


def changed_lines(before: str, after: str) -> list[tuple[str, str]]:
    """Return the lines that differ, as before and after."""
    old, new = before.splitlines(keepends=True), after.splitlines(keepends=True)
    assert len(old) == len(new)
    return [(a, b) for a, b in zip(old, new, strict=True) if a != b]


def test_lot_alone_changes_the_cells_given(issue: Issue) -> None:
    """US-1120: a lot of one lot is named by its story; the cells given change, no other."""
    code, _ = issue.run("--lot", "US-1090", "--state", "en cours", "--pr", "#1900")
    assert code == 0
    assert changed_lines(BODY, issue.body) == [
        (
            LOT_ROW.format("fusionné", "#1898"),
            LOT_ROW.format("en cours", "#1900"),
        )
    ]


def test_lot_of_a_story_of_several_is_found_under_its_story(issue: Issue) -> None:
    """US-1120: US-1120/L2 is the row of L2 under the row of US-1120, its first cells empty."""
    code, _ = issue.run("--lot", "US-1120/L2", "--model", "opus")
    assert code == 0
    assert changed_lines(BODY, issue.body) == [
        (
            "|   |   |   | L2 #1888 | US-1120/L1 #1887 | — | à faire | — | sonnet |\n",
            "|   |   |   | L2 #1888 | US-1120/L1 #1887 | — | à faire | — | opus |\n",
        )
    ]
    code, _ = issue.run("--lot", "US-1120/L1", "--state", "en cours")
    assert code == 0
    assert "| L1 #1887 | — | US-1090 #1883 | en cours | — | sonnet |" in issue.body


def test_story_status_changes_on_the_row_of_the_story(issue: Issue) -> None:
    """US-1120: --us changes the cell « Statut » of the row of the story, not of its lots."""
    code, _ = issue.run("--us", "US-1120", "--status", "en cours")
    assert code == 0
    assert changed_lines(BODY, issue.body) == [
        (
            US_ROW.format("à faire"),
            US_ROW.format("en cours"),
        )
    ]


def test_table_without_the_pas_avec_column_is_read_by_its_header(tmp_path: Path) -> None:
    """US-1120: the columns are found by name; an older epic has no « Pas avec »."""
    body = (
        "## Ordre de réalisation\n\n"
        "| # | US | Statut | Lot | Dépend de | État du lot | PR | Modèle |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 1 | US-0010 #5 | à faire | lot unique | — | à faire | — | sonnet |\n"
    )
    other = Issue(tmp_path, body)
    code, _ = other.run("--lot", "US-0010", "--pr", "#9")
    assert code == 0
    assert other.body.endswith(
        "| 1 | US-0010 #5 | à faire | lot unique | — | à faire | #9 | sonnet |\n"
    )


def test_finding_is_added_with_its_title_and_bold_decision(issue: Issue) -> None:
    """US-1120: a finding is added from its issue: [EP-19] dropped, « à trancher » in bold."""
    issue.finding(1912, "[EP-19] outil : un | tube", "OPEN")
    code, _ = issue.run(
        "--finding", "1912", "--attached", "US-1110 #1885", "--decision", "à trancher"
    )
    assert code == 0
    expected = "| #1912 outil : un \\| tube | US-1110 #1885 | **à trancher** |\n"
    assert issue.body == BODY.replace(
        "\nAucun constat n'est", expected + "\nAucun constat n'est", 1
    )


def test_finding_already_there_is_changed(issue: Issue) -> None:
    """US-1120: a finding already in the table is changed, not added again."""
    issue.finding(1890, "[EP-19] outil : formes d'arrêt", "OPEN")
    code, _ = issue.run("--finding", "1890", "--decision", "corrigé par US-1120/L2 #1888")
    assert code == 0
    assert changed_lines(BODY, issue.body) == [
        (
            "| #1890 outil : formes d'arrêt | US-1080 #1882 | **à trancher** |\n",
            "| #1890 outil : formes d'arrêt | US-1080 #1882 | corrigé par US-1120/L2 #1888 |\n",
        )
    ]


def test_finding_whose_issue_is_closed_is_removed(issue: Issue) -> None:
    """US-1120: a finding whose issue is closed leaves the table; #190 is not #1903."""
    issue.finding(1903, "[EP-19] outil : agents", "CLOSED")
    code, _ = issue.run("--finding", "1903")
    assert code == 0
    assert issue.body == BODY.replace(
        "| #1903 outil : agents | US-1120/L2 #1888 | corrigé par US-1120/L2 #1888 |\n", ""
    )


def test_finding_is_added_in_place_of_the_sentence_without_findings(tmp_path: Path) -> None:
    """US-1120: where the section has « Aucun constat… » and no table, a table replaces it."""
    other = Issue(tmp_path, "# Epic\n\n" + NO_FINDINGS)
    other.finding(5, "[EP-01] front : un titre", "OPEN")
    code, _ = other.run("--finding", "5", "--attached", "US-1 #2", "--decision", "à trancher")
    assert code == 0
    assert other.body == (
        "# Epic\n\n## Constats ouverts\n\n| Constat | Rattaché à | Décision |\n|---|---|---|\n"
        "| #5 front : un titre | US-1 #2 | **à trancher** |\n\n### Before opening\n"
    )


def test_unknown_lot_story_and_finding_are_refused_and_the_body_is_unchanged(issue: Issue) -> None:
    """US-1120: a lot, a story or a finding to remove that is not there: code 1, nothing written."""
    issue.finding(4, "[EP-19] outil : absent", "CLOSED")
    calls = [
        (["--lot", "US-9999", "--state", "x"], "US-9999"),
        (["--lot", "US-1120", "--state", "x"], "US-1120"),
        (["--lot", "US-1120/L3", "--state", "x"], "US-1120/L3"),
        (["--lot", "US-1080/L1", "--state", "x"], "US-1080/L1"),
        (["--us", "US-9999", "--status", "fini"], "US-9999"),
        (["--finding", "4"], "#4"),
    ]
    for arguments, named in calls:
        code, error = issue.run(*arguments)
        assert code == 1
        assert named in error
        assert issue.body == BODY
    assert issue.writes == 0


def test_a_call_that_names_nothing_to_change_is_refused(issue: Issue) -> None:
    """US-1120: a lot without a cell to change, a story without a status, two targets, none."""
    for arguments in (
        ["--lot", "US-1080"],
        ["--us", "US-1080"],
        ["--lot", "US-1080", "--us", "US-1080", "--state", "x"],
        [],
    ):
        code, error = issue.run(*arguments)
        assert code == 1
        assert "give" in error
    assert issue.body == BODY
    assert issue.writes == 0


def test_a_new_finding_needs_its_cells(issue: Issue) -> None:
    """US-1120: a finding that is not in the table cannot be added without ATTACHED and DECISION."""
    issue.finding(8, "[EP-19] outil : neuf", "OPEN")
    code, error = issue.run("--finding", "8")
    assert code == 1
    assert "ATTACHED" in error
    assert issue.body == BODY


def test_missing_section_and_column_are_refused(tmp_path: Path) -> None:
    """US-1120: no section is invented; a column the table lacks is named."""
    other = Issue(tmp_path, "# Epic\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
    code, error = other.run("--us", "US-1", "--status", "fini")
    assert code == 1
    assert "Ordre de réalisation" in error
    other.set_body("## Ordre de réalisation\n\n| # | US |\n|---|---|\n| 1 | US-1 #2 |\n")
    code, error = other.run("--us", "US-1", "--status", "fini")
    assert code == 1
    assert "Statut" in error


def test_the_rest_of_the_body_is_written_byte_for_byte(tmp_path: Path) -> None:
    """US-1120: carriage returns, trailing spaces and the lack of a final newline are kept."""
    body = BODY.replace("\n", "\r\n").rstrip("\r\n")
    other = Issue(tmp_path, body)
    code, _ = other.run("--lot", "US-1080", "--state", "x")
    assert code == 0
    assert other.body == body.replace("| fusionné | #1894 | opus |", "| x | #1894 | opus |")
    other.finding(9, "[EP-19] t", "OPEN")
    before = other.body
    code, _ = other.run("--finding", "9", "--attached", "a", "--decision", "d")
    assert code == 0
    assert other.body.replace("| #9 t | a | d |\r\n", "") == before


def test_a_gh_that_fails_is_said(issue: Issue) -> None:
    """US-1120: a finding whose issue gh cannot read stops the tool, the body unchanged."""
    code, error = issue.run("--finding", "404", "--attached", "a", "--decision", "d")
    assert code == 1
    assert "gh issue view failed" in error
    assert issue.body == BODY


def test_two_simultaneous_calls_each_keep_their_change(issue: Issue) -> None:
    """US-1120: two processes on two lines; gh waits between reading and writing; both survive."""
    first = issue.start(["--lot", "US-1080", "--state", "A"], delay="1")
    second = issue.start(["--us", "US-1120", "--status", "B"], delay="1")
    for process in (first, second):
        process.communicate(timeout=60)
        assert process.returncode == 0
    assert "| fini | lot unique | — | — | A | #1894 | opus |" in issue.body
    assert "| 5 | US-1120 #1886 | B | L1 #1887 |" in issue.body
    assert issue.writes == 2


def test_the_lock_is_the_one_of_the_issue_in_the_runtime_directory(issue: Issue) -> None:
    """US-1120: waterfall-tracking-<issue>.lock in XDG_RUNTIME_DIR, /tmp where it is not set."""
    assert tracking.lock_path({"XDG_RUNTIME_DIR": "/run/x"}, 7) == Path(
        "/run/x/waterfall-tracking-7.lock"
    )
    assert tracking.lock_path({}, 7) == Path(os.sep, "tmp", "waterfall-tracking-7.lock")
    issue.run("--us", "US-1080", "--status", "x")
    assert (issue.directory / "waterfall-tracking-7.lock").exists()
