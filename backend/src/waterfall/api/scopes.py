# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The scope of the indicators, as the routes that read a document a marking kept read it.

Shared by the routes of the indicators, of their curves, of the estimate and of the remaining to
commit (US-1670/L2): the scope the contract writes, and the refusal of one that a revision does
not know.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from waterfall.core.costs.interface import PROJECT, UNASSIGNED, CostScope
from waterfall.core.indicators.interface import kept_of_kind
from waterfall.platform.errors import VALIDATION_FAILED, FieldError, UnprocessableError
from waterfall.platform.identifiers import read_identifier

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface import Document, IndicatorKind

SCOPE_POINTER = "/query/scope"
UNKNOWN_SUBPROJECT = "UNKNOWN_SUBPROJECT"
# The identifier a malformed scope is read as: no subproject bears it.
NO_SUBPROJECT = UUID(int=0)


def scope_of(text: str) -> CostScope:
    """Read the scope asked: the project, the project alone, or the identifier of a subproject."""
    if text == PROJECT:
        return PROJECT
    if text == UNASSIGNED:
        return UNASSIGNED
    return read_identifier(text) or NO_SUBPROJECT


def unknown_scope() -> UnprocessableError:
    """Give the refusal of a scope that is none of the project's, or that a revision never had."""
    return UnprocessableError(
        VALIDATION_FAILED, fields=(FieldError(SCOPE_POINTER, UNKNOWN_SUBPROJECT),)
    )


def kept_document(
    session: Session, revision_id: UUID, kind: IndicatorKind, scope: CostScope
) -> Document | None:
    """Give the document a marked revision kept for a kind and a scope; refuse a scope it lacks.

    A revision that kept the kind but not the scope — a subproject created since its marking —
    does not know that scope: refused (422), as a scope the project does not have. None when the
    revision kept nothing of the kind, marked before the indicators were kept: the caller decides.
    """
    kept = kept_of_kind(session, revision_id, kind, scope)
    if kept.document is None and kept.kind_kept:
        raise unknown_scope()
    return kept.document
