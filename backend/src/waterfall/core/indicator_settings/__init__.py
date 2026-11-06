# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicator settings (FBS-3.4): what other modules read goes through ``interface``.

No table of its own: the thresholds of the indices and the delay between two reviews are a part of
the settings the installation shares, read and written through the interface of
``cost_settings``; this module holds their rules.
"""
