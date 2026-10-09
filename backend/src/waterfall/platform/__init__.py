# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What is not a function of the business: settings and secrets, logs, correlation, errors.

It sits under the core: the core, the API and the worker import it, and it imports none of
them. A module here knows no table of the core.
"""
