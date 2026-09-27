# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The harness of the numeric examples of the document (WF-QUA-0020).

Every test under ``tests/examples`` replays a numeric example of a Vérif field, with the
same inputs and the same expected value, taken from the fixture that cites the example's
key (``fixtures/``, listed by ``make fixtures``). Sockets are closed for the whole
directory: a database, a service or a browser cannot be reached, so an example that
passes here needs none of them.
"""

import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import cast

import pytest
from pytest_socket import disable_socket, enable_socket

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"


@pytest.fixture(autouse=True)
def no_socket() -> Iterator[None]:
    """Close sockets around each test of this directory."""
    disable_socket(allow_unix_socket=False)
    yield
    enable_socket()


@pytest.fixture
def example() -> Callable[[str], dict[str, object]]:
    """Return a loader of the fixture that cites an example's key."""

    def load(key: str) -> dict[str, object]:
        for path in sorted(FIXTURES.rglob("*.json")):
            data = cast("dict[str, object]", json.loads(path.read_text(encoding="utf-8")))
            if key in cast("list[str]", data.get("examples", [])):
                return data
        message = f"no fixture cites {key}: write one under fixtures/"
        raise LookupError(message)

    return load
