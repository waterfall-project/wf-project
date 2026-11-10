# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a write of a line sends, judged, private to the module (WF-DEV-0020; EP-07, US-1490).

A role sent at the creation makes the line a labour line, whose category is its role's (computed:
another refused by ``COMPUTED_VALUE``) and which accepts no unit disbursement; any other line names
its category (``VALUE_REQUIRED``) and accepts neither role nor hours (``FIELD_NOT_ACCEPTED``) — a
category of labour without a role asks for one (``RESOURCE_ROLE_REQUIRED``). A modification writes
only what it sends, the kind of the line kept: a labour line does not lose its role
(``RESOURCE_ROLE_REQUIRED``), another does not take one. A category of the provision kind is the
risk's (``PROVISION_CATEGORY_RESERVED``, WF-RIS-0010); an object unknown or deactivated is refused
(``UNKNOWN_*``, ``INACTIVE_REFERENCE_OBJECT``); a figure below nought too (``VALUE_OUT_OF_RANGE``);
a line of a task started or completed does not leave a subproject that received actual costs
(``SUBPROJECT_HAS_ACTUAL_COSTS``, WF-PRJ-0050, never before EP-09). Every fault is named at once
(422 ``VALIDATION_FAILED``), on the field as the body names it.

A line absent its label takes the one composed of its task's and its role's, separated by an em dash
between two spaces, cut at 300 characters. Absent at the creation, the hours of a labour line and
the unit disbursement of another are nought, the payment delay nought.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.cost_settings.interface import category_labels
from waterfall.core.estimate.recalling import recalled
from waterfall.core.estimate.tables import LABEL_LENGTH
from waterfall.core.projects.interface import subproject_has_actual_costs, subproject_labels
from waterfall.core.resource_settings.interface import read_roles
from waterfall.platform.errors import FieldError, UnprocessableError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.cost_settings.interface import CategoryLabel
    from waterfall.core.estimate.tables import EstimateLine
    from waterfall.core.planning.interface import BearingTask
    from waterfall.core.resource_settings.interface import RoleView

VALIDATION_FAILED = "VALIDATION_FAILED"
FIELD_NOT_ACCEPTED = "FIELD_NOT_ACCEPTED"
VALUE_REQUIRED = "VALUE_REQUIRED"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
COMPUTED_VALUE = "COMPUTED_VALUE"
RESOURCE_ROLE_REQUIRED = "RESOURCE_ROLE_REQUIRED"
PROVISION_CATEGORY_RESERVED = "PROVISION_CATEGORY_RESERVED"
SUBPROJECT_HAS_ACTUAL_COSTS = "SUBPROJECT_HAS_ACTUAL_COSTS"
UNKNOWN_COST_CATEGORY = "UNKNOWN_COST_CATEGORY"
UNKNOWN_RESOURCE_ROLE = "UNKNOWN_RESOURCE_ROLE"
UNKNOWN_SUBPROJECT = "UNKNOWN_SUBPROJECT"
INACTIVE_REFERENCE_OBJECT = "INACTIVE_REFERENCE_OBJECT"
LABOR = "labor"
PROVISION = "provision"
NOT_STARTED = "not_started"
SEPARATOR = " — "
NOUGHT = Decimal(0)


@dataclass(frozen=True, slots=True)
class LineEntry:
    """What a write sends of a line (``EstimateLineWrite``, ``EstimateLineUpdate``).

    ``sent`` names the fields the body holds, null ones included; ``lock_version`` the counter a
    modification read.
    """

    label: str | None = None
    cost_category_id: UUID | None = None
    quantity: Decimal | None = None
    resource_role_id: UUID | None = None
    hours: Decimal | None = None
    unit_disbursement: Decimal | None = None
    payment_delay_days: int | None = None
    subproject_id: UUID | None = None
    sent: frozenset[str] = frozenset()
    lock_version: int | None = None

    def given(self, name: str) -> bool:
        """Tell whether the body holds a field, null or not."""
        return name in self.sent


@dataclass(frozen=True, slots=True)
class Draft:
    """A line as a write leaves it, judged: its figures, its role and its category as read."""

    label: str
    cost_category_id: UUID
    category: CategoryLabel
    resource_role_id: UUID | None
    role: RoleView | None
    quantity: Decimal
    hours: Decimal | None
    unit_disbursement: Decimal | None
    payment_delay_days: int
    subproject_id: UUID | None

    @property
    def labour(self) -> bool:
        """Tell whether the line is a labour line: it names a role."""
        return self.resource_role_id is not None


class _Faults:
    """The faults of a write, each on its field as the body names it."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.found: list[FieldError] = []

    def add(self, name: str, code: str, params: dict[str, object] | None = None) -> None:
        self.found.append(FieldError(f"{self.prefix}/{name}", code, params or {}))

    def raise_any(self) -> None:
        if self.found:
            raise UnprocessableError(VALIDATION_FAILED, fields=tuple(self.found))


def _not_negative[T: (Decimal, int)](faults: _Faults, name: str, value: T | None) -> None:
    if value is not None and value < 0:
        faults.add(name, VALUE_OUT_OF_RANGE, {"minimum": 0})


def _role(
    session: Session, faults: _Faults, role_id: UUID | None, *, changed: bool
) -> RoleView | None:
    """Read the role a line names; refuse it unknown, or deactivated when the write gives it."""
    if role_id is None:
        return None
    found = recalled(
        session, ("role", role_id), lambda: read_roles(session, [role_id], may_change=False)
    )
    if not found:
        faults.add("resource_role_id", UNKNOWN_RESOURCE_ROLE)
        return None
    if changed and not found[0].is_active:
        faults.add("resource_role_id", INACTIVE_REFERENCE_OBJECT)
    return found[0]


def _category(
    session: Session, faults: _Faults, category_id: UUID | None, *, changed: bool
) -> CategoryLabel | None:
    """Read the category a line names; refuse it unknown, the risk's, or deactivated if given."""
    if category_id is None:
        return None
    labels = recalled(
        session, ("category", category_id), lambda: category_labels(session, [category_id])
    )
    category = labels.get(category_id)
    if category is None:
        faults.add("cost_category_id", UNKNOWN_COST_CATEGORY)
    elif category.cost_type_kind == PROVISION:
        faults.add("cost_category_id", PROVISION_CATEGORY_RESERVED)
    elif changed and not (category.is_active and category.cost_type_is_active):
        faults.add("cost_category_id", INACTIVE_REFERENCE_OBJECT)
    return category


def _subproject(
    session: Session,
    faults: _Faults,
    held: tuple[UUID, BearingTask, UUID | None],
    entry: LineEntry,
    *,
    locking: bool = True,
) -> UUID | None:
    """Judge the subproject a write leaves the line in, of its project (WF-PRJ-0050).

    ``held`` is the project, the task that bears the line and its subproject before the write. The
    subproject named is read ``FOR KEY SHARE`` (#2616): one a concurrent deletion took away is
    unknown, as one that never was. The analysis of an import writes nothing, in a transaction
    that cannot lock: it reads them as they are (``locking`` false).
    """
    project_id, bearer, before = held
    if not entry.given("subproject_id"):
        return before
    after = entry.subproject_id
    if after is not None and not recalled(
        session,
        ("subproject", project_id, after),
        lambda: subproject_labels(session, project_id, [after], held=locking),
    ):
        faults.add("subproject_id", UNKNOWN_SUBPROJECT)
    if (
        before is not None
        and after != before
        and bearer.progress != NOT_STARTED
        and subproject_has_actual_costs(session, before)
    ):
        label = subproject_labels(session, project_id, [before]).get(before, "")
        named: dict[str, object] = {"subproject": {"subproject_id": str(before), "label": label}}
        faults.add("subproject_id", SUBPROJECT_HAS_ACTUAL_COSTS, named)
    return after


def _figure(
    faults: _Faults, entry: LineEntry, name: str, held: tuple[Decimal | None, bool]
) -> Decimal | None:
    """Give a figure a line accepts, as the write leaves it; refuse it sent where not accepted.

    ``held`` is the figure before the write — none at a creation — and whether the line accepts it.
    """
    before, accepted = held
    value: Decimal | None = getattr(entry, name)
    if not accepted:
        if entry.given(name) and value is not None:
            faults.add(name, FIELD_NOT_ACCEPTED)
        return None
    if not entry.given(name):
        return NOUGHT if before is None else before
    if value is None:
        faults.add(name, VALUE_REQUIRED)
    _not_negative(faults, name, value)
    return value


def _kind(
    session: Session, faults: _Faults, entry: LineEntry, current: EstimateLine | None
) -> tuple[UUID | None, RoleView | None, UUID | None, CategoryLabel | None]:
    """Judge the role and the category a write leaves a line with: its kind, and their objects."""
    creating = current is None
    role_id = entry.resource_role_id if creating else current.resource_role_id
    if current is not None and entry.given("resource_role_id"):
        sent = entry.resource_role_id
        if sent is None and role_id is not None:
            faults.add("resource_role_id", RESOURCE_ROLE_REQUIRED)
        elif sent is not None and role_id is None:
            faults.add("resource_role_id", FIELD_NOT_ACCEPTED)
        elif sent is not None:
            role_id = sent
    changed = current is None or role_id != current.resource_role_id
    role = _role(session, faults, role_id, changed=changed)
    sent_category = entry.cost_category_id if entry.given("cost_category_id") else None
    category_id = None if current is None else current.cost_category_id
    if role_id is not None:
        category_id = role.cost_category_id if role is not None else sent_category
        if role is not None and sent_category is not None and sent_category != category_id:
            faults.add("cost_category_id", COMPUTED_VALUE)
    elif sent_category is not None:
        category_id = sent_category
    elif creating:
        faults.add("cost_category_id", VALUE_REQUIRED)
    changed = current is None or category_id != current.cost_category_id
    category = _category(session, faults, category_id, changed=changed)
    if role_id is None and category is not None and category.cost_type_kind == LABOR:
        faults.add("resource_role_id", RESOURCE_ROLE_REQUIRED)
    return role_id, role, category_id, category


def _scalars(
    faults: _Faults, entry: LineEntry, current: EstimateLine | None
) -> tuple[Decimal, int]:
    """Judge the quantity and the payment delay a write leaves a line with."""
    quantity = entry.quantity if entry.given("quantity") else _held(current, "quantity")
    if quantity is None:
        faults.add("quantity", VALUE_REQUIRED)
    _not_negative(faults, "quantity", quantity)
    delay = entry.payment_delay_days if entry.given("payment_delay_days") else _delay(current)
    if delay is None:
        faults.add("payment_delay_days", VALUE_REQUIRED)
    _not_negative(faults, "payment_delay_days", delay)
    if entry.given("label") and entry.label is None:
        faults.add("label", VALUE_REQUIRED)
    return quantity or NOUGHT, delay or 0


def judged_line(
    session: Session,
    held: tuple[UUID, BearingTask],
    entry: LineEntry,
    current: EstimateLine | None,
    *,
    locking: bool = True,
) -> Draft:
    """Judge what a write sends of a line, created (``current`` none) or changed; or refuse (422).

    ``held`` is the project and the task that bears the line. ``locking`` false for the analysis
    of an import, which cannot lock what it reads.
    """
    project_id, bearer = held
    faults = _Faults("/estimate_line" if current is None else "")
    role_id, role, category_id, category = _kind(session, faults, entry, current)
    labour = role_id is not None
    hours = _figure(faults, entry, "hours", (None if current is None else current.hours, labour))
    before_disbursement = None if current is None else current.unit_disbursement
    disbursement = _figure(faults, entry, "unit_disbursement", (before_disbursement, not labour))
    quantity, delay = _scalars(faults, entry, current)
    before_subproject = None if current is None else current.subproject_id
    subproject = _subproject(
        session, faults, (project_id, bearer, before_subproject), entry, locking=locking
    )
    faults.raise_any()
    if category is None or category_id is None:
        msg = "a line judged names its category"
        raise RuntimeError(msg)
    kept = _composed(bearer.label, role) if current is None else current.label
    return Draft(
        label=entry.label if entry.given("label") and entry.label is not None else kept,
        cost_category_id=category_id,
        category=category,
        resource_role_id=role_id,
        role=role,
        quantity=quantity,
        hours=hours,
        unit_disbursement=disbursement,
        payment_delay_days=delay,
        subproject_id=subproject,
    )


def _held(current: EstimateLine | None, name: str) -> Decimal:
    """Give a figure of the line before the write, nought at a creation."""
    value: Decimal | None = None if current is None else getattr(current, name)
    return NOUGHT if value is None else value


def _delay(current: EstimateLine | None) -> int:
    """Give the payment delay of the line before the write, nought at a creation."""
    return 0 if current is None else current.payment_delay_days


def _composed(task_label: str, role: RoleView | None) -> str:
    """Compose the label of a line: its task's, and its role's after an em dash (WF-DEV-0020)."""
    label = task_label if role is None else f"{task_label}{SEPARATOR}{role.label}"
    return label[:LABEL_LENGTH]
