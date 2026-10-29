# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The answers of the entries of a risk: declared, modified, reviewed, declared occurred (#763).

The forms of the risks declare a risk, modify it, review it and declare it occurred (US-0520):
their answers are read, as the register is, from the risks of ``wftools.mockwitnessrisks`` by
``wftools.mockhistory.risk_item``, never written by hand (K5 of EP-15):

- a risk declared today, its own structure opened empty with it — its severity and its provision
  nought until its own estimate is priced in the grid of estimate — and its line of provision on
  the first task of the first level, no task designated (``risk_created``, WF-RIS-0010, #786);
- that risk modified, its line of provision moved to the task its form designates, the total of
  the estimate unchanged (``risk_updated``);
- the rework of the wiring confirmed today without a change, a review dated of today
  (``risk_reviewed``, WF-RIS-0010), and its reviews read after it (``risk_reviews_reviewed``);
- the rework of the wiring dismissed today instead, a counterfactual, its line of provision
  withdrawn (``risk_dismissed``), and the unavailability of the automation engineer, dismissed on
  2 February, identified again today, its line recreated on the task it designated
  (``risk_reidentified``, WF-RIS-0010, WF-RIS-0020);
- the occurrence of the delay of the cabinets, on 20 February, put in the queue
  (``task_occurrence_queued``, WF-RIS-0060, WF-ARC-0090);
- a declaration whose provision names a task the main structure does not bear
  (``risk_provision_task_refused``);
- the line of provision of the rework of the wiring moved in the grid, which its form alone
  moves (``nodes_move_provision_refused``, WF-RIS-0010, #1227);
- and the occurrence of the rework of the wiring before its confirmation (US-0680, #1383): its own
  estimate, the structure 204, read (``nodes_risk_estimate``, WF-RIS-0030); the report of what its
  occurrence would make of the main structure of the current revision (``risk_occurrence_report``,
  WF-RIS-0060), and the confirmation that returns what it read (``risk_occurrence_sent``); the
  report and the occurrence refused for a risk not identified (``risk_occurrence_not_identified``),
  and the confirmation refused for a report gone stale (``risk_occurrence_report_stale``,
  WF-IHM-0110).

The risk declared is a counterfactual: no reading of the witness knows its risk 754, its own
structure 208 or its line of provision 585 — the register, the structures and the grids read the
witness as it is, before the declaration (``DECLARED``). The reviews are of the register: the
confirmation of 751 and the return of 753 follow the witness today; the dismissal of 751, which
would render it at the version its confirmation renders, is a counterfactual (#421).

They would have carried ``mockhistory`` past the thousand lines (``wftools.sources``).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockamendment, mockcore, mockdating, mocktext
from wftools.mockhistory import (
    reference_budget,
    reference_rows,
    reviews,
    risk_item,
    stamp,
)
from wftools.mockids import universe
from wftools.mockstructure import described
from wftools.mockwitness import REWORK_ESTIMATE, TODAY, N, lineage_id
from wftools.mockwitnessrisks import (
    AUTOMATION_ENGINEER,
    DELIVERY_DELAY,
    DISMISSED,
    IDENTIFIED,
    REFERENCE_PROVISIONS,
    REGISTER,
    REWORK,
    Review,
    Risk,
)

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue

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


def _reviewed(risk: Risk, state: str) -> Risk:
    """Return a risk reviewed today, its probability and its severity kept, in the state given."""
    return replace(risk, reviews=(*risk.reviews, replace(risk.last, at=TODAY, state=state)))


def risk_reviewed() -> JsonObject:
    """Return what reviewRisk answers when the rework of the wiring is confirmed without a change.

    Its probability and its state sent as they are: a review dated of today (WF-RIS-0010).
    """
    return risk_item(_reviewed(REWORK, IDENTIFIED), _budget())


def risk_reviews_reviewed() -> list[JsonValue]:
    """Return the reviews of the rework of the wiring read after its confirmation of today.

    The review dated of today first, before those the register knows (WF-RIS-0010).
    """
    return reviews(_reviewed(REWORK, IDENTIFIED))


def risk_dismissed() -> JsonObject:
    """Return what reviewRisk answers when the rework of the wiring is dismissed today.

    A counterfactual: the witness confirms it today (``risk_reviewed``). Its probability kept, it
    bears no line of provision any more, nor a task for it (WF-RIS-0010, WF-RIS-0020).
    """
    return risk_item(_reviewed(REWORK, DISMISSED), _budget())


REIDENTIFIED_LINE = 586
"""The line of provision the return of the unavailability of the automation engineer recreates in
the main structure of the current revision: a node of its own, which no reading of the witness
renders (#421)."""


def reidentified_task() -> int:
    """Return the task that bears the line recreated: the one the risk designated (#1227).

    The commissioning, which bore its line in the reference, is still a task of the main structure
    of the current revision; were it not, the first task of the first level would bear it.
    """
    designated, _ = REFERENCE_PROVISIONS[AUTOMATION_ENGINEER.number]
    tasks = {row.number for row in mockcore.current() if row.node["kind"] == "task"}
    if designated not in tasks:
        message = f"the task {designated} is no task of the main structure any more"
        raise ValueError(message)
    return designated


def risk_reidentified() -> JsonObject:
    """Return what reviewRisk answers when the unavailability of the automation engineer returns.

    Dismissed on 2 February, identified again today at the probability it had: its category still
    active, it is not asked; its line of provision is recreated on the task it designated
    (WF-RIS-0010, WF-RIS-0020, #1227).
    """
    returned = replace(_reviewed(AUTOMATION_ENGINEER, IDENTIFIED), provision_line=REIDENTIFIED_LINE)
    return risk_item(returned, _budget(), reidentified_task())


def task_occurrence_queued() -> JsonObject:
    """Return what declareRiskOccurrence answered when the delay of the cabinets occurred.

    On 20 February 2026, the instant of its last review (``mockwitnessrisks``): the merge of its own
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


MOVED_PROVISION_CORRELATION = universe(1304)
PROVISION_MOVED_UNDER = DESIGNATED
"""The task the line of provision of the rework of the wiring is sent under, in the grid: the
mounting of the cabinets on site, which its risk does not designate."""


def nodes_move_provision_refused() -> JsonObject:
    """Return what moveNodes answers to the line of provision of the rework moved in the grid.

    A line of provision is borne by the task its risk designates, which its form changes alone
    (``provision_task_id``): moved among other lines, it is refused on its place in ``node_ids``,
    and the refusal names the risk, which the grid does not read (WF-RIS-0010, #1227).
    """
    rows = {row.number: row for row in mockcore.current()}
    line = rows[cast("int", REWORK.provision_line)]
    if not cast("JsonObject", line.node["estimate_line"])["is_computed"]:
        message = f"the line {line.number} is no line of provision"
        raise ValueError(message)
    if line.parent == PROVISION_MOVED_UNDER or [
        risk for risk in REGISTER if risk.provision_line == line.number
    ] != [REWORK]:
        message = f"the line {line.number} is not moved away from the task of its one risk"
        raise ValueError(message)
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [
            {
                "pointer": "/node_ids/0",
                "code": "PROVISION_LINE_MOVED_BY_RISK",
                "params": {"risk": {"risk_id": universe(REWORK.number), "label": REWORK.label}},
            }
        ],
        "correlation_id": MOVED_PROVISION_CORRELATION,
    }


# --- The report before the occurrence ----------------------------------------------------------

OCCURRING = REWORK
"""The risk whose occurrence the report describes: the rework of the wiring, identified, its own
estimate the structure 204 (``mockwitness.REWORK_ESTIMATE``, US-0680)."""

NOT_IDENTIFIED = AUTOMATION_ENGINEER
"""The risk whose report and occurrence are refused: the unavailability of the automation engineer,
dismissed on 2 February (WF-RIS-0020)."""

NOT_IDENTIFIED_CORRELATION = universe(1591)
STALE_CORRELATION = universe(1592)

READ = ("main_structure_lock_version", "risk_lock_version", "creates_current_revision")
"""What the confirmation returns of the report, as it read it (`RiskOccurrence`)."""

SCHEDULE = ("duration", "start", "finish")
"""What the occurrence may change of the task that bore the line of provision, in the order of
`NodeColumn`: its dates and its duration, a summary spanning its subordinates (WF-PLA-0040)."""
SCHEDULE_SAID = {"duration": "sa durée", "start": "son début", "finish": "sa fin"}


def risk_estimate() -> list[mockcore.Row]:
    """Return the own estimate of the rework of the wiring read today, dated and priced.

    It has no previous review: an own estimate has no remaining to commit (WF-RAE-0040).
    """
    return mockcore.core(REWORK_ESTIMATE)


def nodes_risk_estimate() -> JsonObject:
    """Return what listNodes answers of the own estimate of the rework, the structure 204.

    Every node, every total; its tasks name neither a lot, nor a post, nor an inscription among the
    fields they accept, those being the main structure's alone (WF-PLA-0170), and no node is marked,
    an own estimate being read against nothing (`Node.difference`).
    """
    answer = mockcore.whole(risk_estimate())
    items = [
        {
            **node,
            "editable_fields": [
                field
                for field in cast("list[JsonValue]", node["editable_fields"])
                if field not in mockamendment.MAIN_ONLY
            ],
        }
        for node in cast("list[JsonObject]", answer["items"])
    ]
    return {**answer, "items": cast("list[JsonValue]", items)}


def bearer() -> mockcore.Row:
    """Return the task of the main structure that bears the line of provision of the rework.

    Not a milestone: the tasks of the own estimate go under it, in last position, and not after it
    (WF-RIS-0060).
    """
    rows = {row.number: row for row in mockcore.current()}
    task = rows[cast("int", rows[cast("int", OCCURRING.provision_line)].parent)]
    if cast("JsonObject", task.node["task"])["is_milestone"]:
        message = f"the task {task.number} that bears the provision is a milestone"
        raise ValueError(message)
    return task


def bearer_changes() -> list[JsonValue]:
    """Return what the occurrence changes of the task that bears the provision, as columns.

    It becomes a summary of the tasks of the own estimate, which keep the dates they had there
    (WF-RIS-0060): its dates span theirs, and its duration is the work between them on its own
    calendar, that of the lines it bears (WF-PLA-0040).
    """
    was = mockdating.schedule(described())[bearer().number]
    placed = mockdating.schedule(REWORK_ESTIMATE).values()
    start = min(each.start for each in placed)
    finish = max(each.finish for each in placed)
    changed = {
        "duration": was.calendar.work_between(start, finish) != was.hours,
        "start": start != was.start,
        "finish": finish != was.finish,
    }
    return [name for name in SCHEDULE if changed[name]]


def _difference(change: str, row: mockcore.Row, fields: list[JsonValue]) -> JsonObject:
    """Return a node added, updated or removed, as the report of a merge names it."""
    return {
        "change": change,
        "target": row.kind,
        "lineage_id": None if change == "added" else lineage_id(row.number),
        "label": row.label,
        "predecessor_label": None,
        "fields": fields,
    }


def risk_occurrence_report() -> JsonObject:
    """Return what getRiskOccurrenceReport answers of the rework of the wiring (WF-RIS-0060).

    The tasks and the lines of its own estimate added under the task that bears its provision, in
    the order of its plan; that task modified, become their summary; the line of provision
    withdrawn, and its amount withdrawn from the remaining to commit; nothing refusing it. The
    counters read: the main structure's, as `structures` lists it, and the risk's, as the register
    reads it; the witness has a current revision, the 102, which the occurrence does not create
    (WF-RIS-0060, WF-REV-0010). An added node has no lineage in the main structure yet; the links
    within the own estimate come with its tasks, as those of the tasks an amendment adds
    (``mockamendment``).
    """
    main = {row.number: row for row in mockcore.current()}
    differences: list[JsonValue] = [_difference("added", row, []) for row in risk_estimate()]
    differences.append(_difference("updated", bearer(), bearer_changes()))
    line = main[cast("int", OCCURRING.provision_line)]
    differences.append(_difference("removed", line, []))
    risk = risk_item(OCCURRING, _budget())
    return {
        "main_structure_lock_version": mockamendment.structure("main")["lock_version"],
        "risk_lock_version": risk["lock_version"],
        "creates_current_revision": False,
        "differences": differences,
        "provision_amount": risk["provision_amount"],
        "refusals": [],
    }


def risk_occurrence_sent() -> JsonObject:
    """Return the confirmation of the occurrence of the rework, as its report read it.

    It returns the two counters and ``creates_current_revision`` of ``risk_occurrence_report`` as
    they were read (WF-IHM-0110).
    """
    report = risk_occurrence_report()
    return {"confirmed": True, **{name: report[name] for name in READ}}


def risk_occurrence_not_identified() -> JsonObject:
    """Return the refusal of the report, and of the occurrence, of a risk not identified.

    The condition its command ``declare_occurrence`` says it lacks (WF-RIS-0020, WF-IHM-0090).
    """
    item = risk_item(NOT_IDENTIFIED, _budget())
    [command] = [
        each
        for each in cast("list[JsonObject]", item["available_commands"])
        if each["command"] == "declare_occurrence"
    ]
    [condition] = cast("list[JsonValue]", command["missing_conditions"])
    return {
        "code": "STATE_FORBIDS_OPERATION",
        "status": 409,
        "params": {"missing_condition": condition},
        "correlation_id": NOT_IDENTIFIED_CORRELATION,
    }


def risk_occurrence_report_stale() -> JsonObject:
    """Return the refusal of an occurrence confirmed with the counters of a stale report.

    The report read before the review of the risk of 2 March, which advanced its counter: the
    version returned is the risk's, the object the path names, and nothing else, as every 412
    (#296, WF-IHM-0110). The main structure is at its first version: no earlier report read it.
    """
    return {
        "code": "STALE_LOCK_VERSION",
        "status": 412,
        "params": {"expected_lock_version": risk_item(OCCURRING, _budget())["lock_version"]},
        "correlation_id": STALE_CORRELATION,
    }


# --- The examples ------------------------------------------------------------------------------


def _task_label(item: JsonObject) -> str:
    return cast("str", cast("JsonObject", item["provision_task"])["label"])


def _reviews_examples() -> dict[str, JsonObject]:
    """Return the named examples of the reviews of a risk, by file name."""
    reviewed, dismissed, returned = risk_reviewed(), risk_dismissed(), risk_reidentified()
    rework = mocktext.amount(REWORK.last.probability * 100, 0)
    return {
        "risk_reviewed.json": mocktext.example(
            f"« {REWORK.label} » réexaminé aujourd'hui sans modification, sa probabilité de "
            f"{rework} % et son état identifié envoyés tels quels : la confirmation produit un "
            f"réexamen daté du jour (last_review_on), qui s'ajoute à son historique "
            f"(risk_reviews_reviewed) ; sa gravité et sa provision inchangées, sa ligne toujours "
            f"portée par « {_task_label(reviewed)} » ; une version de plus (201, WF-RIS-0010, "
            f"WF-RIS-0020).",
            reviewed,
        ),
        "risk_reviews_reviewed.json": mocktext.example(
            f"L'historique des réexamens de « {REWORK.label} » relu après sa confirmation "
            f"d'aujourd'hui (risk_reviewed), du plus récent au plus ancien : le réexamen daté du "
            f"{mocktext.day(TODAY.date())}, sa probabilité, sa gravité et son état inchangés, "
            f"avant ceux que l'historique portait déjà (risk_reviews ; WF-RIS-0010).",
            risk_reviews_reviewed(),
        ),
        "risk_dismissed.json": mocktext.example(
            f"Variante contrefactuelle : « {REWORK.label} » écarté aujourd'hui au lieu d'être "
            f"confirmé (risk_reviewed), sa probabilité de {rework} % envoyée telle quelle et "
            f"l'état écarté retenu : un réexamen daté du jour ; sa ligne de provision retirée, il "
            f"ne pèse plus sur le devis ni sur le reste à engager et ne nomme plus de ligne ni de "
            f"tâche de provision (provision_node_id, provision_task) ; il garde la catégorie de sa "
            f"provision, que son retour reprendrait ; il ne change plus la catégorie ni le "
            f"sous-projet de sa provision et ne se déclare plus survenu (risk_identified), mais se "
            f"réexamine pour redevenir identifié ; une version de plus (201, WF-RIS-0010, "
            f"WF-RIS-0020).",
            dismissed,
        ),
        "risk_reidentified.json": mocktext.example(
            f"« {AUTOMATION_ENGINEER.label} », écarté le "
            f"{mocktext.day(AUTOMATION_ENGINEER.last.at.date())}, redevenu identifié aujourd'hui "
            f"à la probabilité de "
            f"{mocktext.amount(AUTOMATION_ENGINEER.last.probability * 100, 0)} % qu'il avait : "
            f"un réexamen daté du jour ; sa catégorie « "
            f"{returned['provision_cost_category_label']} » encore active, elle n'est pas "
            f"redemandée ; sa ligne de provision recréée (provision_node_id) sur la tâche qu'il "
            f"désignait, « {_task_label(returned)} », encore une tâche de la structure principale "
            f"(provision_task) ; ses commandes de nouveau disponibles, sauf la suppression, une "
            f"révision marquée le citant (risk_not_cited) ; une version de plus (201, "
            f"WF-RIS-0010, WF-RIS-0020, #1227).",
            returned,
        ),
    }


def _occurrence_examples() -> dict[str, JsonObject]:
    """Return the named examples of the occurrence of a risk before its confirmation."""
    estimate = nodes_risk_estimate()
    report = risk_occurrence_report()
    tasks = [row for row in risk_estimate() if row.kind == mockcore.TASK]
    said = mocktext.listed([f"« {row.label} »" for row in tasks])
    entered = next(each.manual for each in REWORK_ESTIMATE if each.manual is not None)
    task = bearer()
    main = {row.number: row for row in mockcore.current()}
    line = main[cast("int", OCCURRING.provision_line)]
    changed = mocktext.listed([SCHEDULE_SAID[cast("str", name)] for name in bearer_changes()])
    severity = cast("JsonObject", estimate["totals"])["reestimated_amount"]
    reviewed = NOT_IDENTIFIED.last.at.date()
    return {
        "nodes_risk_estimate.json": mocktext.example(
            f"Le devis propre de « {OCCURRING.label} », structure {OCCURRING.own_structure} de la "
            f"révision courante, lu le {mocktext.day(mockcore.READ_ON)} : {said}, sous-traitées, "
            f"la première en mode manuel du {mocktext.day(entered[0])} au "
            f"{mocktext.day(entered[1])}, la seconde à sa suite ; leur total, "
            f"{mocktext.amount(Decimal(cast('str', severity)))}, est la gravité du risque "
            f"(risk). Les tâches n'y portent ni lot, ni poste, ni "
            f"inscription, et ne les nomment pas parmi les champs qu'elles acceptent ; aucun nœud "
            f"n'est marqué, le devis propre ne se lisant contre rien (WF-RIS-0010, WF-RIS-0030, "
            f"WF-PLA-0170, US-0680).",
            estimate,
        ),
        "risk_occurrence_report.json": mocktext.example(
            f"Le compte rendu préalable de la survenance de « {OCCURRING.label} », risque "
            f"identifié du témoin : {said}, avec leurs lignes, ajoutées en dernière position sous "
            f"le « {task.label} », qui "
            f"portait la ligne de provision et n'est pas un jalon (nodes_risk_estimate) ; le "
            f"« {task.label} » modifié par {changed}, devenu la récapitulative de ces tâches, "
            f"dont il couvre les dates ; la ligne « "
            f"{line.label} » retirée, et sa provision de "
            f"{mocktext.amount(Decimal(cast('str', report['provision_amount'])))} retirée du "
            f"reste à engager ; aucun motif de refus. Rien n'est écrit : la confirmation, qui "
            f"renverra les compteurs lus — celui de la structure principale, "
            f"{report['main_structure_lock_version']}, comme `structures` le dit, et celui du "
            f"risque, {report['risk_lock_version']}, comme `risk` le dit, et "
            f"creates_current_revision faux, la révision en cours existant déjà —, est offerte "
            f"(risk_occurrence_sent ; WF-RIS-0060, WF-IHM-0110, #1383).",
            report,
        ),
        "risk_occurrence_sent.json": mocktext.example(
            f"La confirmation de la survenance de « {OCCURRING.label} », après son compte rendu "
            f"(risk_occurrence_report) : elle renvoie ce qu'il a lu, tel quel — le compteur de "
            f"la structure principale, {report['main_structure_lock_version']}, celui du risque, "
            f"{report['risk_lock_version']}, et creates_current_revision faux, le projet ayant "
            f"une révision en cours, que la survenance ne crée donc pas. Lu vrai, faute de "
            f"révision en cours, il ferait refuser la confirmation par 412 si une révision en "
            f"cours était née depuis la lecture (WF-RIS-0060, WF-REV-0010, WF-IHM-0110).",
            risk_occurrence_sent(),
        ),
        "risk_occurrence_not_identified.json": mocktext.example(
            f"Le compte rendu de la survenance de « {NOT_IDENTIFIED.label} », écarté le "
            f"{mocktext.day(reviewed)}, ou sa survenance, demandés aujourd'hui : seul un risque "
            f"identifié survient, et la commande declare_occurrence du risque nomme la condition "
            f"qui manque (risks). Rien n'est lu ni écrit (WF-RIS-0020, WF-IHM-0090, #1383).",
            risk_occurrence_not_identified(),
        ),
        "risk_occurrence_report_stale.json": mocktext.example(
            f"La survenance de « {OCCURRING.label} » confirmée aujourd'hui avec les compteurs "
            f"d'un compte rendu lu avant son réexamen du "
            f"{mocktext.day(OCCURRING.last.at.date())}, qui l'a fait avancer : le compte rendu "
            f"est périmé, rien n'est fusionné, et la version courante du risque, l'objet que le "
            f"chemin nomme, est rendue ; l'écran propose de relire le compte rendu (WF-RIS-0060, "
            f"WF-IHM-0110, #1383).",
            risk_occurrence_report_stale(),
        ),
    }


def examples() -> dict[str, JsonObject]:
    """Return the named examples of the entries of a risk, by file name."""
    created, updated = risk_created(), risk_updated()
    rows = {row.number: row for row in mockamendment.rows()}
    main = {row.number: row for row in mockcore.current()}
    provision = main[cast("int", REWORK.provision_line)]
    percent = mocktext.amount(DECLARED.last.probability * 100, 0)
    return {
        "risk_created.json": mocktext.example(
            f"Variante contrefactuelle : « {DECLARED.label} », déclaré aujourd'hui à {percent} %, "
            f"un risque qu'aucune lecture du témoin ne connaît, ni sa structure propre "
            f"{DECLARED.own_structure} ni sa ligne de provision {DECLARED.provision_line}. "
            f"La déclaration ouvre sa "
            f"structure propre (structure_id), vide — sa gravité et sa provision sont nulles "
            f"jusqu'à ce que son devis propre soit chiffré dans la grille de devis, ni l'une ni "
            f"l'autre saisies — et sa ligne de provision dans la structure principale de la "
            f"révision courante (provision_node_id). Aucune tâche n'étant désignée, la ligne est "
            f"portée par la première tâche de premier niveau, « {_task_label(created)} » "
            f"(provision_task) ; elle porte la catégorie « "
            f"{created['provision_cost_category_label']} », la seule de type provision pour "
            f"risques, et aucun sous-projet. À sa première version (201), toutes ses commandes "
            f"disponibles (WF-RIS-0010, WF-RIS-0030, #786).",
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
        **_reviews_examples(),
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
        "nodes_move_provision_refused.json": mocktext.example(
            f"La ligne de provision de « {REWORK.label} », « {provision.label} », portée par le "
            f"« {main[cast('int', provision.parent)].label} », déplacée dans la grille sous le "
            f"« {main[PROVISION_MOVED_UNDER].label} » : le déplacement est refusé sur elle, sa "
            f"tâche étant celle que son risque désigne, qui se change par le formulaire du "
            f"risque ; le refus nomme le risque, que la grille ne lit pas. Rien ne bouge "
            f"(WF-RIS-0010, #1227).",
            nodes_move_provision_refused(),
        ),
        **_occurrence_examples(),
    }
