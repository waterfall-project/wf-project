# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the operations of ``api/hourly_rates.py`` ask for: the hourly rates.

``test_access_evaluation.py`` gathers them; US-0830 declares each operation it serves.
"""

READ = "cost_settings.read"
CHANGE = "cost_settings.write"

# The permissions each operation asks for, in the order they are evaluated. The rates are close to
# the payroll: the grid and the rates of a category are read under the permission to read the cost
# settings, a rate is set under the one to change them.
ASKED: dict[str, tuple[str, ...]] = {
    "getHourlyRateGrid": (READ,),
    "listHourlyRates": (READ,),
    "setHourlyRate": (CHANGE,),
}
# The permission a list asks for besides when it asks for deactivated objects (decision of the
# author of 2026-11-06, #2084): the permission to change, not to read, as the contract refuses.
INACTIVE: dict[str, str] = {"getHourlyRateGrid": CHANGE}
