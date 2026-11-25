# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The deposits of the imports a cascade takes away: expired before the rows go (US-3250/L2b).

An import is deleted with the structure it aims at or the revision it writes in (``CASCADE``,
US-3060): neither ``abandonImport`` nor the purge runs, and the row that named its deposit is gone.
A deposit an import employed never becomes free again (WF-DAT-0120): the abandonment of a
differential (``expire_structure_deposits``) and that of a revision (``expire_revision_deposits``,
registered in the closing of the revisions) say the deposits of the imports they carry expired, in
their own transaction, before the structure or the revision is deleted.

The deposits expire at the instant of the act for a differential (``at``, that of its writer), at
``utc_now()`` for a revision: ``RevisionClosing`` carries no ``Act`` — the session, the project, the
revision and the kind alone —, so no instant of the act reaches this hook. Both are the moment of
the transaction, within the request.
"""

from typing import TYPE_CHECKING

from sqlalchemy import or_, select

from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.revisions.interface import register_closing, revision_structures
from waterfall.platform.database import utc_now
from waterfall.platform.uploads import expire_uploads

if TYPE_CHECKING:
    from collections.abc import Collection
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy import ColumnElement
    from sqlalchemy.orm import Session

    from waterfall.core.revisions.interface import RevisionClosing


def _expire(session: Session, where: ColumnElement[bool], at: datetime) -> None:
    """Say expired the deposits of the imports ``where`` selects."""
    expire_uploads(session, session.scalars(select(ImportReport.upload_id).where(where)).all(), at)


def expire_structure_deposits(
    session: Session, project_id: UUID, structure_ids: Collection[UUID], at: datetime
) -> None:
    """Say expired at ``at`` the deposits of the imports aimed at structures about to be deleted."""
    _expire(
        session,
        (ImportReport.project_id == project_id) & ImportReport.structure_id.in_(structure_ids),
        at,
    )


def expire_revision_deposits(closing: RevisionClosing) -> None:
    """Say expired the deposits of the imports written in a revision about to be abandoned.

    The cascade takes an import by the revision it writes in or by the structure it aims at: an
    import of the project alone has no revision (``revision_id`` null, ``scope=project``) yet aims
    at a structure of the revision it reads, so both keys select. Registered in the closing of the
    revisions, which a marking runs as well: it does nothing then, the revision and its imports
    staying.
    """
    if closing.kind == "abandoned":
        structures = revision_structures(closing.session, closing.project_id, closing.revision_id)
        where = (ImportReport.project_id == closing.project_id) & or_(
            ImportReport.revision_id == closing.revision_id,
            ImportReport.structure_id.in_(structures),
        )
        _expire(closing.session, where, utc_now())


register_closing("evaluations", expire_revision_deposits)
