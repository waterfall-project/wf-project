# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The examples of the majors of the review of the contract of the 2026-10-31 (US-0704).

The author decided each major point by point (`docs/api/DECISIONS.md`, the sections « (US-0704,
#1735, …) »), and the contract follows them with their examples, drawn from those written by hand:

- ``projects_with_created.json``, ``listProjects`` read today under the six states, after the
  creation of a project (``project_created``): the project created, in the state Created, is
  retained, as every state the list names, by a parameter of its own (``ProjectStates``; D-01,
  #1747);
- ``subproject_code_too_long.json``, a subproject created under a code one character longer than
  the tab of the file of the remaining to commit admits, refused by ``VALUE_TOO_LONG``, its
  ``params.max_length`` the bound of the field, which every ``VALUE_TOO_LONG`` bears (J-02, #1796);
- ``rate_update_category_not_proposed.json``, the rate update of the revision 101 sent with a
  category its proposal does not present, refused by the rank of that category in the list sent
  (``RateUpdateApply``; E-03, #1755);
- ``node_create_under_milestone.json`` and ``nodes_move_under_milestone.json``, a task created
  under the reception of the studies and one moved under the factory acceptance, two milestones,
  which bear no subtask: refused on ``/parent_id``, the milestone named (F-04, #1771);
- ``nodes_awaiting_own_lines.json``, the studies read in a counterfactual variant where they bear
  a line of their own, 500,00 to commit, and the operator desks, their last open subordinate,
  are completed: the summary stays started, and awaits its own lines (F-05, #1774);
- ``estimate_line_completed_refused.json``, ``estimate_line_completed_update_refused.json``,
  ``node_delete_line_completed_refused.json`` and ``nodes_move_completed_refused.json``, on the
  main structure of the project in progress, a line created under the detailed studies, completed,
  their line modified, then deleted, and the terminal blocks moved under them: refused by
  ``task_not_completed``, the task reopened from the Kanban first, whatever the phase of the
  project — a differential accepts them, its amendment rebudgeting the line (F-01, #1766);
- ``nodes_risk_estimate_occurred.json``, the own estimate of the delay of the cabinets, the
  structure 205, as the reference 101 froze it before its occurrence: its one root, which the
  occurrence placed with its subordinates last under the control station (H-03, #1788);
  ``nodes_from_risk.json``, the main structure read with ``is_from_risk``, each node merged
  bearing the risk, and ``nodes_origin_risk_unknown.json``, a risk not occurred refused by
  ``origin_risk_ids`` (#1761);
- ``risks_filtered.json`` and ``risks_period_inverted.json``, the register filtered by a bound of
  the provision, its totals those of the risks retained, and refused a period of the last review
  inverted (H-01, #1785);
- the life of an import: refused on a terminal project, during a background task, or when it
  would create the current revision for a reader (``import_open_*``; I-03, I-04, #1789, #1792);
  applied expired and abandoned applied, refused by their condition (``import_apply_expired``,
  ``import_abandon_applied``); read ``refused`` once its application is refused
  (``import_apply_refused_permission``; I-01, I-02); and a remaining to commit whose new line
  under the detailed studies, completed, is rejected (``import_remaining_completed_task``; I-05,
  #1793).

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockcore, mockhistory, mocktext
from wftools.mockamendment import MAIN_ONLY
from wftools.mockexchanges import FIRST_ROW, import_commands, main_structure, opened_on
from wftools.mockids import hex_identifier, universe
from wftools.mockindicators import rate_update
from wftools.mocklists import PROJECT_STATES, project_page
from wftools.mockstructure import described
from wftools.mockwitness import (
    AMENDMENT_MERGED,
    CONTROL_STATION,
    CORE,
    DELIVERY_DELAY_RISK,
    SUBCONTRACTING,
    Line,
    N,
    Task,
    fixture,
    rewritten,
)
from wftools.mockwitnessrisks import REGISTER
from wftools.mockwrites import amended, on_task

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue

SUBPROJECT_CODE_BOUND = 31
"""The most characters the code of a subproject admits (`DeclaredSubprojectCode`, WF-PRJ-0050):
that of the name of a tab of the file of the remaining to commit."""

TOO_LONG_CODE = "ESSAIS-MISE-EN-SERVICE-LIGNE-002"
"""The code of ``subproject_code_too_long``, one character beyond the bound."""

TOO_LONG_CORRELATION = universe(1669)
"""The correlation of the refusal of a code of a subproject too long."""


NOT_PROPOSED_CORRELATION = universe(1670)
"""The correlation of the refusal of a rate update sent with a category not proposed."""

NOT_PROPOSED_CATEGORY = universe(403)
"""« Matériel électrique », a category of disbursement, which no rate update presents."""


UNDER_MILESTONE_CORRELATIONS = (universe(1671), universe(1672))
"""The correlations of the refusals of a task created, then moved, under a milestone."""

CREATED_UNDER_MILESTONE = ("Note de calcul des protections", N.STUDIES_RECEIVED)
"""The task created under a milestone, by its label, and the milestone, by its number."""

MOVED_UNDER_MILESTONE = (N.COMMISSIONING, N.FACTORY_ACCEPTANCE)
"""The task moved under a milestone, and the milestone, by their numbers."""


OWN_LINE = Line(595, "Reprographie des dossiers d'études", SUBCONTRACTING, unit=Decimal(500))
"""The line of their own the studies bear in ``nodes_awaiting_own_lines``: 500,00 to commit, as
the Vérif of WF-PLA-0040 says (« dont une ligne propre porte un reste à engager de 500 »)."""


def awaiting_roots() -> tuple[Task, ...]:
    """Return the core where the studies bear OWN_LINE and the operator desks are completed."""

    def own(each: Task) -> Task:
        return replace(each, lines=(*each.lines, OWN_LINE)) if each.number == N.STUDIES else each

    return amended(amended(CORE, own), on_task(N.DESKS, progress="completed"))


def too_long(pointer: str, bound: int) -> JsonObject:
    """Return the refusal by field of a value longer than its field admits (J-02, #1796).

    ``VALUE_TOO_LONG`` always bears the bound of the field refused, ``params.max_length``: the
    ``maxLength`` of a text, the ``maxItems`` of a list.
    """
    return {"pointer": pointer, "code": "VALUE_TOO_LONG", "params": {"max_length": bound}}


def _code_too_long() -> JsonObject:
    if len(TOO_LONG_CODE) != SUBPROJECT_CODE_BOUND + 1:
        message = f"{TOO_LONG_CODE}: {len(TOO_LONG_CODE)} characters, not the bound and one"
        raise ValueError(message)
    return mocktext.example(
        f"Un sous-projet créé sous le code {TOO_LONG_CODE}, de trente-deux caractères quand le "
        f"nom d'un onglet du fichier de reste à engager en admet trente et un : refusé, le code "
        f"désigné par son motif, la borne de son champ nommée (max_length), que le formulaire "
        f"dit au champ ; rien n'est écrit (WF-PRJ-0050, WF-ARC-0110).",
        {
            "code": "VALIDATION_FAILED",
            "status": 422,
            "fields": [too_long("/code", SUBPROJECT_CODE_BOUND)],
            "correlation_id": TOO_LONG_CORRELATION,
        },
    )


def _category_not_proposed() -> JsonObject:
    proposed = cast("list[JsonObject]", rate_update()["categories"])
    if any(entry["cost_category_id"] == NOT_PROPOSED_CATEGORY for entry in proposed):
        message = f"{NOT_PROPOSED_CATEGORY}: the proposal presents it"
        raise ValueError(message)
    first = proposed[0]
    sent = [first["cost_category_id"], NOT_PROPOSED_CATEGORY]
    return mocktext.example(
        f"La mise à jour des taux de la révision 101, le 12 janvier 2026, envoyée pour "
        f"« {first['label']} », que la proposition présente (rate_update), et pour le « Matériel "
        f"électrique », catégorie de débours qu'elle ne présente pas : refusée, la seconde "
        f"désignée par son rang dans la liste envoyée (/cost_category_ids/1) ; rien n'est écrit, "
        f"et la révision garde sa version (WF-REV-0060, #1755).",
        {
            "code": "VALIDATION_FAILED",
            "status": 422,
            "fields": [
                {
                    "pointer": f"/cost_category_ids/{sent.index(NOT_PROPOSED_CATEGORY)}",
                    "code": "UNKNOWN_COST_CATEGORY",
                }
            ],
            "correlation_id": NOT_PROPOSED_CORRELATION,
        },
    )


def under_milestone(milestone: int, correlation: str) -> JsonObject:
    """Return the refusal of a task placed under a milestone, which bears no subtask (#1771).

    On ``/parent_id``, the milestone named by its node and its label (WF-PLA-0050); nothing is
    written.
    """
    rows = {row.number: row for row in mockcore.current()}
    task = rows[milestone].node["task"]
    if not cast("JsonObject", task)["is_milestone"]:
        message = f"the task {milestone} is not a milestone"
        raise ValueError(message)
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [
            {
                "pointer": "/parent_id",
                "code": "MILESTONE_HAS_NO_SUBTASK",
                "params": {"node_id": universe(milestone), "label": rows[milestone].label},
            }
        ],
        "correlation_id": correlation,
    }


def _under_milestone() -> dict[str, JsonObject]:
    rows = {row.number: row for row in mockcore.current()}
    created, received = CREATED_UNDER_MILESTONE
    moved, acceptance = MOVED_UNDER_MILESTONE
    first, second = UNDER_MILESTONE_CORRELATIONS
    return {
        "node_create_under_milestone.json": mocktext.example(
            f"La tâche « {created} » créée sous la « {rows[received].label} », un jalon : un "
            f"jalon ne porte pas de sous-tâches, mais il peut porter des lignes de devis. La "
            f"création est refusée sur le parent visé, le jalon nommé ; rien n'est écrit "
            f"(WF-PLA-0050, #1771).",
            under_milestone(received, first),
        ),
        "nodes_move_under_milestone.json": mocktext.example(
            f"La « {rows[moved].label} » déplacée sous la « {rows[acceptance].label} », un "
            f"jalon : il ne devient pas une récapitulative, un jalon ne portant pas de "
            f"sous-tâches. Le déplacement est refusé sur le parent visé, le jalon nommé ; rien "
            f"ne bouge (WF-PLA-0050, #1771).",
            under_milestone(acceptance, second),
        ),
    }


COMPLETED_UNDER = N.DETAILED_STUDIES
COMPLETED_LINE = N.STUDIES_LINE
COMPLETED_MOVED = N.BLOCKS
"""The task completed of the main structure, the detailed studies; its one line, the detailed
engineering; and the line sent under it from a task not completed, the terminal blocks of the
wiring of the cabinets."""

COMPLETED_CORRELATION, MOVE_COMPLETED_CORRELATION = universe(1186), universe(1195)
UPDATE_COMPLETED_CORRELATION, DELETE_COMPLETED_CORRELATION = universe(1674), universe(1675)


def completed_refused(correlation: str) -> JsonObject:
    """Return the refusal of a line written on the main structure under the detailed studies.

    On the main structure, no line is created under a task completed, nor modified, deleted, or
    moved to it or from it: the task is reopened from the Kanban first (WF-DEV-0050, WF-RAE-0040,
    WF-RAE-0030). The state of the task refuses it, by the condition a line under it misses; the
    phase of the project refuses nothing (C-358), and a differential refuses nothing either, its
    amendment rebudgeting the line (WF-REV-0050; F-01, #1766).
    """
    rows = {row.number: row for row in mockcore.current()}
    if cast("JsonObject", rows[COMPLETED_UNDER].node["task"])["progress"] != "completed":
        message = f"the task {COMPLETED_UNDER} is not completed"
        raise ValueError(message)
    if rows[COMPLETED_LINE].parent != COMPLETED_UNDER:
        message = f"the line {COMPLETED_LINE} is not under the task {COMPLETED_UNDER}"
        raise ValueError(message)
    return {
        "code": "STATE_FORBIDS_OPERATION",
        "status": 409,
        "params": {"missing_condition": "task_not_completed"},
        "correlation_id": correlation,
    }


def estimate_line_completed_refused() -> JsonObject:
    """Return what createNode answers to a line created under a task completed (#1184)."""
    return completed_refused(COMPLETED_CORRELATION)


def estimate_line_completed_update_refused() -> JsonObject:
    """Return what updateEstimateLine answers to the line of a task completed, modified."""
    return completed_refused(UPDATE_COMPLETED_CORRELATION)


def node_delete_line_completed_refused() -> JsonObject:
    """Return what deleteNode answers to the line of a task completed, deleted."""
    return completed_refused(DELETE_COMPLETED_CORRELATION)


def nodes_move_completed_refused() -> JsonObject:
    """Return what moveNodes answers to the blocks moved under a task completed (#1214).

    « Le déplacement d'une ligne vers elle, est refusé » (Vérif of WF-DEV-0050): the blocks of the
    wiring, a task not completed, sent under the detailed studies.
    """
    rows = {row.number: row for row in mockcore.current()}
    bearer = rows[cast("int", rows[COMPLETED_MOVED].parent)]
    if cast("JsonObject", bearer.node["task"])["progress"] == "completed":
        message = f"the line {COMPLETED_MOVED} is under a task completed"
        raise ValueError(message)
    return completed_refused(MOVE_COMPLETED_CORRELATION)


def _completed_examples() -> dict[str, JsonObject]:
    rows = {row.number: row for row in mockcore.current()}
    under, line = rows[COMPLETED_UNDER].label, rows[COMPLETED_LINE].label
    moved_from = rows[cast("int", rows[COMPLETED_MOVED].parent)].label
    on = (
        f"Sur la structure principale de la révision courante, le projet En cours, sous les "
        f"« {under} », terminées"
    )
    reopened = (
        "la tâche se rouvre d'abord depuis le Kanban ; la phase du projet ne refuse rien (C-358), "
        "et un différentiel l'accepterait, son avenant rebudgétant la ligne (WF-REV-0050)"
    )
    return {
        "estimate_line_completed_refused.json": mocktext.example(
            f"{on} : une ligne créée sous elles. Aucune ligne de la structure principale ne se "
            f"crée sous une tâche terminée : {reopened}. La création est refusée, la condition "
            f"nommée ; rien n'est créé (WF-DEV-0050, WF-RAE-0030, #1184, #1766).",
            estimate_line_completed_refused(),
        ),
        "estimate_line_completed_update_refused.json": mocktext.example(
            f"{on} : leur ligne « {line} » modifiée. Une ligne de la structure principale d'une "
            f"tâche terminée ne se modifie pas, son libellé pas plus que ses grandeurs, et ne "
            f"nomme aucun champ parmi ceux qu'elle accepte (editable_fields) : {reopened}. "
            f"La modification est refusée, la condition nommée ; rien n'est écrit (WF-RAE-0040, "
            f"WF-DEV-0050, #1766).",
            estimate_line_completed_update_refused(),
        ),
        "node_delete_line_completed_refused.json": mocktext.example(
            f"{on} : leur ligne « {line} » supprimée. Une ligne de la structure principale d'une "
            f"tâche terminée ne se supprime pas : {reopened}. La suppression est "
            f"refusée, la condition nommée ; rien n'est supprimé (WF-RAE-0040, WF-DEV-0050, "
            f"#1766).",
            node_delete_line_completed_refused(),
        ),
        "nodes_move_completed_refused.json": mocktext.example(
            f"{on} : les « {rows[COMPLETED_MOVED].label} » du "
            f"« {moved_from} », non terminé, déplacés sous elles. Aucune "
            f"ligne de la structure principale ne se déplace vers une tâche terminée, ni depuis "
            f"elle : {reopened}. Le déplacement est refusé, la condition nommée ; rien ne bouge "
            f"(WF-DEV-0050, WF-RAE-0030, #1214, #1766).",
            nodes_move_completed_refused(),
        ),
    }


def _awaiting_own_lines() -> JsonObject:
    rows = mockcore.current(described(awaiting_roots()))
    read = mockcore.subtree(rows, N.STUDIES)
    [studies] = [
        node
        for node in cast("list[JsonObject]", read["items"])
        if node["node_id"] == universe(N.STUDIES)
    ]
    facet = cast("JsonObject", studies["task"])
    if not facet["awaiting_own_lines"] or facet["progress"] != "started":
        message = "the studies do not await their own lines"
        raise ValueError(message)
    named = {row.number: row.label for row in rows}
    return mocktext.example(
        f"Variante contrefactuelle déclarée : les « {named[N.STUDIES]} » lues seules (subtree_of), "
        f"comme si elles portaient une ligne propre, « {OWN_LINE.label} », 500,00 à engager, et "
        f"que les « {named[N.DESKS]} », leur dernière subordonnée ouverte, avaient été "
        f"terminés : toutes leurs subordonnées terminées, la récapitulative reste démarrée tant "
        f"que sa ligne propre garde un reste à engager, et le dit (awaiting_own_lines) ; la "
        f"grille de reste à engager et le Kanban la signalent avec sa ligne, seule ligne ouverte "
        f"de la phase (WF-PLA-0040, WF-IHM-0070, #1774).",
        read,
    )


def _with_created() -> JsonObject:
    projects = cast("list[JsonObject]", fixture("projects")["items"])
    created = fixture("project_created")
    read = project_page([*projects, created], PROJECT_STATES)
    rows = cast("list[JsonObject]", read["items"])
    labels = mocktext.listed([f"« {row['label']} »" for row in rows])
    return mocktext.example(
        f"La liste des projets lue aujourd'hui sous les six états, comme l'accueil les demande, "
        f"après la création de « {created['label']} » (project_created) : {labels}, le projet "
        f"créé, à l'état Créé, retenu en tête, le plus récemment modifié — tout état nommé est "
        f"retenu (ProjectStates) ; sa créatrice en est chef de projet et le lit dans sa liste "
        f"(WF-IHM-0120, WF-PRJ-0060).",
        read,
    )


# --- The nodes merged by an occurrence (#1761, H-03 #1788) ----------------------------------------


OWN_ESTIMATE_OFFSET = 6
"""What separates a node of the own estimate of 752 from the node its occurrence merged: the node
535 of the structure 205 became the node 541 of the main structure, of a lineage of its own, as
every node a merge adds (`ImportDifference`)."""


def delivery_delay_estimate() -> tuple[Task, ...]:
    """Return the own estimate of the delay of the cabinets, the structure 205, as 101 froze it.

    Its one root, the delay of the cabinets, and its subordinates, the reminder and the transport,
    as the occurrence of 20 February merged them under the control station (WF-RIS-0060; H-03,
    #1788), each node of its own (``OWN_ESTIMATE_OFFSET``): before the merge, its lines bear their
    own amount for budget, and no node bears the risk, which the occurrence alone sets
    (`Node.origin_risk_id`, #1761).
    """
    [merged] = [each for each in CONTROL_STATION.children if each.number == N.MERGED]

    def own(each: Task) -> Task:
        lines = tuple(
            replace(
                line,
                number=line.number - OWN_ESTIMATE_OFFSET,
                budgeted=None,
                origin_risk=None,
            )
            for line in each.lines
        )
        links = tuple(
            replace(link, predecessor=link.predecessor - OWN_ESTIMATE_OFFSET) for link in each.links
        )
        return replace(
            each,
            number=each.number - OWN_ESTIMATE_OFFSET,
            lines=lines,
            links=links,
            origin_risk=None,
        )

    return rewritten((merged,), own)


def delivery_delay_rows() -> list[mockcore.Row]:
    """Return the own estimate of 752 read on the day the reference 101 froze it, lines opened."""
    return mockcore.opened(mockcore.core(delivery_delay_estimate(), AMENDMENT_MERGED.on))


def nodes_risk_estimate_occurred() -> JsonObject:
    """Return what listNodes answers of the own estimate of 752 in the reference 101 (H-03).

    Read on the day the reference was marked, which froze it before the occurrence merged it
    (WF-RIS-0030): every node, every total; no lot, post or inscription among the fields of its
    tasks, which are the main structure's alone (WF-PLA-0170).
    """
    answer = mockcore.whole(delivery_delay_rows())
    items = [
        {
            **node,
            "editable_fields": [
                field
                for field in cast("list[JsonValue]", node["editable_fields"])
                if field not in MAIN_ONLY
            ],
        }
        for node in cast("list[JsonObject]", answer["items"])
    ]
    return {**answer, "items": cast("list[JsonValue]", items)}


def nodes_from_risk() -> JsonObject:
    """Return the main structure of the current revision read with ``is_from_risk`` (#1761).

    The nodes the occurrence of 752 merged, each bearing it, and the control station, their
    ancestor, rendered for the tree to stay a tree and counted in no total (WF-IHM-0130).
    """
    return mockcore.filtered(mockcore.current(), lambda row: row.node["origin_risk_id"] is not None)


ORIGIN_UNKNOWN_CORRELATION = universe(1676)
"""The correlation of the refusal of a risk not occurred named by ``origin_risk_ids``."""


def nodes_origin_risk_unknown() -> JsonObject:
    """Return the refusal of ``origin_risk_ids`` naming a risk that has not occurred (#1761).

    By its rank in the list sent, as every parameter of the query (`NodeOriginRiskFilter`).
    """
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [{"pointer": "/query/origin_risk_ids/1", "code": "UNKNOWN_RISK"}],
        "correlation_id": ORIGIN_UNKNOWN_CORRELATION,
    }


def _from_risk_examples() -> dict[str, JsonObject]:
    rows = {row.number: row for row in mockcore.current()}
    merged, station = rows[N.MERGED], rows[N.CONTROL_STATION]
    estimate = nodes_risk_estimate_occurred()
    found = nodes_from_risk()
    origins = {
        cast("JsonObject", node).get("origin_risk_id")
        for node in cast("list[JsonObject]", found["items"])
        if node["node_id"] != station.node["node_id"]
    }
    if origins != {universe(DELIVERY_DELAY_RISK)}:
        message = f"the nodes merged bear {origins}, not the risk {DELIVERY_DELAY_RISK}"
        raise ValueError(message)
    total = cast("JsonObject", estimate["totals"])["reestimated_amount"]
    return {
        "nodes_risk_estimate_occurred.json": mocktext.example(
            f"Le devis propre du risque « {merged.label} », structure 205, lu dans la référence "
            f"101 qui le fige le {mocktext.day(AMENDMENT_MERGED.on)}, avant sa survenance du 20 "
            f"février : sa racine unique, « {merged.label} », et ses subordonnées, la relance du "
            f"fournisseur, en mode manuel, et le transport exceptionnel à sa suite, avec leurs "
            f"lignes de 120 et 80, budgétées à leur montant ; leur total, "
            f"{mocktext.amount(Decimal(cast('str', total)))}, est la gravité du risque. La "
            f"survenance a placé cette racine, avec ses subordonnées, en dernière position sous "
            f"le « {station.label} », qui portait la provision (nodes_risk_occurred) : le témoin "
            f"montre un devis propre à une racine, quand celui de 751 est à plat "
            f"(nodes_risk_estimate). Aucun nœud ne porte encore le risque (origin_risk_id), que "
            f"seule la survenance pose (WF-RIS-0030, WF-RIS-0060, #1788).",
            estimate,
        ),
        "nodes_from_risk.json": mocktext.example(
            f"La structure principale de la révision courante lue aujourd'hui avec is_from_risk : "
            f"les nœuds que la survenance de « {merged.label} » a fusionnés, sa racine « "
            f"{merged.label} », ses deux tâches et leurs lignes, chacun portant le risque "
            f"(origin_risk_id) ; le « {station.label} », leur ancêtre, rendu pour que l'arbre "
            f"reste un arbre et compté dans aucun total. Les totaux sont ceux des lignes "
            f"retenues, le réestimé courant que le registre présente en regard du coût à la "
            f"survenance (occurred_reestimated_amount ; WF-RIS-0060, WF-IHM-0130, #1761).",
            found,
        ),
        "nodes_origin_risk_unknown.json": mocktext.example(
            f"La structure principale lue aujourd'hui avec origin_risk_ids nommant « "
            f"{merged.label} », survenu, puis le risque de reprise du câblage, encore identifié : "
            f"sa survenance n'a rien fusionné, et le second est refusé, par son rang dans la "
            f"liste envoyée ; rien n'est lu (WF-RIS-0060, #1761).",
            nodes_origin_risk_unknown(),
        ),
    }


# --- The register filtered on its columns (H-01, #1785) -----------------------------------------

FILTERED_PROVISION_MIN = Decimal(100000)
"""The lower bound of the provision `risks_filtered` reads (`provision_amount_min`)."""


def risks_filtered() -> JsonObject:
    """Return the register read with ``provision_amount_min``: the risks retained and their totals.

    The totals are those of the risks retained, whatever the page read (WF-IHM-0130).
    """
    rows = mockhistory.reference_rows()
    budget = mockhistory.reference_budget(rows)
    kept = [
        risk for risk in REGISTER if mockhistory.provision_amount(risk) >= FILTERED_PROVISION_MIN
    ]
    if not 0 < len(kept) < len(REGISTER):
        message = f"the bound {FILTERED_PROVISION_MIN} retains {len(kept)} risks"
        raise ValueError(message)
    return {
        "items": [mockhistory.risk_item(risk, budget) for risk in kept],
        "totals": mockhistory.totals(rows, kept),
        "meta": {"limit": mocktext.PAGE, "offset": 0, "total": len(kept)},
    }


PERIOD_INVERTED_CORRELATION = universe(1677)
REVIEWED_FROM, REVIEWED_TO = date(2026, 3, 1), date(2026, 2, 1)
"""The period of the last review `risks_period_inverted` sends, its end before its start."""


def risks_period_inverted() -> JsonObject:
    """Return the refusal of a period of the last review whose end precedes its start (#1785)."""
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [
            {
                "pointer": "/query/last_review_on_to",
                "code": "VALUE_OUT_OF_RANGE",
                "params": {"minimum": REVIEWED_FROM.isoformat()},
            }
        ],
        "correlation_id": PERIOD_INVERTED_CORRELATION,
    }


def _risks_filtered() -> JsonObject:
    read = risks_filtered()
    items = cast("list[JsonObject]", read["items"])
    named = mocktext.listed([f"« {item['label']} »" for item in items])
    sums = cast("JsonObject", read["totals"])
    return mocktext.example(
        f"Le registre des risques lu aujourd'hui avec provision_amount_min="
        f"{FILTERED_PROVISION_MIN} : les risques dont la provision atteint "
        f"{mocktext.amount(FILTERED_PROVISION_MIN, 0)}, {named}, l'écarté pour la provision que "
        f"portait la référence ; les totaux de provisions sont ceux des seuls risques retenus, "
        f"{mocktext.amount(Decimal(cast('str', sums['total'])))} au total, la réserve en regard "
        f"inchangée. Chaque colonne de nombres se filtre ainsi par ses deux bornes, et la date "
        f"du dernier réexamen par sa période (WF-IHM-0130, WF-RIS-0040, #1785).",
        read,
    )


# --- The life of an import (I-01 to I-05, #1789, #1792, #1793) ----------------------------------

IMPORT_CORRELATIONS = {
    "import_open_terminal": universe(1678),
    "import_open_background_running": universe(1679),
    "import_open_may_create_revision": universe(1680),
    "import_apply_expired": universe(1681),
    "import_abandon_applied": universe(1682),
}
"""The correlations of the refusals of the life of an import, by example."""


def _refused(name: str, condition: str) -> JsonObject:
    return {
        "code": "STATE_FORBIDS_OPERATION",
        "status": 409,
        "params": {"missing_condition": condition},
        "correlation_id": IMPORT_CORRELATIONS[name],
    }


def _listed(status: str) -> JsonObject:
    """Return the most recent import of the list in a status: the journal of the witness."""
    return next(
        item
        for item in cast("list[JsonObject]", fixture("imports")["items"])
        if item["status"] == status
    )


def import_apply_refused_permission() -> JsonObject:
    """Return the estimate analysed this morning, its application refused (counterfactual).

    Confirmed by a user whose permission was withdrawn since the analysis: the application is
    refused, the file deleted, and the import ``refused`` — no longer applicable, its expiry gone
    (WF-ARC-0100; I-01, #1789). Its report and the task of its analysis stay.
    """
    analysed = fixture("import_analysed")
    status = "refused"
    return {
        **analysed,
        "status": status,
        "expires_at": None,
        "available_commands": import_commands(status, cast("JsonObject", analysed["report"])),
    }


COMPLETED_IMPORT, COMPLETED_IMPORT_TASK = hex_identifier(0xA1C), universe(924)
COMPLETED_IMPORT_AT = ("2026-06-03T11:00:05Z", "2026-06-03T11:01:00Z", "2026-06-04T11:01:00Z")
"""The remaining to commit imported this morning with a new line under the detailed studies: when
it was opened, analysed, and until when it applies."""

NEW_LINE_LABEL = "Reprise des notes de calcul"
"""The new line the file places under the detailed studies, without an identifier."""


def import_remaining_completed_task() -> JsonObject:
    """Return the remaining to commit whose new line under a completed task is rejected (I-05).

    On the main structure, as its entry: ``STATE_FORBIDS_OPERATION``, ``task_not_completed``, the
    task named by its lineage and its label (WF-INTF-0120; #1793). The tab « Hors sous-projet »,
    whose name does not depend on the language (ANNEXE B).
    """
    rows = {row.number: row for row in mockcore.current()}
    under = rows[COMPLETED_UNDER]
    if cast("JsonObject", under.node["task"])["progress"] != "completed":
        message = f"the task {COMPLETED_UNDER} is not completed"
        raise ValueError(message)
    opened, analysed, expires = COMPLETED_IMPORT_AT
    report: JsonObject = {
        "format_version": "1",
        "read_count": 1,
        "unchanged_count": 0,
        "rejected": [
            {
                "sheet": "Hors sous-projet",
                "row": FIRST_ROW,
                "code": "STATE_FORBIDS_OPERATION",
                "params": {
                    "missing_condition": "task_not_completed",
                    "tasks": [
                        {"lineage_id": mockcore.lineage(COMPLETED_UNDER), "label": under.label}
                    ],
                },
            }
        ],
        "refusals": [],
        "differences": [],
        "ignored": [],
        "completed_tasks": [],
        "date_mismatches": [],
        "signals": [],
        "requires_confirmation_reasons": [],
    }
    status = "analysed"
    return {
        "import_id": COMPLETED_IMPORT,
        "kind": "remaining",
        "filename": "reste-a-engager-etudes.xlsx",
        **opened_on(main_structure()),
        "status": status,
        "created_at": opened,
        "expires_at": expires,
        "report": report,
        "task": {
            "task_id": COMPLETED_IMPORT_TASK,
            "kind": "import_analysis",
            "status": "succeeded",
            "progress": 100,
            "submitted_at": opened,
            "finished_at": analysed,
            "problem": None,
            "result_url": None,
        },
        "available_commands": import_commands(status, report),
    }


def _import_examples() -> dict[str, JsonObject]:
    expired, applied = _listed("expired"), _listed("applied")
    under = {row.number: row for row in mockcore.current()}[COMPLETED_UNDER].label
    analysed = fixture("import_analysed")
    return {
        "import_open_terminal.json": mocktext.example(
            "Un import ouvert sur le projet témoin après sa clôture (project_completed) : un "
            "projet terminal ne liste aucune commande, et seul ce refus nomme la condition qui "
            "manque, "
            "project_not_terminal ; rien n'est analysé (WF-CYC-0100, #1789).",
            _refused("import_open_terminal", "project_not_terminal"),
        ),
        "import_open_background_running.json": mocktext.example(
            "Un devis importé pendant que court le marquage de la révision en cours, la 102 "
            "(revision_marking) : les imports de planning, de devis et de reste à engager sont "
            "indisponibles, comme la commande du projet le dit "
            "(project_background_task_running) ; refusé par la condition qui manque, aucun "
            "traitement de fond en cours, un 409 et non un 403 ; rien n'est analysé "
            "(WF-IHM-0080, WF-IHM-0090, #1792).",
            _refused("import_open_background_running", "no_background_task_running"),
        ),
        "import_open_may_create_revision.json": mocktext.example(
            "Un planning importé le 1er février 2026, quand le projet n'a pas de révision en cours "
            "(revision_marked_merge_offered), par un compte qui n'a pas la permission de créer une "
            "révision : l'import la créerait, et il est refusé par la condition qui manque, un 409 "
            "et non un 403, comme la fusion (merge_may_create_revision_refused) ; rien n'est "
            "analysé (WF-INTF-0090, #1792).",
            _refused("import_open_may_create_revision", "may_create_revision"),
        ),
        "import_apply_expired.json": mocktext.example(
            f"L'application demandée aujourd'hui de « {expired['filename']} », expirée ce matin, "
            f"vingt-quatre heures après son analyse sans avoir été appliquée (imports) : il n'y a "
            f"plus rien à appliquer, et le refus nomme la condition qui manque, un import qui "
            f"attend la décision ; l'import ne change pas (WF-ARC-0100, #1789).",
            _refused("import_apply_expired", "import_awaiting_decision"),
        ),
        "import_abandon_applied.json": mocktext.example(
            f"L'abandon demandé aujourd'hui de « {applied['filename']} », appliquée ce matin "
            f"(imports) : ce qu'un import a écrit ne se défait pas par l'abandon, et le refus "
            f"nomme la condition qui manque ; rien n'est changé (WF-INTF-0080, #1789).",
            _refused("import_abandon_applied", "import_not_applied"),
        ),
        "import_apply_refused_permission.json": mocktext.example(
            f"Variante contrefactuelle : l'import de « {analysed['filename']} » (import_analysed), "
            f"sur le différentiel de l'avenant 2 (structure_id {analysed['structure_id']}), "
            f"confirmé par un compte dont la permission de saisir le devis a été retirée depuis "
            f"l'analyse ; l'application refusée, son fichier est supprimé et l'import se lit "
            f"refusé (refused), sans échéance : il ne s'applique plus, la condition manquante "
            f"nommée à sa commande apply, et son abandon rendrait 204 sans effet ; son compte "
            f"rendu et la tâche de son analyse demeurent (WF-ARC-0100, WF-IHM-0090, #1789).",
            import_apply_refused_permission(),
        ),
        "import_remaining_completed_task.json": mocktext.example(
            f"L'import d'un reste à engager ouvert ce matin sur la structure principale, analysé "
            f"à 11 h 01 et applicable jusqu'à demain : une ligne nouvelle, « {NEW_LINE_LABEL} », "
            f"sans identifiant, placée dans l'onglet « Hors sous-projet » sous les « {under} », "
            f"terminées. Comme sa saisie, elle est rejetée au compte rendu par la condition qui "
            f"manque, la tâche nommée par sa lignée et son libellé : la tâche se rouvre d'abord "
            f"depuis le Kanban ; un différentiel l'accepterait, son avenant la rebudgétant "
            f"(WF-INTF-0120, WF-INTF-0080, #1793, #1766).",
            import_remaining_completed_task(),
        ),
    }


def examples() -> dict[str, JsonObject]:
    """Return the examples of the majors of the review of the 2026-10-31, by file name."""
    return {
        "projects_with_created.json": _with_created(),
        "subproject_code_too_long.json": _code_too_long(),
        "rate_update_category_not_proposed.json": _category_not_proposed(),
        **_under_milestone(),
        "nodes_awaiting_own_lines.json": _awaiting_own_lines(),
        **_completed_examples(),
        **_from_risk_examples(),
        "risks_filtered.json": _risks_filtered(),
        **_import_examples(),
        "risks_period_inverted.json": mocktext.example(
            f"Le registre des risques demandé aujourd'hui par la période du dernier réexamen, du "
            f"{mocktext.day(REVIEWED_FROM)} au {mocktext.day(REVIEWED_TO)} (last_review_on_from, "
            f"last_review_on_to) : la fin de la période précède son début, et le paramètre "
            f"last_review_on_to est refusé, désigné par /query/last_review_on_to, le début nommé "
            f"(README du contrat, WF-IHM-0130, #1785).",
            risks_period_inverted(),
        ),
    }
