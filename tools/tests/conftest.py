# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Fixtures shared by the tests of the repository tools.

The universe of the fake back takes some fifteen seconds to compute (``wftools.mockdata``). The
tests of how it is written and checked — files written, left over, outdated, missing — do not try
the computation, which other tests try: they share one, computed once a session.
"""

import json
import os
from typing import TYPE_CHECKING, Any

import pytest

from wftools import heavyturns, mockdata

if TYPE_CHECKING:
    from pathlib import Path

# A test that skips without declaring it by the mark ``unexecuted`` fails (US-2440); Pytester runs
# the plugin on tests written for its own tests.
pytest_plugins = ("pytester", "wftools.unexecuted")


@pytest.fixture(autouse=True)
def no_process_table(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Point ``WATERFALL_SLOTS_PROC`` at an empty directory: no test can stop a server of the poste.

    A test that needs a real table (an ephemeral port it listens on) passes ``/proc`` explicitly.
    """
    empty = tmp_path_factory.mktemp("process-table")
    monkeypatch.setenv("WATERFALL_SLOTS_PROC", str(empty))


@pytest.fixture(autouse=True)
def no_workstation_locks(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Point ``WATERFALL_RUNTIME_DIR`` at a temporary directory, inherited by the subprocesses.

    No test, in process or not, can then take a lock or a slot of the workstation (US-2460). A test
    that sets its own directory overrides it; ``user_runtime`` removes it to test the default.
    """
    monkeypatch.setenv(heavyturns.RUNTIME_VARIABLE, str(tmp_path_factory.mktemp("runtime")))


@pytest.fixture
def user_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Move ``/run/user`` under the test, and return the directory of the user in it, created.

    A session without ``WATERFALL_RUNTIME_DIR`` then locks there, never in the directory of the
    workstation (US-2460).
    """
    root = tmp_path / "run-user"
    own = root / str(os.getuid())
    own.mkdir(parents=True)
    monkeypatch.setattr(heavyturns, "USER_RUNTIME_ROOT", root)
    monkeypatch.delenv(heavyturns.RUNTIME_VARIABLE, raising=False)
    return own


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


@pytest.fixture(scope="module")
def readings() -> dict[str, Any]:
    """Read the named examples back from the text the generator writes."""
    return {
        name: json.loads(mockdata.render(example))["value"]
        for name, example in mockdata.readings().items()
    }
