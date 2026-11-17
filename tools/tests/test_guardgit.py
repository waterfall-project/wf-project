# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The forms of the command guard that reach ``.git`` and its locks, judged by ``guardgit.py``.

US-2450 (#2417): ``find`` that names ``.git`` and removes, ``rm``, ``mv`` and ``truncate`` of an
operand that reaches ``.git`` — a path through it, a pattern that matches it, the value of an
option —, and the patterns too long or too many to follow, which the guard refuses without
looking. The guard is a tool of the repository: no test cites a requirement (WF-QUA-0010).
"""

import pytest

from wftools import guard


def refused(command: str) -> bool:
    return guard.refusal(command) is not None


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    "command",
    [
        "find . -name .git -exec rm -rf {} +",
        "find . -name .git -delete",
        "find . -type d -name .git -prune -exec rm -rf {} +",
        "find . -path '*/.git' -prune -exec rm -rf {} ';'",
        "find . -name '.git*' -execdir rm -rf {} +",
        "find . \\( -name .git -o -name x \\) -exec rm -rf {} +",
        "find . -name x -o -name .git -prune -exec rm -rf {} +",
        "find . -name .git -exec truncate -s0 {} +",
    ],
)
def test_a_find_that_names_git_and_removes_is_refused(command: str) -> None:
    """#2417: `find -name .git` with `-exec rm` or `-delete`, and `-prune -exec rm -rf`."""
    form = guard.refusal(command)
    assert form is not None
    assert "`find … -name .git` with `-delete` or `-exec rm`" in form


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    "command",
    [
        "find . -name .git -prune -o -name '*.pyc' -delete",
        "find . -name .git -prune -o -type f -name '*.o' -exec rm {} +",
        "find . -name .github -exec rm -rf {} +",
        "find . -name .gitignore -delete",
        "find . -name .git -print",
    ],
)
def test_a_find_that_skips_git_or_only_lists_it_passes(command: str) -> None:
    """#2417: past an `-o`, the removal does not reach what `-name .git -prune` matched."""
    assert not refused(command)


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    ("command", "form"),
    [
        ("rm -rf .git/refs", "`rm .git/refs`"),
        ("rm -rf .git*", "`rm .git*`"),
        ("rm -f .git?", "`rm .git?`"),
        ("rm .git", "`rm .git`"),
        ("rm .git/HEAD", "`rm .git/HEAD`"),
        ("rm -rf -- ../other/.git/objects", "`rm ../other/.git/objects`"),
        ("unlink .git", "`unlink .git`"),
        ("mv .git /tmp/git.old", "`mv .git`"),
        ("mv .git/refs/heads/main /tmp", "`mv .git/refs/heads/main`"),
        ("mv -t .git/hooks pre-commit", "`mv .git/hooks`"),
        ("truncate -s0 .git/index", "`truncate .git/index`"),
        ("sudo truncate --size 0 .git/HEAD", "`truncate .git/HEAD`"),
        ("mv --target-directory=.git x", "`mv .git`"),
        ("mv -t.git/hooks x", "`mv .git/hooks`"),
        ("truncate --reference=.git/index -s0 x", "`truncate .git/index`"),
        ("rm -rf .g*", "`rm .g*`"),
        ("rm -rf .gi?", "`rm .gi?`"),
        ("rm -rf .[g]it", "`rm .[g]it`"),
        ("rm -rf .[^x]it", "`rm .[^x]it`"),
        ("rm -rf .*", "`rm .*`"),
        ("rm -rf .{git,x}", "`rm .{git,x}`"),
        ("rm -rf {.git,x}/refs", "`rm {.git,x}/refs`"),
    ],
)
def test_rm_mv_and_truncate_of_an_operand_that_reaches_git_are_refused(
    command: str, form: str
) -> None:
    """#2417: an operand that is `.git`, passes through `.git/` or opens by `.git` and a joker."""
    said = guard.refusal(command)
    assert said is not None
    assert said.startswith(form)
    assert "the repository that every worktree shares" in said


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    "command",
    ["truncate -s0 .git/index.lock", "cd .git && truncate -s 0 index.lock"],
)
def test_truncating_a_lock_of_git_is_refused_as_its_removal(command: str) -> None:
    """#2417: `truncate -s0 .git/index.lock` empties the lock a git command holds."""
    said = guard.refusal(command)
    assert said is not None
    assert "a lock of git is held by a git command that runs" in said


@pytest.mark.story("US-2450")
@pytest.mark.parametrize("operand", ["." + "[" * 300, "{a,b}" * 9 + "x"])
def test_a_pattern_too_long_to_match_or_braces_too_many_to_expand_are_taken_for_git(
    operand: str,
) -> None:
    """#2417: past a name's length, or 256 expansions, the guard does not look: it refuses."""
    said = guard.refusal(f"rm -rf {operand}")
    assert said is not None
    assert "the repository that every worktree shares" in said


@pytest.mark.story("US-2450")
@pytest.mark.parametrize(
    "command",
    [
        "rm -rf .gitignore .github .git-old",
        "mv .gitignore .gitignore.bak",
        "truncate -s0 build/log.txt",
        "truncate -s 0 frontend/.github/x",
        "rename 's/.git/x/' notes.txt",
        "rm -rf * .gitignore",
        "rm -rf .g?thub .{github,gitignore} .[!g]it",
        "mv --target-directory=build x",
        "find . -name x -exec truncate -s0 {} +",
    ],
)
def test_an_operand_next_to_git_passes(command: str) -> None:
    """#2417: `.gitignore`, `.github`, `.git-old` are not `.git`; `rename` takes an expression."""
    assert not refused(command)
