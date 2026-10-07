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
  of itself, the summaries above and the totals, recalculated from the same lines
  (``wftools.mockwrites``);
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

And the named examples of ``listNodes`` and of ``getComputedValueDependencies``, written under
``fixtures/api/`` by their name — ``nodes``, ``nodes_core``, ``nodes_planning``,
``nodes_estimate``, ``nodes_installation``, ``nodes_milestone``, ``nodes_risk_occurred``,
``dependencies_summary``, ``dependencies_summary_moved``, ``dependencies_labour``,
``dependencies_task_amount``, ``dependencies_provision``, ``dependencies_manual_float`` —:
readings of the readable core of the witness, described once in ``wftools.mockwitness`` and
dated in ``wftools.mockcore``, so that every example names each node by one identifier, one
lineage and one figure (EP-02/L21, #287); and the answers of the writes of the grids, made on
that core or on the structure of a thousand tasks, written beside them by ``wftools.mockwrites``
(EP-02/L22).

They live in the universe of the other examples: identifiers are kept, and what the
witness project, the offer and the labels of the universe say is read from their fixtures,
never copied here. Nothing here reads the clock or draws at random, so that two runs write
the same bytes. Amounts are ``Decimal`` and travel as the strings of the contract.

With ``--check``, nothing is written: the volumes directory is compared with what the
generator writes, and a file missing, outdated or unreadable, or any entry left over, fails; a
named example missing or outdated fails too.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from wftools import REPOSITORY, mockcore, mockhistory, mocktext, mocktoday, mockwrites, paths
from wftools.mockportfolio import (
    ALERT_THRESHOLD,
    PAGE,
    PROJECT_COUNT,
    UNOPENABLE_EVERY,
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
    COMMISSIONING_RATE,
    ELECTRICAL_RATE,
    LABOR,
    LINES_PER_TASK,
    NON_LABOR,
    PROVISION,
    JsonObject,
    JsonValue,
    draw,
    estimate_indicators,
    hourly_rate,
    money,
    structure,
)
from wftools.mockwitness import (
    ASSEMBLY,
    CATEGORIES,
    COMMISSIONING,
    CONTROL_STATION,
    CORE,
    ELECTRICAL_ENGINEERING,
    EQUIPMENT,
    FACTORY_ACCEPTANCE,
    FIXTURES,
    INSTALLATION,
    INSTALLED,
    LABOUR,
    PROVISIONS,
    STUDIES,
    SUBCONTRACTING,
    TIMELINES,
    TODAY,
    WIRING,
    fixture,
    identifier,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from wftools.mockwitness import Task

_day, _count, _amount, _example = mocktext.day, mocktext.count, mocktext.amount, mocktext.example
"""How the summaries write a day, a count and an amount, and the envelope of an example."""

VOLUME = "volume"
"""Where the volumes are written, under the fixtures: a directory the generator owns, entry by
entry. The named examples of the witness are written beside it, file by file."""

LABOR_CATEGORY_COUNT = 150
CATEGORY_COUNT = 200
RATE_YEARS = range(2012, 2027)
"""Fifteen years of rates, up to the reference year of the witness estimate."""


USER = "01926f3a-7c00-7000-8000-000000000301"


_AUDIT: JsonObject = {
    "created_at": mockhistory.stamp(INSTALLED.instant),
    "created_by": {"kind": "user", "user_id": USER, "display_name": "Camille Martin"},
    "updated_at": mockhistory.stamp(INSTALLED.instant),
    "updated_by": {"kind": "user", "user_id": USER, "display_name": "Camille Martin"},
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


def hourly_rates() -> list[JsonValue]:
    """Return the answer of listHourlyRates: the years of rates of the electrical engineering."""
    return [_rate(ELECTRICAL_ENGINEERING, ELECTRICAL_RATE, year) for year in RATE_YEARS]


def _rate(category: str, last_amount: Decimal, year: int) -> JsonObject:
    """Return the rate of a category for a year, grown by the step each year up to the last."""
    return {
        "cost_category_id": category,
        "year": year,
        "amount": money(hourly_rate(last_amount, year)),
        "audit": _AUDIT,
        "lock_version": 1,
    }


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


# --- The readings of the witness ------------------------------------------------------------

_WIRING, _ACCEPTANCE, _LABOUR, _PROVISION = WIRING, FACTORY_ACCEPTANCE, LABOUR, 555
_DESKS = 523
_RISK_OCCURRED = 541
_MILESTONE = "Réception usine"
"""The nodes of the core the readings and the dependencies are about (``mockwitness``)."""

_TASKS = frozenset({mockcore.TASK})


def named() -> dict[str, JsonObject]:
    """Return the named examples of the witness, by file name.

    Its readings, its writes, its history — its revisions compared and its risks —, and its
    indicators today.
    """
    return {
        **readings(),
        **mockwrites.writes(),
        **mockhistory.examples(),
        **mocktoday.examples(),
    }


def nested() -> tuple[Task, ...]:
    """Return the core with the lot of the control station ranged under the installation.

    A counterfactual variant, declared as such: its tree has four levels of tasks, the subtree
    the occurrence merged a summary of the third (WF-PLA-0110).
    """
    installation = replace(INSTALLATION, children=(CONTROL_STATION, *INSTALLATION.children))
    return tuple(
        installation if root is INSTALLATION else root
        for root in CORE
        if root is not CONTROL_STATION
    )


def wiring_completed() -> tuple[Task, ...]:
    """Return the core with the wiring of the cabinets declared completed today, by hand.

    Its finish is the day of the gesture, never later (WF-PLA-0130); the factory acceptance, a
    milestone whose one predecessor it is, keeps its date of 30 June, entered by hand, and is
    not started: its predecessors completed, nothing completes it by itself, and the Kanban
    invites one to (WF-RAE-0030).
    """
    declared = (date(2026, 5, 4), TODAY.date())
    acceptance = (date(2026, 6, 30), date(2026, 6, 30))
    roots = mockwrites.amended(
        CORE, mockwrites.on_task(_WIRING, manual=declared, progress="completed")
    )
    return mockwrites.amended(
        roots, mockwrites.on_task(_ACCEPTANCE, manual=acceptance, progress="not_started")
    )


def readings() -> dict[str, JsonObject]:
    """Return the named examples read from the core of the witness, by file name.

    Each is a reading of the one tree at TODAY — a subtree, with or without its lines, a
    search —, or what a computed value of one of its nodes depends on.
    """
    rows = mockcore.core()
    day = _day(TODAY.date())
    studies = mockcore.subtree(rows, STUDIES.number)
    estimate = mockcore.subtree(rows, CONTROL_STATION.number)
    total = cast("JsonObject", estimate["totals"])
    return {
        "nodes.json": _example(
            f"Le sous-arbre « Études » du cœur du témoin, lu avec ses lignes (subtree_of) le "
            f"{day} : la récapitulative, les études de détail terminées et leur ligne de "
            f"sous-traitance de {_amount(Decimal(100_000))}, les pupitres opérateurs en mode "
            f"manuel, démarrés et en dépassement de fin, la revue de conception, le jalon de "
            f"réception des études et le dossier de conception. Les numéros de ligne sont ceux "
            f"de toute la structure, où le cœur vient en tête (WF-PLA-0080, WF-DEV-0050).",
            studies,
        ),
        "nodes_core.json": _example(
            f"Le cœur du témoin lu entier, sans filtre, le {day} : les études, le lot « Poste de "
            f"commande » et l'installation sur site, avec leurs lignes, et les totaux de la "
            f"structure entière — ceux que rendent les écritures du cœur (NodeTotals, "
            f"WF-DEV-0050, WF-PLA-0080).",
            mockcore.whole(rows),
        ),
        "nodes_planning.json": _example(
            f"Le planning du groupe « Études », lu sans ses lignes (subtree_of, kinds=task) le "
            f"{day} : la récapitulative, les études de détail terminées et la revue de conception "
            f"qui les suit, sur le chemin critique, les pupitres opérateurs en mode manuel, sans "
            f"marge, démarrés et en dépassement de fin, le jalon de réception, lié en fin à début "
            f"à la revue et en début à début aux pupitres avec une semaine de décalage, et le "
            f"dossier de conception, lié avec deux jours d'avance, qui porte sa marge jusqu'à la "
            f"fin du cœur (WF-PLA-0030, WF-PLA-0040, WF-PLA-0080, WF-PLA-0100). Les numéros "
            f"de ligne sont ceux de toute la structure : la ligne des études de détail, que le "
            f"planning ne rend pas, garde le numéro 3 ; les totaux sont ceux des lignes retenues, "
            f"aucune.",
            mockcore.subtree(rows, STUDIES.number, _TASKS),
        ),
        "nodes_estimate.json": _example(
            f"Le devis du lot « Poste de commande », récapitulative rattachée au poste "
            f"« {ASSEMBLY.label} » du lotissement (WF-PLA-0130), lu avec ses lignes (subtree_of) "
            f"le {day} : "
            f"sous le câblage des armoires, démarré le 4 mai et qui s'achève le 30 juin, une "
            f"ligne de main-d'œuvre de 12,5 h à {_amount(ELECTRICAL_RATE)} — "
            f"{_amount(Decimal(1_000))} —, un débours de {_amount(Decimal('1234.56'))} et la "
            f"ligne de provision de {_amount(Decimal(500))} du risque de reprise du câblage, "
            f"dont la grille ne saisit ni les grandeurs ni le montant ; le sous-arbre fusionné "
            f"par la survenance du risque 752, ses lignes de 120 et 80 budgétées à zéro ; le "
            f"jalon de réception usine, le 30 juin. Le devis totalise "
            f"{_amount(Decimal(str(total['base_amount'])))}, dont "
            f"{_amount(Decimal(str(total['budgeted_amount'])))} budgétés (WF-DEV-0020, "
            f"WF-RIS-0060, WF-INTF-0180, WF-DAT-0100).",
            estimate,
        ),
        "nodes_installation.json": _example(
            f"L'installation sur site, lue avec ses lignes (subtree_of) le {day} : après la "
            f"réception usine, le montage des armoires sur site, du 1er juillet au 18 décembre "
            f"2026, son câblage par l'ingénieur électricien et l'assistance du technicien de mise "
            f"en service aux essais, tous deux sur la semaine standard, et la mise en service qui "
            f"le suit, démarrée en 2026 et consommée cette année-là, sur le chemin critique "
            f"jusqu'à la fin du cœur (WF-PLA-0010, WF-DEV-0040, WF-DEV-0050).",
            mockcore.subtree(rows, INSTALLATION.number),
        ),
        "nodes_milestone.json": _example(
            f"La recherche « {_MILESTONE} » dans la structure, le {day} : le jalon, tâche de durée "
            f"nulle au 30 juin 2026, et la récapitulative qui le porte, rendue pour la lisibilité "
            f"de l'arbre et absente des totaux (WF-PLA-0050, WF-PLA-0080).",
            mockcore.search(rows, _MILESTONE),
        ),
        "nodes_nested.json": _example(
            f"Variante contrefactuelle du planning du témoin, lue sans ses lignes (subtree_of, "
            f"kinds=task) le {day} : le lot « Poste de commande » rangé sous l'installation sur "
            f"site, de sorte que l'arbre a quatre niveaux de tâches — l'installation, le lot, le "
            f"sous-arbre fusionné par la survenance du risque 752, récapitulative du troisième "
            f"niveau, et ses deux tâches au quatrième (WF-PLA-0040, WF-PLA-0110).",
            mockcore.subtree(mockcore.core(nested()), INSTALLATION.number, _TASKS),
        ),
        "nodes_risk_occurred.json": _example(
            f"Le sous-arbre fusionné dans la structure principale de la révision en cours par la "
            f"survenance du risque « Retard de livraison des armoires », de gravité 200 à 30 %, lu "
            f"seul (subtree_of) le {day} : ses deux tâches, terminées en mai, et leurs lignes de "
            f"120 et 80, aux montants budgétés nuls — la survenance ne déplace pas la référence — "
            f"et réestimés de 120 et 80 ; la ligne de provision a disparu, et la récapitulative "
            f"somme ses lignes (WF-RIS-0060, WF-RIS-0050).",
            mockcore.subtree(rows, _RISK_OCCURRED),
        ),
        "timelines.json": _example(
            f"Les chronologies du projet témoin le {day} (WF-PLA-0140) : le comité de pilotage, "
            f"auquel sont inscrits les études, leur réception, la réception usine et la mise en "
            f"service, et la revue client, les deux réceptions — inscriptions que porte chaque "
            f"tâche (`tracking`, WF-PLA-0060).",
            [{"timeline_id": timeline, "label": label} for timeline, label in TIMELINES],
        ),
        "startable_tasks.json": _example(
            f"Le Kanban du cœur du témoin le {day}, sur la révision en cours : les tâches "
            f"démarrées, les pupitres opérateurs, en mode manuel et en dépassement de fin, et le "
            f"câblage des armoires ; aucune tâche à démarrer — la réception usine attend la fin du "
            f"câblage, et rien ne se termine seul. Jamais une récapitulative, dont l'état dérive "
            f"de ses subordonnées (WF-RAE-0030, WF-PLA-0040).",
            mockcore.startable(rows),
        ),
        "startable_tasks_milestone.json": _example(
            f"Le Kanban du cœur du témoin le {day}, le câblage des armoires déclaré terminé ce "
            f"jour-là : la réception usine, jalon dont le seul prédécesseur est terminé, posée à "
            f"la main au 30 juin, non démarrée tant que personne ne la termine, et signalée à "
            f"terminer ; les "
            f"pupitres opérateurs toujours démarrés, en dépassement de fin (WF-RAE-0030, "
            f"WF-PLA-0130).",
            mockcore.startable(mockcore.core(wiring_completed())),
        ),
        "dependencies_summary.json": _example(
            "Ce dont dépend la date de fin de la récapitulative « Études » du planning : ses cinq "
            "subordonnées directes, nommées par leur numéro et leur libellé, que la grille les "
            "montre ou non (WF-IHM-0030, WF-PLA-0040).",
            mockcore.dependencies(rows, STUDIES.number, "task.finish"),
        ),
        "dependencies_summary_moved.json": _example(
            "Ce dont dépend la date de fin de la récapitulative « Études », relue après "
            "l'insertion d'une ligne au-dessus de ses subordonnées : les mêmes subordonnées "
            "directes, sous leurs nouveaux numéros, la récapitulative elle-même inchangée "
            "(WF-IHM-0030, WF-PLA-0040).",
            mockcore.dependencies(rows, STUDIES.number, "task.finish", inserted_above=1),
        ),
        "dependencies_labour.json": _example(
            "Ce dont dépend le montant à l'année de référence de la ligne de main-d'œuvre du "
            "devis : le taux horaire de sa catégorie pour l'année de référence ; aucune ligne "
            "(WF-IHM-0030, WF-DEV-0030, WF-DEV-0050).",
            mockcore.dependencies(rows, _LABOUR, "estimate_line.base_amount"),
        ),
        "dependencies_task_amount.json": _example(
            "Ce dont dépend le montant à l'année de référence de la tâche « Câblage des "
            "armoires » : les trois lignes qu'elle porte (WF-IHM-0030, WF-DEV-0050).",
            mockcore.dependencies(rows, _WIRING, "task.base_amount"),
        ),
        "dependencies_provision.json": _example(
            "Ce dont dépend la quantité de la ligne de provision du devis : son risque "
            "(WF-IHM-0030, WF-RIS-0010).",
            mockcore.dependencies(rows, _PROVISION, "estimate_line.quantity"),
        ),
        "dependencies_manual_float.json": _example(
            "Ce dont dépend la marge de la tâche en mode manuel du planning : son mode, qui ne "
            "lui en donne aucune (WF-IHM-0030, WF-PLA-0100).",
            mockcore.dependencies(rows, _DESKS, "task.total_float"),
        ),
    }


# --- Writing and checking ------------------------------------------------------------------


def volumes() -> dict[str, JsonObject]:
    """Return every volume, as the example of the contract its file holds, by file name."""
    built = structure()
    # The witness is read in memory, never from the file the same command writes.
    witness = mocktoday.estimate_today()
    labels = {nature["cost_type_id"]: nature["label"] for nature in fixture("cost_types")}
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
            mockwrites.task_lengthened(),
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
            f"de {_amount(WATCH_THRESHOLD, 1)} et {_amount(ALERT_THRESHOLD, 1)}. La liste est "
            f"lue par un contributeur sans « consulter tous les projets » : chaque "
            f"{_ordinal(UNOPENABLE_EVERY)} projet engendré, qu'il ne peut pas ouvrir, figure sous "
            f"son libellé et son code, sans lien (can_open faux), et compte dans les totaux "
            f"(WF-PTF-0030, WF-ADM-0110).",
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
            "la matrice remplie, la couverture des risques agrégée — la somme des réserves "
            "de référence face aux provisions restantes et au coût des risques survenus —, et "
            "les provisions survenues et écartées sur l'année (WF-PTF-0090, WF-RIS-0050). Un "
            "risque dit si le lecteur peut ouvrir son projet, comme la ligne de ce projet dans "
            "la liste (WF-PTF-0030).",
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


_ORDINALS = {7: "septième", 9: "neuvième"}


def _ordinal(value: int) -> str:
    return _ORDINALS[value]


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


def write(fixtures: Path) -> list[Path]:
    """Write the volumes under the fixtures, and the named examples of the witness among them.

    The volumes directory is owned: a file it no longer makes is removed, a directory left in it
    is not — the check names it, to be removed by hand. The named examples are written file by
    file beside the other examples. The text is written with plain line ends whatever the
    system, as the check reads it.
    """
    directory = fixtures / VOLUME
    directory.mkdir(parents=True, exist_ok=True)
    expected = {name: render(example) for name, example in volumes().items()}
    for stale in sorted(set(_entries(directory)) - expected.keys()):
        if (directory / stale).is_file():
            (directory / stale).unlink()
    written: list[Path] = []
    for name, text in expected.items():
        written.append(_write(directory / name, text))
    for name, example in named().items():
        written.append(_write(fixtures / name, render(example)))
    return written


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def check(fixtures: Path, declared: Iterable[str] | None = None) -> list[str]:
    """Return what differs between the fixtures and what the generator writes.

    The named examples ``tools/paths.toml`` declares written by ``make mock-data`` — given
    here, or read from it — must each be one the generator writes: a name declared and not
    written would be left out of the size of a lot without being checked.
    """
    directory = fixtures / VOLUME
    expected = {name: render(example) for name, example in volumes().items()}
    present = _entries(directory)
    problems = [_left_over(directory / name) for name in sorted(set(present) - expected.keys())]
    for name, text in expected.items():
        problems.extend(_differences(directory / name, text, f"{VOLUME}/{name}"))
    examples = named()
    for name, example in examples.items():
        problems.extend(_differences(fixtures / name, render(example), name))
    problems.extend(
        f"{name} is declared generated by {BY}, which does not write it"
        for name in (declared_names() if declared is None else declared)
        if name not in examples
    )
    return problems


BY = "make mock-data"
"""The command ``tools/paths.toml`` names for what this module writes."""


def declared_names() -> list[str]:
    """Return the named examples ``tools/paths.toml`` declares written by this module.

    The paths under the fixtures without a wildcard: the volumes directory is declared whole.
    """
    prefix = FIXTURES.relative_to(REPOSITORY).as_posix() + "/"
    return [
        path.removeprefix(prefix)
        for entry in paths.read().generated
        if entry.by == BY
        for path in entry.paths
        if path.startswith(prefix) and "*" not in path
    ]


def _differences(path: Path, text: str, name: str) -> list[str]:
    """Name a file missing, or one that does not hold the text the generator writes."""
    if not path.exists():
        return [f"{name} is missing"]
    if not _holds(path, text):
        return [f"{name} is outdated"]
    return []


def _left_over(path: Path) -> str:
    """Name an entry the generator does not make: a directory, `write` does not remove."""
    if path.is_dir():
        return f"{VOLUME}/{path.name} is a directory left over, {BY_HAND}"
    return f"{VOLUME}/{path.name} is left over"


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


def main(arguments: list[str], fixtures: Path = FIXTURES) -> int:
    """Write the volumes, or check that the versioned ones are what the generator writes."""
    parser = argparse.ArgumentParser(
        prog="wftools.mockdata", description="Generate the volumes the fake back serves."
    )
    parser.add_argument("--check", action="store_true", help="compare, write nothing")
    options = parser.parse_args(arguments)
    if options.check:
        problems = check(fixtures)
        for problem in problems:
            remedy = "" if problem.endswith(BY_HAND) else ", run make mock-data"
            print(f"  {fixtures}: {problem}{remedy}", file=sys.stderr)
        return 1 if problems else 0
    for path in write(fixtures):
        print(f"  -> {path} ({path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
