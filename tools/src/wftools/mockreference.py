# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Page, sort, bound and command the lists of the reference the fake back serves (EP-02/L42).

The lists of the reference are read by pages, as every other list of the contract, and each of
their objects bears the command that changes its state (#509, #510, #532, #545).
``wftools.mockdata`` draws the categories of cost and the grid of hourly rates of §4.6.2; this
module makes their examples, under ``volume/``:

- ``cost_categories.json``, ``listCostCategories``: the categories read whole, by code, by the
  largest page the contract takes, each with the command that deactivates it and the one that
  moves it under a nature of another kind — unavailable for a category a line of the witness bears,
  that bears hourly rates (`CostCategoryCommand`, EP-02/L42g), or that a role is attached to
  (EP-14/L42r);
  ``cost_categories_page.json``, their second page; ``cost_categories_reader.json``, the same read
  by a session that may not modify the cost settings — no command;
- ``hourly_rate_grid.json``, ``getHourlyRateGrid``: the grid read whole, by the largest page;
  ``hourly_rate_grid_by_rate.json``, its first page sorted by the rate of the reference year, the
  highest first; ``hourly_rate_grid_bounded.json``, the categories whose rate that year reaches a
  bound — the years those of the whole grid, whatever the page, the sort or the bound.

And, beside them by their name, what is read from the lists written by hand (``org_nodes``,
``resource_roles``, ``calendars``, ``cost_types``, ``org_nodes_with_inactive``): each read by a
session without the permission to modify them (``*_reader``) — the active objects alone, without
commands —, the roles bounded by their monthly hours, and the reactivation of the office of
automation, alone, its child left deactivated (WF-REF-0080).

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockcore, mockhistory, mocktext
from wftools.mockids import universe
from wftools.mockwitness import TODAY, fixture

if TYPE_CHECKING:
    from collections.abc import Sequence

    from wftools.mockstructure import JsonObject, JsonValue

MAX_LIMIT = mocktext.MAX_LIMIT
"""The largest page the contract takes (`Limit`): a list read whole, as a choice reads it."""

PAGE = mocktext.PAGE
"""The page the contract gives by default (`Limit`), that a table reads."""

RATE_BOUND_CODE = "MO-066"
"""The category whose rate of the reference year bounds ``hourly_rate_grid_bounded``: a rate a row
bears — MO-137 bears it too —, so that the reading shows the bound included."""

HOURS_BOUND_ROLE = universe(452)
"""The role whose monthly hours bound ``resource_roles_bounded``, the commissioning technician:
hours a row bears, so that the reading shows the bound included."""

AUTOMATION_OFFICE = universe(474)
"""The office of automation, deactivated with the robotics cell under it (``org_nodes``)."""

CHANGE_COST_TYPE = "change_cost_type"
"""The command that moves a category under a nature of another kind (`CostCategoryCommand`)."""

UNUSED, UNRATED = "cost_category_unused", "cost_category_unrated"
"""The conditions the move misses: a category a line bears, a category that bears hourly rates."""

WITHOUT_ROLE = "cost_category_without_role"
"""The condition the move misses for a category a resource role is attached to (WF-REF-0040)."""

_count, _amount, _example = mocktext.count, mocktext.amount, mocktext.example


def commands(command: str, missing: Sequence[str] = ()) -> list[JsonValue]:
    """Return the commands of an object of the reference: the one that changes its state.

    It is available unless a condition is missing (`ReferenceCommand`, WF-IHM-0090).
    """
    return [
        {
            "command": command,
            "is_available": not missing,
            "missing_conditions": cast("list[JsonValue]", list(missing)),
        }
    ]


def category_commands(
    category: JsonObject, employed: set[str], rated: set[str], attached: set[str]
) -> list[JsonValue]:
    """Return the commands of a category: the one that changes its state, then its move.

    The move under a nature of another kind misses `cost_category_unused` while a line bears the
    category, `cost_category_unrated` while it bears hourly rates, and `cost_category_without_role`
    while a resource role, active or not, is attached to it (WF-REF-0040, WF-REF-0050) — in that
    order. Its state always changes: the last active category of provision for risks goes as any
    other, the rule of #578 withdrawn (WF-REF-0030, WF-CYC-0120, WF-RIS-0010; EP-14/L42p).
    """
    identifier = cast("str", category["cost_category_id"])
    missing = [
        condition
        for condition, held in (
            (UNUSED, identifier in employed),
            (UNRATED, identifier in rated),
            (WITHOUT_ROLE, identifier in attached),
        )
        if held
    ]
    state = commands("deactivate" if category["is_active"] is True else "reactivate")
    return [*state, *commands(CHANGE_COST_TYPE, missing)]


def employed() -> set[str]:
    """Return the categories the lines of the witness bear: those of its core.

    The lines drawn after the core take their categories among them (`mockstructure.LINE_KINDS`).
    """
    return {
        cast("str", cast("JsonObject", row.node["estimate_line"])["cost_category_id"])
        for row in mockcore.core()
        if row.kind == mockcore.ESTIMATE_LINE
    }


def attached(roles: Sequence[JsonValue]) -> set[str]:
    """Return the categories the resource roles given are attached to, deactivated roles counted.

    A deactivated role keeps its category, and reactivates without a look at it (WF-REF-0090).
    """
    return {cast("str", role["cost_category_id"]) for role in cast("list[JsonObject]", roles)}


def rated(grid: JsonObject) -> set[str]:
    """Return the categories that bear an hourly rate, a cell of their row in the grid filled."""
    return {
        cast("str", row["cost_category_id"])
        for row in cast("list[JsonObject]", grid["rows"])
        if any(cell is not None for cell in cast("list[JsonValue]", row["cells"]))
    }


def commanded(entry: JsonObject, available: list[JsonValue]) -> JsonObject:
    """Return an object of the reference with its commands, written before its audit."""
    written: JsonObject = {}
    for key, value in entry.items():
        if key == "available_commands":
            continue
        if key == "audit":
            written["available_commands"] = available
        written[key] = value
    return written


def page(items: Sequence[JsonValue], limit: int, offset: int) -> JsonObject:
    """Return a page of a list the server pages: its items, and where it stands in the whole."""
    return {
        "items": list(items[offset : offset + limit]),
        "meta": {"limit": limit, "offset": offset, "total": len(items)},
    }


def read_by_a_reader(entries: Sequence[JsonValue]) -> list[JsonValue]:
    """Return a list as a session without the permission to modify it reads it.

    The active objects alone — it may not ask for the deactivated ones (`include_inactive`) —, and
    no command, which the permission alone would list (`ReferenceCommands`, WF-IHM-0090).
    """
    return [
        commanded(entry, [])
        for entry in cast("list[JsonObject]", entries)
        if entry["is_active"] is True
    ]


def rate(row: JsonObject, years: Sequence[int], year: int) -> Decimal | None:
    """Return the rate of a row of the grid for a year: none for an empty cell or a year absent."""
    if year not in years:
        return None
    cell = cast("list[JsonObject | None]", row["cells"])[list(years).index(year)]
    return None if cell is None else Decimal(cast("str", cell["amount"]))


def by_code(entries: Sequence[JsonValue]) -> list[JsonObject]:
    """Return objects in the order of their code, which a list without `sort_by` gives."""
    return sorted(cast("list[JsonObject]", entries), key=lambda entry: str(entry["code"]))


def by_rate(grid: JsonObject, year: int, *, descending: bool) -> list[JsonObject]:
    """Return the rows of the grid sorted by the rate of a year, as `rate.<year>` asks.

    A row without a rate that year comes after the others in the increasing order, before them in
    the decreasing one; rows at the same rate, or without one, keep the order of their code.
    """
    years = cast("list[int]", grid["years"])
    rated: list[tuple[Decimal, JsonObject]] = []
    empty: list[JsonObject] = []
    for row in by_code(cast("list[JsonValue]", grid["rows"])):
        found = rate(row, years, year)
        if found is None:
            empty.append(row)
        else:
            rated.append((found, row))
    # Sorted by code first, the stable sort keeps the ties in that order, in either direction.
    rated.sort(key=lambda pair: -pair[0] if descending else pair[0])
    ordered = [row for _, row in rated]
    return [*empty, *ordered] if descending else [*ordered, *empty]


def bounded(grid: JsonObject, year: int, low: Decimal) -> list[JsonObject]:
    """Return the rows whose rate of a year is at least a bound, in the order of their code.

    A row without a rate that year is retained by no bound (`rate_min`).
    """
    years = cast("list[int]", grid["years"])
    return [
        row
        for row in by_code(cast("list[JsonValue]", grid["rows"]))
        if (found := rate(row, years, year)) is not None and found >= low
    ]


def grid_page(grid: JsonObject, rows: Sequence[JsonValue], limit: int, offset: int) -> JsonObject:
    """Return a page of the grid: the years of the whole grid, the rows of the page."""
    paged = page(rows, limit, offset)
    return {"years": grid["years"], "rows": paged["items"], "meta": paged["meta"]}


def _said(row: JsonObject, years: Sequence[int], year: int) -> str:
    """Say a row of the grid by its label and its rate of a year."""
    found = rate(row, years, year)
    amount = "sans taux" if found is None else f"à {_amount(found)}"
    return f"« {row['label']} » {amount}"


def examples(categories: list[JsonValue], grid: JsonObject) -> dict[str, JsonObject]:
    """Return the examples of the categories and of the grid of rates, by file name."""
    lines, bearing = employed(), rated(grid)
    roles = attached(cast("list[JsonValue]", fixture("resource_roles")["items"]))
    listed: list[JsonValue] = [
        commanded(entry, category_commands(entry, lines, bearing, roles))
        for entry in by_code(categories)
    ]
    years = cast("list[int]", grid["years"])
    rows = cast("list[JsonValue]", grid["rows"])
    year = years[-1]
    ranked = by_rate(grid, year, descending=True)
    [bounding] = [row for row in by_code(rows) if row["code"] == RATE_BOUND_CODE]
    bound = rate(bounding, years, year)
    if bound is None:
        message = f"{RATE_BOUND_CODE} bears no rate in {year}"
        raise ValueError(message)
    kept = bounded(grid, year, bound)
    readable = read_by_a_reader(listed)
    return {
        "cost_categories.json": _example(
            f"Les {_count(len(listed))} catégories de coût du §4.6.2, par code, dont "
            f"{_count(len(rows))} de main-d'œuvre — les lignes de la grille des taux horaires —, "
            f"lues en une page de {_count(MAX_LIMIT)}, comme une liste de choix les lit, chacune "
            f"avec la commande qui la désactive et celle qui la rattache à une nature d'un autre "
            f"type, indisponible pour les {_count(len(lines))} que le devis du projet témoin "
            f"emploie, pour les {_count(len(bearing))} qui portent des taux horaires et pour les "
            f"{_count(len(roles))} auxquelles un rôle de ressource est rattaché ; "
            f"chacune se désactive, la dernière de type provision pour risques comme les autres "
            f"(WF-REF-0030, WF-REF-0040, WF-REF-0050, WF-IHM-0090).",
            page(listed, MAX_LIMIT, 0),
        ),
        "cost_categories_page.json": _example(
            f"La deuxième page de {_count(PAGE)} catégories de coût du §4.6.2, par code : les "
            f"catégories {_count(PAGE + 1)} à {_count(2 * PAGE)} sur {_count(len(listed))} "
            f"(WF-REF-0040).",
            page(listed, PAGE, PAGE),
        ),
        "cost_categories_reader.json": _example(
            f"Les {_count(len(readable))} catégories de coût actives du §4.6.2, par code, lues "
            f"par une session qui ne peut pas modifier les paramètres de coûts — un estimateur "
            f"qui choisit la catégorie d'une ligne de devis : aucune commande (WF-DEV-0020, "
            f"WF-IHM-0090).",
            page(readable, MAX_LIMIT, 0),
        ),
        "hourly_rate_grid.json": _example(
            f"La grille des taux horaires du §4.6.2 : les {_count(len(rows))} catégories de "
            f"main-d'œuvre en lignes, par code, lues en une page de {_count(MAX_LIMIT)}, les "
            f"{_count(len(years))} ans de {years[0]} à {years[-1]} en colonnes ; une catégorie "
            f"sans taux pour une année y a une cellule vide (WF-REF-0050, WF-REF-0060).",
            grid_page(grid, rows, MAX_LIMIT, 0),
        ),
        "hourly_rate_grid_by_rate.json": _example(
            f"La première page de {_count(PAGE)} catégories de la grille des taux horaires du "
            f"§4.6.2, triées par leur taux de {year} décroissant (rate.{year}), à taux égal par "
            f"code : en tête, {_said(ranked[0], years, year)} de l'heure, en dernier "
            f"{_said(ranked[PAGE - 1], years, year)} ; les colonnes sont les "
            f"{_count(len(years))} ans de toute la grille, quelle que soit la page (WF-REF-0050, "
            f"WF-IHM-0060).",
            grid_page(grid, cast("list[JsonValue]", ranked), PAGE, 0),
        ),
        "hourly_rate_grid_bounded.json": _example(
            f"Les catégories de la grille des taux horaires du §4.6.2 dont le taux de {year} "
            f"atteint {_amount(bound)}, celui de {RATE_BOUND_CODE} (rate_year={year}, "
            f"rate_min={bound}), bornes incluses, par code, "
            f"en une page de {_count(PAGE)} : {_count(len(kept))} sur {_count(len(rows))} ; les "
            f"colonnes restent les {_count(len(years))} ans de toute la grille (WF-REF-0050, "
            f"WF-IHM-0130).",
            grid_page(grid, cast("list[JsonValue]", kept), PAGE, 0),
        ),
    }


def named() -> dict[str, JsonObject]:
    """Return the readings of the lists written by hand, by file name."""
    roles = cast("list[JsonValue]", fixture("resource_roles")["items"])
    calendars = cast("list[JsonValue]", fixture("calendars")["items"])
    natures = cast("list[JsonValue]", fixture("cost_types")["items"])
    readable_roles = read_by_a_reader(roles)
    readable_calendars = read_by_a_reader(calendars)
    readable_natures = read_by_a_reader(natures)
    hours = {
        cast("str", role["resource_role_id"]): Decimal(
            cast("dict[str, str]", role["capacity"])["monthly_hours"]
        )
        for role in cast("list[JsonObject]", roles)
    }
    bound = hours[HOURS_BOUND_ROLE]
    heavy = [
        role
        for role in cast("list[JsonObject]", roles)
        if hours[cast("str", role["resource_role_id"])] >= bound
    ]
    return {
        "org_nodes_reader.json": _example(
            "L'arbre d'organisation lu par une session qui ne peut pas modifier les paramètres de "
            "ressources : les nœuds actifs seuls, dans l'ordre de l'arbre, aucun avec une "
            "commande (WF-REF-0070, WF-IHM-0090).",
            cast("JsonValue", read_by_a_reader(fixture("org_nodes"))),
        ),
        "resource_roles_reader.json": _example(
            f"Les {_count(len(readable_roles))} rôles de ressources actifs, lus par une session "
            f"qui ne peut pas modifier les paramètres de ressources — un estimateur qui choisit "
            f"le rôle d'une ligne de devis, sans pouvoir demander les désactivés : aucune "
            f"commande (WF-DEV-0020, WF-REF-0150, WF-IHM-0090).",
            page(readable_roles, PAGE, 0),
        ),
        "resource_roles_bounded.json": _example(
            f"Les rôles de ressources d'au moins {_amount(bound)} heures mensuelles, celles du "
            f"technicien de mise en service (monthly_hours_min={bound}), borne incluse, lus avec "
            f"les désactivés : "
            f"{mocktext.listed([str(role['label']).lower() for role in heavy])}, chacun avec la "
            f"commande qui le désactive (WF-REF-0100, WF-IHM-0130).",
            page(cast("list[JsonValue]", heavy), PAGE, 0),
        ),
        "calendars_reader.json": _example(
            f"Les {_count(len(readable_calendars))} calendriers actifs, lus par une session qui ne "
            f"peut pas modifier les paramètres de ressources : aucune commande, pas même la "
            f"désactivation indisponible du calendrier par défaut (WF-REF-0110, WF-IHM-0090).",
            page(readable_calendars, PAGE, 0),
        ),
        "cost_types_reader.json": _example(
            f"Les {_count(len(readable_natures))} natures de coût actives, lues par une session "
            f"qui ne peut pas modifier les paramètres de coûts : aucune commande (WF-REF-0030, "
            f"WF-IHM-0090).",
            page(readable_natures, PAGE, 0),
        ),
        "org_node_reactivated.json": _example(
            "Le bureau d'études automatismes réactivé aujourd'hui, à partir de la version lue, "
            "son parent, la direction technique, étant actif : lui seul, sa version avancée "
            "d'une, avec la commande qui le désactive ; la cellule robotique, sous lui, et le "
            "programmeur d'automates restent désactivés et se réactivent un à un — la "
            "réactivation ne cascade pas, et le client relit les listes (WF-REF-0080).",
            {"org_nodes": [_reactivated(AUTOMATION_OFFICE)], "resource_roles": []},
        ),
    }


def _reactivated(org_node_id: str) -> JsonValue:
    """Return a deactivated node of the organisation reactivated today, from the version read."""
    [node] = [
        entry
        for entry in cast("list[JsonObject]", fixture("org_nodes_with_inactive"))
        if entry["org_node_id"] == org_node_id
    ]
    audit = dict(cast("JsonObject", node["audit"]))
    audit["updated_at"] = mockhistory.stamp(TODAY)
    written = commanded(node, commands("deactivate"))
    written.update(is_active=True, audit=audit, lock_version=cast("int", node["lock_version"]) + 1)
    return written
