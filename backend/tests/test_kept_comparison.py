# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The comparison of two marked revisions from the readings kept of their structures (US-2270).

The criterion of US-2270 this lot closes, its own — the story has no requirement of its own, its
gain being read in the report of WF-QUA-0060 (US-2300) —: ``compareRevisions`` of two marked
revisions reads the two readings kept, made at its first reading if they are not, the body the same
to the byte as from the rows, whatever ``difference`` and ``fields`` it asks; a filtered one reads
the rows. On the witness's marked revisions 100 and 101; the cases of the union — a removed node
in its place, a predecessor renamed, a moved task — are those of ``test_comparison``, which a
comparison no filter restricts now reads from what is kept. Since US-2320/L3, the revision read may
be the current one, whose columns are read (``test_comparison_current``), and a current base is
refused before anything is read: the Vérif of WF-REV-0080-A, « Une révision en cours prise pour
base est refusée. », on the witness.
"""

import hashlib
import json
import zlib
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from projects_support import PROJECTS, READING, person
from sqlalchemy import update
from test_kept_readings import FORGED, kept_row, place_of, read
from test_reading_bodies import COMPARED_DIGESTS, ESTIMATE_FIELDS, gains_digest
from test_witness_projects import PRJ_001, REVISION_100, REVISION_101, REVISION_102

from waterfall.api.comparison import comparison_body, kept_comparison
from waterfall.api.nodes import node_body, read_body
from waterfall.core.estimate.interface import ComparisonAsked, compare_revisions
from waterfall.core.planning.interface import NodeFilters
from waterfall.core.planning.tables import StructureReading
from waterfall.platform.errors import STATE_FORBIDS_OPERATION, ConflictError

if TYPE_CHECKING:
    from realm import TestRealm
    from support import ContractClient

    from waterfall.platform.database import Database

COMPARISON = (
    f"{PROJECTS}/{PRJ_001}/revisions/comparison"
    f"?from_revision_id={REVISION_100}&to_revision_id={REVISION_101}"
)
# The comparisons no filter restricts: whole, by their marks, projected by ``fields``.
UNFILTERED = {
    "whole": ("", None, None),
    "modified": ("&difference=modified", ("modified",), None),
    "added and removed": ("&difference=added,removed", ("added", "removed"), None),
    "the grid of the estimate": (f"&fields={ESTIMATE_FIELDS}", None, ESTIMATE_FIELDS),
    "removed, projected": (
        "&difference=removed&fields=task.label,estimate_line.label,predecessors,parent_id",
        ("removed",),
        "task.label,estimate_line.label,predecessors,parent_id",
    ),
}


def from_rows(witness: Database, differences: tuple[str, ...] | None, fields: str | None) -> bytes:
    """Give the body of the comparison of the revisions 100 and 101 read from their rows."""
    asked = ComparisonAsked(REVISION_100, REVISION_101, NodeFilters(), differences)
    with witness.transaction() as session:
        found = compare_revisions(session, PRJ_001, asked, node_body)
        chosen = None if fields is None else frozenset(fields.split(","))
        return bytes(read_body(comparison_body(found, chosen)).body)


@pytest.mark.parametrize("name", list(UNFILTERED))
def test_a_comparison_no_filter_restricts_reads_the_readings_kept_the_same_body_as_the_rows(
    api: ContractClient, witness: Database, realm: TestRealm, name: str
) -> None:
    # The first comparison makes and keeps the readings of the two structures, the next reads
    # them: the same body as from the rows, to the byte, made or read.
    query, differences, fields = UNFILTERED[name]
    headers = person(witness, realm, *READING).headers
    places = [place_of(witness, revision) for revision in (REVISION_100, REVISION_101)]
    expected = hashlib.sha256(from_rows(witness, differences, fields)).hexdigest()
    assert [kept_row(witness, place) for place in places] == [None, None]
    made = read(api, headers, COMPARISON + query)
    assert all(kept_row(witness, place) is not None for place in places)
    again = read(api, headers, COMPARISON + query)
    assert hashlib.sha256(made).hexdigest() == hashlib.sha256(again).hexdigest() == expected


def test_a_comparison_reads_what_is_kept_and_a_filtered_one_reads_the_rows(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The reading kept of the compared structure replaced by a body no reading gives: the
    # comparison no filter restricts gives its totals, which no row gives; a filtered one reads
    # the rows, its body as before the lot.
    headers = person(witness, realm, *READING).headers
    read(api, headers, COMPARISON)
    compared = place_of(witness, REVISION_101)
    with witness.transaction() as session:
        session.execute(
            update(StructureReading)
            .where(
                StructureReading.project_id == compared.project_id,
                StructureReading.structure_id == compared.structure_id,
            )
            .values(document=zlib.compress(FORGED))
        )
    assert api.client.get(COMPARISON, headers=headers).json()["totals"] == {}
    filtered = (
        "&difference=modified&reestimated_amount_min=1000&sort_by=base_amount&sort_order=desc"
    )
    body = read(api, headers, COMPARISON + filtered)
    assert gains_digest(body) == COMPARED_DIGESTS["comparison filtered and sorted"]


@pytest.mark.requirement("WF-IHM-0160-A")
def test_the_totals_difference_of_a_kept_comparison_is_its_totals_less_those_of_its_base(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The pair of the witness differs: ``totals`` is the document kept of the revision read,
    # ``totals_delta`` and ``base_totals`` the union's, the base counted from the same kept
    # document of its own. Whatever the way, the difference is the totals less the base's, the
    # counts and the hours and amounts, field by field. A document kept is of the format of this
    # code, else it is ignored and made again (``kept_reading``): a line of it always bears its
    # hours and its base amount, required of a node.
    headers = person(witness, realm, *READING).headers
    for _ in range(2):  # made, then read
        found = json.loads(read(api, headers, COMPARISON))
        totals, base, delta = (found[name] for name in ("totals", "base_totals", "totals_delta"))
        assert set(delta) == set(base) == set(totals) != set()
        for name, value in totals.items():
            assert Decimal(str(value)) - Decimal(str(base[name])) == Decimal(str(delta[name]))
        assert any(Decimal(str(each)) != 0 for each in delta.values())


@pytest.mark.requirement("WF-REV-0080-A")
def test_a_comparison_of_revisions_judged_first_refuses_a_base_not_marked(
    witness: Database,
) -> None:
    # The revisions judged before any reading kept is read or made: the current one refused for
    # base (409), as from the rows (US-2320).
    asked = ComparisonAsked(REVISION_102, REVISION_100, NodeFilters())
    with witness.transaction() as session, pytest.raises(ConflictError) as refused:
        kept_comparison(session, PRJ_001, asked, None)
    assert refused.value.code == STATE_FORBIDS_OPERATION
    assert kept_row(witness, place_of(witness, REVISION_100)) is None
