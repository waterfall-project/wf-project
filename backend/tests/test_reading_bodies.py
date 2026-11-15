# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The bodies of the readings of PRJ-001, to the byte, before and after the read path (US-2220).

The read path of a structure — ``list_nodes`` and ``read_structure`` — changes how it reads, not
what it answers: the SHA-256 of each body below was taken on the loaded witness before US-2220/L1
touched the code, and a byte apart fails the test (EP-26, "La lecture d'une structure"). The
readings are those of the issue: ``listNodes`` of the current revision whole, with ``kinds=task``,
with the fields the grid of the estimate asks, filtered and sorted — by a task, by a line —, and
``compareRevisions`` of the two marked revisions, whole, then filtered and sorted. US-2280 reads the
tasks alone without their lines: ``kinds=task`` filtered by a task, and of a marked revision, are
added, their SHA-256 taken before US-2280/L1 touched the code (``TASKS_DIGESTS``).
The bodies are read straight from the application, unchecked against the contract: their form is
the other tests' (``test_witness_lines_reads``), their bytes this one's.
"""

import hashlib
from typing import TYPE_CHECKING

import pytest
from projects_support import PROJECTS, READING, person
from test_witness_projects import PRJ_001, REVISION_100, REVISION_101, REVISION_102
from test_witness_tasks import structure_of

if TYPE_CHECKING:
    from realm import TestRealm
    from support import ContractClient

    from waterfall.platform.database import Database

# What the grid of the estimate asks of a node (``ESTIMATE_FIELDS``, frontend).
ESTIMATE_FIELDS = ",".join(
    (
        "origin_risk_id",
        "task.progress",
        "task.base_amount",
        "task.reestimated_amount",
        *(
            f"estimate_line.{name}"
            for name in (
                "cost_category_id",
                "cost_category_label",
                "resource_role_label",
                "quantity",
                "hours",
                "unit_disbursement",
                "subproject_id",
                "subproject_label",
                "payment_delay_days",
                "uses_inactive_object",
                "base_amount",
                "reestimated_amount",
            )
        ),
    )
)

NODES = {
    "whole": "",
    "kinds=task": "?kinds=task",
    "fields": f"?fields={ESTIMATE_FIELDS}",
    "filtered by a task": "?search=revue&progress=not_started,started",
    "filtered by a line, sorted": (
        "?reestimated_amount_min=1000&reestimated_amount_max=10000"
        "&sort_by=base_amount&sort_order=desc"
    ),
}
# The readings of the tasks alone added by US-2280/L1, and their SHA-256 taken before it (commit
# 7a43a670c of epic/EP-26).
TASKS = {
    "kinds=task, filtered by a task": "?kinds=task&search=revue&progress=not_started,started",
    "kinds=task, by level, sorted by a line": (
        "?kinds=task&max_level=2&sort_by=base_amount&sort_order=desc"
    ),
}
TASKS_DIGESTS = {
    "kinds=task, filtered by a task": (
        "27426087badf17a3dc8e8577f886f1f718d23bf64ba989ee7405c9fdb317baf8"
    ),
    "kinds=task, by level, sorted by a line": (
        "056334a6ccf96fd37b9085d82066a283de0e581ee00a71fd65e8c1caf363a594"
    ),
    "kinds=task of a marked revision": (
        "d4bc9de494d853535c226b866f15973338ea67ed3b364656f3f4c4ea6604c601"
    ),
}
COMPARISONS = {
    "whole comparison": "",
    "comparison filtered and sorted": (
        "&difference=modified&reestimated_amount_min=1000&sort_by=base_amount&sort_order=desc"
    ),
}

# The SHA-256 of each body, taken before US-2220/L1 (commit 587127f0c of epic/EP-26).
DIGESTS = {
    "whole": "c0d1f910a1b38dbb10ba0225be04e80e41a9825eea270d06a930e51f3d94b4e5",
    "kinds=task": "5c2fdea32bcb6f7d5d79430581afc9f1f370551c6937f8ffa81ca8c81ffe58da",
    "fields": "0f8680e6fe285210e034e71ffcef1736a4f19c9e8c788022bf5373dea06ced19",
    "filtered by a task": "0c1b40347c5356ed44382a02106fd5e0b56f6c9adcc657a4e2b8fad6c1802ba5",
    "filtered by a line, sorted": (
        "8ce9e40c194093e648537f8b4ce30239281bacc6d94f8915b419cdaf6ded1028"
    ),
    "whole comparison": "d5ba4c6bc35b8bdc412d1a2b0c8a9f6ef981aaaba505d2151331853bc126d34f",
    "comparison filtered and sorted": (
        "92f786349644c9d42758e484d27e56dac904d24f527703fbf3cc8f5a45e6c7a5"
    ),
}


# The SHA-256 of ``listNodes`` of the marked revision REVISION_100, whole: its labels are read
# through the revisions of the tasks bearing the lines. Taken at 587127f0c, as the others.
MARKED_DIGEST = "eaadbe84e77482ac75b037e5a3269ab44183badd3154112f6d9818a503967dae"


def digest(api: ContractClient, witness: Database, realm: TestRealm, url: str) -> str:
    """Read a route as a reader of the project, unchecked; give the SHA-256 of its body."""
    answer = api.client.get(url, headers=person(witness, realm, *READING).headers)
    assert answer.status_code == 200, answer.text
    return hashlib.sha256(answer.content).hexdigest()


@pytest.mark.parametrize("name", list(NODES))
def test_the_nodes_of_the_current_revision_read_to_the_byte_what_they_read_before_the_lot(
    api: ContractClient, witness: Database, realm: TestRealm, name: str
) -> None:
    with witness.transaction() as session:
        structure = structure_of(session, REVISION_102)
    url = f"{PROJECTS}/{PRJ_001}/revisions/{REVISION_102}/structures/{structure}/nodes{NODES[name]}"
    assert digest(api, witness, realm, url) == DIGESTS[name]


@pytest.mark.parametrize("name", list(TASKS))
def test_the_tasks_of_the_current_revision_read_alone_to_the_byte_what_they_read_before_us_2280(
    api: ContractClient, witness: Database, realm: TestRealm, name: str
) -> None:
    with witness.transaction() as session:
        structure = structure_of(session, REVISION_102)
    url = f"{PROJECTS}/{PRJ_001}/revisions/{REVISION_102}/structures/{structure}/nodes{TASKS[name]}"
    assert digest(api, witness, realm, url) == TASKS_DIGESTS[name]


def test_the_tasks_of_a_marked_revision_read_alone_to_the_byte_what_they_read_before_us_2280(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    with witness.transaction() as session:
        structure = structure_of(session, REVISION_100)
    url = f"{PROJECTS}/{PRJ_001}/revisions/{REVISION_100}/structures/{structure}/nodes?kinds=task"
    assert digest(api, witness, realm, url) == TASKS_DIGESTS["kinds=task of a marked revision"]


@pytest.mark.parametrize("name", list(COMPARISONS))
def test_the_comparison_of_two_revisions_reads_to_the_byte_what_it_read_before_the_lot(
    api: ContractClient, witness: Database, realm: TestRealm, name: str
) -> None:
    url = (
        f"{PROJECTS}/{PRJ_001}/revisions/comparison"
        f"?from_revision_id={REVISION_100}&to_revision_id={REVISION_101}{COMPARISONS[name]}"
    )
    assert digest(api, witness, realm, url) == DIGESTS[name]


def test_the_nodes_of_a_marked_revision_read_to_the_byte_what_they_read_before_the_lot(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    with witness.transaction() as session:
        structure = structure_of(session, REVISION_100)
    url = f"{PROJECTS}/{PRJ_001}/revisions/{REVISION_100}/structures/{structure}/nodes"
    assert digest(api, witness, realm, url) == MARKED_DIGEST
