# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""One instance of the service: insert accounts on a signal, and print their identifiers.

Run by ``test_users_data_access.py`` twice at once, as two processes with a connection each: each
one opens its connection, writes ``ready``, and waits for a line on its input before inserting.
"""

import sys

from sqlalchemy import text

from waterfall.core.users.accounts import NewAccount, Stamp, add_account
from waterfall.platform.database import Database, create_database_engine, utc_now
from waterfall.platform.settings import load_settings


def main(name: str, count: int) -> None:
    """Signal readiness, wait for the start, insert ``count`` accounts, one transaction each."""
    database = Database(create_database_engine(load_settings().database_url.get_secret_value()))
    with database.engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    sys.stdout.write("ready\n")
    sys.stdout.flush()
    sys.stdin.readline()
    for number in range(count):
        with database.transaction() as session:
            account = add_account(
                session,
                NewAccount(
                    "Martin", "Claire", f"{name}{number}@example.org", f"{name}-{number}", "local"
                ),
                Stamp(None, utc_now()),
            )
            sys.stdout.write(f"{account.id}\n")
    database.dispose()


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
