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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from projects_support import PROJECTS, READING, person
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session
from support import wait_for_a_lock
from test_reading_bodies import ESTIMATE_FIELDS, MARKED_DIGEST, TASKS_DIGESTS
from test_witness_projects import PRJ_001, REVISION_100, REVISION_101, REVISION_102
from test_witness_tasks import structure_of

from waterfall.api.contract.models import Node, NodeListMeta, NodeTotals
from waterfall.api.nodes import FORMAT, joined, kept_body, kept_document, nodes_body, read_body
from waterfall.core.planning.interface import (
    NodeFilters,
    Place,
    TrackingView,
    keep_reading,
    kept_reading,
    list_records,
)
from waterfall.core.planning.tables import Node as NodeRow
from waterfall.core.planning.tables import StructureReading, TrackingEntry

if TYPE_CHECKING:
    from uuid import UUID

    from realm import TestRealm
    from support import ContractClient

    from waterfall.platform.database import Database

# The shape of the body a format writes: the SHA-256 of the schemas of the contract of a node, of
# the totals and of the meta. A field added to a node changes it, and fails the test until
# ``FORMAT`` changes with it (EP-26, "Le format").
FORMAT_SHAPES = {
    1: "b6ea495a278e259e6c01f87644f2905e907b2592bbea8c8c46c9903444023da7",
    2: "b6ea495a278e259e6c01f87644f2905e907b2592bbea8c8c46c9903444023da7",
    3: "830a4c76c3b031aa300035acb46f0124bb89fb58821796102f5861b3ccb97ff7",
}
# The body of the marked revision 100 as a format writes it, as the rows give it: a value written
# otherwise, the shape the same, changes it, and fails the test until ``FORMAT`` changes with it.
# 2: the physical progress of its summaries computed (US-1680), not computable in 1. 3: the manual
# task of a conflict named (US-3300): the same body, the revision bearing no conflict.
FORMAT_BODIES = {
    1: "eaadbe84e77482ac75b037e5a3269ab44183badd3154112f6d9818a503967dae",
    2: "29cbdfd16bd179c92aed66a6684a5bb5d7086c7a6fe4e679bd0669980dea3f75",
    3: "29cbdfd16bd179c92aed66a6684a5bb5d7086c7a6fe4e679bd0669980dea3f75",
}
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
        keep_reading(session, place, FORMAT, kept, b"first")
        keep_reading(session, place, FORMAT, kept, b"second")
        held = kept_reading(session, place, FORMAT)
        assert held is not None
        assert (held.document, held.settings_digest) == (b"first", kept.settings_digest)
        keep_reading(session, place, FORMAT, replace(kept, settings_digest=bytes(32)), b"third")
        stale = kept_reading(session, place, FORMAT)
        assert stale is not None
        assert stale.document is None
        keep_reading(session, place, FORMAT, kept, b"fourth")
        again = kept_reading(session, place, FORMAT)
        assert again is not None
        assert again.document == b"fourth"


def test_an_older_reading_does_not_replace_a_newer_one_of_other_settings(
    witness: Database,
) -> None:
    # A reads the settings, a setting changes, B reads the changed ones and is kept first; A, kept
    # after, does not put its stale settings back; the reading that follows is not made again.
    place = place_of(witness, REVISION_100)
    with witness.transaction() as session:
        older = kept_reading(session, place, FORMAT)
    with witness.transaction() as session:
        session.execute(text("UPDATE calendar SET monday = monday - 1 WHERE is_default"))
    with witness.transaction() as session:
        newer = kept_reading(session, place, FORMAT)
        assert newer is not None
        keep_reading(session, place, FORMAT, newer, b"newer")
    assert older is not None
    assert older.read_at < newer.read_at
    assert older.settings_digest != newer.settings_digest
    with witness.transaction() as session:
        keep_reading(session, place, FORMAT, older, b"older")
    row = kept_row(witness, place)
    assert row is not None
    assert zlib.decompress(row.document) == b"newer"
    with witness.transaction() as session:
        again = kept_reading(session, place, FORMAT)
    assert again is not None
    assert again.document == b"newer"


def test_a_write_waits_for_the_row_another_transaction_inserts_and_leaves_it_as_it_is(
    witness: Database,
) -> None:
    # Two processes read the structure together: the first inserts and has not committed, the
    # second waits for its row, then finds it, of the same settings, and replaces nothing.
    place = place_of(witness, REVISION_100)
    with witness.transaction() as session:
        kept = kept_reading(session, place, FORMAT)
    assert kept is not None

    def second() -> None:
        with witness.transaction() as session:
            keep_reading(session, place, FORMAT, kept, b"second")

    with ThreadPoolExecutor(1) as others, Session(witness.engine) as first:
        keep_reading(first, place, FORMAT, kept, b"first")
        writing = others.submit(second)
        wait_for_a_lock(witness)
        assert not writing.done()
        first.commit()
        writing.result(timeout=10)
    row = kept_row(witness, place)
    assert row is not None
    assert zlib.decompress(row.document) == b"first"


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


def test_the_format_names_the_body_it_writes(witness: Database) -> None:
    # What the properties do not tell: a value written otherwise changes the body of a marked
    # revision, and the format with it.
    body = from_rows(witness, place_of(witness, REVISION_100))
    assert FORMAT_BODIES[FORMAT] == sha(body)


# --- The inscriptions joined (#3481) and the order of the readings kept (#3505) ------------------


def test_the_inscriptions_are_written_in_the_document_as_reading_it_would_write_them(
    witness: Database,
) -> None:
    # The document kept is not read again to join the inscriptions of its tasks: written in it,
    # they give the bytes the document read, joined and written again gives, which are the rows'.
    place = place_of(witness, REVISION_101)
    with witness.transaction() as session:
        found = kept_document(session, place)
        assert found is not None
        document, kept = found
        reread = kept_body(session, place)
        assert reread is not None
        written = bytes(read_body(reread).body)
    assert kept.inscriptions
    assert joined(document, kept.inscriptions) == written == from_rows(witness, place)


def test_the_keys_of_a_node_are_written_in_the_order_the_join_of_the_inscriptions_reads(
    witness: Database,
) -> None:
    # ``joined`` glues bytes: each node opens with its ``node_id``, its ``lineage_id`` comes before
    # the ``tracking`` of its task. A change of the order of the keys of ``Node`` fails here.
    place = place_of(witness, REVISION_101)
    with witness.transaction() as session:
        found = kept_document(session, place)
    assert found is not None
    nodes = found[0].split(b'"node_id":')[1:]
    tasks = [each for each in nodes if b'"tracking":[]' in each]
    assert tasks
    for each in tasks:
        assert each.count(b'"lineage_id":"') == 1
        assert each.index(b'"lineage_id":"') < each.index(b'"tracking":[]')


def test_an_inscription_is_joined_to_its_task_alone_never_to_the_node_after_it() -> None:
    # A lineage inscribed that is a line's has no inscriptions of its own to receive: the empty
    # ones of the task after it are left as they are. A text that writes the key is escaped.
    line, task = uuid4(), uuid4()
    document = bytes(
        read_body(
            {
                "items": [
                    {"node_id": "a", "lineage_id": str(line), "task": None},
                    {
                        "node_id": "b",
                        "lineage_id": str(task),
                        "task": {"label": '"tracking":[]', "tracking": []},
                    },
                ]
            }
        ).body
    )
    inscribed = (TrackingView("milestone_tracking", None),)
    assert joined(document, {line: inscribed}) == document
    assert json.loads(joined(document, {task: inscribed}))["items"][1]["task"] == {
        "label": '"tracking":[]',
        "tracking": [{"kind": "milestone_tracking", "timeline_id": None}],
    }


def test_the_inscriptions_read_are_those_of_the_tasks_of_the_structure_alone(
    witness: Database,
) -> None:
    # An inscription of a lineage the structure has no task of is not read with its reading kept,
    # though of the project.
    place = place_of(witness, REVISION_100)
    elsewhere = uuid4()
    with Session(witness.engine) as session:
        now = session.execute(select(func.now())).scalar_one()
        session.add(
            TrackingEntry(
                id=uuid4(),
                project_id=PRJ_001,
                lineage_id=elsewhere,
                kind="milestone_tracking",
                timeline_id=None,
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()
        kept = kept_reading(session, place, FORMAT)
        tasks = set(
            session.scalars(
                select(NodeRow.lineage_id).where(
                    NodeRow.project_id == place.project_id,
                    NodeRow.structure_id == place.structure_id,
                    NodeRow.kind == "task",
                )
            )
        )
        session.rollback()
    assert kept is not None
    assert kept.inscriptions
    assert elsewhere not in kept.inscriptions
    assert set(kept.inscriptions) <= tasks


def test_a_reading_of_the_same_instant_replaces_one_of_other_settings_an_earlier_one_does_not(
    witness: Database,
) -> None:
    # The guard of ``keep_reading`` at its bound (#3505): a reading whose settings were read at
    # the instant of the one kept, of other settings, replaces it; one a microsecond earlier does
    # not.
    place = place_of(witness, REVISION_100)
    with witness.transaction() as session:
        kept = kept_reading(session, place, FORMAT)
        assert kept is not None
        keep_reading(session, place, FORMAT, kept, b"first")
        same = replace(kept, settings_digest=bytes(32))
        keep_reading(session, place, FORMAT, same, b"same instant")
        earlier = replace(kept, read_at=kept.read_at - timedelta(microseconds=1))
        keep_reading(session, place, FORMAT, earlier, b"earlier")
    row = kept_row(witness, place)
    assert row is not None
    assert (zlib.decompress(row.document), row.kept_at) == (b"same instant", kept.read_at)


def test_the_instant_of_a_reading_is_read_on_the_clock_of_the_database(witness: Database) -> None:
    # One clock for every process of the API (#3505): the instant the settings are read is the
    # database's, between two readings of its clock.
    place = place_of(witness, REVISION_100)
    with witness.transaction() as session:
        before = session.execute(select(func.clock_timestamp())).scalar_one()
        kept = kept_reading(session, place, FORMAT)
        after = session.execute(select(func.clock_timestamp())).scalar_one()
    assert kept is not None
    assert before <= kept.read_at <= after
