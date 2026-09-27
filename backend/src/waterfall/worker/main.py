# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Entry point of the worker.

The task queue arrives with EP-03; until then the process starts, states its version, and
stops.
"""

import sys

from waterfall import __version__


def main() -> int:
    """Start the worker."""
    print(f"waterfall-worker {__version__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
