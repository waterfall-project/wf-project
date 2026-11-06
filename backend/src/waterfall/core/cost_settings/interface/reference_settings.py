# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The settings the installation shares.

Its currency and name, the matrix of risks, the thresholds of the indices and the delay
between two reviews (WF-REF-0140, 0160, 0170, 0180; WF-EXP-0020): a single row, read whole,
written field by field under the permission of each, with the counter they share — for the matrix
and the thresholds, through ``risk_settings`` and ``indicator_settings``, which hold their rules
and judge them before this module writes them; the database refuses besides what would slip by.

The bootstrap writes the row with the currency and the name it is given and the values the
installation is delivered with; nothing writes the currency afterwards (WF-REF-0140).
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from waterfall.core.cost_settings.tables import LABEL_LENGTH, SINGLE_ROW, ReferenceSetting
from waterfall.core.users.interface import Author, read_author
from waterfall.platform.errors import FieldError, PreconditionFailedError, UnavailableError
from waterfall.platform.installation import COMPONENT_UNAVAILABLE
from waterfall.platform.logs import get_logger

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
VALIDATION_FAILED = "VALIDATION_FAILED"
VALUE_REQUIRED = "VALUE_REQUIRED"
VALUE_TOO_LONG = "VALUE_TOO_LONG"
# The first version of the settings, written by the bootstrap.
FIRST_VERSION = 1
# The permission each field of a writing asks for, in the order of the contract
# (``ReferenceSettingsWrite``): the name beside the currency, the matrix, the thresholds and the
# delay, each under the function it belongs to (WF-ADM-0100).
FIELD_PERMISSIONS: dict[str, str] = {
    "company_name": "cost_settings.write",
    "risk_matrix": "risk_settings.write",
    "index_thresholds": "indicator_settings.write",
    "max_weeks_between_reviews": "indicator_settings.write",
}
NOT_BLANK = re.compile(r"\S")

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RiskMatrix:
    """The three bounds of each axis, from the lowest, and the zones of the sixteen cells.

    The bounds are fractions (``0.25``); the zones are ranked by level of probability, then of
    severity, each from the lowest (contract, ``RiskMatrixSettings``).
    """

    probability_bounds: tuple[Decimal, ...]
    severity_bounds: tuple[Decimal, ...]
    zones: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IndexThresholds:
    """The thresholds of watch and of alert of the index of cost and of the index of schedule."""

    cost_watch: Decimal
    cost_alert: Decimal
    schedule_watch: Decimal
    schedule_alert: Decimal


@dataclass(frozen=True, slots=True)
class SettingsChange:
    """What a writing changes: a field left ``None`` stays as it is."""

    company_name: str | None = None
    risk_matrix: RiskMatrix | None = None
    index_thresholds: IndexThresholds | None = None
    max_weeks_between_reviews: int | None = None


@dataclass(frozen=True, slots=True)
class ReferenceSettingsView:
    """The settings as they are read, with their audit and the counter they share."""

    currency_code: str
    company_name: str
    risk_matrix: RiskMatrix
    index_thresholds: IndexThresholds
    max_weeks_between_reviews: int
    lock_version: int
    created_at: datetime
    created_by: Author | None
    updated_at: datetime
    updated_by: Author | None


# What a new installation is delivered with (WF-EXP-0020): the bounds at 25, 50 and 75 % of
# probability and at 1, 5 and 10 % of severity, the zones of the example ``reference_settings`` of
# the contract, the thresholds at 0.9 and 0.8 for each index, six weeks between two reviews.
DELIVERED_MATRIX = RiskMatrix(
    probability_bounds=(Decimal("0.25"), Decimal("0.5"), Decimal("0.75")),
    severity_bounds=(Decimal("0.01"), Decimal("0.05"), Decimal("0.1")),
    zones=(
        *("nominal", "nominal", "nominal", "watch"),
        *("nominal", "nominal", "watch", "watch"),
        *("nominal", "watch", "watch", "alert"),
        *("watch", "watch", "alert", "alert"),
    ),
)
DELIVERED_THRESHOLDS = IndexThresholds(
    cost_watch=Decimal("0.9"),
    cost_alert=Decimal("0.8"),
    schedule_watch=Decimal("0.9"),
    schedule_alert=Decimal("0.8"),
)
DELIVERED_WEEKS = 6


def company_name_faults(name: str) -> list[FieldError]:
    """Refuse a name that is empty, longer than 200 characters, or made of blanks (WF-EXP-0020)."""
    pointer = "/company_name"
    if not name:
        return [FieldError(pointer, VALUE_REQUIRED)]
    if len(name) > LABEL_LENGTH:
        return [FieldError(pointer, VALUE_TOO_LONG, {"max_length": LABEL_LENGTH})]
    if NOT_BLANK.search(name) is None:
        return [FieldError(pointer, VALIDATION_FAILED)]
    return []


def _values(change: SettingsChange) -> dict[str, Any]:
    """Give the columns a change writes, the fields it leaves out left alone."""
    values: dict[str, Any] = {}
    if change.company_name is not None:
        values["company_name"] = change.company_name
    if (matrix := change.risk_matrix) is not None:
        for rank, bound in enumerate(matrix.probability_bounds, start=1):
            values[f"probability_bound_{rank}"] = bound
        for rank, bound in enumerate(matrix.severity_bounds, start=1):
            values[f"severity_bound_{rank}"] = bound
        values["risk_zones"] = list(matrix.zones)
    if (thresholds := change.index_thresholds) is not None:
        values["cost_watch"] = thresholds.cost_watch
        values["cost_alert"] = thresholds.cost_alert
        values["schedule_watch"] = thresholds.schedule_watch
        values["schedule_alert"] = thresholds.schedule_alert
    if change.max_weeks_between_reviews is not None:
        values["max_weeks_between_reviews"] = change.max_weeks_between_reviews
    return values


def install_reference_settings(
    session: Session, currency_code: str, company_name: str, act: Act
) -> bool:
    """Write the settings delivered with the currency and the name given, unless they are there.

    Tell whether they were written: the bootstrap writes them once, at their first version, and a
    later run, whatever its currency and name, leaves them as they are.
    """
    change = SettingsChange(
        company_name=company_name,
        risk_matrix=DELIVERED_MATRIX,
        index_thresholds=DELIVERED_THRESHOLDS,
        max_weeks_between_reviews=DELIVERED_WEEKS,
    )
    written = session.execute(
        insert(ReferenceSetting)
        .values(
            id=SINGLE_ROW,
            currency_code=currency_code,
            **_values(change),
            lock_version=FIRST_VERSION,
            created_at=act.at,
            created_by=act.author,
            updated_at=act.at,
            updated_by=act.author,
        )
        .on_conflict_do_nothing()
        .returning(ReferenceSetting.id)
    ).first()
    return written is not None


def reference_settings_installed(session: Session) -> bool:
    """Tell whether the bootstrap wrote the settings: the loader of the witness sets them then."""
    return session.get(ReferenceSetting, SINGLE_ROW) is not None


def _not_bootstrapped() -> UnavailableError:
    logger.warning("reference_settings.not_bootstrapped")
    return UnavailableError(COMPONENT_UNAVAILABLE, {"component": "database"})


def read_reference_settings(session: Session) -> ReferenceSettingsView:
    """Read the settings; refused while the bootstrap has not written them (503).

    An installation without them is not ready to serve, as one without its row (``installation``):
    never served with values nobody chose.
    """
    row = session.scalars(
        select(ReferenceSetting)
        .where(ReferenceSetting.id == SINGLE_ROW)
        .execution_options(populate_existing=True)
    ).one_or_none()
    if row is None:
        raise _not_bootstrapped()
    return ReferenceSettingsView(
        currency_code=row.currency_code,
        company_name=row.company_name,
        risk_matrix=RiskMatrix(
            (row.probability_bound_1, row.probability_bound_2, row.probability_bound_3),
            (row.severity_bound_1, row.severity_bound_2, row.severity_bound_3),
            tuple(row.risk_zones),
        ),
        index_thresholds=IndexThresholds(
            row.cost_watch, row.cost_alert, row.schedule_watch, row.schedule_alert
        ),
        max_weeks_between_reviews=row.max_weeks_between_reviews,
        lock_version=row.lock_version,
        created_at=row.created_at,
        created_by=read_author(session, row.created_by),
        updated_at=row.updated_at,
        updated_by=read_author(session, row.updated_by),
    )


def write_reference_settings(
    session: Session, change: SettingsChange, expected_lock_version: int, act: Act
) -> ReferenceSettingsView:
    """Write the fields a change carries with the counter read, or refuse and write nothing.

    The values are judged before, each by the module that holds its rule — the name here
    (``company_name_faults``), the matrix by ``risk_settings``, the thresholds and the delay by
    ``indicator_settings`` —; the permission of each field by whoever calls. 412 when the counter
    is stale, said by the write itself, which takes the row. A change that carries no field writes
    nothing — neither the counter nor the audit —: it asks for no permission, and would otherwise
    let a session that may write nothing make stale the counter every other one read (WF-ADM-0100);
    the settings are given as they are, unless the counter is stale (412) all the same. The
    settings are read back in the same transaction.
    """
    values = _values(change)
    if not values:
        held = read_reference_settings(session)
        if held.lock_version != expected_lock_version:
            raise PreconditionFailedError(
                STALE_LOCK_VERSION, {"expected_lock_version": held.lock_version}
            )
        return held
    taken = session.execute(
        update(ReferenceSetting)
        .where(
            ReferenceSetting.id == SINGLE_ROW,
            ReferenceSetting.lock_version == expected_lock_version,
        )
        .values(
            **values,
            lock_version=ReferenceSetting.lock_version + 1,
            updated_at=act.at,
            updated_by=act.author,
        )
        .returning(ReferenceSetting.id)
    ).first()
    if taken is None:
        current = session.execute(select(ReferenceSetting.lock_version)).scalar_one_or_none()
        if current is None:
            raise _not_bootstrapped()
        raise PreconditionFailedError(STALE_LOCK_VERSION, {"expected_lock_version": current})
    return read_reference_settings(session)
