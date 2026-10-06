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
- ``task_lengthened.json``, ``updateTaskFacet``: a duration lengthened in that structure, which
  pushes a successor into the next year — its schedule, the amounts corrected of its lines and
  of itself, the summaries above and the totals, recalculated from the same lines;
- ``portfolio_projects.json``, ``getPortfolioProjects``: the projects of the portfolio, the
  witness project and the offer of the other examples first, and ``portfolio_projects_page.json``,
  its second page of fifty;
- ``portfolio_value.json``, ``portfolio_performance.json``, ``portfolio_cost_structure.json``
  and ``portfolio_risks.json``, of ``getPortfolioValue``, ``getPortfolioPerformance``,
  ``getPortfolioCostStructure`` and ``getPortfolioRisks``: the views of the same projects,
  summed from their rows, so that the list and the views tell the same story;
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
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from wftools.mockportfolio import (
    ALERT_THRESHOLD,
    PAGE,
    PROJECT_COUNT,
    WATCH_THRESHOLD,
    portfolio,
    portfolio_cost_structure,
    portfolio_page,
    portfolio_performance,
    portfolio_risks,
    portfolio_value,
)
from wftools.mockstructure import (
    CATEGORY_LABELS,
    COMMISSIONING,
    ELECTRICAL_RATE,
    LABOR,
    LINES_PER_TASK,
    NON_LABOR,
    PROVISION,
    JsonObject,
    JsonValue,
    draw,
    estimate_indicators,
    money,
    structure,
    task_lengthened,
)
from wftools.mockwitness import (
    CATEGORIES,
    ELECTRICAL_ENGINEERING,
    EQUIPMENT,
    FIXTURES,
    PROVISIONS,
    SUBCONTRACTING,
    fixture,
    identifier,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

VOLUME = FIXTURES / "volume"
"""Where the volumes are written: a directory the generator owns, entry by entry."""

LABOR_CATEGORY_COUNT = 150
CATEGORY_COUNT = 200
RATE_YEARS = range(2012, 2027)
"""Fifteen years of rates, up to the reference year of the witness estimate."""


USER = "01926f3a-7c00-7000-8000-000000000301"


_AUDIT: JsonObject = {
    "created_at": "2026-01-05T09:00:00Z",
    "created_by": {"kind": "user", "user_id": USER, "display_name": "Camille Martin"},
    "updated_at": "2026-01-05T09:00:00Z",
    "updated_by": {"kind": "user", "user_id": USER, "display_name": "Camille Martin"},
}

_DESCRIPTION = "Exemple engendré par `make mock-data` (`wftools.mockdata`) : il ne se retouche pas."


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
        (ELECTRICAL_ENGINEERING, CATEGORY_LABELS[ELECTRICAL_ENGINEERING]),
        (COMMISSIONING, CATEGORY_LABELS[COMMISSIONING]),
    ]
    labor.extend(
        (identifier(CATEGORIES, n), f"{_TRADES[n % len(_TRADES)]} — niveau {n // len(_TRADES) + 1}")
        for n in range(LABOR_CATEGORY_COUNT - len(labor))
    )
    non_labor = [
        (SUBCONTRACTING, CATEGORY_LABELS[SUBCONTRACTING]),
        (EQUIPMENT, CATEGORY_LABELS[EQUIPMENT]),
    ]
    others = CATEGORY_COUNT - LABOR_CATEGORY_COUNT - 1
    non_labor.extend(
        (
            identifier(CATEGORIES, LABOR_CATEGORY_COUNT + n),
            f"{_PURCHASES[n % len(_PURCHASES)]} — lot {n // len(_PURCHASES) + 1}",
        )
        for n in range(others - len(non_labor))
    )
    # Each category names its nature as the natures of the universe do (`cost_types.json`).
    natures = {nature["cost_type_id"]: nature["label"] for nature in fixture("cost_types")}
    return [
        *_categories(labor, "MO", "641", (LABOR, natures[LABOR])),
        *_categories(non_labor, "ACH", "604", (NON_LABOR, natures[NON_LABOR])),
        *_categories(
            [(PROVISIONS, CATEGORY_LABELS[PROVISIONS])],
            "PRV",
            "681",
            (PROVISION, natures[PROVISION]),
        ),
    ]


def _categories(
    entries: Iterable[tuple[str, str]], code: str, account: str, nature: tuple[str, str]
) -> list[JsonValue]:
    cost_type, cost_type_label = nature
    return [
        {
            "cost_category_id": category,
            "code": f"{code}-{rank:03d}",
            "label": label,
            "cost_type_id": cost_type,
            "cost_type_label": cost_type_label,
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
    projects = portfolio()
    rows = cast("list[JsonObject]", projects["items"])
    return {
        "nodes_thousand.json": _example(_structure_summary(built.nodes), built.nodes),
        "summary_dependencies.json": _example(
            "Ce dont dépend la date de fin de la première récapitulative de la structure aux "
            "volumes du §4.6.2 : ses subordonnées directes, nommées par leur numéro et leur "
            "libellé (WF-IHM-0030, WF-PLA-0040).",
            summary_dependencies(built.nodes),
        ),
        "task_lengthened.json": _example(
            "La durée de « Revue 3.1.27 » allongée de deux jours ouvrés dans la structure aux "
            "volumes du §4.6.2 : la tâche finit le 31 décembre 2026, dans sa marge, et « Reprise "
            "3.1.30 », qui la suit, glisse au premier jour ouvré de 2027 ; ses lignes sont "
            "consommées un an plus tard, leur montant corrigé de l'inflation et le sien changent "
            "(reinflated), sa marge diminue (rescheduled), les récapitulatives au-dessus et les "
            "totaux sont recalculés, le montant à l'année de référence inchangé (WF-PLA-0020, "
            "WF-DEV-0040, WF-DEV-0050).",
            task_lengthened(),
        ),
        "estimate_indicators.json": _example(
            f"Les indicateurs du devis de la structure aux volumes du §4.6.2, sommés sur les "
            f"mêmes lignes que la grille : {_amount(built.totals.amount)} au total, dont "
            f"{_amount(built.totals.by_cost_type[PROVISION])} de provisions, ventilés par "
            f"nature de coût et par sous-projet (WF-DEV-0060).",
            indicators,
        ),
        "portfolio_projects.json": _example(
            f"Les {_count(PROJECT_COUNT)} projets du portefeuille du §4.6.2, les projets en "
            f"cours et, ajoutés par la requête au périmètre par défaut (WF-PTF-0010), ceux en "
            f"chiffrage, le projet témoin et l'offre en tête ; indices classés par les seuils "
            f"de {_amount(WATCH_THRESHOLD, 1)} et {_amount(ALERT_THRESHOLD, 1)}.",
            projects,
        ),
        "portfolio_projects_page.json": _example(
            f"La deuxième page de {_count(PAGE)} projets de la liste du portefeuille du §4.6.2, "
            f"les projets en cours et, ajoutés par la requête au périmètre par défaut "
            f"(WF-PTF-0010), ceux en chiffrage, lue page par page : les projets "
            f"{_count(PAGE + 1)} à {_count(2 * PAGE)} sur {_count(PROJECT_COUNT)} (WF-PTF-0040).",
            portfolio_page(projects),
        ),
        "portfolio_value.json": _example(
            "La valeur du portefeuille du §4.6.2 au 16 mars 2026, les projets en chiffrage "
            "ajoutés par la requête au périmètre par défaut, les projets en cours "
            "(WF-PTF-0010) : le carnet des projets en cours, le pipeline des offres brut et "
            "pondéré par leur probabilité de gain, rien de "
            "réalisé, aucun projet du périmètre n'étant terminé, et le taux de transformation de "
            "dix offres sorties du chiffrage sur l'année, dont quatre gagnées (WF-PTF-0050).",
            portfolio_value(rows),
        ),
        "portfolio_performance.json": _example(
            "La performance des projets en cours du portefeuille du §4.6.2 au 16 mars 2026 : "
            "chaque indice est le rapport des sommes de leurs valeurs acquises, coûts réels et "
            "valeurs planifiées, la répartition compte chaque projet dans la zone de chacun de "
            "ses indices, et l'évolution court sur quatre trimestres, le premier non calculable, "
            "rien n'ayant encore été dépensé ni planifié (WF-PTF-0070).",
            portfolio_performance(rows),
        ),
        "portfolio_cost_structure.json": _example(
            "La structure des coûts des projets en cours du portefeuille du §4.6.2 au 16 mars "
            "2026 : leur budget de référence et leur reste à engager par nature, en montant et "
            "en part, et leur main-d'œuvre par nœud d'organisation ; aucune ventilation du coût "
            "réel (WF-PTF-0080).",
            portfolio_cost_structure(rows),
        ),
        "portfolio_risks.json": _example(
            "Les risques des projets en cours du portefeuille du §4.6.2 au 16 mars 2026 : le "
            "total des provisions identifiées, les dix risques les plus lourds avec leur projet, "
            "la matrice remplie, et les provisions survenues et écartées sur l'année "
            "(WF-PTF-0090).",
            portfolio_risks(rows),
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
