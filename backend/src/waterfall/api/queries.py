# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The parameters of a query that several operations of the API share, typed once."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
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


def refuse_query(faults: Iterable[FieldError]) -> None:
    """Refuse a query at every parameter at fault, all named at once (422); none, nothing."""
    named = tuple(faults)
    if named:
        raise UnprocessableError(VALIDATION_FAILED, fields=named)


def read_list[T](
    name: str, text: str | None, read: Callable[[str], T]
) -> tuple[tuple[T, ...] | None, tuple[FieldError, ...]]:
    """Read a list of the query, its values separated by commas (``explode: false``), and its fault.

    ``None`` when the parameter is absent. A value that ``read`` refuses (``ValueError``), an empty
    one included, is the fault of the parameter, which the caller names with its others.
    """
    if text is None:
        return None, ()
    try:
        return tuple(read(value) for value in text.split(",")), ()
    except ValueError:
        return None, (FieldError(f"/query/{name}", VALIDATION_FAILED),)


def listed[T](name: str, text: str | None, read: Callable[[str], T]) -> tuple[T, ...] | None:
    """Read a list of the query, as ``read_list`` does; its fault refuses the parameter (422)."""
    values, faults = read_list(name, text, read)
    refuse_query(faults)
    return values


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


@dataclass(frozen=True, slots=True)
class FiltersRead[T]:
    """Filters as the query gives them, and its faults, given rather than raised.

    The table that reads several of them names all their faults at once (``refuse_query``).
    """

    filters: T
    faults: tuple[FieldError, ...] = ()


def audit_column_filters(
    query: Annotated[AuditColumnsQuery, Query()],
) -> FiltersRead[AuditColumnFilters]:
    """Read the filters of the columns of audit of a flat table (WF-IHM-0130, #936).

    A period whose end precedes its start is a fault at its end, the start named, the rule of
    every period of the contract; both are if both are. The faults are given, not raised: the
    table names them with its own, in one refusal (422).
    """
    faults = tuple(
        fault
        for fault in (
            _inverted("created_at", query.created_at_from, query.created_at_to),
            _inverted("updated_at", query.updated_at_from, query.updated_at_to),
        )
        if fault is not None
    )
    filters = AuditColumnFilters(
        created=Period(query.created_at_from, query.created_at_to),
        created_by=_author(query.created_by_user_id, query.created_by_kind),
        updated=Period(query.updated_at_from, query.updated_at_to),
        updated_by=_author(query.updated_by_user_id, query.updated_by_kind),
    )
    return FiltersRead(filters, faults)
