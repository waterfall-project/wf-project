# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tables of the core, all declared: what a process that writes rows imports once.

A key of one table may name the table of another module by its name — the author of a row, an
account; the node an account is attached to (WF-DAT-0090); a revision, its project, and the project
its revisions in return —, which SQLAlchemy finds among the
tables declared when it writes a row. A module does not import the tables of another (WF-ARC-0010):
the entry points do — the API, the worker, the migrations, the bootstrap and the loader of the
witness, where the metadata must be whole — by importing this module, which nothing else does.
It exposes nothing.
"""

from typing import TYPE_CHECKING

from waterfall.core.access_roles import tables as access_roles_tables
from waterfall.core.backups import tables as backups_tables
from waterfall.core.cost_settings import tables as cost_settings_tables
from waterfall.core.exchanges import tables as exchanges_tables
from waterfall.core.history import tables as history_tables
from waterfall.core.planning import tables as planning_tables
from waterfall.core.projects import tables as projects_tables
from waterfall.core.resource_settings import tables as resource_settings_tables
from waterfall.core.revisions import tables as revisions_tables
from waterfall.core.users import tables as users_tables
from waterfall.platform.database import Base

if TYPE_CHECKING:
    from sqlalchemy import MetaData

__all__ = [
    "access_roles_tables",
    "backups_tables",
    "cost_settings_tables",
    "declared",
    "exchanges_tables",
    "history_tables",
    "planning_tables",
    "projects_tables",
    "resource_settings_tables",
    "revisions_tables",
    "users_tables",
]


def declared() -> MetaData:
    """Give the metadata of the tables, every table of the core declared in it.

    An entry point calls it before it writes, or reads the schema: that is what keeps the import
    of this module from being a bare side effect.
    """
    return Base.metadata
