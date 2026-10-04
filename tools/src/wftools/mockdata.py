# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Generate the volumes the fake back serves: the sizes of §4.6.2 (EP-02/L2).

Usage: ``python -m wftools.mockdata [--check]``.

Examples of the contract, written under ``fixtures/api/volume/`` and cited by it:

- ``nodes_thousand.json``, ``listNodes``: the structure of a thousand tasks and their lines
  (``wftools.mockstructure``);
- ``estimate_indicators.json``, ``getEstimateIndicators``: the indicators of that estimate,
  summed from the same lines, so that the fake back tells the same story on both;
- ``summary_dependencies.json``, ``getComputedValueDependencies``: what the finish date of its
  first summary depends on, its direct subordinates named from the same structure — the
  refusal the journeys try on it;
- ``portfolio_projects.json``, ``getPortfolioProjects``: the projects of the portfolio, the
  witness project and the offer of the other examples first;
- ``cost_categories.json``, ``listCostCategories``: the categories of §4.6.2, most of them
  labour — the rows of the grid of hourly rates;
- ``hourly_rates.json``, ``listHourlyRates``: fifteen years of rates of one labour category;
- ``hourly_rate_grid.json``, ``getHourlyRateGrid``: the grid of hourly rates, the labour
  categories in rows and the fifteen years in columns, read in one call (#162).

They live in the universe of the other examples: identifiers are kept, and what the
witness project, the offer and the labels of the universe say is read from their fixtures,
never copied here. Nothing here reads the clock or draws at random, so that two runs write
the same bytes. Amounts are ``Decimal`` and travel as the strings of the contract.

With ``--check``, nothing is written: the directory is compared with what the generator
writes, and a file missing, outdated or unreadable, or any entry left over, fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from wftools import REPOSITORY
from wftools.mockstructure import (
    AS_OF,
    COMMISSIONING,
    ELECTRICAL_ENGINEERING,
    ELECTRICAL_RATE,
    EQUIPMENT,
    LABOR,
    LINES_PER_TASK,
    NON_LABOR,
    PROVISION,
    PROVISIONS,
    SUBCONTRACTING,
    JsonObject,
    JsonValue,
    decimal,
    draw,
    estimate_indicators,
    identifier,
    money,
    structure,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

FIXTURES = REPOSITORY / "fixtures" / "api"
VOLUME = FIXTURES / "volume"
"""Where the volumes are written: a directory the generator owns, entry by entry."""

PROJECT_COUNT = 300
LABOR_CATEGORY_COUNT = 150
CATEGORY_COUNT = 200
RATE_YEARS = range(2012, 2027)
"""Fifteen years of rates, up to the reference year of the witness estimate."""

WATCH_THRESHOLD = Decimal("0.9")
ALERT_THRESHOLD = Decimal("0.8")
"""The thresholds of the zones of an index, those of the Vérif of WF-REF-0170-A."""

USER = "01926f3a-7c00-7000-8000-000000000301"

# The families of the identifiers made here; those of the nodes are 1 and 2.
_PROJECT, _CATEGORY = 3, 4

_AUDIT: JsonObject = {
    "created_at": "2026-01-05T09:00:00Z",
    "created_by": {"kind": "user", "user_id": USER, "display_name": "Camille Martin"},
    "updated_at": "2026-01-05T09:00:00Z",
    "updated_by": {"kind": "user", "user_id": USER, "display_name": "Camille Martin"},
}

_DESCRIPTION = "Exemple engendré par `make mock-data` (`wftools.mockdata`) : il ne se retouche pas."


def fixture(name: str) -> Any:
    """Return the value of an example of the universe, from its fixture."""
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))["value"]


# --- The portfolio of three hundred projects -------------------------------------------

_SUBJECTS = (
    "Modernisation",
    "Extension",
    "Rénovation",
    "Automatisation",
    "Mise en conformité",
    "Remplacement",
    "Construction",
)
_OBJECTS = (
    "du poste de commande",
    "de la ligne d'essais",
    "de la station de pompage",
    "du banc de mesure",
    "de l'atelier de montage",
    "du réseau de distribution",
    "de la sous-station",
    "du système de supervision",
    "de l'unité de traitement",
    "du magasin automatisé",
    "de la chaufferie",
)
_WIN_PROBABILITIES = ("0.2", "0.3", "0.4", "0.6", "0.8")


def zone(index: Decimal) -> str:
    """Return the zone of an index, as the server classes it by the thresholds (WF-REF-0170)."""
    if index >= WATCH_THRESHOLD:
        return "nominal"
    if index >= ALERT_THRESHOLD:
        return "watch"
    return "alert"


_SITES = ("Lyon", "Grenoble", "Dunkerque", "Toulouse")


def portfolio() -> JsonObject:
    """Return the answer of getPortfolioProjects: the witness and the offer, then the others."""
    universe = universe_rows()
    taken = {str(row["label"]) for row in universe}
    rows: list[JsonValue] = [*universe]
    # Each generated label is a subject, an object and a site; the witness project and the
    # offer keep theirs, and no other project takes their subject and object.
    names = [
        f"{subject} {thing}"
        for thing in _OBJECTS
        for subject in _SUBJECTS
        if f"{subject} {thing}" not in taken
    ]
    for n in range(len(universe) + 1, PROJECT_COUNT + 1):
        rank = n - len(universe) - 1
        label = f"{names[rank % len(names)]} — {_SITES[rank // len(names)]}"
        rows.append(_portfolio_row(n, label))
    return {
        "scope": {
            "states": ["in_progress", "pricing"],
            "as_of": AS_OF.isoformat(),
            "from": None,
            "to": None,
            "org_node_id": None,
            "project_count": PROJECT_COUNT,
        },
        "items": rows,
        # The whole portfolio in one page: the largest page the contract allows.
        "meta": {"limit": 500, "offset": 0, "total": PROJECT_COUNT},
    }


def universe_rows() -> list[JsonObject]:
    """Return the rows of the witness project and of the offer, from their fixtures.

    The witness project shows the indicators of its own example, and the date its reference
    revision was marked; the offer, without revision, has neither budget nor index.
    """
    project = fixture("project")
    indicators = fixture("project_indicators")
    offer = fixture("project_pricing")
    marked = next(
        revision["marked_at"]
        for revision in fixture("revisions")["items"]
        if revision["revision_id"] == project["reference_revision_id"]
    )
    witness: JsonObject = {
        "project_id": project["project_id"],
        "label": project["label"],
        "code": project["code"],
        "state": project["state"],
        "reference_budget": indicators["reference_budget"],
        "current_estimate": None,
        "win_probability": project["win_probability"],
        "project_manager_projection": indicators["projections"]["project_manager"],
        "delta_to_reference": indicators["projections"]["variance_project_manager"],
        "cost_index": indicators["cost_index"],
        "schedule_index": indicators["schedule_index"],
        "last_marked_at": marked,
    }
    pricing: JsonObject = {
        "project_id": offer["project_id"],
        "label": offer["label"],
        "code": offer["code"],
        "state": offer["state"],
        "reference_budget": None,
        "current_estimate": None,
        "win_probability": offer["win_probability"],
        "project_manager_projection": None,
        "delta_to_reference": None,
        "cost_index": None,
        "schedule_index": None,
        "last_marked_at": None,
    }
    return [witness, pricing]


def _portfolio_row(n: int, label: str) -> JsonObject:
    amount = Decimal(draw(f"amount/{n}", 2_000, 200_000)) * 100
    row: JsonObject = {
        "project_id": identifier(_PROJECT, n),
        "label": label,
        "code": f"PRJ-{n:03d}",
    }
    if n % 10 == 0:
        pricing: JsonObject = {
            "state": "pricing",
            "reference_budget": None,
            "current_estimate": money(amount),
            "win_probability": _WIN_PROBABILITIES[draw(f"win/{n}", 0, len(_WIN_PROBABILITIES) - 1)],
            "project_manager_projection": None,
            "delta_to_reference": None,
            "cost_index": None,
            "schedule_index": None,
            "last_marked_at": None,
        }
        return row | pricing
    projection = amount * draw(f"projection/{n}", 95, 115) / 100
    marked = date(2026, 2, 2) + timedelta(days=draw(f"marked/{n}", 0, 25))
    progressing: JsonObject = {
        "state": "in_progress",
        "reference_budget": money(amount),
        "current_estimate": None,
        "win_probability": "1",
        "project_manager_projection": money(projection),
        "delta_to_reference": money(projection - amount),
        "cost_index": _index(Decimal(draw(f"cost/{n}", 70, 120)) / 100),
        "schedule_index": _index(Decimal(draw(f"schedule/{n}", 70, 120)) / 100),
        "last_marked_at": f"{marked.isoformat()}T17:00:00Z",
    }
    return row | progressing


def _index(value: Decimal) -> JsonObject:
    return {
        "value": {"is_computable": True, "value": decimal(value), "reason": None},
        "zone": zone(value),
    }


# --- The grid of hourly rates -------------------------------------------------------------

_TRADES = (
    "Ingénierie mécanique",
    "Automatisme",
    "Électricité",
    "Instrumentation",
    "Génie civil",
    "Tuyauterie",
    "Chaudronnerie",
    "Informatique industrielle",
    "Qualité",
    "Méthodes",
)
_PURCHASES = (
    "Matériel mécanique",
    "Câbles",
    "Instruments",
    "Location d'engins",
    "Transport",
    "Essais en laboratoire",
    "Études externes",
)


def categories() -> list[JsonValue]:
    """Return the answer of listCostCategories: the labour categories first, then the others."""
    labor = [
        (ELECTRICAL_ENGINEERING, "Ingénierie électrique"),
        (COMMISSIONING, "Mise en service"),
    ]
    labor.extend(
        (identifier(_CATEGORY, n), f"{_TRADES[n % len(_TRADES)]} — niveau {n // len(_TRADES) + 1}")
        for n in range(LABOR_CATEGORY_COUNT - len(labor))
    )
    non_labor = [(SUBCONTRACTING, "Sous-traitance"), (EQUIPMENT, "Matériel électrique")]
    others = CATEGORY_COUNT - LABOR_CATEGORY_COUNT - 1
    non_labor.extend(
        (
            identifier(_CATEGORY, LABOR_CATEGORY_COUNT + n),
            f"{_PURCHASES[n % len(_PURCHASES)]} — lot {n // len(_PURCHASES) + 1}",
        )
        for n in range(others - len(non_labor))
    )
    return [
        *_categories(labor, "MO", "641", LABOR),
        *_categories(non_labor, "ACH", "604", NON_LABOR),
        *_categories([(PROVISIONS, "Provisions pour risques")], "PRV", "681", PROVISION),
    ]


def _categories(
    entries: Iterable[tuple[str, str]], code: str, account: str, cost_type: str
) -> list[JsonValue]:
    return [
        {
            "cost_category_id": category,
            "code": f"{code}-{rank:03d}",
            "label": label,
            "cost_type_id": cost_type,
            "accounting_code": f"{account}{rank:03d}",
            "is_active": True,
            "audit": _AUDIT,
            "lock_version": 1,
        }
        for rank, (category, label) in enumerate(entries, start=1)
    ]


# How much the rate grew each year, up to the reference year.
_RATE_STEP = Decimal("1.50")


def hourly_rates() -> list[JsonValue]:
    """Return the answer of listHourlyRates: the years of rates of the electrical engineering."""
    return [_rate(ELECTRICAL_ENGINEERING, ELECTRICAL_RATE, year) for year in RATE_YEARS]


def _rate(category: str, last_amount: Decimal, year: int) -> JsonObject:
    """Return the rate of a category for a year, grown by the step each year up to the last."""
    return {
        "cost_category_id": category,
        "year": year,
        "amount": money(last_amount - _RATE_STEP * (RATE_YEARS[-1] - year)),
        "audit": _AUDIT,
        "lock_version": 1,
    }


COMMISSIONING_RATE = Decimal("75.00")
"""The hourly rate of the commissioning in the reference year, the one the structure's lines pay."""

_EMPTY_YEARS = 4
"""How many of the first years a category may leave without a rate: an empty cell of the grid."""


def hourly_rate_grid() -> JsonObject:
    """Return the answer of getHourlyRateGrid: the labour categories in rows, the years in columns.

    The two categories the estimate employs carry their fifteen years — the electrical
    engineering those of ``listHourlyRates`` —; each other category draws its rate of the
    reference year, and the first years it left without a rate (WF-REF-0060).
    """
    known = {ELECTRICAL_ENGINEERING: ELECTRICAL_RATE, COMMISSIONING: COMMISSIONING_RATE}
    rows: list[JsonValue] = []
    for entry in categories():
        category = cast("JsonObject", entry)
        if category["cost_type_id"] != LABOR:
            continue
        identifier_ = str(category["cost_category_id"])
        last = known.get(identifier_)
        if last is None:
            last = Decimal(draw(f"rate/{identifier_}", 4_000, 12_000)) / 100
        first = RATE_YEARS[0] + (
            0 if identifier_ in known else draw(f"first-year/{identifier_}", 0, _EMPTY_YEARS)
        )
        rows.append(
            {
                "cost_category_id": identifier_,
                "code": category["code"],
                "label": category["label"],
                "is_active": True,
                "cells": [
                    _rate(identifier_, last, year) if year >= first else None for year in RATE_YEARS
                ],
            }
        )
    return {"years": list(RATE_YEARS), "rows": rows}


# --- Writing and checking ------------------------------------------------------------------


def volumes() -> dict[str, JsonObject]:
    """Return every volume, as the example of the contract its file holds, by file name."""
    built = structure()
    witness = fixture("estimate_indicators")
    labels = {
        entry["key"]: entry["label"]
        for entry in fixture("estimate_indicators_breakdown")["by_cost_type"]
    }
    labels.update((entry["subproject_id"], entry["label"]) for entry in fixture("subprojects"))
    indicators = estimate_indicators(built.totals, witness, labels)
    return {
        "nodes_thousand.json": _example(_structure_summary(built.nodes), built.nodes),
        "summary_dependencies.json": _example(
            "Ce dont dépend la date de fin de la première récapitulative de la structure aux "
            "volumes du §4.6.2 : ses subordonnées directes, nommées par leur numéro et leur "
            "libellé (WF-IHM-0030, WF-PLA-0040).",
            summary_dependencies(built.nodes),
        ),
        "estimate_indicators.json": _example(
            f"Les indicateurs du devis de la structure aux volumes du §4.6.2, sommés sur les "
            f"mêmes lignes que la grille : {_amount(built.totals.amount)} au total, dont "
            f"{_amount(built.totals.by_cost_type[PROVISION])} de provisions, ventilés par "
            f"nature de coût et par sous-projet (WF-DEV-0060).",
            indicators,
        ),
        "portfolio_projects.json": _example(
            f"Les {_count(PROJECT_COUNT)} projets du portefeuille du §4.6.2, en cours et en "
            f"chiffrage, le projet témoin et l'offre en tête ; indices classés par les seuils "
            f"de {_amount(WATCH_THRESHOLD, 1)} et {_amount(ALERT_THRESHOLD, 1)}.",
            portfolio(),
        ),
        "cost_categories.json": _example(
            f"Les {_count(CATEGORY_COUNT)} catégories de coût du §4.6.2, dont "
            f"{_count(LABOR_CATEGORY_COUNT)} de main-d'œuvre : les lignes de la grille des "
            f"taux horaires.",
            categories(),
        ),
        "hourly_rates.json": _example(
            f"{_count(len(RATE_YEARS))} ans de taux horaires de l'ingénierie électrique, de "
            f"{RATE_YEARS[0]} à {RATE_YEARS[-1]}, l'année de référence du devis, où il vaut "
            f"{_amount(ELECTRICAL_RATE)} de l'heure.",
            hourly_rates(),
        ),
        "hourly_rate_grid.json": _example(
            f"La grille des taux horaires du §4.6.2 : les {_count(LABOR_CATEGORY_COUNT)} "
            f"catégories de main-d'œuvre en lignes, les {_count(len(RATE_YEARS))} ans de "
            f"{RATE_YEARS[0]} à {RATE_YEARS[-1]} en colonnes ; une catégorie sans taux pour une "
            f"année y a une cellule vide (WF-REF-0050, WF-REF-0060).",
            hourly_rate_grid(),
        ),
    }


def summary_dependencies(answer: JsonObject) -> JsonObject:
    """Return what the finish date of the first summary depends on: its direct subordinates.

    The subordinates of a summary are its tasks: a line it bears is not one of them.
    """
    items = cast("list[dict[str, Any]]", answer["items"])
    summary = next(node for node in items if node["kind"] == "task" and node["task"]["is_summary"])
    rows: list[JsonValue] = [
        {
            "node_id": node["node_id"],
            "row_number": node["row_number"],
            "label": node["task"]["label"],
        }
        for node in items
        if node["parent_id"] == summary["node_id"] and node["kind"] == "task"
    ]
    return {
        "node_id": summary["node_id"],
        "field": "task.finish",
        "depends_on": ["subordinates"],
        "rows": rows,
    }


def _structure_summary(answer: JsonObject) -> str:
    """Say what the structure holds, counted from the answer itself."""
    items = cast("list[dict[str, Any]]", answer["items"])
    tasks = [item for item in items if item["kind"] == "task"]
    lines = [item for item in items if item["kind"] == "estimate_line"]
    count = Counter(
        "milestone" if task["task"]["is_milestone"] else task["level"]
        for task in tasks
        if task["task"]["is_milestone"] or task["task"]["is_summary"]
    )
    work = len(tasks) - sum(count.values())
    provisions = sum(1 for line in lines if line["estimate_line"]["is_computed"])
    return (
        f"La structure principale du projet aux volumes du §4.6.2 : {_count(len(tasks))} tâches "
        f"— {_count(count[1])} phases, {_count(count[2])} lots, leurs {_count(work)} tâches de "
        f"travail et leurs {_count(count['milestone'])} jalons, datés en jours ouvrés, avec leur "
        f"chemin critique — et {_count(len(lines))} lignes de devis, {LINES_PER_TASK} par "
        f"tâche : {LINES_PER_TASK} sur chaque tâche de travail, et une provision de plus sur "
        f"{_count(provisions)} d'entre elles."
    )


def _count(value: int) -> str:
    """Write a count as French does: thousands apart by a narrow no-break space."""
    return f"{value:,}".replace(",", "\u202f")


def _amount(value: Decimal, places: int = 2) -> str:
    """Write an amount as French does: 60 553 621,36."""
    return f"{value:,.{places}f}".replace(",", "\u202f").replace(".", ",")


def _example(summary: str, value: JsonValue) -> JsonObject:
    return {"summary": summary, "description": _DESCRIPTION, "value": value}


# The envelope of an example and its value are laid out; below them, one line per item.
_EXPANDED_DEPTH = 2


def render(example: JsonObject) -> str:
    """Return the text of an example: one line for each item of its lists, for readable diffs."""
    return _render(example, 0) + "\n"


def _render(value: JsonValue, depth: int) -> str:
    indent = "  " * depth
    inner = indent + "  "
    if isinstance(value, list) and value:
        items = ",\n".join(inner + _compact(item) for item in value)
        return f"[\n{items}\n{indent}]"
    if isinstance(value, dict) and depth < _EXPANDED_DEPTH:
        fields = ",\n".join(
            f"{inner}{_compact(key)}: {_render(item, depth + 1)}" for key, item in value.items()
        )
        return f"{{\n{fields}\n{indent}}}"
    return _compact(value)


def _compact(value: JsonValue) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def write(directory: Path) -> list[Path]:
    """Write every volume in the directory, removing a file it no longer makes.

    A directory left in it is not removed: the check names it, to be removed by hand. The
    text is written with plain line ends whatever the system, as the check reads it.
    """
    directory.mkdir(parents=True, exist_ok=True)
    expected = {name: render(example) for name, example in volumes().items()}
    for stale in sorted(set(_entries(directory)) - expected.keys()):
        if (directory / stale).is_file():
            (directory / stale).unlink()
    written: list[Path] = []
    for name, text in expected.items():
        path = directory / name
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
    return written


def check(directory: Path) -> list[str]:
    """Return what differs between the directory and what the generator writes."""
    expected = {name: render(example) for name, example in volumes().items()}
    present = _entries(directory)
    problems = [_left_over(directory / name) for name in sorted(set(present) - expected.keys())]
    for name, text in expected.items():
        if name not in present:
            problems.append(f"{name} is missing")
        elif not _holds(directory / name, text):
            problems.append(f"{name} is outdated")
    return problems


def _left_over(path: Path) -> str:
    """Name an entry the generator does not make: a directory, `write` does not remove."""
    if path.is_dir():
        return f"{path.name} is a directory left over, {BY_HAND}"
    return f"{path.name} is left over"


BY_HAND = "remove it by hand"
"""What `write` cannot do for a directory: the check says so instead of `make mock-data`."""


def _entries(directory: Path) -> list[str]:
    return sorted(path.name for path in directory.iterdir()) if directory.is_dir() else []


def _holds(path: Path, text: str) -> bool:
    """Whether a file holds exactly this text; a directory or undecodable bytes do not."""
    if not path.is_file():
        return False
    try:
        return path.read_bytes().decode("utf-8") == text
    except UnicodeDecodeError:
        return False


def main(arguments: list[str], directory: Path = VOLUME) -> int:
    """Write the volumes, or check that the versioned ones are what the generator writes."""
    parser = argparse.ArgumentParser(
        prog="wftools.mockdata", description="Generate the volumes the fake back serves."
    )
    parser.add_argument("--check", action="store_true", help="compare, write nothing")
    options = parser.parse_args(arguments)
    if options.check:
        problems = check(directory)
        for problem in problems:
            remedy = "" if problem.endswith(BY_HAND) else ", run make mock-data"
            print(f"  {directory}: {problem}{remedy}", file=sys.stderr)
        return 1 if problems else 0
    for path in write(directory):
        print(f"  -> {path} ({path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
