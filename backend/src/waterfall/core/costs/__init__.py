# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The actual costs (FBS-4.7, FLX-07): the lines the ERP extracts, imported, imputed and excluded.

What other modules read goes through ``interface``. The module imports the projects, the cost
settings — the mapping of the extraction —, the exchanges — the format it registers —, the users and
the platform; neither the estimate nor the planning, which read it or call its registries (EP-09,
"Ce que le cadrage décide").
"""
