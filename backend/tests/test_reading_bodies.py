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

US-1680 computes the physical progress of the summaries, not computable before in every body: the
SHA-256 of the bodies that give a summary's are taken again after it, the body of the fields of the
estimate grid, which does not ask it, keeping its own. Read before and after, field by field, the
bodies differ only by ``task.physical_progress`` of the summaries that bear a budgeted amount — 39
of the 40 of the current revision, the 39 of the marked one —, from "not computable" to a value, a
leaf's null in both (EP-10, "L'avancement physique").
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
# 7a43a670c of epic/EP-26), then again after US-1680, their summaries' physical progress computed.
TASKS = {
    "kinds=task, filtered by a task": "?kinds=task&search=revue&progress=not_started,started",
    "kinds=task, by level, sorted by a line": (
        "?kinds=task&max_level=2&sort_by=base_amount&sort_order=desc"
    ),
}
TASKS_DIGESTS = {
    "kinds=task, filtered by a task": (
        "bc8abb4fc4e0499b47b81bd619adf3cc99fcdc3aa9791c3900fb8a0216127557"
    ),
    "kinds=task, by level, sorted by a line": (
        "c13f2162c31378310b50bd07366cc88b9f4d33c94b645a512c74b322f128ff8a"
    ),
    "kinds=task of a marked revision": (
        "a5a54050ee30477cac09b5d00462809b2c5c5bd09ed185d57a834816f83eab26"
    ),
}
COMPARISONS = {
    "whole comparison": "",
    "comparison filtered and sorted": (
        "&difference=modified&reestimated_amount_min=1000&sort_by=base_amount&sort_order=desc"
    ),
}

# The SHA-256 of each body, taken before US-2220/L1 (commit 587127f0c of epic/EP-26), then again
# after US-1680 but the fields of the estimate grid, which ask no physical progress.
DIGESTS = {
    "whole": "c354cb22a3180302a4d6810dd3b1cdeb07d024f987bb9a21eb120db0fd5ff502",
    "kinds=task": "42c5452c592bfea4e4988ef98fe4ba4a6c6d1d5deb4e56d0185c5225ff26a6cd",
    "fields": "0f8680e6fe285210e034e71ffcef1736a4f19c9e8c788022bf5373dea06ced19",
    "filtered by a task": "b472c386ce4c8cd48318c501bfb65e396bf3e20b2101e561915f860cc2cc23f5",
    "filtered by a line, sorted": (
        "425a759da25aad539bc4488bb6c11fadb00efc4da1176f7e98f4ad0d5819e098"
    ),
    "whole comparison": "d635d9e709ea15dbebe14249aedf2bd48c8d97b1412fac3e251f255f31fc1247",
    "comparison filtered and sorted": (
        "908485770a32aeba12ade836c31fd12d034ff77e4446d27b7297a3e8f40b0c03"
    ),
}


# The SHA-256 of ``listNodes`` of the marked revision REVISION_100, whole: its labels are read
# through the revisions of the tasks bearing the lines. Taken at 587127f0c, as the others, and
# again after US-1680.
MARKED_DIGEST = "29cbdfd16bd179c92aed66a6684a5bb5d7086c7a6fe4e679bd0669980dea3f75"


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
