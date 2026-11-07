# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Create and check the merge queue of an epic's branch (US-1370).

Usage: ``python -m wftools.mergequeue create EP-nn`` or ``check EP-nn``.

GitHub accepts a merge queue on a branch, not on a pattern of branches: each ``epic/EP-nn`` has
its own ruleset. ``create`` reads the model ``.github/rulesets/merge-queue.json``, puts in it the
name ``merge queue epic/EP-nn`` and the branch ``refs/heads/epic/EP-nn``, and posts it through
``gh api``, refusing when a ruleset already targets the branch. It is for a person: a deliverer
only runs ``check``, which wants a ruleset targeting the branch that is ``active`` and has a
``merge_queue`` rule, and says what is missing. The list of rulesets does not carry their
conditions: each one is read to know the branch it targets, over all the pages of the list
(``--paginate --slurp``), and a ruleset that excludes the branch does not target it. ``check``
passes as soon as one of the rulesets targeting the branch is active with a ``merge_queue`` rule.
"""

import argparse
import json
import re
import sys
from typing import cast

from wftools import REPOSITORY
from wftools.tracking import TrackingError, gh, refuse

MODEL = REPOSITORY / ".github" / "rulesets" / "merge-queue.json"
EPIC = re.compile(r"EP-\d+")
RULESETS = "repos/{owner}/{repo}/rulesets"


def parse_json(text: str, what: str) -> object:
    """Return the JSON ``gh`` answered, or refuse an answer that is not."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        message = f"gh api did not answer JSON for {what}"
        raise TrackingError(message) from error


def read_ruleset(identifier: object) -> dict[str, object]:
    """Return a ruleset by its identifier."""
    data = parse_json(gh(["api", f"{RULESETS}/{identifier}"]), f"ruleset {identifier}")
    if not isinstance(data, dict):
        refuse(f"gh api did not answer an object for ruleset {identifier}")
    return cast("dict[str, object]", data)


def targeting(branch: str) -> list[dict[str, object]]:
    """Return the rulesets of the repository that target a branch, each read in full."""
    pages = parse_json(gh(["api", "--paginate", "--slurp", RULESETS]), "the rulesets")
    if not isinstance(pages, list):
        refuse("gh api did not answer a list of pages for the rulesets")
    listed: list[object] = []
    for page in cast("list[object]", pages):
        if not isinstance(page, list):
            refuse("gh api did not answer a list of pages for the rulesets")
        listed.extend(cast("list[object]", page))
    found: list[dict[str, object]] = []
    for summary in listed:
        if not isinstance(summary, dict) or "id" not in summary:
            refuse("gh api answered a ruleset without id")
        ruleset = read_ruleset(cast("dict[str, object]", summary)["id"])
        if matches(branch, ref_names(ruleset, "include")) and not matches(
            branch, ref_names(ruleset, "exclude")
        ):
            found.append(ruleset)
    return found


def matches(branch: str, patterns: list[object]) -> bool:
    """Say whether a reference matches one of the patterns of ``ref_name``.

    The patterns of GitHub (``refs/heads/epic/*``, ``refs/heads/epic/EP-2?``, ``~ALL``) are read
    as ``fnmatch`` does with ``File::FNM_PATHNAME``, which GitHub applies: a ``*`` and a ``?``
    stop at a ``/``, a ``**`` crosses it. So ``refs/heads/*`` does not take an epic's branch,
    ``refs/heads/epic/EP-21``, and ``refs/heads/**`` does. ``~DEFAULT_BRANCH`` is not resolved: it
    never matches an epic's branch.
    """
    return any(
        isinstance(pattern, str)
        and (pattern == "~ALL" or re.fullmatch(pathname_pattern(pattern), branch) is not None)
        for pattern in patterns
    )


def pathname_pattern(pattern: str) -> str:
    """Translate a pattern of ``fnmatch`` with ``FNM_PATHNAME`` into a regular expression."""
    translated: list[str] = []
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if pattern.startswith("**", index):
            translated.append(".*")
            index += 2
            continue
        closing = pattern.find("]", index + 2) if char == "[" else -1
        if char == "[" and closing > 0:
            members = pattern[index + 1 : closing]
            members = "^" + members[1:] if members[:1] in ("!", "^") else members
            translated.append(f"[{members.replace(chr(92), chr(92) * 2)}]")
            index = closing
        elif char == "*":
            translated.append("[^/]*")
        elif char == "?":
            translated.append("[^/]")
        else:
            translated.append(re.escape(char))
        index += 1
    return "".join(translated)


def ref_names(ruleset: dict[str, object], key: str) -> list[object]:
    """Return the references a ruleset includes or excludes (``key``), none when it names none."""
    conditions = ruleset.get("conditions")
    names = (
        cast("dict[str, object]", conditions).get("ref_name")
        if isinstance(conditions, dict)
        else None
    )
    if not isinstance(names, dict):
        return []
    listed = cast("dict[str, object]", names).get(key)
    return cast("list[object]", listed) if isinstance(listed, list) else []


def problems(ruleset: dict[str, object]) -> list[str]:
    """Return what keeps a ruleset from being a working merge queue."""
    missing: list[str] = []
    if ruleset.get("enforcement") != "active":
        missing.append(f"the ruleset is {ruleset.get('enforcement')}, not active")
    rules = ruleset.get("rules")
    kinds = (
        [
            cast("dict[str, object]", rule).get("type")
            for rule in cast("list[object]", rules)
            if isinstance(rule, dict)
        ]
        if isinstance(rules, list)
        else []
    )
    if "merge_queue" not in kinds:
        missing.append("the ruleset has no merge_queue rule")
    return missing


def create(epic: str) -> None:
    """Create the ruleset of the merge queue of an epic's branch, from the model."""
    branch = f"refs/heads/epic/{epic}"
    if targeting(branch):
        refuse(f"a ruleset already targets {branch}")
    model = parse_json(MODEL.read_text(encoding="utf-8"), str(MODEL))
    if not isinstance(model, dict):
        refuse(f"{MODEL} is not an object")
    ruleset = cast("dict[str, object]", model)
    ruleset["name"] = f"merge queue epic/{epic}"
    ruleset["conditions"] = {"ref_name": {"exclude": [], "include": [branch]}}
    gh(["api", "--method", "POST", RULESETS, "--input", "-"], stdin=json.dumps(ruleset))
    print(f"merge-queue: created the ruleset {ruleset['name']!r} on {branch}")


def check(epic: str) -> None:
    """Refuse, saying what is missing, unless a working merge queue targets the branch."""
    branch = f"refs/heads/epic/{epic}"
    found = targeting(branch)
    if not found:
        refuse(f"no ruleset targets {branch}: a person runs `make merge-queue EPIC={epic}`")
    if any(not problems(ruleset) for ruleset in found):
        print(f"merge-queue: {branch} has an active merge queue")
        return
    missing = [f"{ruleset.get('name')}: {text}" for ruleset in found for text in problems(ruleset)]
    refuse(f"no working merge queue on {branch}: " + "; ".join(missing))


def main(arguments: list[str]) -> int:
    """Run the command; return 1 and say why when it fails."""
    parser = argparse.ArgumentParser(prog="mergequeue", description=__doc__)
    parser.add_argument("command", choices=["create", "check"])
    parser.add_argument("epic", nargs="?", default="")
    options = parser.parse_args(arguments)
    try:
        if not EPIC.fullmatch(options.epic):
            refuse(f"EPIC must be of the form EP-nn, not {options.epic!r}")
        (create if options.command == "create" else check)(options.epic)
    except (TrackingError, OSError) as error:
        print(f"merge-queue: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
