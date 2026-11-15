# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of a structure of a marked revision, kept in PostgreSQL and read (EP-26, US-2270).

The criteria of US-2270 this lot closes, its own — the story has no requirement of its own, its
gain being read in the report of WF-QUA-0060 (US-2300) —: the reading kept in PostgreSQL and read
by ``listNodes``, whole, projected by ``fields`` or not, the body the same to the byte as from the
rows; the moment it is kept, here its first whole reading, in the transaction of the reading, the
second write of the same ignored; what changes after the marking, established by marking — the
witness's revisions 100 and 101 are —, keeping the body, changing, reading again and comparing to
the byte; the format, a reading of another being ignored and made again.
"""

import hashlib
import json
import zlib
from typing import TYPE_CHECKING

import pytest
from projects_support import PROJECTS, READING, person
from sqlalchemy import select, text, update
from test_reading_bodies import ESTIMATE_FIELDS, MARKED_DIGEST, TASKS_DIGESTS
from test_witness_projects import PRJ_001, REVISION_100, REVISION_101, REVISION_102
from test_witness_tasks import structure_of

from waterfall.api.contract.models import Node, NodeListMeta, NodeTotals
from waterfall.api.nodes import FORMAT, nodes_body, read_body
from waterfall.core.planning.interface import (
    KeptReading,
    NodeFilters,
    Place,
    keep_reading,
    kept_reading,
    list_records,
)
from waterfall.core.planning.tables import StructureReading

if TYPE_CHECKING:
    from uuid import UUID

    from realm import TestRealm
    from support import ContractClient

    from waterfall.platform.database import Database

# The shape of the body a format writes: the SHA-256 of the schemas of the contract of a node, of
# the totals and of the meta. A field added to a node changes it, and fails the test until
# ``FORMAT`` changes with it (EP-26, "Le format").
FORMAT_SHAPES = {1: "b6ea495a278e259e6c01f87644f2905e907b2592bbea8c8c46c9903444023da7"}
# A body no reading gives, which a reading kept is replaced by to tell it is read.
FORGED = b'{"items":[],"totals":{},"meta":{}}'


def place_of(witness: Database, revision: UUID) -> Place:
    """Give the main structure of a revision of PRJ-001."""
    with witness.transaction() as session:
        return Place(PRJ_001, revision, structure_of(session, revision))


def url_of(place: Place, query: str = "") -> str:
    """Give the address of ``listNodes`` of a structure."""
    return (
        f"{PROJECTS}/{place.project_id}/revisions/{place.revision_id}/structures/"
        f"{place.structure_id}/nodes{query}"
    )


def read(api: ContractClient, headers: dict[str, str], url: str) -> bytes:
    """Read a route, unchecked against the contract; give its body."""
    answer = api.client.get(url, headers=headers)
    assert answer.status_code == 200, answer.text
    return answer.content


def from_rows(witness: Database, place: Place, fields: frozenset[str] | None = None) -> bytes:
    """Give the body of a structure read whole from its rows, as a revision not marked is read."""
    with witness.transaction() as session:
        read = list_records(session, place, NodeFilters())
        return bytes(read_body(nodes_body(read, fields)).body)


def kept_row(witness: Database, place: Place) -> StructureReading | None:
    """Read the reading kept of a structure, if any."""
    with witness.transaction() as session:
        return session.scalar(
            select(StructureReading).where(
                StructureReading.project_id == place.project_id,
                StructureReading.structure_id == place.structure_id,
            )
        )


def forge(witness: Database, place: Place, **values: object) -> None:
    """Replace the reading kept of a structure by a body no reading gives, and the values given."""
    with witness.transaction() as session:
        session.execute(
            update(StructureReading)
            .where(
                StructureReading.project_id == place.project_id,
                StructureReading.structure_id == place.structure_id,
            )
            .values(document=zlib.compress(FORGED), **values)
        )


def sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def test_a_structure_of_a_marked_revision_read_whole_is_kept_and_read_from_what_is_kept(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # The first whole reading keeps the body, in the transaction of the reading; the next reads it:
    # the same body, to the byte, as before the lot; then the forged one, which no row gives.
    place = place_of(witness, REVISION_100)
    headers = person(witness, realm, *READING).headers
    assert kept_row(witness, place) is None
    first = read(api, headers, url_of(place))
    row = kept_row(witness, place)
    assert row is not None
    assert (row.revision_id, row.format) == (REVISION_100, FORMAT)
    assert len(row.document) < len(first) / 5
    second = api.get(url_of(place), headers=headers)
    assert sha(first) == sha(second.content) == MARKED_DIGEST
    assert second.headers["content-type"] == "application/json"
    forge(witness, place)
    assert read(api, headers, url_of(place)) == FORGED


@pytest.mark.parametrize(
    "fields",
    [ESTIMATE_FIELDS, "task.tracking,task.label,estimate_line.label"],
    ids=["the grid of the estimate", "the inscriptions"],
)
def test_a_marked_revision_projected_by_fields_reads_what_is_kept_as_the_rows_give_it(
    api: ContractClient, witness: Database, realm: TestRealm, fields: str
) -> None:
    # Projected by ``fields``, a whole reading keeps the body whole and reads it, its inscriptions
    # joined: the same body, to the byte (SHA-256), as from the rows, kept or not yet.
    place = place_of(witness, REVISION_101)
    headers = person(witness, realm, *READING).headers
    expected = sha(from_rows(witness, place, frozenset(fields.split(","))))
    assert sha(read(api, headers, url_of(place, f"?fields={fields}"))) == expected
    assert kept_row(witness, place) is not None
    assert sha(read(api, headers, url_of(place, f"?fields={fields}"))) == expected


def test_a_current_revision_and_a_filtered_reading_keep_nothing_and_read_the_rows(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    # A current revision still changes: its reading is never kept. A filtered reading of a marked
    # one reads the rows, a reading kept or not (#3168): the forged body is not given.
    headers = person(witness, realm, *READING).headers
    current = place_of(witness, REVISION_102)
    read(api, headers, url_of(current))
    assert kept_row(witness, current) is None
    marked = place_of(witness, REVISION_100)
    tasks = sha(read(api, headers, url_of(marked, "?kinds=task")))
    assert kept_row(witness, marked) is None
    read(api, headers, url_of(marked))
    forge(witness, marked)
    assert sha(read(api, headers, url_of(marked, "?kinds=task"))) == tasks
    assert tasks == TASKS_DIGESTS["kinds=task of a marked revision"]


def test_a_reading_kept_of_another_format_is_ignored_and_made_again(
    api: ContractClient, witness: Database, realm: TestRealm
) -> None:
    place = place_of(witness, REVISION_100)
    headers = person(witness, realm, *READING).headers
    read(api, headers, url_of(place))
    forge(witness, place, format=FORMAT + 1)
    assert sha(read(api, headers, url_of(place))) == MARKED_DIGEST
    row = kept_row(witness, place)
    assert row is not None
    assert row.format == FORMAT
    assert sha(zlib.decompress(row.document)) != sha(FORGED)


def test_the_second_write_of_the_same_reading_is_ignored_another_replaces_it(
    witness: Database,
) -> None:
    # Two processes that make the reading together write the same: the second write, of the same
    # format and settings, is ignored; one of other settings replaces it.
    place = place_of(witness, REVISION_100)
    with witness.transaction() as session:
        kept = kept_reading(session, place, FORMAT)
        assert kept is not None
        assert kept.document is None
        keep_reading(session, place, FORMAT, kept.settings_digest, b"first")
        keep_reading(session, place, FORMAT, kept.settings_digest, b"second")
        assert kept_reading(session, place, FORMAT) == KeptReading(
            b"first", kept.settings_digest, kept.inscriptions
        )
        keep_reading(session, place, FORMAT, bytes(32), b"third")
        stale = kept_reading(session, place, FORMAT)
        assert stale is not None
        assert stale.document is None
        keep_reading(session, place, FORMAT, kept.settings_digest, b"fourth")
        again = kept_reading(session, place, FORMAT)
        assert again is not None
        assert again.document == b"fourth"


def test_a_revision_not_marked_has_no_reading_kept(witness: Database) -> None:
    place = place_of(witness, REVISION_102)
    with witness.transaction() as session:
        assert kept_reading(session, place, FORMAT) is None


# What changes after the marking (EP-26, "Ce qui change encore après le marquage"), each change as
# the service writes it: what it changes in the body of the marked revision 101, field by field,
# and whether the reading kept is made again (a setting) or kept, the change joined (a gesture).
CHANGES: dict[str, tuple[str, tuple[str, ...], frozenset[str], bool]] = {
    "an inscription of a task": (
        "DELETE FROM tracking_entry WHERE project_id = :project",
        (),
        frozenset({"task.tracking"}),
        False,
    ),
    "the label of a work package": (
        "UPDATE work_package SET label = label || ' bis' WHERE project_id = :project",
        ("UPDATE order_item SET label = label || ' bis' WHERE project_id = :project",),
        frozenset({"task.work_breakdown_label"}),
        True,
    ),
    "a remaining to commit set to nought in the current revision": (
        (
            "UPDATE estimate_line SET reestimated_amount = 0 FROM node "
            "WHERE node.project_id = estimate_line.project_id "
            "AND node.id = estimate_line.node_id AND node.revision_id = :current"
        ),
        (),
        frozenset(),
        False,
    ),
    "the hours of a calendar": (
        "UPDATE calendar SET monday = monday - 1 WHERE is_default",
        (),
        frozenset({"task.calendar_hours"}),
        True,
    ),
    "the calendar of a role": (
        "UPDATE resource_role SET calendar_id = (SELECT id FROM calendar WHERE is_default)",
        (),
        frozenset({"task.calendar_id", "task.calendar_hours"}),
        True,
    ),
    "the label of a subproject": (
        "UPDATE subproject SET label = label || ' bis' WHERE project_id = :project",
        (),
        frozenset({"estimate_line.subproject_label"}),
        True,
    ),
}


def differing(before: bytes, after: bytes) -> frozenset[str]:
    """Name the fields of a node, ``<facet>.<field>``, that differ between two bodies."""
    found: set[str] = set()
    pairs = zip(json.loads(before)["items"], json.loads(after)["items"], strict=True)
    for old, new in pairs:
        for name in old.keys() | new.keys():
            if isinstance(old.get(name), dict) and isinstance(new.get(name), dict):
                found.update(
                    f"{name}.{held}"
                    for held in old[name].keys() | new[name].keys()
                    if old[name].get(held) != new[name].get(held)
                )
            elif old.get(name) != new.get(name):
                found.add(name)
    return frozenset(found)


@pytest.mark.parametrize("change", list(CHANGES))
def test_what_changes_after_the_marking_is_joined_to_the_reading_or_makes_it_again(
    api: ContractClient, witness: Database, realm: TestRealm, change: str
) -> None:
    # The body of the marked revision kept, the change made, the reading read again is the body
    # of the rows, to the byte: a gesture is joined to the reading kept, which stays as it was; a
    # setting makes it stale, and it is made again.
    statement, more, fields, again = CHANGES[change]
    place = place_of(witness, REVISION_101)
    headers = person(witness, realm, *READING).headers
    before = read(api, headers, url_of(place))
    kept = kept_row(witness, place)
    assert kept is not None
    with witness.transaction() as session:
        for each in (statement, *more):
            session.execute(text(each), {"project": PRJ_001, "current": REVISION_102})
    after = read(api, headers, url_of(place))
    assert sha(after) == sha(from_rows(witness, place))
    assert differing(before, after) == fields
    if fields:
        assert after != before
    made = kept_row(witness, place)
    assert made is not None
    assert (made.settings_digest != kept.settings_digest) is again
    assert (made.document != kept.document) is again


def test_the_format_names_the_shape_of_the_body_it_writes() -> None:
    # A field added to a node, to its facets, to the totals or to the meta changes the shape: the
    # format of the body changes with it, and a reading kept of the former one is made again.
    # The names of the properties of each object, its own and those of the objects it holds: what
    # a version of pydantic writes besides of a schema does not change the shape.
    shape: dict[str, list[str]] = {}
    for model in (Node, NodeTotals, NodeListMeta):
        schema = model.model_json_schema()
        for name, held in {model.__name__: schema, **schema.get("$defs", {})}.items():
            shape[name] = sorted(held.get("properties", {}))
    digest = hashlib.sha256(json.dumps(shape, sort_keys=True).encode()).hexdigest()
    assert FORMAT_SHAPES[FORMAT] == digest
