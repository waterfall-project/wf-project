# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the settings and of the minimal reference share (US-0810/L2).

An installation as its bootstrap leaves it, without Keycloak: its row, and the reference the
bootstrap writes by ``install_reference``, as the owner of the tables (#701). Sessions that hold
any permissions asked for, each the header of a token of an account of its own.
"""

from typing import TYPE_CHECKING
from uuid import uuid4

from access_rows import role
from realm import KEY
from sqlalchemy import insert
from support import bearer, raw_account

from waterfall.bootstrap import Chosen, install_reference
from waterfall.core.access_roles.tables import UserAccessRole
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act
from waterfall.platform.database import Database, utc_now
from waterfall.platform.installation import THE_ROW, Installation

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine

# The currency and the name of the company of the example ``reference_settings`` of the contract.
CHOSEN = Chosen("EUR", "Delmas Automatismes", "fr")


def install(owner: Engine, choice: Chosen = CHOSEN) -> None:
    """Write the row of the installation and its reference, as the bootstrap does, as the owner."""
    database = Database(owner)
    with database.transaction() as session:
        session.execute(
            insert(Installation).values(
                id=THE_ROW,
                default_language=choice.language,
                avatar_max_bytes=2 * 1024**2,
                external_backup_max_bytes=20 * 1024**3,
                installed_at=utc_now(),
            )
        )
        assert install_reference(session, choice, Act(None, utc_now()))


def holding(database: Database, realm: TestRealm, *permissions: str) -> dict[str, str]:
    """Give the header of a session of a new account whose one role holds ``permissions``."""
    account = raw_account(email=f"{uuid4().hex}@example.org")
    held = role(database, f"Rôle {uuid4().hex}", permissions=permissions)
    with database.transaction() as session:
        session.execute(insert(UserAccount).values(**account))
        session.execute(
            insert(UserAccessRole).values(user_account_id=account["id"], access_role_id=held)
        )
    return bearer(realm.token(str(account["idp_subject"]), KEY))
