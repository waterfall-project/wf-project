# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""An opportunity and its occurrence: declared variants of the risks of the witness (US-3080/L1).

EP-30 makes the severity of a risk the net gap its own estimate makes to the project, signed:
an own estimate that abandons a task and adds nothing gives a negative severity, and the risk is
an opportunity (WF-RIS-0080); its occurrence completes the task it abandons, which acquires its
budgeted amount at once, and the earned value curve marks it by a step (WF-RIS-0060,
WF-IND-0140); its cost at occurrence is negative, and the coverage counts it as it is
(WF-RIS-0050). The witness bears none of these: its three risks are those of EP-08
(``mockwitnessrisks``, US-3150), and 751 alone abandons a task, already completed
(``mockownestimate``). A declared counterfactual shows them, from one risk:

- the risk 755, « Mise en service par l'automaticien du client », identified on 2 March, after
  the reference 101 was marked — new since it —, whose own estimate abandons the « Mise en
  service », not started: its severity is minus the re-estimated amount of its line — the
  counterfactual leaves aside what the dates downstream would change —, and its provision nought,
  its line kept on the first task of the first level (``OPPORTUNITY``);
- ``risks_opportunity``, the register of the witness with it, and ``risk_matrix_opportunity``, the
  matrix, where it is at the lowest severity level and counted in its cell (WF-RIS-0040);
- ``risk_occurrence_report_abandoned_task``, the report of its occurrence today, in the form of a
  merge: the commissioning kept and completed, the earned value it brings, its provision line of
  nought removed (WF-RIS-0060);
- ``earned_value_curves_occurrence``, the curves of the witness once that occurrence is confirmed:
  the earned value of today raised by the budgeted amount of the commissioning, a step dated today,
  signed and attributed to the occurrence (WF-IND-0140);
- ``risk_coverage_opportunity``, the coverage then, the negative cost at occurrence of the
  opportunity offsetting that of 752 (WF-RIS-0050).

Its structure 217 and its line of provision 588 are read by no other example.
"""

from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockamendment, mockcore, mockcurves, mockhistory, mocktext, mocktoday
from wftools.mockids import universe
from wftools.mockriskwrites import first_root
from wftools.mockstructure import money
from wftools.mockwitness import STUDIES_STARTED, TODAY, N, lineage_id
from wftools.mockwitnessrisks import OCCURRED, REGISTER, Review, Risk

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue

ABANDONED = N.COMMISSIONING
"""The task the own estimate of the opportunity abandons: the commissioning, not started."""


def abandoned_lines() -> list[mockcore.Row]:
    """Return the lines of the task the opportunity abandons, as the current revision reads them."""
    return [
        row
        for row in mockcore.current()
        if row.kind == mockcore.ESTIMATE_LINE and row.parent == ABANDONED
    ]


def severity() -> Decimal:
    """Return the severity of the opportunity: minus what the lines it abandons cost today.

    The gap of the re-estimated totals of the main structure without the commissioning and of the
    main structure as it is, the counterfactual leaving aside what the dates downstream would
    change to their amounts (WF-RIS-0080).
    """
    return -sum((row.amounts.reestimated for row in abandoned_lines()), Decimal(0))


def brought() -> Decimal:
    """Return the earned value its occurrence brings: the budgeted amount of the commissioning."""
    return sum((row.amounts.budgeted for row in abandoned_lines()), Decimal(0))


PROBABILITY = Decimal("0.5")

OPPORTUNITY = Risk(
    755,
    "Mise en service par l'automaticien du client",
    "L'automaticien du client propose d'assurer lui-même la mise en service, à sa charge, "
    "dans le cadre de sa propre réception.",
    None,
    217,
    (
        Review(STUDIES_STARTED.instant, PROBABILITY, Decimal("0.00")),
        Review(STUDIES_STARTED.instant, PROBABILITY, severity()),
    ),
    provision_line=588,
)
"""The opportunity: declared on 2 March at 50 %, its own estimate then entered, which abandons the
commissioning; its line of provision 588, of nought, on the first task of the first level."""

OCCURRED_TODAY = replace(
    OPPORTUNITY,
    reviews=(*OPPORTUNITY.reviews, Review(TODAY, PROBABILITY, severity(), OCCURRED)),
)
"""The opportunity declared occurred today, its cost at occurrence its severity then."""


def _register() -> tuple[Risk, ...]:
    return (*REGISTER, OPPORTUNITY)


def _budget() -> Decimal:
    return mockhistory.reference_budget(mockhistory.reference_rows())


def item() -> JsonObject:
    """Return the opportunity as the register reads it (`Risk`)."""
    return mockhistory.risk_item(OPPORTUNITY, _budget(), first_root())


def risks_opportunity() -> JsonObject:
    """Return the register of the witness with the opportunity, last in the order of declaration."""
    register = mockhistory.readings()["risks"]
    items: list[JsonValue] = [*cast("list[JsonValue]", register["items"]), item()]
    return {
        "items": items,
        "totals": mockhistory.totals(mockhistory.reference_rows(), _register()),
        "meta": {"limit": mocktext.PAGE, "offset": 0, "total": len(items)},
    }


def risk_matrix_opportunity() -> JsonObject:
    """Return the matrix of the witness with the opportunity, at the lowest severity level."""
    return mockhistory.matrix(mockhistory.reference_rows(), _budget(), _register())


def risk_occurrence_report_abandoned_task() -> JsonObject:
    """Return the report of the occurrence of the opportunity today, in the form of a merge.

    The commissioning it abandons kept (`kept`) and completed on the day of the occurrence, not yet
    dated, its earned value brought; its provision line removed, of nought; nothing reopened,
    nothing refusing it (WF-RIS-0060, WF-IND-0030). The counters read: the main structure's, as
    `structures` lists it, and the risk's.
    """
    rows = {row.number: row for row in mockcore.current()}
    task = rows[ABANDONED]
    line = cast("int", OPPORTUNITY.provision_line)
    differences: list[JsonValue] = [
        {
            "change": "kept",
            "target": "task",
            "lineage_id": lineage_id(ABANDONED),
            "label": task.label,
            "predecessor_label": None,
            "fields": [],
        },
        {
            "change": "removed",
            "target": "estimate_line",
            "lineage_id": lineage_id(line),
            "label": f"Provision — {OPPORTUNITY.label}",
            "predecessor_label": None,
            "fields": [],
        },
    ]
    read = item()
    return {
        "main_structure_lock_version": mockamendment.structure("main")["lock_version"],
        "risk_lock_version": read["lock_version"],
        "creates_current_revision": False,
        "differences": differences,
        "completed_tasks": [
            {"lineage_id": lineage_id(ABANDONED), "label": task.label, "completed_on": None}
        ],
        "reopened_tasks": [],
        "earned_value_added": money(brought()),
        "earned_value_removed": money(Decimal(0)),
        "provision_amount": read["provision_amount"],
        "refusals": [],
    }


def earned_value_curves_occurrence() -> JsonObject:
    """Return the earned value curves of the witness once the opportunity occurred today.

    The earned value of today raised by the budgeted amount of the commissioning, which the
    occurrence completes; the planned value and the actual cost unchanged; one step, dated today,
    signed and attributed to the occurrence (WF-IND-0030, WF-IND-0140).
    """
    found = mocktoday.witness()
    curves = mockcurves.earned_value_curves(found.today, found.reference, found.costs)
    day = TODAY.date().isoformat()

    def raised(series: JsonObject) -> JsonObject:
        if series["name"] != "earned_value":
            return series
        points = [
            {**point, "amount": money(Decimal(cast("str", point["amount"])) + brought())}
            if point["date"] == day
            else point
            for point in cast("list[JsonObject]", series["points"])
        ]
        return {**series, "points": cast("list[JsonValue]", points)}

    step: JsonObject = {
        "date": day,
        "amount": money(brought()),
        "cause": "risk_occurrence",
        "risk_id": universe(OPPORTUNITY.number),
        "risk_label": OPPORTUNITY.label,
    }
    series = [raised(each) for each in cast("list[JsonObject]", curves["series"])]
    return {**curves, "series": cast("list[JsonValue]", series), "steps": [step]}


def risk_coverage_opportunity() -> JsonObject:
    """Return the coverage of the witness once the opportunity occurred today (WF-RIS-0050).

    Its cost at occurrence, negative, added as it is to that of 752: the cost of the occurred
    risks falls by as much, and the coverage variance rises; what they cost today with it, the
    opportunity having added no line, its frozen part alone. Its provision, nought, changes nothing.
    """
    covered = mockhistory.readings()["risk_coverage"]
    cost = cast("Decimal", mockhistory.occurrence_cost(OCCURRED_TODAY))

    def plus(name: str, amount: Decimal) -> str:
        return money(Decimal(cast("str", covered[name])) + amount)

    return {
        **covered,
        "occurred_cost": plus("occurred_cost", cost),
        "occurred_reestimated": plus("occurred_reestimated", cost),
        "coverage_variance": plus("coverage_variance", -cost),
    }


_amount, _day = mocktext.amount, mocktext.day


def examples() -> dict[str, JsonObject]:
    """Return the examples of the opportunity and of its occurrence, by file name."""
    read = item()
    budget = _budget()
    cell = cast("dict[str, int]", read["matrix_cell"])
    commissioning = next(row.label for row in mockcore.current() if row.number == ABANDONED)
    declared = (
        f"Variante contrefactuelle : le témoin porte en plus « {OPPORTUNITY.label} », identifiée "
        f"le {_day(STUDIES_STARTED.on)} à {_amount(PROBABILITY * 100, 0)} %, après le marquage de "
        f"la référence 101, dont le devis propre abandonne la « {commissioning} », non démarrée, "
        f"sans rien ajouter"
    )
    gravity = (
        f"sa gravité, l'écart net que son devis propre fait au coût du projet, vaut "
        f"{_amount(severity())}, moins le réestimé de la ligne abandonnée"
    )
    report = risk_occurrence_report_abandoned_task()
    curves = earned_value_curves_occurrence()
    [earned] = [
        cast("list[JsonObject]", each["points"])
        for each in cast("list[JsonObject]", curves["series"])
        if each["name"] == "earned_value"
    ]
    covered = risk_coverage_opportunity()
    witness = mockhistory.readings()["risk_coverage"]
    return {
        "risks_opportunity.json": mocktext.example(
            f"{declared}. Le registre la lit comme une opportunité : {gravity} ; sa provision est "
            f"nulle, et non de {_amount(severity() * PROBABILITY)}, sa ligne de provision restant "
            f"à montant nul sur la première tâche de premier niveau ; elle est nouvelle depuis la "
            f"référence (trend), et au niveau de gravité le plus bas, sa part de l'assiette étant "
            f"négative, {_amount(severity() / budget * 100, 4)} %. Les totaux de provisions sont "
            f"ceux du témoin, qu'elle ne change pas (WF-RIS-0010, WF-RIS-0040, WF-RIS-0080).",
            risks_opportunity(),
        ),
        "risk_matrix_opportunity.json": mocktext.example(
            f"{declared}. La matrice la classe au niveau de gravité le plus bas, "
            f"{cell['severity_level']}, sa part de l'assiette, négative, étant sous la première "
            f"borne, dans la case de sa probabilité, niveau {cell['probability_level']}, où elle "
            f"est comptée ; son point porte sa gravité négative en montant et en part, et une "
            f"provision nulle (WF-RIS-0040, WF-RIS-0080, WF-REF-0160).",
            risk_matrix_opportunity(),
        ),
        "risk_occurrence_report_abandoned_task.json": mocktext.example(
            f"{declared} ; {gravity}. Le compte rendu préalable de sa survenance aujourd'hui, dans "
            f"la forme de celui d'une fusion : la « {commissioning} » abandonnée n'est pas "
            f"retirée mais conservée (kept) et terminée le jour de la survenance, sans date tant "
            f"qu'elle n'est pas appliquée (completed_tasks), son reste à engager porté à zéro et "
            f"le montant budgété de sa ligne inchangé ; elle apporte d'un coup à la valeur acquise "
            f"ce montant budgété, {_amount(brought())}, et la survenance ne rouvre aucune tâche ; "
            f"la ligne de provision, de montant nul, est retirée ; rien ne la refuse (WF-RIS-0060, "
            f"WF-IND-0030).",
            report,
        ),
        "earned_value_curves_occurrence.json": mocktext.example(
            f"{declared}. Les courbes de valeur acquise du projet une fois sa survenance "
            f"confirmée aujourd'hui, le {_day(TODAY.date())} : la « {commissioning} » terminée "
            f"acquiert son montant budgété, "
            f"{_amount(brought())}, et la valeur acquise à la date de calcul passe à "
            f"{_amount(Decimal(cast('str', earned[-1]['amount'])))} ; la marche de la survenance, "
            f"datée du jour, signée et attribuée au risque (steps, cause risk_occurrence), le dit, "
            f"la série la portant déjà à son point ; la valeur planifiée et le coût réel sont ceux "
            f"du témoin (WF-IND-0110, WF-IND-0140).",
            curves,
        ),
        "risk_coverage_opportunity.json": mocktext.example(
            f"{declared} ; {gravity}. La couverture des risques du témoin une fois sa survenance "
            f"déclarée aujourd'hui : son coût à la survenance, {_amount(severity())}, s'ajoute "
            f"tel quel à celui de « {REGISTER[1].label} », et le coût des survenus passe de "
            f"{_amount(Decimal(cast('str', witness['occurred_cost'])))} à "
            f"{_amount(Decimal(cast('str', covered['occurred_cost'])))} ; l'écart de couverture "
            f"passe de {_amount(Decimal(cast('str', witness['coverage_variance'])))} à "
            f"{_amount(Decimal(cast('str', covered['coverage_variance'])))}, l'économie "
            f"compensant le dépassement d'un autre risque survenu ; sa provision, nulle, ne "
            f"change pas les provisions restantes (WF-RIS-0050).",
            covered,
        ),
    }
