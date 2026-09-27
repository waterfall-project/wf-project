# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The business core (PBS-2.3): one subpackage per module, modelled on a block of the FBS.

A module exposes what others may use in its ``interface`` module, and nothing else: its
tables and its data access are private to it. ``make check-back`` rejects an import from
one module into another that does not go through the interface.
"""
