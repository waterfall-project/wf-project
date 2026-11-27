# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The known failures of the family ``migrations``, against which its outcomes are judged (US-2850).

The family fails on a failure of the version N that no entry of ``tools/migrations-known.toml``
recognises, and on an entry that no longer fails; these tests hold that judgement on outcomes
written by hand, and the list of the repository itself, which must read. They cite WF-DAT-0140-A:
an incompatibility of the migrations with the code of N is found, never let through unseen.
"""

import json
from typing import TYPE_CHECKING

import pytest

from wftools import migrationknown
from wftools.migrationknown import (
    KNOWN,
    KnownError,
    Outcome,
    judge,
    judged,
    load,
    outcomes,
)

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.story("US-2850")

SETUP = '[setup] E   psycopg.errors.NotNullViolation: null value in column "time_zone"'
COLUMN = 'E   psycopg.errors.UndefinedColumn: column "monthly_hours" does not exist'
ENTRIES = """
[[known]]
version = "v0.3.0"
part = "tests"
issue = "#5090"
message = 'null value in column "time_zone"'
cause = "établie : 0029 retire le défaut"

[[known]]
version = "v0.3.0"
part = "tests"
issue = "#5091"
tests = ["tests/test_roles.py"]
message = 'column "monthly_hours" does not exist'
cause = "établie : 0034 supprime la colonne"

[[known]]
version = "v0.3.0"
part = "tests"
category = "frozen schema"
tests = ["tests/test_constraints.py::test_named", "tests/test_index.py::test_plan"]
cause = "établie : le test lit le nom d'une contrainte de N"

[[known]]
version = "v0.2.0"
part = "tests"
issue = "#4000"
tests = ["tests/test_old.py::test_gone"]
cause = "établie : une version d'avant"
"""


def held(part: str = "tests", version: str = "v0.3.0") -> list[migrationknown.Known]:
    """Return the entries above of a version and a part, as the judge holds them."""
    return [each for each in load(ENTRIES) if each.version == version and each.part == part]


@pytest.mark.requirement("WF-DAT-0140-A")
def test_a_failure_no_entry_recognises_is_new_and_fails_the_family() -> None:
    run = [
        Outcome("tests/test_projects.py::test_create", "failed", SETUP),
        Outcome("tests/test_projects.py::test_rename", "failed", "E   assert 500 == 200"),
        Outcome("tests/test_constraints.py::test_named", "failed", "E   assert 'a' == 'b'"),
        Outcome("tests/test_index.py::test_plan", "failed", "E   assert False"),
    ]
    verdict = judge(run, held())
    assert [outcome.test for outcome in verdict.new] == ["tests/test_projects.py::test_rename"]
    assert verdict.recognised == {0: 1, 1: 0, 2: 2}
    assert not verdict.passed


@pytest.mark.requirement("WF-DAT-0140-A")
def test_an_entry_by_its_message_recognises_a_shared_error_of_setting_up_in_any_test() -> None:
    run = [Outcome(f"tests/test_{n}.py::test_x", "failed", SETUP) for n in range(30)]
    verdict = judge(run, held())
    assert verdict.recognised[0] == 30
    assert verdict.new == []


@pytest.mark.requirement("WF-DAT-0140-A")
def test_an_entry_by_its_tests_and_its_message_does_not_recognise_another_failure_of_them() -> None:
    run = [
        Outcome("tests/test_roles.py::test_a", "failed", COLUMN),
        Outcome("tests/test_roles.py::test_b[case1]", "failed", "E   KeyError: 'hours'"),
        Outcome("tests/test_other.py::test_c", "failed", COLUMN),
    ]
    verdict = judge(run, held())
    assert [outcome.test for outcome in verdict.new] == [
        "tests/test_roles.py::test_b[case1]",
        "tests/test_other.py::test_c",
    ]


@pytest.mark.requirement("WF-DAT-0140-A")
def test_a_known_failure_that_passes_now_fails_the_family_so_that_its_entry_leaves() -> None:
    run = [
        Outcome("tests/test_projects.py::test_create", "failed", SETUP),
        Outcome("tests/test_roles.py::test_a", "failed", COLUMN),
        Outcome("tests/test_constraints.py::test_named", "passed"),
        Outcome("tests/test_index.py::test_plan", "failed", "E   assert False"),
    ]
    verdict = judge(run, held())
    assert verdict.new == []
    assert [(entry.reason, said) for entry, said in verdict.stale] == [
        ("frozen schema", "tests/test_constraints.py::test_named passes")
    ]
    assert not verdict.passed


@pytest.mark.requirement("WF-DAT-0140-A")
def test_an_entry_by_its_message_that_recognises_nothing_any_more_is_stale() -> None:
    run = [
        Outcome("tests/test_projects.py::test_create", "passed"),
        Outcome("tests/test_roles.py::test_a", "failed", COLUMN),
        Outcome("tests/test_constraints.py::test_named", "failed", "E"),
        Outcome("tests/test_index.py::test_plan", "failed", "E"),
    ]
    verdict = judge(run, held())
    assert [(entry.reason, said) for entry, said in verdict.stale] == [
        ("#5090", "it recognised no failure")
    ]


@pytest.mark.requirement("WF-DAT-0140-A")
def test_a_part_of_the_suite_without_a_failure_of_an_entry_by_its_message_holds() -> None:
    # SHARD=i/N: the failures of #5090 may all lie in another part; only the whole suite judges it.
    run = [
        Outcome("tests/test_projects.py::test_create", "passed"),
        Outcome("tests/test_roles.py::test_a", "failed", COLUMN),
    ]
    assert judge(run, held(), whole=False).passed
    assert not judge(run, held()).passed


def test_a_test_named_that_this_part_did_not_run_or_skipped_is_not_judged() -> None:
    # SHARD=i/N runs a part of the tests: those of the other parts are absent from the outcomes.
    run = [
        Outcome("tests/test_projects.py::test_create", "failed", SETUP),
        Outcome("tests/test_constraints.py::test_named", "skipped"),
    ]
    verdict = judge(run, held())
    assert verdict.passed
    assert verdict.recognised == {0: 1, 1: 0, 2: 0}


def test_a_file_named_is_stale_only_when_none_of_its_tests_fails_as_said() -> None:
    entries = [each for each in held() if each.reason == "#5091"]
    still = [
        Outcome("tests/test_roles.py::test_a", "passed"),
        Outcome("tests/test_roles.py::test_b", "failed", COLUMN),
    ]
    assert judge(still, entries).stale == []
    settled = [Outcome("tests/test_roles.py::test_a", "passed")]
    assert [said for _, said in judge(settled, entries).stale] == ["tests/test_roles.py passes"]


def test_an_intermittent_entry_recognises_its_failure_where_it_lands_and_is_never_stale() -> None:
    entries = load(
        """
[[known]]
version = "v0.3.0"
part = "tests"
issue = "#5200"
message = 'Exception ignored while calling deallocator'
intermittent = true
cause = "hypothèse : une connexion laissée ouverte par un autre test"
"""
    )
    landed = [
        Outcome(
            "tests/test_users.py::test_x", "failed", "Exception ignored while calling deallocator"
        )
    ]
    assert judge(landed, entries).recognised == {0: 1}
    assert judge([Outcome("tests/test_users.py::test_x", "passed")], entries).passed


def test_the_entries_of_another_version_or_part_are_not_judged() -> None:
    assert [each.reason for each in held("tests", "v0.2.0")] == ["#4000"]
    assert held("backup") == []


@pytest.mark.parametrize(
    ("entry", "said"),
    [
        ('part = "tests"\nissue = "#1"\ntests = ["t"]\ncause = "c"', "its version"),
        ('version = "v0.3.0"\npart = "e2e"\nissue = "#1"\ntests = ["t"]\ncause = "c"', "its part"),
        ('version = "v0.3.0"\npart = "tests"\ntests = ["t"]\ncause = "c"', "one of a finding"),
        (
            (
                'version = "v0.3.0"\npart = "tests"\nissue = "#1"\ncategory = "frozen schema"\n'
                'tests = ["t"]\ncause = "c"'
            ),
            "one of a finding",
        ),
        ('version = "v0.3.0"\npart = "tests"\nissue = "5090"\ntests = ["t"]\ncause = "c"', "#n"),
        (
            'version = "v0.3.0"\npart = "tests"\ncategory = "slow"\ntests = ["t"]\ncause = "c"',
            "its category",
        ),
        ('version = "v0.3.0"\npart = "tests"\nissue = "#1"\ntests = ["t"]', "its cause"),
        ('version = "v0.3.0"\npart = "tests"\nissue = "#1"\ncause = "c"', "names its tests"),
        ('version = "v0.3.0"\npart = "tests"\nissue = "#1"\ntests = [1]\ncause = "c"', "nodes"),
        (
            'version = "v0.3.0"\npart = "tests"\nissue = "#1"\nmessage = "("\ncause = "c"',
            "no pattern",
        ),
        (
            (
                'version = "v0.3.0"\npart = "tests"\nissue = "#1"\nmessage = "x"\ncause = "c"\n'
                'intermittent = "yes"'
            ),
            "true or false",
        ),
    ],
)
def test_an_entry_that_would_recognise_anything_or_nothing_is_refused(
    entry: str, said: str
) -> None:
    with pytest.raises(KnownError, match=said):
        load(f"[[known]]\n{entry}\n")


def test_a_list_that_does_not_read_is_refused() -> None:
    with pytest.raises(KnownError, match="do not read"):
        load("[[known]\n")


def test_the_outcomes_are_read_a_line_each_and_a_line_that_does_not_read_is_named() -> None:
    line = json.dumps({"test": "tests/t.py::test_a", "status": "failed", "message": "E"})
    assert outcomes(f"{line}\n") == [Outcome("tests/t.py::test_a", "failed", "E")]
    with pytest.raises(KnownError, match="line 2"):
        outcomes(f"{line}\nnot json\n")
    with pytest.raises(KnownError, match="no status"):
        outcomes(json.dumps({"test": "t", "status": "xfailed", "message": ""}))


@pytest.mark.requirement("WF-DAT-0140-A")
def test_the_known_failures_of_the_repository_read_and_each_names_its_finding_or_category() -> None:
    entries = load(KNOWN.read_text(encoding="utf-8"))
    for entry in entries:
        assert entry.reason.startswith("#") or entry.reason in migrationknown.CATEGORIES
        assert entry.cause.startswith(("établie : ", "hypothèse : "))


def write(path: Path, rows: list[Outcome]) -> Path:
    """Write outcomes as the plugin writes them."""
    lines = [json.dumps({"test": r.test, "status": r.status, "message": r.message}) for r in rows]
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    return path


@pytest.mark.requirement("WF-DAT-0140-A")
def test_a_run_judged_says_each_entry_and_names_each_new_failure_with_its_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    known = tmp_path / "known.toml"
    known.write_text(ENTRIES, encoding="utf-8")
    monkeypatch.setattr(migrationknown, "KNOWN", known)
    report = write(
        tmp_path / "outcomes.jsonl",
        [
            Outcome("tests/test_projects.py::test_create", "failed", SETUP),
            Outcome("tests/test_new.py::test_x", "failed", "E   assert 500 == 200"),
            Outcome("tests/test_constraints.py::test_named", "failed", "E"),
            Outcome("tests/test_index.py::test_plan", "failed", "E"),
        ],
    )
    assert not judged("v0.3.0", "tests", report, 1)
    said = capsys.readouterr()
    assert "known, #5090: 1 failure(s) of v0.3.0 (tests)" in said.out
    assert "new failure: tests/test_new.py::test_x\n    E   assert 500 == 200" in said.out
    assert "the known failures of v0.2.0 are not judged: N is v0.3.0" in said.out
    assert "1 new failure(s) of v0.3.0" in said.err


def test_pytest_that_did_not_run_its_tests_to_their_end_fails_whatever_its_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = write(tmp_path / "outcomes.jsonl", [])
    assert not judged("v0.3.0", "backup", report, 2)
    assert "did not run the tests of backup to their end (2)" in capsys.readouterr().err


def test_a_report_that_is_missing_fails_the_part(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert not judged("v0.3.0", "tests", tmp_path / "absent.jsonl", 0)
    assert "absent.jsonl" in capsys.readouterr().err


def test_a_run_without_new_failure_nor_stale_entry_holds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    known = tmp_path / "known.toml"
    known.write_text(ENTRIES, encoding="utf-8")
    monkeypatch.setattr(migrationknown, "KNOWN", known)
    report = write(
        tmp_path / "outcomes.jsonl",
        [
            Outcome("tests/test_projects.py::test_create", "failed", SETUP),
            Outcome("tests/test_projects.py::test_rename", "passed"),
        ],
    )
    assert judged("v0.3.0", "tests", report, 1)


@pytest.mark.requirement("WF-DAT-0140-A")
@pytest.mark.parametrize("statuses", [[], ["skipped", "skipped"]])
def test_a_part_where_no_test_passed_or_failed_fails_though_nothing_is_new(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    statuses: list[str],
) -> None:
    known = tmp_path / "known.toml"
    known.write_text(ENTRIES, encoding="utf-8")
    monkeypatch.setattr(migrationknown, "KNOWN", known)
    rows = [Outcome(f"tests/test_x.py::test_{n}", status) for n, status in enumerate(statuses)]
    report = write(tmp_path / "outcomes.jsonl", rows)
    assert not judged("v0.3.0", "backup", report, 0)
    assert "no test of backup passed or failed" in capsys.readouterr().err
