# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Waterfall: the business core, the API service and the worker, in one package."""

from importlib.metadata import version

__version__ = version("waterfall")
"""The version of the installed distribution, which the API and the worker both report."""
