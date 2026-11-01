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
  which bear no subtask: refused on ``/parent_id``, the milestone named (F-04, #1771).

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from wftools import mockcore, mocktext
from wftools.mockids import universe
from wftools.mockindicators import rate_update
from wftools.mocklists import PROJECT_STATES, project_page
from wftools.mockwitness import N, fixture

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
    }
