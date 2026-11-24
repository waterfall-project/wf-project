# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Generate the volumes the fake back serves: the sizes of §4.6.2 (EP-02/L2).

Usage: ``python -m wftools.mockdata [--check]``.

The volumes themselves are made by ``wftools.mockvolumes``, from the categories and the rates of
``wftools.mockrates``; this module writes and checks them (US-2520).

Examples of the contract, written under ``fixtures/api/volume/`` and cited by it:

- ``nodes_thousand.json``, ``listNodes``: the structure of a thousand tasks and their lines
  (``wftools.mockstructure``);
- ``comparison_volume.json``, ``compareRevisions``: the offer and the reference compared over that
  whole structure, read with ``fields`` as the screen of the comparison reads it
  (``wftools.mockhistory``, #1201);
- ``estimate_indicators_volume.json``, ``getEstimateIndicators``: the indicators of that estimate,
  the reading of the witness itself since it sums its whole structure (``wftools.mocktoday``,
  EP-14/L45a), so that the fake back tells the same story on both;
- ``summary_dependencies.json``, ``getComputedValueDependencies``: what the finish date of its
  first summary depends on, its direct subordinates named from the same structure — the
  refusal the journeys try on it;
- ``task_lengthened.json``, ``updateTaskFacet``: a duration lengthened in that structure, which
  pushes a successor into the next year — its schedule, the amounts corrected of its lines and
  of itself, the summaries above and the totals, recalculated from the same lines
  (``wftools.mockwrites``);
- ``structure_planning_start_advanced.json``, ``updateCostStructure``: the planning start of that
  structure advanced a week, in a declared variant read before any task started — the tasks in
  automatic mode it redates (``wftools.mockplanning``, WF-PLA-0020);
- ``portfolio_projects.json``, ``getPortfolioProjects``: the projects of the portfolio, the
  witness project and the offer of the other examples first, and ``portfolio_projects_page.json``,
  its second page of fifty, and ``portfolio_projects_filtered.json``, read with column filters
  (``portfolio_projects_bounds_inverted.json`` and
  ``portfolio_projects_marking_period_inverted.json``, the refusals of its bounds and of its period
  of marking, are written by ``wftools.mockportfolio``);
- ``portfolio_value.json``, ``portfolio_performance.json``, ``portfolio_cost_structure.json``
  and ``portfolio_risks.json``, of ``getPortfolioValue``, ``getPortfolioPerformance``,
  ``getPortfolioCostStructure`` and ``getPortfolioRisks``: the views of the same projects,
  summed from their rows, so that the list and the views tell the same story;
- ``cost_categories.json``, ``listCostCategories``: the categories of §4.6.2, most of them labour —
  the rows of the grid of hourly rates —, and their second page (``wftools.mockreference``);
- ``hourly_rates.json``, ``listHourlyRates``: fifteen years of rates of one labour category;
- ``hourly_rate_grid.json``, ``getHourlyRateGrid``: the grid of hourly rates, the labour
  categories in rows and the fifteen years in columns (#162), and its first page sorted by the
  rate of the reference year (``wftools.mockreference``).

And the named examples of ``listNodes`` and of ``getComputedValueDependencies``, written under
``fixtures/api/`` by their name — ``nodes``, ``nodes_core``, ``nodes_planning``, ``nodes_estimate``,
``nodes_estimate_sorted`` and ``nodes_estimate_hours`` (sorted by ``wftools.mocksort``),
``nodes_installation``, ``nodes_milestone``, ``nodes_risk_occurred``, ``dependencies_summary``,
``dependencies_summary_moved``, ``dependencies_labour``, ``dependencies_labour_category``,
``dependencies_task_amount``, ``dependencies_provision``, ``dependencies_manual_float``,
``dependencies_provision_subproject`` —: readings of the readable core of the witness, described
once in ``wftools.mockwitness`` and dated in ``wftools.mockcore``, so that every example names each
node by one identifier, one lineage and one figure (EP-02/L21, #287); and the answers of the writes
of the grids, made on that core or on the structure of a thousand tasks, written beside them by
``wftools.mockwrites`` (EP-02/L22), and those of the gestures of the structure and of the entries of
a task, by ``wftools.mockgestures`` (EP-15/US-0460) — those of the estimate made on the amendment 2
by ``wftools.mockamendmentwrites`` (#1214) —, and the refusals of a paste and of an import, by
``wftools.mockexchanges`` (EP-15/US-0460), and those of a date on a day without hours of work,
refused entered and kept imported, by ``wftools.mocknonworking`` (#1271); and the answers of the
entries of a risk, by ``wftools.mockriskwrites`` (EP-15/US-0520); and the revisions of the witness
while the designation of its reference is open, by ``wftools.mockcycle`` (US-0490/L2); and its exit,
its code refused and its readings by the quality of its reader, by ``wftools.mockproject``
(US-0701/L9); and the refusals of one form each, by ``wftools.mockrefusals`` (US-0702/L1); and the
refusals the contract declared without a code, a condition nor an example, by
``wftools.mockdeclared`` (US-0702/L2); and the examples of the majors of the review of the
2026-10-31, by ``wftools.mockreview`` (US-0704), with the Kanban of the summary that awaits its own
lines (US-1240); and the examples of the contract of the exchanges that EP-33 changes, by
``wftools.mockimportfindings`` (US-3250/L1), and those of the WBS element compared whole and of the
free subproject code, by ``wftools.mockfreecodes`` (US-3270/L1); and the chronology, the tasks, the
lines and the costs of the witness, by ``wftools.mockchronology`` and ``mockwitness*``.

They live in the universe of the other examples: identifiers are kept, and what the witness project,
the offer and the labels of the universe say is read from their fixtures, never copied here. Nothing
here reads the clock or draws at random, so that two runs write the same bytes. Amounts are
``Decimal`` and travel as the strings of the contract.

With ``--check``, nothing is written: the volumes directory is compared with what the
generator writes, and a file missing, outdated or unreadable, or any entry left over, fails; a
named example missing or outdated fails too.
"""

import argparse
import sys
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import (
    REPOSITORY,
    mockadminrefusals,
    mockamendment,
    mockamendmentwrites,
    mockanonymized,
    mockaudit,
    mockauditadmin,
    mockchronology,
    mockcomparisons,
    mockcore,
    mockcosts,
    mockcycle,
    mockdeclared,
    mockdifferentials,
    mockexchanges,
    mockfreecodes,
    mockgestures,
    mockhistory,
    mockimportfindings,
    mockkanban,
    mocklists,
    mocknonworking,
    mockportfolio,
    mockportfoliotime,
    mockproject,
    mockrates,
    mockrebase,
    mockreference,
    mockrefusals,
    mockrender,
    mockreview,
    mockrevisionminors,
    mockriskwrites,
    mockservedrefusals,
    mocksliceviews,
    mocksnapshot,
    mocksort,
    mockspendingrefusals,
    mocktext,
    mocktoday,
    mockvolumes,
    mockwitness,
    mockwitnesscostfile,
    mockwitnesslines,
    mockwitnessrisksfile,
    mockwitnesstasks,
    mockwrites,
    paths,
)
from wftools.mockids import universe
from wftools.mockstructure import (
    ELECTRICAL_RATE,
    JsonObject,
    described,
)
from wftools.mockwitness import (
    CONTROL_STATION,
    CORE,
    CREATED_PROJECT,
    CREATED_TIMELINE,
    DEFAULT_BREAKDOWN,
    FIRST_ITEM,
    FIRST_LOT,
    FIXTURES,
    INSTALLATION,
    STEERING,
    STUDIES,
    TIMELINES,
    TODAY,
    WORK_BREAKDOWN,
    N,
)
from wftools.mockwitnessrisks import OCCURRENCE_EXAMPLE

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from wftools.mockwitness import Task

_day, _count, _amount, _example = mocktext.day, mocktext.count, mocktext.amount, mocktext.example
"""How the summaries write a day, a count and an amount, and the envelope of an example."""

VOLUME = "volume"
"""Where the volumes are written, under the fixtures: a directory the generator owns, entry by
entry. The named examples of the witness are written beside it, file by file."""

# --- The readings of the witness ------------------------------------------------------------

_WIRING, _ACCEPTANCE, _LABOUR, _PROVISION = N.WIRING, N.FACTORY_ACCEPTANCE, N.LABOUR, N.PROVISION
_DESKS = N.DESKS
_RISK_OCCURRED = N.MERGED
_MILESTONE = "Réception usine"
"""The nodes of the core the readings and the dependencies are about (``mockwitness``)."""

_TASKS = frozenset({mockcore.TASK})


def named() -> dict[str, JsonObject]:
    """Return the named examples of the witness, by file name.

    Its readings, its writes, its history — its revisions compared and its risks —, its indicators
    today, its actual costs with the journal of their imports; the views of the portfolio over time
    (``mockportfoliotime``); the audit (``mockaudit``) and its variants of the administration and of
    a restore (``mockauditadmin``); the lists of the reference (``mockreference``), of the projects,
    the subprojects and the contributors (``mocklists``), the contributors once an account is
    anonymised (``mockanonymized``); the exit of the witness (``mockproject``); the refusals of one
    form each (``mockrefusals``), those the contract declared without a code, a condition nor an
    example (``mockdeclared``), of the administration (``mockadminrefusals``), served undeclared
    (``mockservedrefusals``), of the differentials (``mockdifferentials``); the contract of the
    exchanges of EP-33 (``mockimportfindings``) and of the free codes (``mockfreecodes``); the
    update of the amendment 2 (``mockrebase``); the majors of the review (``mockreview``); the
    loaders' (``mockwitness*``, ``mockchronology``).
    """
    marked = mocksnapshot.revisions(mockrates.categories())
    return {
        **readings(),
        **mockwrites.writes(),
        **mockkanban.examples(),
        **mockgestures.examples(),
        **mockamendmentwrites.examples(),
        **mockexchanges.examples(),
        **mocknonworking.examples(),
        **mockamendment.examples(marked["revision_marked"]),
        **mocksnapshot.examples(marked),
        **mockhistory.examples(),
        **mockcycle.examples(),
        **mockcomparisons.examples(),
        **mockriskwrites.examples(),
        **mocktoday.examples(),
        **mockcosts.examples(),
        **mockportfoliotime.examples(),
        **mockportfolio.refusals(),
        **mockaudit.examples(),
        **mockauditadmin.examples(),
        **mockreference.named(),
        **mocklists.examples(),
        **mockanonymized.examples(),
        **mockproject.examples(),
        **mockrefusals.examples(),
        **mockadminrefusals.examples(),
        **mockdeclared.examples(),
        **mockreview.examples(),
        **mockrevisionminors.examples(),
        **mockdifferentials.examples(),
        **mockrebase.examples(),
        **mockservedrefusals.examples(),
        **mockimportfindings.examples(),
        **mockfreecodes.examples(),
        **mockspendingrefusals.examples(),
        **mockchronology.examples(),
        **mockwitnesstasks.examples(),
        **mockwitnesslines.examples(),
        **mockwitnesscostfile.examples(),
        **mockwitnessrisksfile.examples(),
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
    rows = mockcore.current()
    facets = {
        row.number: cast("JsonObject", row.node["task"]) for row in rows if row.kind == "task"
    }
    day = _day(TODAY.date())
    studies = mockcore.subtree(rows, STUDIES.number)
    estimate = mockcore.subtree(rows, CONTROL_STATION.number)
    total = cast("JsonObject", estimate["totals"])
    [provision] = [row.amounts.base for row in rows if row.number == _PROVISION]
    # The Kanban of the whole structure, today and after the wiring declared completed (#528).
    today = mockkanban.kanban(rows)
    gesture = mockkanban.kanban(mockcore.current(described(wiring_completed())))
    core = {universe(row.number) for row in rows if row.number < mockwitness.GENERATED}
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
            f"Variante contrefactuelle : le cœur du témoin lu seul, sans filtre, comme si la "
            f"structure ne portait que lui, le {day} — marges jusqu'à la fin du cœur, totaux du "
            f"cœur, et non ceux de la structure de mille tâches qui le porte en tête : les études, "
            f"le lot « Poste de commande » et l'installation sur site, avec leurs lignes "
            f"(NodeTotals, WF-DEV-0050, WF-PLA-0080).",
            mockcore.whole(mockcore.alone()),
        ),
        "nodes_planning.json": _example(
            f"Le planning du groupe « Études », lu sans ses lignes (subtree_of, kinds=task) le "
            f"{day} : la récapitulative, les études de détail terminées et la revue de conception "
            f"qui les suit, {mocktext.float_said(facets[N.DESIGN_REVIEW])}, les pupitres "
            f"opérateurs en mode manuel, sans "
            f"marge, démarrés et en dépassement de fin, le jalon de réception, lié en fin à début "
            f"à la revue et en début à début aux pupitres avec une semaine de décalage, et le "
            f"dossier de conception, lié avec deux jours d'avance, sans successeur, "
            f"{mocktext.float_said(facets[N.DESIGN_FILE])} jusqu'à la fin de la structure "
            f"(WF-PLA-0030, WF-PLA-0040, WF-PLA-0080, WF-PLA-0100). Les numéros "
            f"de ligne sont ceux de toute la structure : la ligne des études de détail, que le "
            f"planning ne rend pas, garde le numéro 3 ; les totaux sont ceux du sous-arbre lu, "
            f"sa ligne comprise, que `kinds` ne rend pas (#487).",
            mockcore.subtree(rows, STUDIES.number, _TASKS),
        ),
        "nodes_estimate.json": _example(
            f"Le devis de la récapitulative « Poste de commande », rattachée au lot "
            f"« {FIRST_LOT.label} » du lotissement (WF-PLA-0170), lu avec ses lignes (subtree_of) "
            f"le {day} : "
            f"sous le câblage des armoires, démarré le 4 mai et qui s'achève le 30 juin, une "
            f"ligne de main-d'œuvre de 12,5 h à {_amount(ELECTRICAL_RATE)} — "
            f"{_amount(Decimal(1_000))} —, un débours de {_amount(Decimal('1234.56'))} et la "
            f"ligne de provision de {_amount(provision)} du risque de reprise du câblage, "
            f"dont la grille ne saisit ni les grandeurs ni le montant ; le sous-arbre fusionné "
            f"par la survenance du risque 752, ses lignes de 120 et 80 budgétées à zéro ; le "
            f"jalon de réception usine, le 30 juin. Le devis totalise "
            f"{_amount(Decimal(str(total['base_amount'])))}, dont "
            f"{_amount(Decimal(str(total['budgeted_amount'])))} budgétés (WF-DEV-0020, "
            f"WF-RIS-0060, WF-INTF-0180, WF-DAT-0100).",
            estimate,
        ),
        **mocksort.examples(rows),
        "nodes_installation.json": _example(
            f"L'installation sur site, lue avec ses lignes (subtree_of) le {day} : après la "
            f"réception usine, le montage des armoires sur site, "
            f"{mocktext.span(facets[N.MOUNTING])}, son câblage par l'ingénieur électricien et "
            f"l'assistance du technicien de mise en service aux essais, tous deux sur la semaine "
            f"standard, et la mise en service qui le suit, "
            f"{mocktext.span(facets[N.COMMISSIONING])}, "
            f"consommée l'année où elle démarre, {mocktext.float_said(facets[N.COMMISSIONING])} "
            f"jusqu'au jalon de la mise en service du poste de commande (WF-PLA-0010, "
            f"WF-DEV-0040, WF-DEV-0050).",
            mockcore.subtree(rows, INSTALLATION.number),
        ),
        "nodes_milestone.json": _example(
            f"La recherche « {_MILESTONE} » dans la structure, le {day} : le jalon, tâche de durée "
            f"nulle au 30 juin 2026, et la récapitulative qui le porte, rendue pour la lisibilité "
            f"de l'arbre et absente des totaux (WF-PLA-0050, WF-PLA-0080).",
            mockcore.search(rows, _MILESTONE),
        ),
        "nodes_nested.json": _example(
            f"Variante contrefactuelle du planning du témoin, son cœur lu seul — marges jusqu'à la "
            f"fin du cœur, totaux du cœur —, lue sans ses lignes (subtree_of, "
            f"kinds=task) le {day} : le lot « Poste de commande » rangé sous l'installation sur "
            f"site, de sorte que l'arbre a quatre niveaux de tâches — l'installation, le lot, le "
            f"sous-arbre fusionné par la survenance du risque 752, récapitulative du troisième "
            f"niveau, et ses deux tâches au quatrième (WF-PLA-0040, WF-PLA-0110).",
            mockcore.subtree(mockcore.alone(nested()), INSTALLATION.number, _TASKS),
        ),
        "nodes_summaries.json": _example(
            f"Variante contrefactuelle du planning du témoin, à quatre niveaux comme "
            f"nodes_nested : son arborescence de tâches, son cœur lu seul — totaux du cœur —, "
            f"demandée au niveau 2 (kinds=task, summaries_only, max_level=2) le {day} : les "
            f"récapitulatives des deux premiers niveaux — les études, l'installation sur site et "
            f"le lot « Poste de commande » rangé sous elle —, que le front dessine sous le nœud "
            f"du projet ; ni le sous-arbre fusionné par la survenance, récapitulative du "
            f"troisième niveau, ni aucune feuille ni aucun jalon ; les totaux sont ceux de ces "
            f"récapitulatives et des lignes qu'elles portent elles-mêmes, aucune (#487). La "
            f"plus profonde récapitulative de la structure est au troisième niveau, quel que soit "
            f"celui demandé (meta.summary_depth) : l'arborescence offre les trois niveaux qui "
            f"existent (WF-PLA-0110, #494).",
            mockcore.summaries(mockcore.alone(nested()), 2),
        ),
        "nodes_empty.json": _example(
            f"La structure principale de la révision ouverte le {day} sur le projet créé à "
            f"14 h 05 (structures_without_tasks), lue sans filtre : aucune tâche, aucune ligne, "
            f"des totaux nuls et aucune récapitulative — l'état vide où la grille de planning "
            f"offre le squelette (WF-PRJ-0030, WF-PLA-0080).",
            mockcore.whole([]),
        ),
        "nodes_summaries_leaves.json": _example(
            f"Variante contrefactuelle : l'arborescence de tâches d'un planning composé "
            f"uniquement de tâches feuilles — les tâches du cœur du témoin sans leurs "
            f"récapitulatives —, demandée au niveau 2 (kinds=task, summaries_only, max_level=2) "
            f"le {day} : aucune récapitulative, rien n'est rendu, la structure n'en portant "
            f"aucune (meta.summary_depth à 0), et le front dessine une arborescence réduite au "
            f"nœud du projet, sans niveau à choisir ; les totaux sont nuls (WF-PLA-0110, #494).",
            mockcore.summaries(
                [
                    row
                    for row in mockcore.alone()
                    if row.kind != mockcore.TASK
                    or not cast("JsonObject", row.node["task"])["is_summary"]
                ],
                2,
            ),
        ),
        "nodes_timeline.json": _example(
            f"La chronologie du comité de pilotage lue dans la structure (kinds=task, "
            f"timeline_id) le {day} : les seules tâches qui y sont inscrites — les études, la "
            f"réception des études, la réception usine et la mise en service —, dans l'ordre du "
            f"plan, sans les ancêtres qui n'y sont pas inscrits, le lot « Poste de commande » et "
            f"l'installation sur site : une chronologie n'est pas un arbre ; les totaux, ceux de "
            f"ces tâches et de la ligne de la mise en service, que `kinds` ne rend pas "
            f"(WF-PLA-0140, WF-PLA-0060, #487).",
            mockcore.timeline(rows, STEERING),
        ),
        "nodes_risk_occurred.json": _example(
            f"Le sous-arbre fusionné dans la structure principale de la révision en cours par la "
            f"survenance du risque « Retard de livraison des armoires », de gravité 200 à 30 %, lu "
            f"seul (subtree_of) le {day} : la racine unique de son devis propre, « Retard de "
            f"livraison des armoires » (nodes_risk_estimate_occurred), placée avec ses "
            f"subordonnées en dernière position sous le « Poste de commande », qui portait la "
            f"provision ; ses deux tâches, terminées en mai — la relance, sans prédécesseur dans "
            f"le devis propre, en mode manuel aux dates qu'elle y avait, le transport à sa suite "
            f"—, et leurs lignes de 120 et 80, aux montants budgétés nuls — la survenance ne "
            f"déplace pas la référence — et réestimés de 120 et 80 ; chaque nœud porte le risque "
            f"(origin_risk_id) ; la ligne de provision a disparu, et la récapitulative somme ses "
            f"lignes (WF-RIS-0060, WF-RIS-0050, #1788, #1761).",
            mockcore.subtree(rows, _RISK_OCCURRED),
            (OCCURRENCE_EXAMPLE,),
        ),
        "timelines.json": _example(
            f"Les chronologies du projet témoin le {day} (WF-PLA-0140) : le comité de pilotage, "
            f"auquel sont inscrits les études, leur réception, la réception usine et la mise en "
            f"service, et la revue client, les deux réceptions — inscriptions que porte chaque "
            f"tâche (`tracking`, WF-PLA-0060).",
            [{"timeline_id": timeline, "label": label} for timeline, label in TIMELINES],
        ),
        "work_breakdown.json": _example(
            f"Le lotissement du projet témoin le {day} (WF-PRJ-0020) : un lot, "
            f"« {FIRST_LOT.label} », que porte la récapitulative « {CONTROL_STATION.label} » ; "
            f"son poste « {FIRST_ITEM.label} », qu'aucune tâche ne porte (WF-PLA-0130) ; et le "
            f"livrable de ce poste. Chaque lot et chaque poste disent la tâche qui les porte, "
            f"par son nœud et son libellé, ou aucune (attached_task, WF-PLA-0170, #802).",
            mocklists.breakdown_reading(WORK_BREAKDOWN, 1, CORE),
        ),
        "work_breakdown_default.json": _example(
            f"Le lotissement du projet créé le {day}, « {CREATED_PROJECT[1]} », dont la "
            f"commande n'est pas saisie : le lotissement par défaut, un lot comprenant un poste "
            f"sans livrable, qui portent le libellé du projet (WF-PRJ-0020), que rien n'a encore "
            f"écrit, et qu'aucune tâche ne porte : sa révision n'en a pas.",
            mocklists.breakdown_reading(DEFAULT_BREAKDOWN, 1),
        ),
        "timelines_empty.json": _example(
            f"Un projet qui n'a encore aucune chronologie nommée, le {day} : la liste est vide, "
            f"et l'écran des chronologies le dit sans lire aucune tâche (WF-PLA-0140).",
            [],
        ),
        "timeline_created.json": _example(
            f"La chronologie « {CREATED_TIMELINE[1]} » créée le {day} sur le projet témoin, à côté "
            f"de ses deux chronologies, sans aucune inscription : les tâches s'y inscrivent "
            f"ensuite depuis le planning (WF-PLA-0140, WF-PLA-0060).",
            {"timeline_id": CREATED_TIMELINE[0], "label": CREATED_TIMELINE[1]},
        ),
        "startable_tasks.json": _example(
            f"Le Kanban de toute la structure du témoin le {day}, sur la révision en cours, ses "
            f"tâches par état, chaque colonne dans l'ordre du plan : {mocktext.kanban(today, core)}"
            f". La réception usine attend la fin du câblage, et rien ne se termine seul ; les "
            f"pupitres opérateurs sont en mode manuel et en dépassement de fin ; les terminées "
            f"portent leur date, et le Kanban les rouvre. Chaque carte liste ses gestes et l'état "
            f"que chacun envoie (available_commands) : la réception usine, jalon sans ligne, se "
            f"termine sans démarrer ; le montage des armoires sur site démarre, et ne se termine "
            f"que par la saisie de son reste à engager, comme le câblage des armoires, démarré ; "
            f"les pupitres opérateurs, démarrés sans ligne, se terminent ; une tâche terminée se "
            f"rouvre démarrée, la réception des études, jalon, non démarrée. Aucune "
            f"récapitulative : aucune n'attend plus que ses lignes propres, seul cas où le Kanban "
            f"en liste une (startable_tasks_awaiting_own_lines), et l'état des autres dérive de "
            f"leurs subordonnées (WF-RAE-0030, WF-PLA-0040, WF-PLA-0050, WF-IHM-0090).",
            today,
        ),
        "startable_tasks_milestone.json": _example(
            f"Variante contrefactuelle du témoin, le câblage des armoires supposé déclaré terminé "
            f"le {day}, ce qu'aucune écriture du témoin ne fait : le Kanban de toute la structure "
            f"ce jour-là, {mocktext.kanban(gesture, core)}. La réception usine, jalon "
            f"dont le seul prédécesseur est terminé, est posée à la main au 30 juin, non démarrée "
            f"tant que personne ne la termine ; les pupitres opérateurs restent démarrés, en "
            f"dépassement de fin ; le câblage est parmi les terminées, à la date du geste "
            f"(WF-RAE-0030, WF-PLA-0130).",
            gesture,
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
        "dependencies_labour_category.json": _example(
            "Ce dont dépend la catégorie de la ligne de main-d'œuvre du devis : son rôle de "
            "ressource, dont elle tient sa catégorie ; aucune ligne (WF-IHM-0030, WF-DEV-0020).",
            mockcore.dependencies(rows, _LABOUR, "estimate_line.cost_category_id"),
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
        "dependencies_provision_subproject.json": _example(
            "Ce dont dépend le sous-projet de la ligne de provision du devis : son risque, qui le "
            "désigne ; la ligne en change par son risque (updateRisk), jamais par la grille "
            "(WF-IHM-0030, WF-RIS-0010, WF-PRJ-0050).",
            mockcore.dependencies(rows, _PROVISION, mockcore.PROVISION_SUBPROJECT),
        ),
    }


# --- Writing and checking ------------------------------------------------------------------


def render(example: JsonObject) -> str:
    """Return the text of an example: one line for each item of its lists (``mockrender``)."""
    return mockrender.render(example)


def write(fixtures: Path) -> list[Path]:
    """Write the volumes under the fixtures, and the named examples of the witness among them.

    The volumes directory is owned: a file it no longer makes is removed, a directory left in it
    is not — the check names it, to be removed by hand. The named examples are written file by
    file beside the other examples. The text is written with plain line ends whatever the
    system, as the check reads it.
    """
    directory = fixtures / VOLUME
    directory.mkdir(parents=True, exist_ok=True)
    expected = {name: render(example) for name, example in mockvolumes.volumes().items()}
    for stale in sorted(set(_entries(directory)) - expected.keys()):
        if (directory / stale).is_file():
            (directory / stale).unlink()
    written: list[Path] = []
    for name, text in expected.items():
        written.append(_write(directory / name, text))
    for name, example in named().items():
        written.append(_write(fixtures / name, render(example)))
    # The slice of the portfolio, its description and its readings, beside the examples (US-2770).
    return [*written, *mocksliceviews.write(mocksliceviews.directory_of(fixtures))]


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
    expected = {name: render(example) for name, example in mockvolumes.volumes().items()}
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
    return [*problems, *mocksliceviews.check(mocksliceviews.directory_of(fixtures))]


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
