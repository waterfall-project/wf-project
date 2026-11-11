# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The exchanges (FBS-4.3.4, FLX-01 to FLX-07): the imports in two steps, and the exports.

What other modules read goes through ``interface``. The exchanges know no format: a module
registers the format of a kind of import and the exporter of a kind of export, and the exchanges
deposit, open, analyse, apply and export through them (EP-06, "L'import en deux temps").
"""
