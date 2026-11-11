# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The mapping of the extraction of the actual costs.

Read, replaced whole, and its labels folded as the import compares them (WF-REF-0190). The
mapping is a single row and its labels: for each of the five columns the import reads, the
labels that name it in the extraction (at most 20), and the labels of the columns it keeps (at
most 50). A label is compared to another, and to a header of the extraction, without case,
accents nor spaces at its ends (``folded``), and no label doubles another over the whole
mapping: the database holds that rule by a unique constraint, the service names the label that
breaks it before writing anything. The mapping is written whole, with the counter read, in one
transaction; an incomplete one is kept — the import refuses it, not the writing.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import Text, delete, func, insert, literal, select, update
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import insert as insert_if_absent

from waterfall.core.cost_settings.refusals import ACTUAL_COST_MAPPING, not_bootstrapped
from waterfall.core.cost_settings.tables import (
    SINGLE_ROW,
    SOURCE_COLUMNS,
    ActualCostMapping,
    ActualCostMappingLabel,
)
from waterfall.core.users.interface import Author, read_author
from waterfall.platform.database import folded
from waterfall.platform.errors import (
    STALE_LOCK_VERSION,
    VALIDATION_FAILED,
    FieldError,
    PreconditionFailedError,
    UnprocessableError,
    json_pointer,
)
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime
    from typing import Any

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

VALUE_TOO_LONG = "VALUE_TOO_LONG"
DUPLICATE_COLUMN_LABEL = "DUPLICATE_COLUMN_LABEL"
# The most labels a column read names, and the most columns the import keeps.
READ_LABELS_LIMIT = 20
KEPT_COLUMNS_LIMIT = 50
# The only column the import reads that it does not require.
OPTIONAL_COLUMN = "document_item"
# What is cut at both ends of a label before it is compared: every kind of space.
ENDS = r"^\s+|\s+$"


@dataclass(frozen=True, slots=True)
class ColumnLabels:
    """The labels that name a column of the extraction, in the order they were declared."""

    column: str
    labels: Sequence[str]


@dataclass(frozen=True, slots=True)
class ActualCostMappingWrite:
    """What the mapping is replaced with: the five columns read, each once in their fixed order."""

    columns: Sequence[ColumnLabels]
    kept_columns: Sequence[str]


@dataclass(frozen=True, slots=True)
class MappingColumn:
    """A column the import reads, with the labels that name it and whether it is required."""

    column: str
    required: bool
    labels: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ActualCostMappingView:
    """The mapping as it is read: complete when each required column has a label."""

    columns: tuple[MappingColumn, ...]
    kept_columns: tuple[str, ...]
    is_complete: bool
    missing_columns: tuple[str, ...]
    lock_version: int
    created_at: datetime
    created_by: Author | None
    updated_at: datetime
    updated_by: Author | None


def create_actual_cost_mapping(session: Session, act: Act) -> bool:
    """Create the mapping, empty, at its version 1, unless it is there; tell whether it was made.

    The bootstrap does it, and the loader of the witness on a platform that has not (WF-REF-0190).
    """
    created = session.execute(
        insert_if_absent(ActualCostMapping)
        .values(
            id=SINGLE_ROW,
            lock_version=1,
            created_at=act.at,
            created_by=act.author,
            updated_at=act.at,
            updated_by=act.author,
        )
        .on_conflict_do_nothing()
        .returning(ActualCostMapping.id)
    ).first()
    return created is not None


def read_actual_cost_mapping(session: Session) -> ActualCostMappingView:
    """Read the mapping, its columns in the fixed order and its labels in the order declared.

    Refused (503) while the bootstrap has not written its row.
    """
    head = session.execute(
        select(
            ActualCostMapping.lock_version,
            ActualCostMapping.created_at,
            ActualCostMapping.created_by,
            ActualCostMapping.updated_at,
            ActualCostMapping.updated_by,
        ).where(ActualCostMapping.id == SINGLE_ROW)
    ).one_or_none()
    if head is None:
        raise not_bootstrapped(ACTUAL_COST_MAPPING)
    named: dict[str, list[str]] = {column: [] for column in SOURCE_COLUMNS}
    kept: list[str] = []
    for column, label in session.execute(
        select(ActualCostMappingLabel.column, ActualCostMappingLabel.label).order_by(
            ActualCostMappingLabel.position
        )
    ):
        (kept if column is None else named[column]).append(label)
    columns = tuple(
        MappingColumn(column, column != OPTIONAL_COLUMN, tuple(named[column]))
        for column in SOURCE_COLUMNS
    )
    missing = tuple(column.column for column in columns if column.required and not column.labels)
    return ActualCostMappingView(
        columns=columns,
        kept_columns=tuple(kept),
        is_complete=not missing,
        missing_columns=missing,
        lock_version=head.lock_version,
        created_at=head.created_at,
        created_by=read_author(session, head.created_by),
        updated_at=head.updated_at,
        updated_by=read_author(session, head.updated_by),
    )


def fold_labels(session: Session, labels: Sequence[str]) -> list[str]:
    """Fold labels as the import compares them: without spaces at their ends, accents nor case."""
    if not labels:
        return []
    unnested = (
        func.unnest(literal(list(labels), ARRAY(Text)))
        .table_valued("label", with_ordinality="rank")
        .render_derived()
    )
    trimmed = func.regexp_replace(unnested.c.label, ENDS, "", "g", type_=Text)
    return list(session.scalars(select(folded(trimmed)).order_by(unnested.c.rank)))


def read_folded_labels(session: Session) -> dict[str, str | None]:
    """Give the folded form of each label of the mapping, with the column it names.

    ``None`` for a column kept: the import looks a header up here, folded by ``fold_labels``.
    """
    rows = session.execute(select(ActualCostMappingLabel.folded, ActualCostMappingLabel.column))
    return dict(rows.all())


def _pointed_labels(write: ActualCostMappingWrite) -> list[tuple[str, str]]:
    """List the labels of a writing in the order of its body, each with its pointer."""
    pointed = [
        (json_pointer("columns", rank, "labels", place), label)
        for rank, column in enumerate(write.columns)
        for place, label in enumerate(column.labels)
    ]
    pointed.extend(
        (json_pointer("kept_columns", place), label)
        for place, label in enumerate(write.kept_columns)
    )
    return pointed


def _refuse_if_malformed(write: ActualCostMappingWrite) -> None:
    """Refuse (422) columns that are not the five of the import, once each, in their order."""
    if [column.column for column in write.columns] != list(SOURCE_COLUMNS):
        raise UnprocessableError(
            VALIDATION_FAILED, fields=(FieldError("/columns", VALIDATION_FAILED),)
        )
    too_many = [
        FieldError(
            json_pointer("columns", rank, "labels"),
            VALUE_TOO_LONG,
            {"max_length": READ_LABELS_LIMIT},
        )
        for rank, column in enumerate(write.columns)
        if len(column.labels) > READ_LABELS_LIMIT
    ]
    if len(write.kept_columns) > KEPT_COLUMNS_LIMIT:
        too_many.append(
            FieldError("/kept_columns", VALUE_TOO_LONG, {"max_length": KEPT_COLUMNS_LIMIT})
        )
    if too_many:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(too_many))


def _fold_without_doubles(session: Session, write: ActualCostMappingWrite) -> list[str]:
    """Fold the labels of a writing in the order of its body, or refuse (422) one that doubles.

    Each label that doubles an earlier one is refused, naming the first that bears its folded form.
    """
    pointed = _pointed_labels(write)
    forms = fold_labels(session, [label for _, label in pointed])
    first: dict[str, str] = {}
    doubles: list[FieldError] = []
    for (pointer, _), form in zip(pointed, forms, strict=True):
        if form in first:
            doubles.append(
                FieldError(pointer, DUPLICATE_COLUMN_LABEL, {"duplicate_of": first[form]})
            )
        else:
            first[form] = pointer
    if doubles:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(doubles))
    return forms


def _label_rows(write: ActualCostMappingWrite, forms: list[str]) -> list[dict[str, Any]]:
    """Give the rows of the labels of a writing, in the order of its body."""
    remaining = iter(forms)
    rows: list[dict[str, Any]] = [
        {"kind": "read", "column": column.column, "position": place, "label": label}
        for column in write.columns
        for place, label in enumerate(column.labels)
    ]
    rows.extend(
        {"kind": "kept", "column": None, "position": place, "label": label}
        for place, label in enumerate(write.kept_columns)
    )
    return [{"id": new_id(), "folded": next(remaining), **row} for row in rows]


def replace_actual_cost_mapping(
    session: Session, write: ActualCostMappingWrite, expected_lock_version: int, act: Act
) -> ActualCostMappingView:
    """Replace the whole mapping with the counter read, or refuse and write nothing.

    422 for columns that are not the five once each in their order, for more labels than a column
    admits, and for a label that doubles another once folded; 412 when the counter is stale, said
    by the write itself, which takes the row: the labels are replaced under it. The mapping is
    read back in the same transaction.

    The refusals come in turn, and a turn names every field in default of its kind: the shape of
    the columns first (the pointers of the others rest on it), then the sizes, then the doubles
    (folded by the database). A body in default of two kinds hears of the first; it is sent again.
    A malformed body is refused (422) before its counter is looked at (412). Refused (503) while
    the bootstrap has not written the row.
    """
    _refuse_if_malformed(write)
    rows = _label_rows(write, _fold_without_doubles(session, write))
    taken = session.execute(
        update(ActualCostMapping)
        .where(
            ActualCostMapping.id == SINGLE_ROW,
            ActualCostMapping.lock_version == expected_lock_version,
        )
        .values(
            lock_version=ActualCostMapping.lock_version + 1,
            updated_at=act.at,
            updated_by=act.author,
        )
        .returning(ActualCostMapping.id)
    ).first()
    if taken is None:
        current = session.execute(select(ActualCostMapping.lock_version)).scalar_one_or_none()
        if current is None:
            raise not_bootstrapped(ACTUAL_COST_MAPPING)
        raise PreconditionFailedError(STALE_LOCK_VERSION, {"expected_lock_version": current})
    session.execute(delete(ActualCostMappingLabel))
    if rows:
        session.execute(insert(ActualCostMappingLabel), rows)
    return read_actual_cost_mapping(session)
