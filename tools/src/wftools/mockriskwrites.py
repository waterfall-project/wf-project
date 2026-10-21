# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The answers of the entries of a risk: declared, modified, reviewed, declared occurred (#763).

The forms of the risks declare a risk, modify it, review it and declare it occurred (US-0520):
their answers are read, as the register is, from the risks of ``wftools.mockwitness`` by
``wftools.mockhistory.risk_item``, never written by hand (K5 of EP-15):

- a risk declared today, its own structure opened empty with it — its severity and its provision
  nought until its own estimate is priced in the grid of estimate — and its line of provision on
  the first task of the first level, no task designated (``risk_created``, WF-RIS-0010, #786);
- that risk modified, its line of provision moved to the task its form designates, the total of
  the estimate unchanged (``risk_updated``);
- the rework of the wiring confirmed today without a change, a review dated of today
  (``risk_reviewed``, WF-RIS-0010);
- the occurrence of the delay of the cabinets, on 20 February, put in the queue
  (``task_occurrence_queued``, WF-RIS-0060, WF-ARC-0090);
- and a declaration whose provision names a task the main structure does not bear
  (``risk_provision_task_refused``).

The risk declared is a counterfactual: no reading of the witness knows its risk 754, its own
structure 208 or its line of provision 585 — the register, the structures and the grids read the
witness as it is, before the declaration (``DECLARED``). The review alone is of the register, on
751.

They would have carried ``mockhistory`` past the thousand lines (``wftools.sources``).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockamendment, mockcore, mocktext
from wftools.mockhistory import (
    reference_budget,
    reference_rows,
    risk_item,
    stamp,
)
from wftools.mockids import universe
from wftools.mockwitness import DELIVERY_DELAY, REWORK, TODAY, N, Review, Risk

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject

DECLARED_AT = TODAY - timedelta(minutes=20)
"""When the risk was declared: earlier today, so that its modification follows at today's instant,
after which nothing has happened (C11, #287)."""

DECLARED = Risk(
    754,
    "Indisponibilité de la grue de levage",
    "Les armoires se lèvent sur site par une grue louée, dont la disponibilité n'est pas "
    "confirmée.",
    None,
    208,
    (Review(DECLARED_AT, Decimal("0.2"), Decimal("0.00")),),
    provision_line=585,
)
"""The risk declared today, at 20 %: its own structure 208 opened empty, and its line of provision
585 in the main structure of the current revision, of the one category of provision of the
universe and no subproject (WF-RIS-0010)."""

DESIGNATED = N.MOUNTING
MITIGATION = "Réservation d'une seconde grue auprès d'un autre loueur."
MODIFIED_AT = TODAY
"""What the modification of the risk declared enters, and when: the task its provision goes to,
the mounting of the cabinets on site, which the crane serves, and its actions of mitigation, at
today's instant, after its declaration."""

OCCURRENCE_TASK = universe(949)
REFUSED_CORRELATION = universe(1193)
REFUSED_TASK = N.TESTS_RESUMED
"""The task a refused declaration designates: the rework of the trials, which only the amendment
2 bears (``mockamendment``)."""


def first_root() -> int:
    """Return the first task of the first level of the main structure, read today."""
    return next(row.number for row in mockcore.current() if row.parent is None)


def _budget() -> Decimal:
    return reference_budget(reference_rows())


def risk_created() -> JsonObject:
    """Return what createRisk answers to the risk declared today, no task designated."""
    return {**risk_item(DECLARED, _budget(), first_root()), "lock_version": 1}


def risk_updated() -> JsonObject:
    """Return what updateRisk answers when the risk declared moves its provision to the mounting.

    It follows the declaration (``risk_created``), one version further; its line stays its line,
    the provision unchanged (WF-RIS-0010).
    """
    changed = replace(DECLARED, mitigation_notes=MITIGATION)
    item = risk_item(changed, _budget(), DESIGNATED)
    audit = {**cast("JsonObject", item["audit"]), "updated_at": stamp(MODIFIED_AT)}
    return {**item, "audit": audit, "lock_version": 2}


def risk_reviewed() -> JsonObject:
    """Return what reviewRisk answers when the rework of the wiring is confirmed without a change.

    Its probability and its state sent as they are: a review dated of today (WF-RIS-0010).
    """
    last = REWORK.last
    confirmed = replace(REWORK, reviews=(*REWORK.reviews, replace(last, at=TODAY)))
    return risk_item(confirmed, _budget())


def task_occurrence_queued() -> JsonObject:
    """Return what declareRiskOccurrence answered when the delay of the cabinets occurred.

    On 20 February 2026, the instant of its last review (``mockwitness``): the merge of its own
    estimate is left to the worker (WF-RIS-0060, WF-ARC-0090).
    """
    return {
        "task_id": OCCURRENCE_TASK,
        "kind": "risk_occurrence",
        "status": "queued",
        "progress": 0,
        "submitted_at": stamp(DELIVERY_DELAY.last.at),
        "finished_at": None,
        "problem": None,
        "result_url": None,
    }


def risk_provision_task_refused() -> JsonObject:
    """Return what createRisk answers to a provision designated on a task of the amendment 2.

    The task is not one of the main structure of the current revision, whatever another structure
    bears: refused on its field (WF-RIS-0010, #786).
    """
    main = {row.number for row in mockcore.current()}
    differential = {row.number for row in mockamendment.rows()}
    if REFUSED_TASK in main or REFUSED_TASK not in differential:
        message = f"the task {REFUSED_TASK} is not of the amendment 2 alone"
        raise ValueError(message)
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [{"pointer": "/provision_task_id", "code": "UNKNOWN_TASK"}],
        "correlation_id": REFUSED_CORRELATION,
    }


# --- The examples ------------------------------------------------------------------------------


def _task_label(item: JsonObject) -> str:
    return cast("str", cast("JsonObject", item["provision_task"])["label"])


def examples() -> dict[str, JsonObject]:
    """Return the named examples of the entries of a risk, by file name."""
    created, updated, reviewed = risk_created(), risk_updated(), risk_reviewed()
    rows = {row.number: row for row in mockamendment.rows()}
    percent = mocktext.amount(DECLARED.last.probability * 100, 0)
    return {
        "risk_created.json": mocktext.example(
            f"« {DECLARED.label} », déclaré aujourd'hui à {percent} % : la déclaration ouvre sa "
            f"structure propre (structure_id), vide — sa gravité et sa provision sont nulles "
            f"jusqu'à ce que son devis propre soit chiffré dans la grille de devis, ni l'une ni "
            f"l'autre saisies — et sa ligne de provision dans la structure principale de la "
            f"révision courante (provision_node_id). Aucune tâche n'étant désignée, la ligne est "
            f"portée par la première tâche de premier niveau, « {_task_label(created)} » "
            f"(provision_task) ; elle porte la catégorie « "
            f"{created['provision_cost_category_label']} », la seule de type provision pour "
            f"risques, et aucun sous-projet. À sa première version (201), toutes ses commandes "
            f"disponibles (WF-RIS-0010, WF-RIS-0030, #786). C'est un contrefactuel : aucune "
            f"lecture du témoin ne connaît ce risque {DECLARED.number}, sa structure propre "
            f"{DECLARED.own_structure} ni sa ligne de provision {DECLARED.provision_line}.",
            created,
        ),
        "risk_updated.json": mocktext.example(
            f"« {DECLARED.label} », déclaré aujourd'hui (risk_created), modifié : ses actions de "
            f"mitigation saisies, et sa ligne de provision déplacée sur la tâche que le formulaire "
            f"désigne, « {_task_label(updated)} » (provision_task_id), le total du devis "
            f"inchangé ; une version de plus, modifié après sa déclaration (audit.updated_at ; "
            f"WF-RIS-0010, #786).",
            updated,
        ),
        "risk_reviewed.json": mocktext.example(
            f"« {REWORK.label} » réexaminé aujourd'hui sans modification, sa probabilité de "
            f"{mocktext.amount(REWORK.last.probability * 100, 0)} % et son état identifié "
            f"envoyés tels quels : la confirmation produit un réexamen daté du jour "
            f"(last_review_on), qui s'ajoute à son historique (risk_reviews) ; sa gravité et sa "
            f"provision inchangées, sa ligne toujours portée par « {_task_label(reviewed)} » ; "
            f"une version de plus (201, WF-RIS-0010, WF-RIS-0020).",
            reviewed,
        ),
        "task_occurrence_queued.json": mocktext.example(
            f"La survenance de « {DELIVERY_DELAY.label} », confirmée le "
            f"{mocktext.day(DELIVERY_DELAY.last.at.date())} à "
            f"{DELIVERY_DELAY.last.at.hour} h : la fusion de son devis propre dans la structure "
            f"principale de la révision en cours est confiée au worker, la tâche de fond en "
            f"file, pas encore commencée (risk_occurred_detail ; WF-RIS-0060, WF-ARC-0090).",
            task_occurrence_queued(),
        ),
        "risk_provision_task_refused.json": mocktext.example(
            f"Un risque déclaré en désignant pour sa provision la « {rows[REFUSED_TASK].label} », "
            f"une tâche de l'avenant 2 que la structure principale de la révision courante ne "
            f"porte pas : refusé sur ce champ, la tâche inconnue de la structure principale ; "
            f"rien n'est écrit (WF-RIS-0010, #786).",
            risk_provision_task_refused(),
        ),
    }
