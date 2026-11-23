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
# The risk whose occurrence the witness replays into the 102.
DELAY = UUID("01926f3a-7c00-7000-8000-000000000752")


def example(name: str) -> Any:
    """Read the value of an example of the contract."""
    return json.loads((WITNESS / f"{name}.json").read_text(encoding="utf-8"))["value"]


def occurred_nodes() -> dict[str, str]:
    """Give the nodes the description gives the occurrence of 752 in the 102: lineage by node.

    The declared deviation of US-3070/L3, which US-3150/L1 (#4614) lifts. The description and the
    examples read these nodes as the graft of EP-08 wrote them: under the task that bore the
    provision of 752, at the identifiers and the lineages they impose. Since EP-30 the occurrence
    merges the own estimate, a copy of the main structure (US-3100): it adds them at the first
    level, as the own estimate holds them, under its lineages and at identifiers drawn. The tests
    that read the main structure of the 102 set them apart on both sides (``occurred_apart``); the
    loader of US-3150/L1 replays the merge under the identifiers and the lineages of the witness.
    """
    risks = example("witness_risks")["risks"]
    return {
        each["node_id"]: each["copy_lineage_id"]
        for risk in risks
        if risk["risk_id"] == str(DELAY)
        for each in risk["grafted"]
    }


def occurred_apart() -> frozenset[str]:
    """Give the identifiers and the lineages of the nodes of ``occurred_nodes``, as text."""
    nodes = occurred_nodes()
    return frozenset({*nodes, *nodes.values()})


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
