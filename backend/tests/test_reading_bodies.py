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

US-2650/L1 changes the witness itself — the 101 the merge of the amendment 1 produces, the
reference, the risks and their provision lines, the occurrence of 752 —: the SHA-256 of every body
are taken again on it, the code of the readings untouched.

US-1680 computes the physical progress of the summaries, not computable before in every body: the
SHA-256 of the bodies that give a summary's are taken again after it, the body of the fields of the
estimate grid, which does not ask it, keeping its own. Read before and after, field by field, the
bodies differ only by ``task.physical_progress`` of the summaries that bear a budgeted amount — 39
of the 40 of the current revision, the 39 of the marked one —, from "not computable" to a value, a
leaf's null in both (EP-10, "L'avancement physique").

The witness now also carries the slice of the portfolio (EP-11, US-2770/L2), loaded after PRJ-001
under derived identifiers: the bodies of PRJ-001 read here do not depend on it, but for the
comparisons, whose identifiers it shifts (``COMPARED_DIGESTS``).

US-3060/L6 reads a provision line as computed, its budgeted amount the provision the reference
fixed (#4274): the SHA-256 of the bodies that hold one, or a sum of budgeted amounts, are taken
again after it. Read before and after, field by field, they differ only by the three provision
lines — ``is_computed``, ``computed_fields``, ``editable_fields``, ``remaining_entry``,
``payment_delay_days`` null, the budgeted amount of 250 000, 60 and 600 000 —, by the budgeted
amount of the tasks above them, and by the budgeted totals, deltas and bases that sum them; the
bodies filtered by a task, which hold none, keep theirs.
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
# 7a43a670c of epic/EP-26), then again after US-1680, their summaries' physical progress computed,
# and after US-3060/L6 for the one that holds the task of a provision line (#4274).
TASKS = {
    "kinds=task, filtered by a task": "?kinds=task&search=revue&progress=not_started,started",
    "kinds=task, by level, sorted by a line": (
        "?kinds=task&max_level=2&sort_by=base_amount&sort_order=desc"
    ),
}
TASKS_DIGESTS = {
    "kinds=task, filtered by a task": (
        "c9442c6ca05a9e9c98b7244d3029c4b4a4042de7478d7726c397fdd668e95b53"
    ),
    "kinds=task, by level, sorted by a line": (
        "90fc0d8dbdc66ddc3c5167f5a3a6bdd63203195cbb60e0b751be8f1c167020fb"
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
# after US-1680 but the fields of the estimate grid, which ask no physical progress, and after
# US-3060/L6 but those filtered by a task (#4274).
DIGESTS = {
    "whole": "ab0364282ea8a6e8f37588f988b13a231e59970e18783e98c6a47353c53d2e19",
    "kinds=task": "d9dcefc43e9076da91accb04a790b34814447107cc12c739819bb5c96faf4c8e",
    "fields": "63eedbe65f6a5d6ae0a7e0d130844d9fc791500e399b2bcbd8edc002a0ddd017",
    "filtered by a task": "70811c278a893bf6ef55cb727d85fff3e767d00b49d91053099aa282eca74a99",
    "filtered by a line, sorted": (
        "8d1e236bb53024c1e416646256f07201aa05cab4d23acc1cbc3315a598293d9f"
    ),
    "whole comparison": "3699796e0c85c057ed56cf42bd580c2460b7e9cbd57522960ee19e6bac67a46a",
    "comparison filtered and sorted": (
        "908485770a32aeba12ade836c31fd12d034ff77e4446d27b7297a3e8f40b0c03"
    ),
}


# The SHA-256 of the comparison filtered by its marks, taken at US-2320/L3, which judges a node on
# every value it carries: ``difference=modified`` retains more nodes than before. Taken again when
# epic/EP-10 took back main, after US-1680: its 39 summaries put back "not computable", the body
# read then gives the SHA-256 of US-2320/L3, bd5415c9…; nothing else differs, no mark included.
# Taken again after US-3060/L6, the budgeted amounts of its provisions written (#4274). Taken again
# when epic/EP-11 and epic/EP-08 met: each marking keeps four documents of the portfolio (EP-11),
# drawn from the loader's count of identifiers, so that every node the witness creates after the
# first marking has its identifier 4 greater — and nothing else of the body changes (checked field
# by field against epic/EP-08: 12 997 identifiers, all shifted by 4).
COMPARED_DIGESTS = {
    "comparison filtered and sorted": (
        "709e123f35d91b44a3c2faf867d479fc6d825de902a2284339f9355fe29ead34"
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
