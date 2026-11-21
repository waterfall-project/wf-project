# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests that read the loaded witness share: its project, its instant, its reads.

PRJ-001, the instant at which the examples of the contract read it, an example read by its name,
and a route read as a reader of every project. The slices of the witness (``test_witness_*``) and
the readings of EP-10 that compare the witness with the examples read them here: the module holds
the helpers that tests outside the family of the witness read too (#3619).
"""

import json
import shutil
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from projects_support import READING, person
from support import WITNESS

if TYPE_CHECKING:
    from pathlib import Path

    from realm import TestRealm
    from support import ContractClient

    from waterfall.platform.database import Database

PRJ_001 = UUID("01926f3a-7c00-7000-8000-000000000001")
# The day of the reading of the examples: the 3 June 2026, 14:05.
READ_AT = datetime(2026, 6, 3, 14, 5, tzinfo=UTC)


def example(name: str) -> Any:
    """Read the value of an example of the contract."""
    return json.loads((WITNESS / f"{name}.json").read_text(encoding="utf-8"))["value"]


def read(api: ContractClient, witness: Database, realm: TestRealm, url: str) -> Any:
    """Read a route of the service as a reader of all the projects; refuse anything but 200."""
    answer = api.get(url, headers=person(witness, realm, *READING).headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def copied_description(tmp_path: Path) -> Path:
    """Copy the description of the witness and, beside it, the slice; give the description.

    The slice is read beside the examples (``witness.portfolio_slice.directory``): a copy of the
    examples alone is no witness. A test that changes a file edits the copy it is given.
    """
    directory = tmp_path / "api"
    shutil.copytree(WITNESS, directory)
    shutil.copytree(WITNESS.parent / "witness", tmp_path / "witness")
    return directory
