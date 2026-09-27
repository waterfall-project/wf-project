# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Repository tools of Waterfall, sharing one reader of the specification projection."""

from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]
"""The root of the repository, whatever directory a tool is started from."""
