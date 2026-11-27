# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The time zone of the installation has its default again: 0058 (US-2850/L5, #5090)."""

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import text

from waterfall.migrations.runner import downgrade, upgrade

if TYPE_CHECKING:
    from sqlalchemy import Engine


@pytest.mark.requirement("WF-DAT-0140-A")
def test_an_installation_inserted_without_its_time_zone_takes_universal_time(
    empty_engine: Engine,
) -> None:
    # #5090: the code of the version before inserts the row without the column (WF-DAT-0140-A);
    # the column stays required.
    upgrade(empty_engine)
    with empty_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO installation (id, default_language, avatar_max_bytes,"
                " external_backup_max_bytes, installed_at) VALUES (1, 'fr', 1000, 1000, now())"
            )
        )
        assert connection.scalar(text("SELECT time_zone FROM installation")) == "UTC"
        nullable = connection.scalar(
            text(
                "SELECT is_nullable FROM information_schema.columns"
                " WHERE table_name = 'installation' AND column_name = 'time_zone'"
            )
        )
    assert nullable == "NO"


@pytest.mark.story("US-2850")
def test_the_descent_removes_the_default_of_the_time_zone(empty_engine: Engine) -> None:
    upgrade(empty_engine)
    downgrade(empty_engine, "0057")
    with empty_engine.connect() as connection:
        default = connection.scalar(
            text(
                "SELECT column_default FROM information_schema.columns"
                " WHERE table_name = 'installation' AND column_name = 'time_zone'"
            )
        )
    assert default is None
