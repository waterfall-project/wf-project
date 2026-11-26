# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The projects of the reference set (WF-QUA-0040; US-2950), drawn from the seed one by one.

The witness holds twelve projects — PRJ-001, the project of a thousand tasks, PRJ-002 and the ten
of the slice of the portfolio —; the set draws the others, until the portfolio holds the number
asked (three hundred by default, six hundred for WF-DAT-0050): table 13 counts the projects "in the
portfolio", in progress and in pricing, the witness's among them (``numbers_of``). The projects
that are closed — lost, abandoned, completed — are drawn along the same numbers, in addition to
that count. Each is described as a project of that slice
(``portfolio_slice.Project``, every write in the form of the contract that carries it), and is
written as those are (``portfolio.write_project``): a project of the set is a project of the
portfolio, of the same shapes, drawn rather than written by hand.

What a project holds is drawn from the seed, its number and nothing else (``Draw``), so that the
``n``-th project is the same whatever the number asked:

- its life, one of six: in pricing, its first revision open (20 %) or its offer marked (10 %); lost
  after its offer (5 %); abandoned, its revision with it (5 %); in progress, from one to six monthly
  reviews marked after the reference, each on the first Monday of a month, the last revision open
  (55 %); completed, every task finished, closed by the review after its last task (5 %);
- three to eight tasks, in manual mode, one after the other from four weeks after its creation, each
  of two to four weeks; one line of labour on each — a role drawn, its category, ten to a hundred
  and sixty hours — and, on one task in two, a line of disbursement;
- for a project that has run: none to two risks, declared the days after the reference, each with
  its own estimate, a disbursement, and reviewed a week after the first review for a project
  reviewed twice; an import of actual costs the week before each review, of one to three lines;
- its manager, an account of the set; a code, ``REF-nnnn``, and a label composed of a kind of work
  and a fictitious site, which designate no real project; a fictitious client, or none.

Every instant falls between January 2024 and the end of October 2026, and every task in the years
the grid rates (2024 to 2026): no line lacks a rate.

Depth is not drawn (US-2950, L1). Table 13 gives, per project, up to a thousand tasks, fifty
contributors and ten subprojects; a drawn project holds three to eight tasks, a manager as its only
contributor, and no subproject. The thousand tasks are PRJ-001's alone, which the witness carries,
and L2 of the story gives it its thousand — as the criterion of the story says: the others are the
breadth of the portfolio, not its depth. What it implies for the measurements (US-2970): they see
three hundred projects of a dozen nodes at most, and one project of a thousand tasks; the cost of a
calculation on a project with fifty contributors or ten subprojects is not measured by this set.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from itertools import count
from typing import TYPE_CHECKING

from waterfall.witness.portfolio_slice import Project
from waterfall.witness.reference_draw import Draw, identifier

if TYPE_CHECKING:
    from uuid import UUID

    from waterfall.witness.reference_draw import Base, Reference

# The Monday the first project of the set may be created on, and the weeks after it the last may.
ORIGIN = date(2024, 1, 1)
CREATED_WITHIN = 95
# The lives a project is drawn among, each with its weight in a hundred.
PRICING, OFFERED, LOST, ABANDONED, IN_PROGRESS, COMPLETED = (
    "pricing",
    "offered",
    "lost",
    "abandoned",
    "in_progress",
    "completed",
)
LIVES = ((PRICING, 20), (OFFERED, 10), (LOST, 5), (ABANDONED, 5), (IN_PROGRESS, 55), (COMPLETED, 5))
RUN = frozenset({IN_PROGRESS, COMPLETED})
CLOSED = frozenset({LOST, ABANDONED, COMPLETED})
PHASES = (
    "Études",
    "Approvisionnement",
    "Fabrication",
    "Montage",
    "Essais",
    "Mise en service",
    "Réception",
    "Documentation",
)
WORKS = (
    "Modernisation de la ligne",
    "Extension de l'atelier",
    "Rénovation du poste",
    "Automatisation du quai",
    "Remplacement des convoyeurs",
    "Banc d'essais",
    "Réseau de distribution",
    "Mise en conformité du site",
)
# Sites that name no place: stars.
SITES = (
    "Altaïr",
    "Bételgeuse",
    "Capella",
    "Deneb",
    "Electra",
    "Fomalhaut",
    "Gemma",
    "Hadar",
    "Izar",
    "Mira",
    "Naos",
    "Rigel",
    "Sirius",
    "Thuban",
    "Véga",
    "Wezen",
)
RISKS = (
    "Retard d'approvisionnement",
    "Indisponibilité d'un poste d'essais",
    "Non-conformité d'un lot",
    "Intempéries sur le chantier",
)
MONTHS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)
LOST_REASON = "Offre concurrente retenue"
ABANDONED_REASON = "Projet suspendu par le client"
OPENED_AFTER, REOPENED_AFTER, CLOSED_AFTER = (
    timedelta(minutes=30),
    timedelta(hours=1),
    timedelta(minutes=1),
)
WEEK = timedelta(weeks=1)
# The reviews after which a risk is reviewed: in the revision that follows the first.
REVIEWED_RISK = 2
PLATFORM = {"kind": "platform"}


def code_of(number: int) -> str:
    """Give the code of the ``number``-th project the set draws."""
    return f"REF-{number:04d}"


def project_id_of(number: int) -> UUID:
    """Give the identifier of the ``number``-th project the set draws."""
    return identifier("project", number)


def manager_of(number: int, reference: Reference) -> UUID:
    """Give the account of the set that manages the ``number``-th project."""
    return Draw("manager", number).choice(reference.accounts).user_id


def life_of(number: int) -> str:
    """Give the life of the ``number``-th project the set draws: its number and the seed alone."""
    weight = Draw("project", number).below(100)
    return next(life for life, bound in _bounds() if weight < bound)


def numbers_of(portfolio: int) -> list[int]:
    """Give the numbers of the projects the set draws for ``portfolio`` projects in the portfolio.

    The portfolio holds the projects in pricing and in progress: the numbers run from one to the
    ``portfolio``-th of them, the projects closed on the way — lost, abandoned, completed —
    counted apart. The ``n``-th project is the same whatever ``portfolio``: a larger one prolongs
    the numbers of a smaller.
    """
    found: list[int] = []
    held = 0
    for number in count(1):
        if held >= portfolio:
            break
        found.append(number)
        held += life_of(number) not in CLOSED
    return found


def draw_project(number: int, base: Base, reference: Reference) -> Project:
    """Draw the ``number``-th project of the set, from the seed and its number alone."""
    return _Drawing(number, base, reference).project()


def _at(day: date, hour: int = 9) -> datetime:
    return datetime.combine(day, time(hour), tzinfo=UTC)


def _instant(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class _Task:
    node_id: UUID
    label: str
    start: date
    finish: date


class _Drawing:
    """The draw of one project: its life, then what that life writes, in the form of the slice."""

    def __init__(self, number: int, base: Base, reference: Reference) -> None:
        self.number, self.base, self.reference = number, base, reference
        self.draw = Draw("project", number)
        # The first number of the draw is the life's: ``life_of`` draws it again.
        self.draw.below(100)
        self.life = life_of(number)
        self.created = _at(ORIGIN + WEEK * self.draw.between(0, CREATED_WITHIN))
        self.tasks = self._tasks()
        # The instant the reference is designated, for a project that runs, and its reviews after.
        self.designated = self.created + 3 * WEEK
        self.reviews = self._reviews()

    def project(self) -> Project:
        ran = self.life in RUN
        return Project.model_validate(
            {
                "project_id": str(project_id_of(self.number)),
                "created_at": _instant(self.created),
                "project": {
                    "label": f"{self.draw.choice(WORKS)} {self.draw.choice(SITES)} {self.number}",
                    "description": None,
                    "client": self._client(),
                    "code": code_of(self.number),
                },
                "inflation_rate": self.draw.choice(("0", "0.01", "0.02")),
                "win_probability": f"0.{self.draw.between(1, 9)}",
                "reference_revision_id": str(self._revision_id(1)) if ran else None,
                "transitions": self._transitions(),
                "revisions": self._revisions(),
                "tasks": [
                    self._task(each, last=each is self.tasks[-1], ran=ran) for each in self.tasks
                ],
                "lines": self._lines(),
                "risks": self._risks() if ran else [],
                "imports": self._imports() if ran else [],
            }
        )

    def _client(self) -> str | None:
        drawn = self.draw.between(0, 40)
        return None if drawn == 0 else f"Client fictif {drawn:02d}"

    def _tasks(self) -> list[_Task]:
        found: list[_Task] = []
        start = self.created.date() + 4 * WEEK
        for rank in range(1, self.draw.between(3, len(PHASES)) + 1):
            weeks = self.draw.between(2, 4)
            finish = start + weeks * WEEK - timedelta(days=3)
            found.append(
                _Task(identifier("task", self.number, rank), PHASES[rank - 1], start, finish)
            )
            start += (weeks + 1) * WEEK
        return found

    def _reviews(self) -> int:
        """Give how many monthly reviews the project marks after its reference.

        A completed project, until the review after its last task finishes, which closes it.
        """
        if self.life == COMPLETED:
            last = self.tasks[-1].finish
            return next(rank for rank in count(1) if self.review(rank).date() > last)
        return self.draw.between(1, 6) if self.life == IN_PROGRESS else 0

    def review(self, rank: int) -> datetime:
        """Give the instant of the ``rank``-th review: a month's first Monday after the reference.

        One review a month, each in a month of its own, whose name it bears.
        """
        months = self.designated.year * 12 + self.designated.month - 1 + rank
        first = date(months // 12, months % 12 + 1, 1)
        return _at(first + timedelta(days=-first.weekday() % 7))

    def _revision_id(self, rank: int) -> UUID:
        return identifier("revision", self.number, rank)

    def _revisions(self) -> list[dict[str, object]]:
        first: dict[str, object] = {
            "revision_id": str(self._revision_id(1)),
            "opened_at": _instant(self.created + OPENED_AFTER),
            "create": {"description": None},
            "marked_at": None,
            "mark": None,
            "abandoned_at": None,
        }
        if self.life == ABANDONED:
            first["abandoned_at"] = _instant(self.created + 6 * WEEK)
        elif self.life != PRICING:
            first["marked_at"] = _instant(self.created + 2 * WEEK)
            first["mark"] = {"action": "mark", "version_name": "Offre"}
        found = [first]
        reviews = self.reviews
        opened = self.designated
        for rank in range(2, reviews + 3 if self.life == IN_PROGRESS else reviews + 2):
            marked = self.review(rank - 1)
            closing = self.life == COMPLETED and rank == reviews + 1
            name = "Clôture" if closing else f"Revue de {MONTHS[marked.month - 1]} {marked.year}"
            last_open = self.life == IN_PROGRESS and rank == reviews + 2
            found.append(
                {
                    "revision_id": str(self._revision_id(rank)),
                    "opened_at": _instant(opened + REOPENED_AFTER),
                    "create": {"description": None},
                    "marked_at": None if last_open else _instant(marked),
                    "mark": None if last_open else {"action": "mark", "version_name": name},
                    "abandoned_at": None,
                }
            )
            opened = marked
        return found

    def _transitions(self) -> list[dict[str, object]]:
        def moved(
            left: str | None, taken: str, at: datetime, reason: str | None = None
        ) -> dict[str, object]:
            return {
                "from_state": left,
                "to_state": taken,
                "occurred_at": _instant(at),
                "actor": PLATFORM,
                "reason": reason,
            }

        found = [
            moved(None, "created", self.created),
            moved("created", "pricing", self.created + OPENED_AFTER),
        ]
        if self.life == LOST:
            found.append(moved("pricing", LOST, self.created + 6 * WEEK, LOST_REASON))
        elif self.life == ABANDONED:
            found.append(moved("pricing", ABANDONED, self.created + 6 * WEEK, ABANDONED_REASON))
        elif self.life in RUN:
            found.append(moved("pricing", IN_PROGRESS, self.designated))
        if self.life == COMPLETED:
            closed = self.review(self.reviews) + CLOSED_AFTER
            found.append(moved(IN_PROGRESS, COMPLETED, closed))
        return found

    def _task(self, task: _Task, *, last: bool, ran: bool) -> dict[str, object]:
        """Describe a task; a project that ran has begun those that start before its last review.

        Finished, those that end before it, the last task of a project in progress excepted, which
        stays open; a completed project has finished them all, its closing review after them.
        """
        reviewed = self.review(self.reviews).date() if ran else None
        completed = self.life == COMPLETED
        begun = ran and (completed or (reviewed is not None and task.start <= reviewed))
        done = ran and (completed or (not last and reviewed is not None and task.finish < reviewed))
        return {
            "node_id": str(task.node_id),
            "node": {
                "kind": "task",
                "parent_id": None,
                "task": {
                    "label": task.label,
                    "scheduling_mode": "manual",
                    "start": {"date": task.start.isoformat()},
                    "finish": {"date": task.finish.isoformat()},
                },
            },
            "started_on": task.start.isoformat() if begun else None,
            "completed_on": task.finish.isoformat() if done else None,
        }

    def _lines(self) -> list[dict[str, object]]:
        found: list[dict[str, object]] = []
        for rank, task in enumerate(self.tasks, start=1):
            role = self.draw.choice(self.reference.roles)
            labour = {
                "label": task.label,
                "cost_category_id": str(role.category_id),
                "quantity": "1",
                "resource_role_id": str(role.role_id),
                "hours": str(10 * self.draw.between(1, 16)),
                "unit_disbursement": None,
                "payment_delay_days": 0,
            }
            found.append(self._line(task, rank, 1, labour))
            if rank % 2 == 0:
                found.append(self._line(task, rank, 2, self._disbursement(task.label)))
        return found

    def _disbursement(self, label: str) -> dict[str, object]:
        return {
            "label": label,
            "cost_category_id": str(self.draw.choice(self.base.non_labour)),
            "quantity": "1",
            "resource_role_id": None,
            "hours": None,
            "unit_disbursement": f"{500 * self.draw.between(2, 100)}.00",
            "payment_delay_days": 0,
        }

    def _line(self, task: _Task, rank: int, line: int, entry: object) -> dict[str, object]:
        return {
            "node_id": str(identifier("line", self.number, rank, line)),
            "node": {
                "kind": "estimate_line",
                "parent_id": str(task.node_id),
                "estimate_line": entry,
            },
        }

    def _risks(self) -> list[dict[str, object]]:
        found: list[dict[str, object]] = []
        # Two risks of a project never bear the same label.
        first = self.draw.below(len(RISKS))
        for rank in range(1, self.draw.between(0, 2) + 1):
            label = RISKS[(first + rank) % len(RISKS)]
            own_task = identifier("own_task", self.number, rank)
            probability = f"0.{self.draw.between(1, 9)}"
            reviews = (
                [
                    {
                        "at": _instant(self.review(1) + WEEK),
                        "review": {
                            "probability": f"0.{self.draw.between(1, 9)}",
                            "state": "identified",
                            "lock_version": 1,
                        },
                    }
                ]
                if self.reviews >= REVIEWED_RISK
                else []
            )
            found.append(
                {
                    "risk_id": str(identifier("risk", self.number, rank)),
                    "declared_at": _instant(self.designated + timedelta(days=rank)),
                    "risk": {
                        "label": label,
                        "description": None,
                        "mitigation_notes": None,
                        "probability": probability,
                        "provision_cost_category_id": str(self.base.provision),
                        "provision_subproject_id": None,
                        "provision_task_id": str(self.draw.choice(self.tasks).node_id),
                    },
                    "own_estimate": [
                        {
                            "node_id": str(own_task),
                            "node": {"kind": "task", "parent_id": None, "task": {"label": label}},
                        },
                        {
                            "node_id": str(identifier("own_line", self.number, rank)),
                            "node": {
                                "kind": "estimate_line",
                                "parent_id": str(own_task),
                                "estimate_line": self._disbursement(label),
                            },
                        },
                    ],
                    "reviews": reviews,
                }
            )
        return found

    def _imports(self) -> list[dict[str, object]]:
        found: list[dict[str, object]] = []
        project_id = str(project_id_of(self.number))
        for rank in range(1, self.reviews + 1):
            imported = self.review(rank) - 6 * timedelta(days=1)
            lines = [
                {
                    "cost_line_id": str(identifier("cost_line", self.number, rank, item)),
                    "document_number": f"FA-{code_of(self.number)}-{rank:02d}",
                    "document_item": str(item),
                    "document_date": (imported.date() - timedelta(days=item)).isoformat(),
                    "amount": f"{100 * self.draw.between(5, 200)}.00",
                    "project_id": project_id,
                    "subproject_id": None,
                    "subproject_code": None,
                    "subproject_label": None,
                    "is_in_tracked_scope": True,
                    "excluded_reason": None,
                    "passthrough": {},
                    "audit": {
                        "created_at": _instant(imported),
                        "created_by": PLATFORM,
                        "updated_at": _instant(imported),
                        "updated_by": PLATFORM,
                    },
                }
                for item in range(1, self.draw.between(1, 3) + 1)
            ]
            found.append(
                {
                    "cost_import_id": str(identifier("import", self.number, rank)),
                    "imported_at": _instant(imported),
                    "lines": lines,
                }
            )
        return found


def _bounds() -> list[tuple[str, int]]:
    """Give each life with the bound, in a hundred, under which a draw falls to it."""
    found: list[tuple[str, int]] = []
    total = 0
    for life, weight in LIVES:
        total += weight
        found.append((life, total))
    return found
