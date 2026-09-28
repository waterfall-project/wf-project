# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Decide the outcome of the chain from the results of its jobs.

GitHub Actions gives a job the results of the jobs it depends on as JSON, through
``toJSON(needs)``; the chain passes the JSON in the ``NEEDS`` environment variable. The
chain passes when no job failed or was cancelled. A job skipped because its family was not
touched is not a failure: this is what lets branch protection require this single check
while each family runs only when a pull request touches it.
"""

import json
import os
import sys
from collections.abc import Mapping

FAILED = frozenset({"failure", "cancelled"})


def failures(needs: Mapping[str, Mapping[str, object]]) -> list[str]:
    """Return the jobs that failed or were cancelled, by name."""
    return sorted(name for name, job in needs.items() if job.get("result") in FAILED)


def main() -> int:
    """Print each job and its result, and fail if one of them failed."""
    needs: dict[str, dict[str, object]] = json.loads(os.environ.get("NEEDS", "{}"))
    if not needs:
        print("NEEDS is empty: the gate has nothing to judge", file=sys.stderr)
        return 1
    for name, job in sorted(needs.items()):
        print(f"  {job.get('result')!s:<10} {name}")
    failed = failures(needs)
    if failed:
        print(f"failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
