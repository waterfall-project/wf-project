# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The permissions of the deliverers follow the repository (US-1350).

``.claude/settings.json`` is versioned, so a fresh worktree has the rules a deliverer needs. The
rules have the form ``Bash(<prefix>:*)``: a command is covered when it starts with ``<prefix>``
followed by a space or the end of the command. The queue rule is ``Bash(gh api graphql:*)``, wider
than the mutation, which stays the only form the deliverer writes. A tool of the repository: no
test cites a requirement (WF-QUA-0010).
"""

import json
from typing import Any, cast

import pytest

from wftools import REPOSITORY

SETTINGS = REPOSITORY / ".claude" / "settings.json"
GUARD_HOOK = 'python3 "$CLAUDE_PROJECT_DIR/tools/src/wftools/guard.py"'
ENQUEUE = (
    "gh api graphql -f query='mutation($id:ID!){enqueuePullRequest(input:{pullRequestId:$id})"
    "{mergeQueueEntry{state}}}' -f id=PR_kwDOAbc123"
)


def _settings() -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads(SETTINGS.read_text(encoding="utf-8")))


def _allow() -> list[str]:
    return cast("list[str]", _settings()["permissions"]["allow"])


def _covered(command: str, rules: list[str]) -> bool:
    for rule in rules:
        if rule.startswith("Bash(") and rule.endswith(":*)"):
            prefix = rule[len("Bash(") : -len(":*)")]
            if command == prefix or command.startswith(prefix + " "):
                return True
    return False


def test_the_pre_tool_use_hook_on_bash_is_the_guard() -> None:
    """The ``PreToolUse`` hook on ``Bash`` runs the guard, and the file stays a JSON."""
    entries = cast("list[dict[str, Any]]", _settings()["hooks"]["PreToolUse"])
    commands = [
        cast("str", h["command"])
        for e in entries
        if e["matcher"] == "Bash"
        for h in cast("list[dict[str, Any]]", e["hooks"])
    ]
    assert commands == [GUARD_HOOK]
    assert (REPOSITORY / "tools" / "src" / "wftools" / "guard.py").is_file()


@pytest.mark.parametrize(
    "command",
    [ENQUEUE, "make tracking ISSUE=2249", "make slot", "make slot-release", "make e2e-down"],
)
def test_the_commands_of_the_deliverer_are_allowed(command: str) -> None:
    """The queue mutation and the four ``make`` commands of the deliverer are covered."""
    assert _covered(command, _allow())


ALLOWED = [
    "Bash(cd:*)",
    "Bash(gh api graphql:*)",
    "Bash(gh issue create:*)",
    "Bash(gh issue close:*)",
    "Bash(gh issue comment:*)",
    "Bash(gh issue edit:*)",
    "Bash(gh pr create:*)",
    "Bash(gh pr view:*)",
    "Bash(gh pr checks:*)",
    "Bash(gh pr list:*)",
    "Bash(gh pr merge:*)",
    "Bash(gh run list:*)",
    "Bash(gh run view:*)",
    "Bash(gh run watch:*)",
    "Bash(git push:*)",
    "Bash(git branch -d:*)",
    "Bash(git worktree unlock:*)",
    "Bash(git worktree remove:*)",
    "Bash(make tracking:*)",
    "Bash(make slot:*)",
    "Bash(make slot-release:*)",
    "Bash(make e2e-down:*)",
]


def test_the_allow_list_is_the_twenty_two_rules_of_the_story() -> None:
    """Exactly the twenty-two rules (US-1350's twenty-one and ``make e2e-down``), no duplicate."""
    allow = _allow()
    assert len(allow) == len(set(allow))
    assert set(allow) == set(ALLOWED)
    assert not _covered("gh api repos/x/y", allow)
