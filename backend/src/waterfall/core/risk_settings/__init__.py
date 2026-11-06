# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The risk settings (FBS-3.3): what other modules read goes through ``interface``.

No table of its own: the matrix of risks is a part of the settings the installation shares, read
and written through the interface of ``cost_settings``; this module holds its rules.
"""
