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
added, their SHA-256 taken before US-2280/L1 touched the code (``TASKS_DIGESTS``). US-2320/L3 makes
the comparison judge a node on every value it carries and give its base: between two marked
revisions, the whole one is the body before, but for what it gains (``as_before``); the filtered
one, which ``difference`` filters by the marks, is taken again (``COMPARED_DIGESTS``). US-2340/L1
adds the deltas of each node and the totals of the base: both comparisons are those bodies but for
what it adds (``without_gains``).
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
import json
from typing import TYPE_CHECKING, Any

import pytest
from projects_support import PROJECTS, READING, person
from test_witness_projects import PRJ_001, REVISION_100, REVISION_101, REVISION_102
from test_witness_tasks import structure_of

from waterfall.api.nodes import read_body

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


# The SHA-256 of the comparison filtered by its marks, taken at US-2320/L3, which judges a node on
# every value it carries: ``difference=modified`` retains more nodes than before. Taken again when
# epic/EP-10 took back main, after US-1680: its 39 summaries put back "not computable", the body
# read then gives the SHA-256 of US-2320/L3, bd5415c9…; nothing else differs, no mark included.
COMPARED_DIGESTS = {
    "comparison filtered and sorted": (
        "a72f125f4f4a89b25f85b2968c0a34ab0ba8888f9f334e9fecf4a8b555ddcff4"
    ),
}


def without_gains(body: dict[str, Any]) -> dict[str, Any]:
    """Give a comparison as it was before US-2340/L1: without its deltas and the base's totals.

    Each node keeps its place, its mark and its base: the lot only adds to the body.
    """
    assert {"base_totals", "totals_delta"} <= set(body)
    del body["base_totals"], body["totals_delta"]
    for each in body["items"]:
        del each["deltas"]
    return body


def gains_digest(body: bytes) -> str:
    """Give the SHA-256 of a comparison written without what US-2340/L1 adds to it."""
    stripped = without_gains(json.loads(body))
    return hashlib.sha256(bytes(read_body(stripped).body)).hexdigest()


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


def as_before(body: dict[str, Any]) -> dict[str, Any]:
    """Give a comparison as it was before US-2320/L3: without its base, ``other`` and its marks.

    A node was modified by the values WF-REV-0080 names, or by its content: a node under it added,
    removed or modified, or moved from under it — the parent the base names (``base.parent_id``).
    """
    items: list[dict[str, Any]] = without_gains(body)["items"]
    parents = {each["node_id"]: each["parent_id"] for each in items}
    formers: list[str | None] = []
    for each in items:
        base = each.pop("base")
        each["changes"] = [change for change in each["changes"] if change != "other"]
        if "parent" in each["changes"]:
            formers.append(base["parent_id"])
    held: set[str] = set()
    pending = [
        parents[each["node_id"]]
        for each in items
        if each["difference"] in {"added", "removed"} or each["changes"]
    ]
    pending += formers
    while pending:
        node = pending.pop()
        if node is not None and node not in held:
            held.add(node)
            pending.append(parents[node])
    for each in items:
        if each["difference"] == "modified" and not each["changes"] and each["node_id"] not in held:
            each["difference"] = "unchanged"
    return body


def comparing(name: str) -> str:
    """Give the path of the comparison of the marked revisions 100 and 101, as ``name`` reads it."""
    return (
        f"{PROJECTS}/{PRJ_001}/revisions/comparison"
        f"?from_revision_id={REVISION_100}&to_revision_id={REVISION_101}{COMPARISONS[name]}"
    )


@pytest.mark.requirement("WF-REV-0080-A")
def test_the_comparison_of_two_marked_revisions_changes_only_by_what_it_gains(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # US-2320 : « entre deux révisions marquées, la réponse d'aujourd'hui ne change que par ce
    # qu'elle gagne » — its base, ``other``, and the nodes modified by a value WF-REV-0080 does not
    # name; the rest, to the byte, the body before the lot.
    headers = person(witness, realm, *READING).headers
    answer = api.client.get(comparing("whole comparison"), headers=headers)
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert any("other" in each["changes"] for each in body["items"])
    before = bytes(read_body(as_before(body)).body)
    assert hashlib.sha256(before).hexdigest() == DIGESTS["whole comparison"]


@pytest.mark.requirement("WF-REV-0080-A")
def test_the_comparison_filtered_by_its_marks_reads_to_the_byte_what_it_read_at_us_2320(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The digest guards the stability of the body; the rightness of the marks is for
    # test_comparison*.py.
    name = "comparison filtered and sorted"
    answer = api.client.get(comparing(name), headers=person(witness, realm, *READING).headers)
    assert answer.status_code == 200, answer.text
    assert gains_digest(answer.content) == COMPARED_DIGESTS[name]


def test_the_nodes_of_a_marked_revision_read_to_the_byte_what_they_read_before_the_lot(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    with witness.transaction() as session:
        structure = structure_of(session, REVISION_100)
    url = f"{PROJECTS}/{PRJ_001}/revisions/{REVISION_100}/structures/{structure}/nodes"
    assert digest(api, witness, realm, url) == MARKED_DIGEST
