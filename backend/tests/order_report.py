# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A plugin that reports the order in which a process of pytest-xdist collected, and runs nothing.

``--collect-only`` skips pytest-xdist: its processes alone know the count they were handed. The
first writes its order to the file ``WATERFALL_ORDER_FILE`` names and gives the controller an empty
list, so that nothing runs (tests/test_sharding.py).
"""

import os
from pathlib import Path

import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_collection_finish(session: pytest.Session) -> None:
    config = session.config
    given = getattr(config, "workerinput", None)
    if given is None:
        return
    target = os.environ.get("WATERFALL_ORDER_FILE")
    if target and given["workerid"] == "gw0":
        Path(target).write_text("\n".join(item.nodeid for item in session.items), encoding="utf-8")
    session.items[:] = []
