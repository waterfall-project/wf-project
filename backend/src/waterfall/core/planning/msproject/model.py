# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A planning of MS Project in memory, as its XML file (MSPDI) carries it, without a database.

What the reader gives and the writer takes (EP-06, "Le format MS Project"): the project, its unit
constants and its calendars, its tasks in the order of the file — the tree by their outline
level —, their links. The values stay those of the file: a duration as its ``xsd:duration``, a
lag in tenths of a minute or of a percent, a date at the hour of the day MS Project placed it;
converting them into the units, the work instants and the calendars of Waterfall is the
analysis's (US-1430/L3), which knows the constants of the installation. What the file carries
besides, and that no import reads, is counted by kind (``Ignored``), as ``ImportReport.ignored``
names it (WF-INTF-0040).

The dates are naive on purpose: MSPDI writes the wall clock of the project, in no time zone, and
a planning instant is a day and its hours, never a timestamp.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from datetime import datetime, time, timedelta
    from uuid import UUID

    from waterfall.core.planning.scheduling import DurationUnit, LagUnit, LinkType

type ConstraintType = Literal[
    "as_soon_as_possible",
    "as_late_as_possible",
    "must_start_on",
    "must_finish_on",
    "start_no_earlier_than",
    "start_no_later_than",
    "finish_no_earlier_than",
    "finish_no_later_than",
]
"""The constraint of a task, ``ConstraintType`` 0 to 7 in the order of the schema."""

CONSTRAINT_TYPES: tuple[ConstraintType, ...] = (
    "as_soon_as_possible",
    "as_late_as_possible",
    "must_start_on",
    "must_finish_on",
    "start_no_earlier_than",
    "start_no_later_than",
    "finish_no_earlier_than",
    "finish_no_later_than",
)
"""The constraints by their code in the file: the code is the position."""

DATE_CONSTRAINTS: frozenset[ConstraintType] = frozenset(CONSTRAINT_TYPES[2:])
"""The constraints that carry a date: Waterfall imports such a task manual, and names it ignored."""

LINK_TYPES: tuple[LinkType, ...] = (
    "finish_to_finish",
    "finish_to_start",
    "start_to_finish",
    "start_to_start",
)
"""The types of a link by their code in the file (``PredecessorLink/Type``): the position."""

FORMAT_UNITS: dict[int, LagUnit] = {
    3: "min",
    4: "emin",
    5: "h",
    6: "eh",
    7: "d",
    8: "ed",
    9: "w",
    10: "ew",
    11: "mo",
    12: "emo",
    19: "percent",
    # Waterfall knows a single percent, of the predecessor's duration in its own kind of time
    # (WF-PLA-0030): an elapsed percent reads as it.
    20: "percent",
}
"""The units of the formats of the schema; the estimated ones are the same plus ``ESTIMATED``."""

ESTIMATED = 32
"""What an estimated format adds to its unit's code: ``35`` is an estimated minute, ``3`` + 32."""

NO_FORMAT: frozenset[int] = frozenset({21, 53})
"""The formats that say no unit: a duration without one, estimated or not."""

FORMAT_CODES: dict[LagUnit, int] = {
    "min": 3,
    "emin": 4,
    "h": 5,
    "eh": 6,
    "d": 7,
    "ed": 8,
    "w": 9,
    "ew": 10,
    "mo": 11,
    "emo": 12,
    "percent": 19,
}
"""The code the writer gives a unit: never estimated, and the percent of work."""

LINEAGE_ALIAS = "Waterfall.lineage"
"""The alias of the custom text field the lineage of a task travels in, as the export writes it.

The schema of MS Project 2013 has no ``GUID`` of a task: a file that wrote one would not be valid
(WF-QUA-0080), so the export writes the lineage in a custom field; the reader takes a ``GUID``
too, which a later MS Project writes.
"""

LINEAGE_FIELD_ID = "188743731"
"""The field the export writes the lineage in: ``Text1`` of a task, by its identifier."""

LINEAGE_FIELD_NAME = "Text1"
"""The name MS Project gives that field."""

type IgnoredKind = Literal[
    "resources", "calendars", "progress", "costs", "custom_fields", "date_constraints"
]
"""What an import of MS Project never reads, by the kinds of ``ImportIgnoredKind``."""


@dataclass(frozen=True, slots=True)
class WorkingDay:
    """A day of the week of a calendar, ``DayType`` 1 for Sunday to 7 for Saturday."""

    day_type: int
    working: bool
    times: tuple[tuple[time, time], ...] = ()


@dataclass(frozen=True, slots=True)
class MsCalendar:
    """A calendar of the file: its days, those it does not list being its base calendar's."""

    uid: int
    name: str | None
    is_base: bool
    base_uid: int | None
    days: tuple[WorkingDay, ...] = ()


@dataclass(frozen=True, slots=True)
class PredecessorLink:
    """A link of a task to its predecessor, its lag in the unit of its format.

    ``lag`` is ``LinkLag`` as the file carries it: tenths of a minute, of work or elapsed, or
    tenths of a percent; ``lag_unit`` is its format, ``None`` when the file says none.
    """

    predecessor_uid: int
    link_type: LinkType
    lag: int = 0
    lag_unit: LagUnit | None = None


@dataclass(frozen=True, slots=True)
class MsTask:
    """A task of the file, its place in the tree being its outline level and its rank.

    ``duration`` is the file's, hours of work or elapsed as its unit says; ``calendar_uid`` is
    ``None`` for a task on the calendar of the project; ``lineage`` is the lineage the export
    wrote, ``None`` for a task created in MS Project.
    """

    uid: int
    name: str
    outline_level: int
    manual: bool = False
    duration: timedelta | None = None
    duration_unit: DurationUnit | None = None
    start: datetime | None = None
    finish: datetime | None = None
    milestone: bool = False
    constraint: ConstraintType = "as_soon_as_possible"
    calendar_uid: int | None = None
    constraint_date: datetime | None = None
    notes: str | None = None
    lineage: UUID | None = None
    predecessors: tuple[PredecessorLink, ...] = ()


@dataclass(frozen=True, slots=True)
class MsProject:
    """A planning of MS Project: its start, its unit constants, its calendars and its tasks.

    The constants are those of the file, in minutes per day and per week and days per month,
    ``None`` when the file does not say them; ``calendar_uid`` is the calendar of the project.
    """

    start: datetime | None
    name: str | None = None
    currency_code: str | None = None
    calendar_uid: int | None = None
    minutes_per_day: int | None = None
    minutes_per_week: int | None = None
    days_per_month: int | None = None
    calendars: tuple[MsCalendar, ...] = ()
    tasks: tuple[MsTask, ...] = ()

    def parents(self) -> dict[int, int | None]:
        """Return the parent of each task by its unique identifier, ``None`` for a root.

        The parent is the nearest task before it of a lower outline level, as MS Project builds its
        tree; the reader has checked that no level skips one.
        """
        parents: dict[int, int | None] = {}
        ancestors: list[MsTask] = []
        for task in self.tasks:
            del ancestors[task.outline_level - 1 :]
            parents[task.uid] = ancestors[-1].uid if ancestors else None
            ancestors.append(task)
        return parents


@dataclass(frozen=True, slots=True)
class Ignored:
    """A kind of what the file carries and no import reads, how many, and their names if any."""

    kind: IgnoredKind
    count: int
    labels: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReadProject:
    """What the reader gives: the planning, and what it carried besides, by kind."""

    project: MsProject
    ignored: tuple[Ignored, ...] = ()


class UnreadableProjectError(ValueError):
    """The file is not a planning of MSPDI the reader can read: the format refuses it.

    ``element`` names what is wrong for the journals; the format turns the refusal into its code
    (``FILE_FORMAT_UNREADABLE``), never this text.
    """

    def __init__(self, element: str) -> None:
        super().__init__(element)
        self.element = element
