# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The business core (PBS-2.3): one subpackage per module, modelled on a block of the FBS.

A module exposes what others may use in its ``interface`` module, and nothing else: its
tables and its data access are private to it. ``make check-back`` rejects an import from
one module into another that does not go through the interface.

A key of one table may name the table of another module by its name — the author of a row, an
account; the node an account is attached to (WF-DAT-0090) —, which SQLAlchemy finds among the
tables declared when it writes a row: every table of the core is therefore declared as soon as
the core is imported, whichever module a process reaches first. Nothing else reads them here.
"""

from waterfall.core.access_roles import tables as access_roles_tables
from waterfall.core.backups import tables as backups_tables
from waterfall.core.cost_settings import tables as cost_settings_tables
from waterfall.core.resource_settings import tables as resource_settings_tables
from waterfall.core.users import tables as users_tables

__all__ = [
    "access_roles_tables",
    "backups_tables",
    "cost_settings_tables",
    "resource_settings_tables",
    "users_tables",
]
