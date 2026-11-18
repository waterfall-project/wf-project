# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of a structure of a marked revision, kept (EP-26, "Ce qui est gardé", US-2270).

A marked revision no longer changes: the body of ``listNodes`` of one of its structures, read whole,
is computed once and kept, compressed (``structure_reading``), and the API reads it rather than the
rows. The core keeps a document it does not read — its form is the API's, which names its format —
and says what a reading kept depends on outside the revision, which still changes after the marking
(EP-26, "Ce qui change encore après le marquage"):

- what a current gesture changes — an inscription of a task to a timeline or to the time/time
  tracking, kept by lineage across the revisions (WF-PLA-0060) — does not enter the document: the
  inscriptions of the tasks of the structure are read at each reading
  (``KeptReading.inscriptions``), and joined to it by the API;
- what a setting changes — the calendars and the calendar of each role (WF-PLA-0010), the label of
  a work package or an order item (WF-PLA-0170), the label of a subproject (EP-07) — makes the
  readings kept of the project stale: their digest (``settings_digest``), read before the reading
  and kept with it, is no longer the settings', and the reading is made again at the next demand.
  The digest read first, a setting changed during a reading is of a later state than its digest:
  the reading is made again, never kept stale.

A reading of another format than the code's is ignored and made again, as a stale one. One is kept
at the first whole reading of its structure, in the transaction of the reading; two processes that
make it together write the same, and the second write is ignored (``keep_reading``).
"""

import hashlib
import json
import zlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert

from waterfall.core.planning.tables import Node, StructureReading, TrackingEntry
from waterfall.core.planning.tree import TASK
from waterfall.core.planning.views import TrackingView
from waterfall.core.projects.interface import project_subproject_labels, work_breakdown_items
from waterfall.core.resource_settings.interface import calendar_settings
from waterfall.core.revisions.interface import revision_marked_at
from waterfall.platform.database import UtcDateTime

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.writing import Place

# The level of the compression of a document: zlib's default, the balance of its size and its time.
COMPRESSION = 6


@dataclass(frozen=True, slots=True)
class KeptReading:
    """What a reading of a structure of a marked revision finds kept, and what it joins to it.

    ``document`` the body kept, decompressed, of the format asked and of the settings of now; none
    when the reading is to be made, and kept with ``settings_digest``. ``inscriptions`` the
    inscriptions of the tasks of the structure, by lineage, in the order a reading gives them.
    ``read_at`` the instant the settings were read, taken as their digest is, by the clock of the
    database: the reading made from them is kept with it (``keep_reading``).
    """

    document: bytes | None
    settings_digest: bytes
    inscriptions: Mapping[UUID, tuple[TrackingView, ...]]
    read_at: datetime


def _settings_digest(session: Session, project_id: UUID) -> bytes:
    """Give the digest of what a reading of a structure of a project reads outside its revision.

    The calendars and the calendar of each role, the work packages and the order items of the
    project, its subprojects, each with what a reading shows of it: a change of one of them changes
    the digest, and makes the readings kept of the project stale. The labels and the states of the
    roles and the categories are not in it: a marked revision reads them on its images, made at its
    marking for every role and category its lines employ, and which no setting changes after.
    """
    items = sorted(
        (str(item.item_id), item.kind, item.label, item.deleted)
        for item in work_breakdown_items(session, project_id).values()
    )
    subprojects = sorted(
        (str(subproject_id), label)
        for subproject_id, label in project_subproject_labels(session, project_id).items()
    )
    settings = json.dumps([calendar_settings(session), items, subprojects], ensure_ascii=False)
    return hashlib.sha256(settings.encode()).digest()


def _inscriptions_of(session: Session, place: Place) -> dict[UUID, tuple[TrackingView, ...]]:
    """Read the inscriptions of the tasks of a structure, by lineage, the time/time tracking first.

    Those of its tasks alone, not of the project's (#3481); in the order a reading gives the
    inscriptions of a task (``tracking_of``).
    """
    found: dict[UUID, list[TrackingView]] = {}
    rows = session.execute(
        select(TrackingEntry.lineage_id, TrackingEntry.kind, TrackingEntry.timeline_id)
        .join(
            Node,
            and_(
                Node.project_id == TrackingEntry.project_id,
                Node.lineage_id == TrackingEntry.lineage_id,
            ),
        )
        .where(
            TrackingEntry.project_id == place.project_id,
            Node.structure_id == place.structure_id,
            Node.kind == TASK,
        )
        .order_by(TrackingEntry.kind, TrackingEntry.created_at, TrackingEntry.id)
    )
    for lineage_id, kind, timeline_id in rows:
        found.setdefault(lineage_id, []).append(TrackingView(kind, timeline_id))
    return {lineage_id: tuple(held) for lineage_id, held in found.items()}


def kept_reading(session: Session, place: Place, form: int) -> KeptReading | None:
    """Read the reading kept of a structure of a marked revision, of the format asked; or none.

    None for a revision not marked — or unknown: the reading of the rows answers, or refuses
    (404). The settings are read first, then the reading kept: one of another format, or of other
    settings, is ignored (``document`` none).
    """
    if revision_marked_at(session, place.revision_id) is None:
        return None
    # The clock of the database, the one every process of the API reads, not each process its own:
    # two processes whose clocks differ still order their readings as the database does (#3505).
    read_at = session.execute(select(func.clock_timestamp(type_=UtcDateTime()))).scalar_one()
    digest = _settings_digest(session, place.project_id)
    row = session.execute(
        select(
            StructureReading.format, StructureReading.settings_digest, StructureReading.document
        ).where(
            StructureReading.project_id == place.project_id,
            StructureReading.structure_id == place.structure_id,
            StructureReading.revision_id == place.revision_id,
        )
    ).first()
    document = (
        zlib.decompress(row.document)
        if row is not None and row.format == form and row.settings_digest == digest
        else None
    )
    return KeptReading(document, digest, _inscriptions_of(session, place), read_at)


def keep_reading(
    session: Session, place: Place, form: int, kept: KeptReading, document: bytes
) -> None:
    """Keep the reading of a structure of a marked revision, of a format and settings, compressed.

    In the transaction of the reading. One of another format or of other settings is replaced; the
    same one, written by a process that read the structure together with this one, is left as it
    is: the second write is ignored. Nor is one of settings read later replaced by one of settings
    read earlier (``kept.read_at``): a reading that read the settings before a change and is kept
    after another's, of the settings changed, is ignored; of the same instant, the other settings
    replace. The instants are the database's, one clock for every process (#3505): put back, it can
    make a reading kept stale, which the next reading finds of other settings and makes again — a
    reading more, never a body of other settings served.
    """
    statement = insert(StructureReading).values(
        project_id=place.project_id,
        structure_id=place.structure_id,
        revision_id=place.revision_id,
        format=form,
        settings_digest=kept.settings_digest,
        document=zlib.compress(document, COMPRESSION),
        kept_at=kept.read_at,
    )
    written = statement.excluded
    session.execute(
        statement.on_conflict_do_update(
            index_elements=[StructureReading.project_id, StructureReading.structure_id],
            set_={
                "format": written.format,
                "settings_digest": written.settings_digest,
                "document": written.document,
                "kept_at": written.kept_at,
            },
            where=and_(
                StructureReading.kept_at <= written.kept_at,
                or_(
                    StructureReading.format != written.format,
                    StructureReading.settings_digest != written.settings_digest,
                ),
            ),
        )
    )
