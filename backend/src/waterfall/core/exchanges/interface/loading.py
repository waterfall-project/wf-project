# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""An import of the witness, written as its analysis and its end left it (US-1650/L2).

The loader of the witness writes its imports through this function, not through the two steps:
no file, no worker, in the one transaction of the command (EP-09, "Ce que le cadrage décide", "Le
chargeur du témoin"). ``load_import`` writes the row of an import at the identifier, the instants
and the author the witness imposes, in the state it ended in — ``applied`` at the instant of the
event, or ``expired``, its report outliving its decision —, with its report as its analysis
presented it and the period it declared — an import of the project, as an extraction of the actual
costs, which aims at no structure. It deposits nothing and submits no task: the row names no
deposit the storage holds, its key that of a deposit of its identifier, and no task (``task_id``
null). The application of an import inscribes itself in the journal of audit; the
witness keeps none of it, its journal the costs' (``load_cost_import``).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from waterfall.core.exchanges.judgments import REPORT_LIFETIME
from waterfall.core.exchanges.tables import ImportReport

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import date, datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.exchanges.interface.imports import ExchangeKind
    from waterfall.platform.audit import Act

# Where the deposit of an import would lie (``uploads/<upload_id>``, EP-06): the witness's lies
# nowhere.
UPLOADS = "uploads"


@dataclass(frozen=True, slots=True)
class ImportLoad:
    """An import of the witness: its identifier, its project, its kind, its file, how it ended.

    ``status`` the state it ended in: ``applied``, or ``expired`` without being applied; its
    period as it was declared, each bound possibly missing; its report as its analysis presented
    it (``ImportReport`` of the contract); the instant it was opened, and the one its report
    expired or expires at, twenty-four hours after its analysis.
    """

    import_id: UUID
    project_id: UUID
    kind: ExchangeKind
    filename: str
    status: Literal["applied", "expired"]
    period_from: date | None
    period_to: date | None
    report: Mapping[str, Any]
    created_at: datetime
    expires_at: datetime


def load_import(session: Session, load: ImportLoad, act: Act) -> None:
    """Write an import of the witness, in the state it ended in, by the author of ``act``.

    Analysed twenty-four hours before its report expires; applied at the instant of ``act``, which
    falls between its analysis and its expiry, or expired, the instant of ``act`` its analysis. A
    load whose instants disagree, or without an author, is a defect of the description: it raises
    ``ValueError``, nothing written. The base refuses an identifier held already.
    """
    analysed_at = load.expires_at - REPORT_LIFETIME
    applied = load.status == "applied"
    if act.author is None:
        message = f"the import {load.import_id} of the witness has no author"
        raise ValueError(message)
    in_time = analysed_at <= act.at <= load.expires_at if applied else act.at == analysed_at
    if load.created_at > analysed_at or not in_time:
        message = f"the instants of the import {load.import_id} of the witness disagree"
        raise ValueError(message)
    session.add(
        ImportReport(
            id=load.import_id,
            project_id=load.project_id,
            kind=load.kind,
            filename=load.filename,
            upload_id=load.import_id,
            object_key=f"{UPLOADS}/{load.import_id}",
            structure_id=None,
            revision_id=None,
            period_from=load.period_from,
            period_to=load.period_to,
            status=load.status,
            report=dict(load.report),
            task_id=None,
            requested_by=act.author,
            created_at=load.created_at,
            analysed_at=analysed_at,
            expires_at=load.expires_at,
            applied_at=act.at if applied else None,
        )
    )
    session.flush()
