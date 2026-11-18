# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The measure of the reading kept and of the marking (US-2270): its volume, and nothing left.

``make measure-core`` reads the last marked revision of PRJ-001 as kept, marks the current one,
compares the two last marked ones from the rows and as kept, and reads filtered readings from the
rows and from the document (US-2270/L2), on the witness of the service platform, each write rolled
back. The tool is no requirement's: these
tests hold its arithmetic of the volume of §4.6.2, and, on the witness of the tests, its promise to
leave nothing written.
"""

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import func, select

from measure.document import (
    measure_comparison,
    measure_filtered,
    measure_kept,
    measure_marking,
    platform_volume,
)
from measure.target import locate
from waterfall.core.planning.tables import StructureReading
from waterfall.core.revisions.tables import Revision
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.logs import PLATFORM, logging_context

if TYPE_CHECKING:
    from waterfall.platform.database import Database


def test_the_volume_kept_is_scaled_to_the_platform_of_the_volumes_of_4_6_2() -> None:
    # 80 bytes a node: 0.8 MB a revision of 10,000 nodes, 180 revisions of 600 projects.
    volume = platform_volume(480_000, 6_000)

    assert volume.bytes_per_node == pytest.approx(80.0)
    assert volume.revision_mb == pytest.approx(0.8)
    assert volume.platform_gb == pytest.approx(86.4)
    assert volume.share_of_space == pytest.approx((0.432, 0.576))


def test_a_structure_of_no_node_weighs_nothing() -> None:
    assert platform_volume(0, 0).platform_gb == 0.0


def _state(database: Database) -> tuple[int, tuple[tuple[object, ...], ...]]:
    """Count the readings kept, and read the status and the name of every revision."""
    with database.transaction() as session:
        kept = session.scalar(select(func.count()).select_from(StructureReading))
        revisions = tuple(
            tuple(row)
            for row in session.execute(
                select(Revision.id, Revision.status, Revision.version_name).order_by(Revision.id)
            )
        )
    return int(kept or 0), revisions


def test_the_reading_kept_and_the_marking_measured_leave_nothing_written(
    witness: Database,
) -> None:
    target = locate(witness)
    before = _state(witness)

    with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
        kept = measure_kept(witness, target, 1)
        marking = measure_marking(witness, target, 1)
        comparison = measure_comparison(witness, target, 1)
        filtered = measure_filtered(witness, target, 1)

    assert _state(witness) == before
    assert before[0] == 0
    made, read, projected = kept[1], kept[2], kept[4]
    assert 0 < float(made.facts["kept_mb"]) < float(made.facts["body_mb"])
    assert 0 < float(read.facts["kept_over_rows"]) < 1
    assert float(projected.facts["kept_over_rows"]) > 0
    assert float(kept[5].facts["platform_gb"]) > 0
    # The comparison from what is kept gives the body of the rows, to the byte (US-2270).
    assert comparison[2].facts["same_body"] is True
    assert float(comparison[2].facts["kept_over_rows"]) > 0
    assert [each["filter"] for each in filtered.rows] == [
        "kinds=task",
        "search=revue&progress=not_started,started",
        "max_level=2",
    ]
    assert all(float(each["document_ms"]) > 0 for each in filtered.rows)
    assert marking.summary is not None
    assert float(marking.facts["keep_median_ms"]) > 0
