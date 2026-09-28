# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Entry point of the API service.

The service itself arrives with EP-03; until then the process starts, states its version,
and stops.
"""

import sys

from waterfall import __version__


def main() -> int:
    """Start the API service."""
    sys.stdout.write(f"waterfall-api {__version__}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
