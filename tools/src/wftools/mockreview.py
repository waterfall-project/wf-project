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
  project — a differential accepts them, its amendment rebudgeting the line (F-01, #1766).

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockcore, mocktext
from wftools.mockids import universe
from wftools.mockindicators import rate_update
from wftools.mocklists import PROJECT_STATES, project_page
from wftools.mockstructure import described
from wftools.mockwitness import CORE, SUBCONTRACTING, Line, N, Task, fixture
from wftools.mockwrites import amended, on_task

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject

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


def examples() -> dict[str, JsonObject]:
    """Return the examples of the majors of the review of the 2026-10-31, by file name."""
    return {
        "projects_with_created.json": _with_created(),
        "subproject_code_too_long.json": _code_too_long(),
        "rate_update_category_not_proposed.json": _category_not_proposed(),
        **_under_milestone(),
        "nodes_awaiting_own_lines.json": _awaiting_own_lines(),
        **_completed_examples(),
    }
