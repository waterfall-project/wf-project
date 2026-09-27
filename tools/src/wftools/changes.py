# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tell which families of checks a change touches.

Usage: ``python -m wftools.changes BASE [HEAD] [--targets]``.

The chain names both ends; on a workstation, leaving HEAD out takes the working tree, so
that a change is checked before it is committed.

Without ``--targets``, prints one ``family=true`` or ``family=false`` line per family: the
form GitHub Actions reads from ``$GITHUB_OUTPUT``. With it, prints the Makefile targets of
the touched families, one per line, for ``make check``.
"""

import argparse
import subprocess
import sys

from wftools import REPOSITORY, paths


def changed_paths(base: str, head: str | None = None) -> list[str]:
    """The paths a change adds, modifies, renames or deletes, relative to the repository.

    With a head, the change is what the head adds to its merge base with the base, as a
    pull request shows it. Without one, it is what the working tree adds to that merge
    base, uncommitted and untracked files included: what `make check` sees before a commit.
    """
    if head is not None:
        return _git("diff", "--name-only", "--no-renames", f"{base}...{head}")
    (merge_base,) = _git("merge-base", base, "HEAD")
    changed = _git("diff", "--name-only", "--no-renames", merge_base)
    untracked = _git("ls-files", "--others", "--exclude-standard")
    return sorted(set(changed) | set(untracked))


def _git(*arguments: str) -> list[str]:
    result = subprocess.run(
        ["git", *arguments], cwd=REPOSITORY, capture_output=True, text=True, check=True
    )
    return [line for line in result.stdout.splitlines() if line]


def main(arguments: list[str]) -> int:
    """Print the families or the targets a change touches."""
    parser = argparse.ArgumentParser(prog="wftools.changes", description=__doc__.splitlines()[0])
    parser.add_argument("base", help="the branch or commit the change is compared with")
    parser.add_argument("head", nargs="?", help="the tip of the change; the working tree if absent")
    parser.add_argument("--targets", action="store_true", help="print Makefile targets")
    options = parser.parse_args(arguments)
    declaration = paths.read()
    touched = declaration.touched(changed_paths(options.base, options.head))
    if options.targets:
        for family in touched:
            print(family.target)
    else:
        for family in declaration.families:
            print(f"{family.name}={'true' if family in touched else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
