# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The harness of the numeric examples runs without a database or a browser (WF-QUA-0020)."""

import socket
from collections.abc import Callable

import pytest
from pytest_socket import SocketBlockedError

pytestmark = pytest.mark.requirement("WF-QUA-0020-A")


def test_an_example_cannot_reach_a_database_or_a_browser() -> None:
    with (
        pytest.raises(SocketBlockedError),
        pytest.warns(UserWarning, match="A test tried to use socket"),
    ):
        socket.create_connection(("127.0.0.1", 5432), timeout=1)


def test_an_example_without_a_fixture_is_named(
    example: Callable[[str], dict[str, object]],
) -> None:
    with pytest.raises(LookupError, match="no fixture cites WF-PTF-0020-A#000000000000"):
        example("WF-PTF-0020-A#000000000000")
