# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Fixtures shared by the tests of the repository tools.

The universe of the fake back takes some fifteen seconds to compute (``wftools.mockdata``). The
tests of how it is written and checked — files written, left over, outdated, missing — do not try
the computation, which other tests try: they share one, computed once a session.
"""

from typing import Any

import pytest

from wftools import mockdata


@pytest.fixture(scope="session")
def universe_computed() -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the volumes and the named examples of the universe, computed once a session."""
    return mockdata.volumes(), mockdata.named()


@pytest.fixture
def computed_once(
    universe_computed: tuple[dict[str, Any], dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Make the writing and the check of the universe use the one computation of the session.

    Never for a test that changes what the generator reads — a register, a description —, which
    must compute its own universe: it does not ask for this fixture.
    """
    volumes, named = universe_computed
    monkeypatch.setattr(mockdata, "volumes", lambda: volumes)
    monkeypatch.setattr(mockdata, "named", lambda: named)
