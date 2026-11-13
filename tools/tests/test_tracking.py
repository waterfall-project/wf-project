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


def test_a_pipe_in_a_value_adds_no_column(issue: Issue) -> None:
    """US-1120: a pipe in a value is escaped in the cell, as in a title; the row keeps its cells."""
    code, _ = issue.run("--lot", "US-1090", "--state", "a|b")
    assert code == 0
    ((before, after),) = changed_lines(BODY, issue.body)
    assert "a\\|b" in after
    assert len(tracking.cells(after)) == len(tracking.cells(before))
    issue.finding(1890, "[EP-19] outil : formes d'arrêt", "OPEN")
    code, _ = issue.run("--finding", "1890", "--decision", "x|y")
    assert code == 0
    assert "| x\\|y |" in issue.body


def test_a_line_break_in_a_value_is_refused(issue: Issue) -> None:
    """US-1120: a cell is one line: a break in any value is refused, nothing written."""
    for option in ("--state", "--pr", "--model"):
        code, error = issue.run("--lot", "US-1090", option, "a\nb")
        assert code == 1
        assert "line break" in error
    for option in ("--attached", "--decision"):
        code, error = issue.run("--finding", "1890", option, "a\rb")
        assert code == 1
        assert "line break" in error
    code, _ = issue.run("--us", "US-1080", "--status", "a\nb")
    assert code == 1
    assert issue.body == BODY
    assert issue.writes == 0


def test_a_row_shorter_than_the_header_is_refused_by_name(issue: Issue) -> None:
    """US-1120: a truncated row is said in a message that names it, not left as a trace."""
    short = "| 2 | US-1090 #1883 | fini | lot unique |\n"
    issue.set_body(BODY.replace(LOT_ROW.format("fusionné", "#1898"), short))
    before = issue.body
    code, error = issue.run("--lot", "US-1090", "--state", "x")
    assert code == 1
    assert "shorter" in error
    assert "US-1090" in error
    assert "Traceback" not in error
    assert issue.body == before


def test_an_unexpected_answer_of_gh_or_an_unusable_lock_is_said_without_a_trace(
    issue: Issue,
) -> None:
    """US-1120: not JSON, a JSON without the key, a lock that cannot be opened: all said."""
    (issue.directory / "issue-9.json").write_text("not json")
    (issue.directory / "issue-10.json").write_text("{}")
    for number in ("9", "10"):
        code, error = issue.run("--finding", number, "--attached", "a", "--decision", "d")
        assert code == 1
        assert error.startswith("tracking: ")
        assert "Traceback" not in error
    (issue.directory / "waterfall-tracking-7.lock").mkdir()
    code, error = issue.run("--us", "US-1080", "--status", "x")
    assert code == 1
    assert error.startswith("tracking: ")
    assert "Traceback" not in error


def make_tracking(issue: Issue, variables: list[str], environment: dict[str, str]) -> int:
    """Run ``make tracking`` of the repository, on the fake ``gh``, and return its code."""
    process = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-C",
            str(REPOSITORY),
            "tracking",
            f"WFTOOLS={sys.executable} -m wftools",
            "ISSUE=7",
            *variables,
        ],
        env={
            **os.environ,
            "PATH": f"{issue.bin}{os.pathsep}{os.environ['PATH']}",
            "PYTHONPATH": str(REPOSITORY / "tools" / "src"),
            "XDG_RUNTIME_DIR": str(issue.directory),
            "FAKE_GH_DIR": str(issue.directory),
            **environment,
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    return process.returncode


def test_make_takes_only_the_variables_of_its_command_line(issue: Issue) -> None:
    """US-1120: PR in the environment of the workstation does not reach the table; STATE does."""
    environment = {"PR": "x", "MODEL": "m", "ATTACHED": "z", "DECISION": "d"}
    code = make_tracking(issue, ["LOT=US-1090", "STATE=l'état | à voir"], environment)
    assert code == 0
    assert changed_lines(BODY, issue.body) == [
        (LOT_ROW.format("fusionné", "#1898"), LOT_ROW.format("l'état \\| à voir", "#1898"))
    ]
    # An empty value is ignored, so a call with nothing else to change is refused.
    before = issue.body
    assert make_tracking(issue, ["LOT=US-1090", "STATE="], environment) != 0
    assert issue.body == before


# US-1290: the part cut off a lot, the lot added, the dependency moved, the gabarit of the epic.

CUT_BODY = """\
## Ordre de réalisation

| # | US | Statut | Lot | Dépend de | Pas avec | État du lot | PR | Modèle |
|---|---|---|---|---|---|---|---|---|
| 1 | US-0820 #2036 | en cours | lot unique (#1840) | — | — | fusionné | #2100 | opus |
|   |   |   | US-0820b #2099 | US-0820 #2036 | — | fusionné | #2118 | sonnet |
| 2 | US-0830 #2037 | à faire | lot unique — en dernier | US-0820 | — | à faire | — | — |
| 3 | US-1270 #2038 | à faire | L1 #2039 | US-0820, US-0850/L1 | — | à faire | — | — |
|   |   |   | L2 #2040 | US-1270/L1 | — | à faire | — | — |
|   |   |   | L2b #2033 | US-1270/L2 | — | à faire | — | — |
| 4 | US-0850 #2041 | à faire | L1 #2042 | US-0820b, US-0820/L1x | — | à faire | — | — |

## Constats ouverts

Aucun constat.
"""


def cut_issue(tmp_path: Path) -> Issue:
    return Issue(tmp_path, CUT_BODY)


def test_a_part_cut_off_and_a_lot_unique_with_a_note_are_found(tmp_path: Path) -> None:
    """US-1290: US-0820b, US-1270/L2b and « lot unique (#n) » name their rows, each its own."""
    issue = cut_issue(tmp_path)
    for lot in ("US-0820", "US-0820b", "US-0830", "US-1270/L2", "US-1270/L2b"):
        assert issue.run("--lot", lot, "--state", "en revue")[0] == 0
    changed = [after for _, after in changed_lines(CUT_BODY, issue.body)]
    assert [row.count("en revue") for row in changed] == [1] * 5
    assert [line.split("|")[4].strip() for line in changed] == [
        "lot unique (#1840)",
        "US-0820b #2099",
        "lot unique — en dernier",
        "L2 #2040",
        "L2b #2033",
    ]


def test_add_lot_inserts_the_row_built_on_the_header(tmp_path: Path) -> None:
    """US-1290: ADD_LOT puts the row under AFTER, empty cells as a continuation row."""
    issue = cut_issue(tmp_path)
    code, _ = issue.run(
        "--add-lot",
        "US-0830b",
        "--after",
        "US-0830",
        "--depends",
        "US-0830",
        "--model",
        "opus",
        "--issue-number",
        "2200",
    )
    assert code == 0
    row = "|   |   |   | US-0830b #2200 | US-0830 | — | à faire | — | opus |\n"
    above = CUT_BODY.splitlines(keepends=True)[6]
    assert "US-0830" in above
    assert issue.body == CUT_BODY.replace(above, above + row)
    assert issue.run("--add-lot", "L9", "--after", "US-1270/L2")[0] != 0


def test_add_lot_of_a_story_of_several_uses_the_label_and_defaults(tmp_path: Path) -> None:
    """US-1290: L3 #n for a story of several lots; no issue, no dependency, no model: the dash."""
    issue = cut_issue(tmp_path)
    assert issue.run("--add-lot", "US-1270/L3", "--after", "US-1270/L2b")[0] == 0
    assert "|   |   |   | L3 | — | — | à faire | — | — |\n| 4 |" in issue.body
    assert (
        issue.run("--add-lot", "US-1270/L4", "--after", "US-1270/L1", "--issue-number", "9")[0] == 0
    )
    assert "| L4 #9 | — |" in issue.body


def test_add_lot_leaves_unknown_columns_empty_and_takes_the_line_ending(tmp_path: Path) -> None:
    """US-1290: a column the tool does not know is empty; the ending is the row above's."""
    body = (
        "## Ordre de réalisation\r\n\r\n| Lot | Autre | US | Dépend de |\r\n|---|---|---|---|\r\n"
        "| lot unique | x | US-0010 #1 | — |\r\n\r\nFin."
    )
    issue = Issue(tmp_path, body)
    assert issue.run("--add-lot", "US-0010b", "--after", "US-0010")[0] == 0
    assert issue.body.endswith(
        "| lot unique | x | US-0010 #1 | — |\r\n| US-0010b |   |   | — |\r\n\r\nFin."
    )


def test_add_lot_refuses_a_row_that_exists_or_a_lot_it_does_not_find(tmp_path: Path) -> None:
    """US-1290: an existing lot, an unknown AFTER, another story's AFTER: refused, body kept."""
    issue = cut_issue(tmp_path)
    for lot, after in (
        ("US-0820b", "US-0820"),
        ("US-0830b", "US-0999"),
        ("US-0830b", "US-0820"),
        ("US-1270/L2b", "US-1270/L1"),
        ("US-0999b", "US-0999"),
    ):
        code, error = issue.run("--add-lot", lot, "--after", after)
        assert code == 1
        assert error.startswith("tracking: ")
    assert issue.run("--add-lot", "nonsense", "--after", "US-0830")[0] == 1
    assert issue.body == CUT_BODY
    assert issue.writes == 0


@pytest.mark.parametrize("ending", ["\n", "\r\n"])
def test_add_lot_after_the_last_line_of_a_body_without_a_final_break(
    tmp_path: Path, ending: str
) -> None:
    """US-1290: AFTER last, no final break: the neighbours' ending; the body ends without one."""
    body = ending.join(
        [
            "## Ordre de réalisation",
            "",
            "| US | Lot | Dépend de |",
            "|---|---|---|",
            "| US-0010 #1 | lot unique | — |",
        ]
    )
    issue = Issue(tmp_path, body)
    assert issue.run("--add-lot", "US-0010b", "--after", "US-0010")[0] == 0
    assert issue.body == body + ending + "|   | US-0010b | — |"


def test_replace_dependency_takes_the_number_of_the_old_lot_with_its_mention(
    tmp_path: Path,
) -> None:
    """US-1290: « US-0820 #2036 » in another row loses #2036, the old lot's issue."""
    body = CUT_BODY.replace("| US-0820, US-0850/L1 |", "| US-0820 #2036, US-0850/L1 |")
    issue = Issue(tmp_path, body)
    assert issue.run("--replace-dependency", "US-0820=US-0820b")[0] == 0
    assert "| US-0820b, US-0850/L1 |" in issue.body
    assert "#2036 |" in issue.body.split("US-0820b #2099")[1]
    assert issue.body.count("2036") == 2


def test_replace_dependency_refuses_a_row_shorter_than_the_header(tmp_path: Path) -> None:
    """US-1290: a short row is refused as change_lot refuses it, the body unchanged."""
    body = CUT_BODY.replace(
        "| 4 | US-0850 #2041 | à faire | L1 #2042 | US-0820b, US-0820/L1x | — | à faire | — | — |",
        "| 4 | US-0850 |",
    )
    assert body != CUT_BODY
    issue = Issue(tmp_path, body)
    code, error = issue.run("--replace-dependency", "US-0820=US-0820b")
    assert code == 1
    assert "shorter than the header" in error
    assert issue.writes == 0


def test_an_empty_value_is_refused_whatever_the_form(tmp_path: Path) -> None:
    """US-1290: --lot, --add-lot and --replace-dependency refuse an empty value."""
    issue = cut_issue(tmp_path)
    for arguments in (
        ["--lot", "", "--state", "x"],
        ["--add-lot", "", "--after", "US-0830"],
        ["--replace-dependency", ""],
    ):
        code, error = issue.run(*arguments)
        assert code == 1
        assert error.startswith("tracking: ")
    assert issue.writes == 0


def test_add_lot_refuses_a_missing_column_of_a_value_given(tmp_path: Path) -> None:
    """US-1290: DEPENDS or MODEL given, and the column missing: refused, as the form LOT does."""
    body = "## Ordre de réalisation\n\n| Lot | US |\n|---|---|\n| lot unique | US-0010 #1 |\n"
    issue = Issue(tmp_path, body)
    for option in ("--depends", "--model"):
        code, error = issue.run("--add-lot", "US-0010b", "--after", "US-0010", option, "x")
        assert code == 1
        assert "no column" in error
    assert issue.body == body


def test_depends_with_lot_replaces_the_cell(tmp_path: Path) -> None:
    """US-1290: LOT with DEPENDS replaces « Dépend de » of the lot, no other cell."""
    issue = cut_issue(tmp_path)
    assert issue.run("--lot", "US-0830", "--depends", "US-0820b #2099 | x")[0] == 0
    ((before, after),) = changed_lines(CUT_BODY, issue.body)
    assert after == before.replace(" US-0820 |", " US-0820b #2099 \\| x |", 1)
    assert issue.run("--us", "US-0830", "--status", "x", "--depends", "y")[0] == 1


def test_replace_dependency_counts_rows_and_keeps_the_cut_part(tmp_path: Path) -> None:
    """US-1290: the mention is replaced where it appears whole; the new lot keeps its own."""
    issue = cut_issue(tmp_path)
    process = issue.start(["--replace-dependency", "US-0820=US-0820b"])
    output, _ = process.communicate(timeout=60)
    assert process.returncode == 0
    assert "2 row" in output
    after = issue.body
    assert "| lot unique — en dernier | US-0820b |" in after
    assert "| US-0820b, US-0850/L1 |" in after
    assert "| US-0820b #2099 | US-0820 #2036 |" in after
    assert "US-0820b, US-0820/L1x" in after
    assert len(changed_lines(CUT_BODY, after)) == 2


def test_replace_dependency_refuses_a_mention_nobody_holds_or_a_malformed_pair(
    tmp_path: Path,
) -> None:
    """US-1290: no row holds the old one, or no « = »: refused, the body unchanged."""
    issue = cut_issue(tmp_path)
    for pair in ("US-0999=US-0820b", "US-0820", "=US-0820b", "US-0820="):
        assert issue.run("--replace-dependency", pair)[0] == 1
    assert issue.run("--replace-dependency", "US-0820=US-0820b", "--model", "x")[0] == 1
    assert issue.body == CUT_BODY
    assert issue.writes == 0


def test_the_new_forms_are_exclusive_and_refuse_a_line_break(tmp_path: Path) -> None:
    """US-1290: one form at a time; a value with a break is refused whatever the form."""
    issue = cut_issue(tmp_path)
    assert issue.run("--lot", "US-0830", "--add-lot", "US-0830b", "--after", "US-0830")[0] == 1
    assert issue.run("--add-lot", "US-0830b", "--replace-dependency", "a=b")[0] == 1
    assert issue.run("--add-lot", "US-0830b")[0] == 1
    assert issue.run("--lot", "US-0830", "--state", "x", "--after", "US-0830")[0] == 1
    assert issue.run("--add-lot", "US-0830b", "--after", "US-0830", "--state", "x")[0] == 1
    for arguments in (
        ["--add-lot", "US-0830b", "--after", "US-0830", "--depends", "a\nb"],
        ["--add-lot", "US-0830b", "--after", "US-0830", "--model", "a\rb"],
        ["--lot", "US-0830", "--depends", "a\nb"],
        ["--replace-dependency", "US-0820=a\nb"],
    ):
        code, error = issue.run(*arguments)
        assert code == 1
        assert "line break" in error
    assert issue.body == CUT_BODY
    assert issue.writes == 0


def test_a_pipe_is_escaped_in_the_added_row(tmp_path: Path) -> None:
    """US-1290: a pipe in DEPENDS or MODEL adds no column to the inserted row."""
    issue = cut_issue(tmp_path)
    code, _ = issue.run(
        "--add-lot", "US-0830b", "--after", "US-0830", "--depends", "a|b", "--model", "c|d"
    )
    assert code == 0
    row = next(line for line in issue.body.splitlines() if "US-0830b" in line)
    assert "a\\|b" in row
    assert "c\\|d" in row
    assert len(tracking.cells(row)) == 9


def test_the_new_forms_hold_the_lock_and_read_just_before_writing(tmp_path: Path) -> None:
    """US-1290: two simultaneous new forms each keep their change; the rest is byte for byte."""
    issue = cut_issue(tmp_path)
    first = issue.start(["--add-lot", "US-0830b", "--after", "US-0830"], delay="1")
    second = issue.start(["--replace-dependency", "US-0820=US-0820b"])
    for process in (first, second):
        process.communicate(timeout=60)
        assert process.returncode == 0
    assert issue.writes == 2
    assert "| US-0830b" in issue.body
    assert "| lot unique — en dernier | US-0820b |" in issue.body
    assert issue.body.endswith("## Constats ouverts\n\nAucun constat.\n")


def test_make_exposes_the_new_forms(tmp_path: Path) -> None:
    """US-1290: ADD_LOT, AFTER, DEPENDS, LOT_ISSUE and REPLACE_DEPENDENCY reach the tool."""
    issue = cut_issue(tmp_path)
    environment = {"AFTER": "US-0999", "DEPENDS": "x"}
    code = make_tracking(
        issue,
        ["ADD_LOT=US-0830b", "AFTER=US-0830", "LOT_ISSUE=2200", "DEPENDS=US-0830"],
        environment,
    )
    assert code == 0
    assert "| US-0830b #2200 | US-0830 |" in issue.body
    assert make_tracking(issue, ["REPLACE_DEPENDENCY=US-0999=US-0830c"], {}) != 0
    assert make_tracking(issue, ["REPLACE_DEPENDENCY=US-0830=US-0830c"], {}) == 0
    assert "| US-0830b #2200 | US-0830c |" in issue.body
    assert make_tracking(issue, ["ADD_LOT=US-0850b"], environment) != 0


def test_not_with_with_lot_replaces_the_cell_of_this_lot_alone(tmp_path: Path) -> None:
    """US-1910 (#3023): LOT with NOT_WITH writes « Pas avec » of that row, and no other row."""
    issue = cut_issue(tmp_path)
    assert issue.run("--lot", "US-1270/L2", "--not-with", "US-0850/L1 #2042 | x")[0] == 0
    ((before, after),) = changed_lines(CUT_BODY, issue.body)
    assert after == before.replace("| US-1270/L1 | — |", "| US-1270/L1 | US-0850/L1 #2042 \\| x |")
    # One row changed: the other side of the pair is written by a call of its own.
    assert issue.run("--lot", "US-1270/L2", "--not-with", "—", "--state", "en revue")[0] == 0


def test_not_with_with_add_lot_fills_the_cell_of_the_new_row(tmp_path: Path) -> None:
    """US-1910 (#3023): ADD_LOT with NOT_WITH writes the cell, and `—` without it."""
    issue = cut_issue(tmp_path)
    assert (
        issue.run("--add-lot", "US-0830b", "--after", "US-0830", "--not-with", "US-0850/L1")[0] == 0
    )
    assert issue.run("--add-lot", "US-1270/L3", "--after", "US-1270/L2")[0] == 0
    table = [line.split("|") for line in issue.body.splitlines() if line.startswith("|")]
    rows = {cells[4].strip(): cells[6].strip() for cells in table if len(cells) > 6}
    assert rows["US-0830b"] == "US-0850/L1"
    assert rows["L3"] == "—"


def test_not_with_goes_with_lot_or_add_lot_only_and_needs_its_column(tmp_path: Path) -> None:
    """US-1910 (#3023): NOT_WITH goes with LOT or ADD_LOT, and a table with its column."""
    issue = cut_issue(tmp_path)
    before = issue.body
    for arguments in (
        ["--us", "US-0830", "--status", "x", "--not-with", "y"],
        ["--replace-dependency", "US-0820=US-0820b", "--not-with", "y"],
        ["--finding", "9", "--not-with", "y"],
        ["--lot", "US-0830", "--not-with", "a\nb"],
    ):
        assert issue.run(*arguments)[0] == 1
    assert issue.body == before
    (tmp_path / "old").mkdir()
    old = Issue(tmp_path / "old", CUT_BODY.replace(" Pas avec |", "").replace("| — | — |", "| — |"))
    code, error = old.run("--lot", "US-0830", "--not-with", "US-0850")
    assert code == 1
    assert "no column" in error


def test_make_exposes_not_with(tmp_path: Path) -> None:
    """US-1910 (#3023): NOT_WITH reaches the tool from the command line of make, not the shell."""
    issue = cut_issue(tmp_path)
    assert make_tracking(issue, ["LOT=US-0830", "NOT_WITH=US-0850/L1"], {"NOT_WITH": "z"}) == 0
    assert "| US-0820 | US-0850/L1 |" in issue.body
    assert make_tracking(issue, ["LOT=US-0830"], {"NOT_WITH": "z"}) != 0


def epic_template() -> str:
    """Return the table of the field ``tracking`` of the epic template, without any YAML library.

    The block ``value: |`` of the field is the body: its lines, less the indentation of the block.
    """
    lines = (REPOSITORY / ".github" / "ISSUE_TEMPLATE" / "04-epic.yml").read_text().splitlines()
    field = lines.index("    id: tracking")
    start = next(i for i in range(field, len(lines)) if lines[i].strip() == "value: |") + 1
    block: list[str] = []
    for line in lines[start:]:
        if line.strip() and not line.startswith("        "):
            break
        block.append(line[8:])
    assert block
    return "\n".join(block).rstrip("\n") + "\n"


def test_the_epic_template_and_the_tool_agree(tmp_path: Path) -> None:
    """US-1290 (#1915): each form of make tracking applies to the table of 04-epic.yml."""
    body = epic_template()
    issue = Issue(tmp_path, body)
    issue.finding(2300, "[EP-99] outil : un constat", "OPEN")
    forms = [
        ["--lot", "US-0010/L1", "--state", "en cours", "--pr", "#5", "--model", "sonnet"],
        ["--lot", "US-0020", "--state", "en cours"],
        ["--us", "US-0020", "--status", "en cours"],
        ["--finding", "2300", "--attached", "US-0010 #", "--decision", "**à trancher**"],
        ["--add-lot", "US-0010/L3", "--after", "US-0010/L2", "--depends", "L2"],
        ["--replace-dependency", "US-0010/L2=US-0010/L3"],
        ["--lot", "US-0020", "--depends", "US-0010/L1"],
    ]
    for arguments in forms:
        before = issue.body
        code, error = issue.run(*arguments)
        assert code == 0, (arguments, error)
        assert issue.body != before, arguments
    assert "|   |   |   | L3 | L2 | — | à faire | — | — |" in issue.body
    assert "| US-0020 # | en cours | lot unique | US-0010/L1 |" in issue.body
