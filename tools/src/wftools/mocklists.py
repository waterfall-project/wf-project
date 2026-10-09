# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Search, filter and sort the list of the projects and the lists of a project (#536).

The lists written by hand — the projects of the home (``projects``), the subprojects
(``subprojects``) and the contributors of the witness (``contributors``) — read as their screens
ask them:

- ``projects_default_states.json``, ``listProjects`` without `states`: the projects in progress
  alone, the default of the perimeter of the portfolio (WF-PTF-0010), which the answer names
  (`meta.states`); ``projects_search_code.json``, a search that finds a project by its code alone;
  ``projects_period.json``, the projects last modified within a period, its bounds included;
- ``subprojects_by_label.json``, ``listSubprojects`` sorted by label;
  ``subprojects_with_actual_costs.json``, those to which actual costs are charged;
- ``contributors_by_name.json``, ``listContributors`` sorted by the name of the account;
  ``contributors_search.json``, searched on it; ``contributors_inactive.json``, those whose account
  was deactivated since they were entered.

Each list written by hand is in the order of the list without sort. A sort here is stable — two
rows of one value keep that order, as every sort of the contract breaks a tie (DECISIONS,
EP-02/L42a) —, a text compares by code point, and a row without a value comes after the others in
the ascending order, before them in the descending one. Nothing here reads the clock or draws at
random, nor a file the same command writes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from wftools import mocktext
from wftools.mockwitness import fixture

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    from wftools.mockstructure import JsonObject, JsonValue

PROJECT_STATES = ("created", "pricing", "in_progress", "completed", "lost", "abandoned")
"""The states of a project in the order of `ProjectState`, that of the life cycle (WF-CYC-0010)."""

DEFAULT_STATES = ("in_progress",)
"""The states a list of projects retains when it names none: the projects in progress, the
default of the perimeter of the portfolio, whose parameter it shares (WF-PTF-0010)."""

CONTRIBUTOR_KINDS = ("project_manager", "contributor")
"""The capacities of a contributor in the order of `ContributorKind`: project managers first."""

SEARCHED_CODE = "PRJ-002"
"""The text of ``projects_search_code``: the code of the offer, which no label holds."""

PERIOD = (datetime(2026, 2, 28, 23, tzinfo=UTC), datetime(2026, 3, 31, 22, tzinfo=UTC))
"""The period of ``projects_period``: March in Paris, as the screen asks it from the days of its
reader — from midnight of 1 March, an hour ahead of universal time, to midnight of 1 April, two
hours ahead since summer time, excluded."""

SEARCHED_NAME = "Petit"
"""The text of ``contributors_search``: the name of the estimator."""

type Key = Callable[[JsonObject], JsonValue]
"""The key of a column: its value in a row, a text, a number or a truth value; none for no value."""

_example, _day = mocktext.example, mocktext.day


def ordered(rows: Iterable[JsonObject], key: Key, *, descending: bool = False) -> list[JsonObject]:
    """Return rows sorted by a key, as a list of the contract sorts them (`sort_by`, `sort_order`).

    Stable in either direction: rows of one value keep the order they came in, that of the list
    without sort. A row whose key is none comes after the others in the ascending order, before
    them in the descending one.
    """
    found = list(rows)
    valued = [row for row in found if key(row) is not None]
    empty = [row for row in found if key(row) is None]
    # Python's sort keeps the ties in their order even reversed: the stable sort the contract asks.
    valued.sort(key=lambda row: cast("str | int | bool", key(row)), reverse=descending)
    return [*empty, *valued] if descending else [*valued, *empty]


def holds(value: JsonValue, text: str) -> bool:
    """Whether a text of a row holds a searched text, whatever its case; none holds nothing."""
    return isinstance(value, str) and text.casefold() in value.casefold()


def first_true(field: str) -> Key:
    """Return the key of a column of truth values: the true rows first in the ascending order.

    As the state of the accounts ranges the active ones first, and the kind of the roles the
    predefined ones (`listUsers`, `listAccessRoles`).
    """
    return lambda row: row[field] is not True


# --- The projects of the home -------------------------------------------------------------------


def retained_states(asked: Sequence[str] = ()) -> list[str]:
    """Return the states a list of projects retains: those asked, or the default, in their order.

    Each once, in the order of `ProjectState`, as `meta.states` names them.
    """
    found = set(asked) or set(DEFAULT_STATES)
    unknown = found - set(PROJECT_STATES)
    if unknown:
        message = f"no state of a project: {sorted(unknown)}"
        raise ValueError(message)
    return [state for state in PROJECT_STATES if state in found]


def searched_projects(projects: Iterable[JsonObject], text: str) -> list[JsonObject]:
    """Return the projects whose label or code holds a text (`search` of `listProjects`)."""
    return [each for each in projects if holds(each["label"], text) or holds(each["code"], text)]


def modified_at(project: JsonObject) -> datetime:
    """Return the instant a project was last modified (`audit.updated_at`)."""
    return datetime.fromisoformat(cast("str", cast("JsonObject", project["audit"])["updated_at"]))


def modified_within(
    projects: Iterable[JsonObject], start: datetime | None, end: datetime | None
) -> list[JsonObject]:
    """Return the projects last modified within a period (`from` included, `to` excluded).

    As the journal of audit reads its period (`listAuditEvents`): instants, the screen turning the
    days of its reader into them. A period whose end precedes its start is refused.
    """
    if start is not None and end is not None and end < start:
        message = f"the period ends at {end}, before it starts at {start}"
        raise ValueError(message)
    return [
        each
        for each in projects
        if (start is None or modified_at(each) >= start)
        and (end is None or modified_at(each) < end)
    ]


def by_default(projects: Iterable[JsonObject]) -> list[JsonObject]:
    """Return projects in the order of the list without sort: the last modified first.

    By the instant of their last modification, decreasing, then by their identifier, as every tie
    of the contract (`sort_by` of `listProjects`, DECISIONS, EP-02/L42a).
    """
    found = sorted(projects, key=lambda each: str(each["project_id"]))
    return sorted(found, key=modified_at, reverse=True)


def project_page(
    projects: Sequence[JsonObject], asked: Sequence[str] = (), limit: int = mocktext.PAGE
) -> JsonObject:
    """Return the first page of the projects in the states retained, which its `meta` names.

    In the order of the list without sort, whatever the order they are given in.
    """
    states = retained_states(asked)
    kept = [each for each in by_default(projects) if each["state"] in states]
    return {
        "items": cast("list[JsonValue]", kept[:limit]),
        "meta": {
            "limit": limit,
            "offset": 0,
            "total": len(kept),
            "states": cast("list[JsonValue]", states),
        },
    }


# --- The subprojects and the contributors of a project ------------------------------------------

SUBPROJECT_KEYS: dict[str, Key] = {
    "code": lambda row: row["code"],
    "label": lambda row: row["label"],
    "has_actual_costs": first_true("has_actual_costs"),
}
"""The columns `listSubprojects` sorts by, each by its key."""

CONTRIBUTOR_KEYS: dict[str, Key] = {
    "display_name": lambda row: row["display_name"],
    "kind": lambda row: CONTRIBUTOR_KINDS.index(cast("str", row["kind"])),
    "is_active": first_true("is_active"),
}
"""The columns `listContributors` sorts by, each by its key."""


def charged(subprojects: Iterable[JsonObject], *, with_costs: bool) -> list[JsonObject]:
    """Return the subprojects to which actual costs are charged, or the others."""
    return [each for each in subprojects if each["has_actual_costs"] is with_costs]


def contributor_list(contributors: JsonObject, items: Iterable[JsonObject]) -> JsonObject:
    """Return a reading of the contributors: the rows kept, the counter of the whole list."""
    return {
        "items": cast("list[JsonValue]", list(items)),
        "lock_version": contributors["lock_version"],
    }


def _labels(rows: Iterable[JsonObject]) -> str:
    """Say rows by their label, quoted: « A », « B » et « C »."""
    return mocktext.listed([f"« {row['label']} »" for row in rows])


def _names(rows: Iterable[JsonObject]) -> str:
    """Say contributors by the name of their account."""
    return mocktext.listed([str(row["display_name"]) for row in rows])


def _stamp(instant: datetime) -> str:
    """Write an instant as the contract carries it: 2026-03-31T22:00:00Z."""
    return instant.isoformat().replace("+00:00", "Z")


def _modified(rows: Iterable[JsonObject]) -> str:
    """Say projects by their label and the day they were last modified."""
    return mocktext.listed(
        [f"« {row['label']} », modifié le {_day(modified_at(row).date())}" for row in rows]
    )


def examples() -> dict[str, JsonObject]:
    """Return the readings of the lists of the projects and of the witness, by file name."""
    projects = cast("list[JsonObject]", fixture("projects")["items"])
    subprojects = cast("list[JsonObject]", fixture("subprojects"))
    contributors = fixture("contributors")
    people = cast("list[JsonObject]", contributors["items"])
    default = project_page(projects)
    by_code = searched_projects(projects, SEARCHED_CODE)
    within = modified_within(projects, *PERIOD)
    outside = [each for each in projects if each not in within]
    by_label = ordered(subprojects, SUBPROJECT_KEYS["label"])
    with_costs = charged(subprojects, with_costs=True)
    by_name = ordered(people, CONTRIBUTOR_KEYS["display_name"])
    found = [each for each in people if holds(each["display_name"], SEARCHED_NAME)]
    inactive = [each for each in people if each["is_active"] is False]
    start, end = PERIOD
    return {
        "projects_default_states.json": _example(
            f"Les projets lus sans état nommé : les projets en cours seuls, le défaut du périmètre "
            f"du portefeuille (WF-PTF-0010) : "
            f"{_labels(cast('list[JsonObject]', default['items']))}, les projets d'un autre état "
            f"écartés ; meta.states nomme l'état retenu, que l'écran montre sans le deviner "
            f"(WF-IHM-0130).",
            default,
        ),
        "projects_search_code.json": _example(
            f"Les projets cherchés par « {SEARCHED_CODE} », les six états nommés : "
            f"{_labels(by_code)}, trouvé par son code, qu'aucun libellé ne contient — la "
            f"recherche porte sur le libellé et sur le code (WF-IHM-0130).",
            project_page(by_code, PROJECT_STATES),
        ),
        "projects_period.json": _example(
            f"Les projets modifiés en mars 2026 à Paris, les six états nommés : de "
            f"{_stamp(start)}, inclus, à {_stamp(end)}, exclu (from, to), les jours du lecteur "
            f"en instants : {_modified(within)}, retenu ; {_modified(outside)}, écarté "
            f"(WF-IHM-0130).",
            project_page(within, PROJECT_STATES),
        ),
        "subprojects_by_label.json": _example(
            f"Les sous-projets triés par libellé, croissant (sort_by=label) : "
            f"{_labels(by_label)}, quand la liste sans tri les range par code "
            f"(WF-IHM-0060).",
            cast("JsonValue", by_label),
        ),
        "subprojects_with_actual_costs.json": _example(
            f"Les sous-projets auxquels des coûts réels sont imputés (has_actual_costs) : "
            f"{_labels(with_costs)}, qui ne se supprime plus ; les autres sont écartés "
            f"(WF-PRJ-0050, WF-IHM-0130).",
            cast("JsonValue", with_costs),
        ),
        "contributors_by_name.json": _example(
            f"Les contributeurs triés par nom, croissant (sort_by=display_name) : "
            f"{_names(by_name)}, comparés par points de code, quand la liste sans tri met les "
            f"chefs de projet d'abord, puis les autres par nom de famille ; le compteur est celui "
            f"de toute la liste (WF-IHM-0060, WF-PRJ-0060).",
            contributor_list(contributors, by_name),
        ),
        "contributors_search.json": _example(
            f"Les contributeurs cherchés par « {SEARCHED_NAME} », sur le nom du compte : "
            f"{_names(found)} ; le compteur reste celui de toute la liste, que "
            f"setContributors exige (WF-IHM-0130, WF-IHM-0110).",
            contributor_list(contributors, found),
        ),
        "contributors_inactive.json": _example(
            f"Les contributeurs dont le compte a été désactivé depuis leur inscription "
            f"(is_active=false) : {_names(inactive)}, que la liste garde et "
            f"signale (WF-ADM-0060, WF-IHM-0130).",
            contributor_list(contributors, inactive),
        ),
    }
