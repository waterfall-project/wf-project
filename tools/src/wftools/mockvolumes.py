# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The volumes of §4.6.2, as the examples of the contract hold them.

Split from ``wftools.mockdata``, which writes and checks them, to keep it under the nine hundred
lines (US-2520): it reads the volumes here, and the categories and rates from
``wftools.mockrates``.
"""

from collections import Counter
from decimal import Decimal
from typing import Any, cast

from wftools import (
    mockcomparisons,
    mockcore,
    mockids,
    mockplanning,
    mockportfoliotime,
    mockrates,
    mockreference,
    mocktext,
    mocktoday,
    mockwrites,
)
from wftools.mockportfolio import (
    ALERT_THRESHOLD,
    PERIOD_FROM,
    PROJECT_COUNT,
    QUARTERS,
    UNOPENABLE_EVERY,
    WATCH_THRESHOLD,
    portfolio,
    portfolio_cost_structure,
    portfolio_filtered,
    portfolio_page,
    portfolio_performance,
    portfolio_risks,
    portfolio_value,
    risk_volume,
)
from wftools.mockstructure import ELECTRICAL_RATE, LINES_PER_TASK, JsonObject, JsonValue
from wftools.mocktext import PAGE
from wftools.mockwitness import TODAY
from wftools.mockwitnessrisks import REGISTER

_day, _count, _amount, _example = mocktext.day, mocktext.count, mocktext.amount, mocktext.example
"""How the summaries write a day, a count and an amount, and the envelope of an example."""


def volumes() -> dict[str, JsonObject]:
    """Return every volume, as the example of the contract its file holds, by file name."""
    rows = mockcore.current()
    nodes = mockcore.whole(rows)
    # The witness is read in memory, never from the file the same command writes.
    indicators = mocktoday.estimate_today()
    total = cast("JsonObject", indicators["total"])
    provisions = Decimal(cast("str", indicators["provisions_identified"]))
    projects = portfolio()
    rows = cast("list[JsonObject]", projects["items"])
    years = mockrates.RATE_YEARS
    return {
        "nodes_thousand.json": _example(_structure_summary(nodes), nodes),
        "comparison_volume.json": mockcomparisons.comparison_volume(),
        "summary_dependencies.json": _example(
            "Ce dont dépend la date de fin de la première récapitulative de la structure aux "
            "volumes du §4.6.2 : ses subordonnées directes, nommées par leur numéro et leur "
            "libellé (WF-IHM-0030, WF-PLA-0040).",
            summary_dependencies(nodes),
        ),
        "task_lengthened.json": _example(
            f"La durée de « {mockwrites.LENGTHENED} » allongée de "
            f"{mocktext.count(mockwrites.LENGTHENED_BY)} jours ouvrés dans la structure du témoin "
            "aux volumes du §4.6.2 : la tâche finit le 31 décembre 2026, dans sa marge, et "
            "« Reprise 2.1.30 », qui la suit, glisse au premier jour ouvré de 2027 ; ses lignes "
            "sont consommées un an plus tard, leur montant réestimé, inflation comprise, et le "
            "sien changent (reinflated), sa marge et celle des tâches de sa chaîne diminuent "
            "(rescheduled), les récapitulatives au-dessus et les totaux sont recalculés ; le "
            "budgété, projeté sur l'année où la référence consommait les lignes, et le montant "
            "aux taux de l'année de référence inchangés (WF-PLA-0020, WF-DEV-0020, WF-DEV-0040).",
            mockwrites.task_lengthened(),
        ),
        "structure_planning_start_advanced.json": mockplanning.example(),
        "estimate_indicators_volume.json": _example(
            f"Les indicateurs du devis de la structure aux volumes du §4.6.2, sommés sur les "
            f"mêmes lignes que la grille : {_amount(Decimal(cast('str', total['value'])))} au "
            f"total, dont {_amount(provisions)} de provision, celle du risque identifié, ventilés "
            f"par nature de coût et par sous-projet, et le poste du lotissement que porte le lot "
            f"« Poste de commande » (WF-DEV-0060). La lecture du témoin lui-même "
            f"(estimate_indicators), qui somme toute sa structure depuis EP-14/L45a.",
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
            f"(WF-PTF-0030, WF-ADM-0110). La ligne du témoin est celle de ses indicateurs, toute "
            f"sa structure sommée.",
            projects,
        ),
        "portfolio_projects_page.json": _example(
            f"La deuxième page de {_count(PAGE)} projets de la liste du portefeuille du §4.6.2, "
            f"les projets en cours et, ajoutés par la requête au périmètre par défaut "
            f"(WF-PTF-0010), ceux en chiffrage, lue page par page : les projets "
            f"{_count(PAGE + 1)} à {_count(2 * PAGE)} sur {_count(PROJECT_COUNT)} (WF-PTF-0040).",
            portfolio_page(projects),
        ),
        "portfolio_projects_filtered.json": portfolio_filtered(projects),
        "portfolio_value.json": _example(
            f"La valeur du portefeuille du §4.6.2 au {_day(TODAY.date())}, les projets en "
            "chiffrage ajoutés par la requête au périmètre par défaut, les projets en cours "
            "(WF-PTF-0010) : le carnet des projets en cours, le pipeline des offres brut et "
            "pondéré par leur probabilité de gain, rien de "
            "réalisé, aucun projet du périmètre n'étant terminé, et le taux de transformation de "
            "dix offres sorties du chiffrage sur l'année, dont quatre gagnées (WF-PTF-0050).",
            portfolio_value(rows),
        ),
        "portfolio_performance.json": _example(
            f"La performance des projets en cours du portefeuille du §4.6.2 au "
            f"{_day(TODAY.date())} : chaque indice est le rapport des sommes de leurs "
            f"valeurs acquises, coûts réels et valeurs planifiées, la répartition compte "
            f"chaque projet dans la zone de chacun de ses indices, et l'évolution court sur "
            f"les {_count(len(QUARTERS))} trimestres que touche la période par défaut, du "
            f"{_day(PERIOD_FROM)} au {_day(TODAY.date())}, chacun lu à sa fin — le dernier au "
            f"jour —, les deux premiers non calculables, rien n'ayant encore été dépensé ni "
            f"planifié (WF-PTF-0070).",
            portfolio_performance(rows, mockportfoliotime.quarterly(rows)),
        ),
        "portfolio_cost_structure.json": _example(
            f"La structure des coûts des projets en cours du portefeuille du §4.6.2 au "
            f"{_day(TODAY.date())} : leur budget de référence, hors lignes de provision, et leur "
            "reste à engager, provisions comprises, par nature, en montant et en part, et leur "
            "main-d'œuvre par nœud d'organisation de ses rôles — celle du monteur câbleur, que "
            "seul le projet témoin emploie, à l'atelier de câblage, le reste au bureau d'études "
            "électricité ; aucune ventilation du coût réel (WF-PTF-0080, WF-IND-0020). Aucun "
            "projet terminé n'est dans la période par défaut.",
            portfolio_cost_structure(rows),
        ),
        "portfolio_risks.json": _example(
            f"Les risques des projets en cours du portefeuille du §4.6.2 au "
            f"{_day(TODAY.date())}, {risk_volume(rows)} : le total des provisions identifiées, "
            f"les dix risques "
            f"les plus lourds avec leur projet, la matrice remplie — chaque risque identifié "
            f"compté dans sa case et placé en point à ses valeurs exactes, avec son projet —, "
            f"la couverture des risques "
            f"agrégée — la somme des réserves de référence des projets face aux provisions "
            f"restantes et au coût des risques survenus —, et les provisions survenues et "
            f"écartées sur l'année (WF-PTF-0090, WF-RIS-0050). Un risque dit si le lecteur "
            f"peut ouvrir son projet, comme la ligne de ce projet dans la liste (WF-PTF-0030).",
            portfolio_risks(rows),
        ),
        **mockreference.examples(mockrates.categories(), mockrates.hourly_rate_grid()),
        "hourly_rates.json": _example(
            f"{_count(len(years))} ans de taux horaires de l'ingénierie électrique, de "
            f"{years[0]} à {years[-1]}, l'année de référence du devis, où il vaut "
            f"{_amount(ELECTRICAL_RATE)} de l'heure.",
            mockrates.hourly_rates(),
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
    drawn = [task for task in tasks if not task["node_id"].startswith(mockids.PREFIX + "0000")]
    count = Counter(
        "milestone" if task["task"]["is_milestone"] else task["level"]
        for task in drawn
        if task["task"]["is_milestone"] or task["task"]["is_summary"]
    )
    work = len(drawn) - sum(count.values())
    day = _day(TODAY.date())
    return (
        f"La structure principale du projet témoin aux volumes du §4.6.2, lue le {day} : "
        f"{_count(len(tasks))} tâches et {_count(len(lines))} lignes de devis, "
        f"{LINES_PER_TASK} par tâche. En tête, son cœur lisible — les études, le lot « Poste de "
        f"commande » et l'installation sur site —, puis {_count(count[1])} phases tirées autour "
        f"de lui et reliées à lui, {_count(count[2])} lots, leurs {_count(work)} tâches de "
        f"travail, cinq lignes sur chacune et une sixième sur certaines, et leurs "
        f"{_count(count['milestone'])} jalons. Les tâches sont datées en heures de travail sur "
        f"le calendrier de leurs rôles — le câblage, au monteur câbleur, sur la semaine de "
        f"quatre jours —, avec leur marge et le chemin critique de toute la structure, et leur "
        f"avancement est celui du jour (WF-PLA-0010, WF-PLA-0100, WF-PLA-0160). Les devis propres "
        f"des trente risques par projet que le §4.6.2 compte en plus sont d'autres structures, "
        f"que cette lecture ne porte pas : le témoin en a {_count(len(REGISTER))}."
    )


_ORDINALS = {7: "septième", 9: "neuvième"}


def _ordinal(value: int) -> str:
    return _ORDINALS[value]
