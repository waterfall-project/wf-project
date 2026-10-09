# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""One instance of the service: insert accounts at a given moment, and print their identifiers.

Run by ``test_users_data_access.py`` twice at once, as two processes with a connection each.
"""

import sys
import time

from waterfall.core.users.accounts import NewAccount, Stamp, add_account
from waterfall.platform.database import Database, create_database_engine, utc_now
from waterfall.platform.settings import load_settings


def main(start: float, name: str, count: int) -> None:
    """Wait for the common start, insert ``count`` accounts one transaction each."""
    database = Database(create_database_engine(load_settings().database_url.get_secret_value()))
    time.sleep(max(0.0, start - time.time()))
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
    main(float(sys.argv[1]), sys.argv[2], int(sys.argv[3]))
