# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The parameters of a query that several operations of the API share, typed once."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Query
from pydantic import AwareDatetime, BaseModel

from waterfall.api.contract.base import Text
from waterfall.api.contract.models import AuditActorKind
from waterfall.platform.audit_columns import AuditColumnFilters, AuthorFilter, Period
from waterfall.platform.errors import FieldError, UnprocessableError

VALIDATION_FAILED = "VALIDATION_FAILED"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"

# The parameter ``search`` of the contract, absent by default; a text, which refuses a NUL.
Search = Annotated[Text | None, Query(min_length=1, max_length=200)]


def listed[T](name: str, text: str | None, read: Callable[[str], T]) -> tuple[T, ...] | None:
    """Read a list of the query, its values separated by commas (``explode: false``).

    ``None`` when the parameter is absent. A value that ``read`` refuses (``ValueError``), an empty
    one included, refuses the parameter (422).
    """
    if text is None:
        return None
    try:
        return tuple(read(value) for value in text.split(","))
    except ValueError:
        fault = FieldError(f"/query/{name}", VALIDATION_FAILED)
        raise UnprocessableError(VALIDATION_FAILED, fields=(fault,)) from None


class AuditColumnsQuery(BaseModel):
    """The filters of the columns of audit of a flat table, as the query names them (#936)."""

    created_at_from: AwareDatetime | None = None
    created_at_to: AwareDatetime | None = None
    created_by_user_id: UUID | None = None
    created_by_kind: AuditActorKind | None = None
    updated_at_from: AwareDatetime | None = None
    updated_at_to: AwareDatetime | None = None
    updated_by_user_id: UUID | None = None
    updated_by_kind: AuditActorKind | None = None


def _inverted(name: str, since: datetime | None, until: datetime | None) -> FieldError | None:
    """Name the end of a period of a column of dates that precedes its start, the start named."""
    if since is None or until is None or until >= since:
        return None
    return FieldError(f"/query/{name}_to", VALUE_OUT_OF_RANGE, {"minimum": since.astimezone(UTC)})


def _author(user_id: UUID | None, kind: AuditActorKind | None) -> AuthorFilter:
    return AuthorFilter(user_id, None if kind is None else kind.value)


def audit_column_filters(query: Annotated[AuditColumnsQuery, Query()]) -> AuditColumnFilters:
    """Read the filters of the columns of audit of a flat table (WF-IHM-0130, #936).

    A period whose end precedes its start is refused at its end, the start named (422), the rule
    of every period of the contract; both are named if both are.
    """
    faults = [
        fault
        for fault in (
            _inverted("created_at", query.created_at_from, query.created_at_to),
            _inverted("updated_at", query.updated_at_from, query.updated_at_to),
        )
        if fault is not None
    ]
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    return AuditColumnFilters(
        created=Period(query.created_at_from, query.created_at_to),
        created_by=_author(query.created_by_user_id, query.created_by_kind),
        updated=Period(query.updated_at_from, query.updated_at_to),
        updated_by=_author(query.updated_by_user_id, query.updated_by_kind),
    )
