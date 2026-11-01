# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The witness read through its history: its marked revisions and its risks (EP-02/L23, #287).

The chronology of the witness is said once in ``wftools.mockwitness``: the offer 100 opened on
3 November 2025 and marked on 15 December; the risks identified on 12 January 2026, whose first
entry opens the revision 101 (WF-RIS-0020); the amendment 1 merged into it on 1 February, which
marks it and makes it the reference (WF-REV-0050); the review of the risk 751 the next day, which
opens the current revision 102; the occurrence of the risk 752 on 20 February, merged into 102 —
it marks no revision and leaves the reference where it is (WF-RIS-0060). The amendment 2, « reprise
des essais », coexisted with the amendment 1 in the reference without being merged; the current
revision took it over, still not merged, a differential read against its main structure
(``wftools.mockamendment``, WF-REV-0100, #791). Here the two marked revisions are described from
the whole structure of the witness, its core first, as they were marked (EP-14/L45a), and what the
examples say of them is read from those descriptions (their comparison is said by
``wftools.mockcomparisons``):

- the reference budget and the reserve for risks of the reference (WF-RIS-0050), which place each
  risk in its cell of the matrix and give the totals of the provisions (WF-RIS-0040);
- the register of the risks, and a page of it, a risk alone, the matrix, the reviews of a risk and
  the coverage of the risks (``risks``, ``risks_page``, ``risk``, ``risk_occurred_detail``,
  ``risk_matrix``, ``risk_reviews``, ``risk_coverage``), from the risks of ``mockwitnessrisks``
  and the whole structure read today, 751 and 753 at its scale (EP-14/L45b).

The formulas are simple and said here, to be replaced by the kernel of EP-07 and EP-08. Each
marked revision is priced at the rates of its reference year: the reference at those of 2026, the
core's; the offer, of 2025, at the rates of 2025 of the volume of rates
(``mockstructure.hourly_rate``), as #232 proposes. What changes of a node is said by
``mockdiff``: the amount of a task is its lines', said by them and by the deltas.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockcategories, mockcore, mocktext
from wftools.mockcalendar import START_TO_START
from wftools.mockids import universe
from wftools.mockstructure import (
    LABOR,
    LABOUR_RATES,
    NON_LABOR,
    PROVISION,
    JsonObject,
    JsonValue,
    described,
    hourly_rate,
    labels,
    money,
    share,
)
from wftools.mockwitness import (
    AMENDMENT_MERGED,
    EQUIPMENT,
    FACTORY_ACCEPTANCE,
    LABOUR,
    OFFER_MARKED,
    OFFER_OPENED,
    OFFER_YEAR,
    RISK_751_REVIEWED,
    RISKS_IDENTIFIED,
    TODAY,
    WIRING,
    Event,
    Line,
    Link,
    N,
    Task,
    fixture,
    rewritten,
)
from wftools.mockwitnessrisks import (
    DISMISSED,
    IDENTIFIED,
    OCCURRED,
    REGISTER,
    Risk,
    reference,
    reference_provision,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime

OFFER, REFERENCE, CURRENT = universe(100), universe(101), universe(102)
"""The revisions of the witness: the offer v1.0, the reference, the current revision."""

REVISIONS: dict[str, tuple[Event, Event | None]] = {
    OFFER: (OFFER_OPENED, OFFER_MARKED),
    REFERENCE: (RISKS_IDENTIFIED, AMENDMENT_MERGED),
    CURRENT: (RISK_751_REVIEWED, None),
}
"""When each revision was created and marked: the examples that carry it say these instants."""

RISKS_PAGE = 2
"""The size of the page of the register `risks_page` reads: fewer than its risks (#1367)."""


def stamp(at: datetime) -> str:
    """Return an instant as the contract carries it, in universal time: 2026-06-03T14:05:00Z.

    As the readings of the nodes write when their structure was dated (``mockcore.stamp``).
    """
    return mockcore.stamp(at)


# --- The marked revisions, described from the core --------------------------------------------

MILESTONE = FACTORY_ACCEPTANCE
MOUNTING, TESTS_LINE, DESIGN_FILE, INSTALLATION_TASK = (
    N.MOUNTING,
    N.TESTS_LINE,
    N.DESIGN_FILE,
    N.INSTALLATION,
)
"""The nodes of the core the history is about (``mockwitness``)."""

OFFER_LABOUR_HOURS = Decimal(10)
OFFER_DESIGN_FILE_DAYS = 3
SITE_TRIALS = Task(
    N.SITE_TRIALS,
    "Essais préliminaires sur site",
    days=5,
    links=(Link(MOUNTING, START_TO_START),),
    lines=(
        Line(
            N.SITE_TRIALS_LINE,
            "Location du banc d'essais",
            EQUIPMENT,
            unit=Decimal("350.00"),
        ),
    ),
)
"""What the amendment 1 changed from the offer: the connection of the terminal blocks, ten hours
in the offer; the assistance of the commissioning technician to the trials of the wiring, which
it added; the factory acceptance, which it added between the wiring and the mounting on site; the
design file, three days in the offer; and the preliminary trials on site, which it removed."""


def offer(roots: Iterable[Task] | None = None) -> tuple[Task, ...]:
    """Return the offer v1.0 as marked on 15 December 2025, from the whole structure of today.

    The reference without the amendment 1, and before any risk was identified: without any line
    of provision. Nor any subproject: their codes come from the ERP with the order, on 15 January
    2026, and the subprojects were declared after it (WF-PRJ-0050, ``subprojects``). The factory
    acceptance, which the amendment added, was not there: what follows it today — the mounting on
    site, the lots of the control station drawn about the core — followed the wiring of the
    cabinets, which it ends. From the structure given, the whole one by default.
    """

    def change(task: Task) -> Task:
        lines = tuple(
            replace(
                line,
                subproject=None,
                hours=OFFER_LABOUR_HOURS if line.number == LABOUR else line.hours,
                # Its own budget is its amount: it is the offer that fixes it.
                budgeted=None,
            )
            for line in task.lines
            if not line.is_provision and line.number != TESTS_LINE
        )
        children = tuple(child for child in task.children if child.number != MILESTONE)
        if task.number == INSTALLATION_TASK:
            children = (*children, SITE_TRIALS)
        links = tuple(
            replace(link, predecessor=WIRING) if link.predecessor == MILESTONE else link
            for link in task.links
        )
        changed = replace(task, lines=lines, children=children, links=links)
        if task.number == DESIGN_FILE:
            return replace(changed, days=OFFER_DESIGN_FILE_DAYS)
        return changed

    return rewritten(reference(described() if roots is None else roots), change)


def reference_rows() -> list[mockcore.Row]:
    """Return the reference read on the day it was marked, on the whole structure."""
    return mockcore.core(mockcore.REFERENCE, AMENDMENT_MERGED.on)


def offer_rates() -> dict[str, Decimal]:
    """Return the hourly rates of the offer, those of its reference year, 2025 (WF-REV-0030).

    The rates of 2025 of the volume of rates (``getHourlyRateGrid``), as #232 proposes, for each
    labour category the core employs.
    """
    return {category: hourly_rate(rate, OFFER_YEAR) for category, rate in LABOUR_RATES.items()}


def offer_rows() -> list[mockcore.Row]:
    """Return the offer read on the day it was marked, at the rates it kept."""
    return mockcore.core(offer(), OFFER_MARKED.on, offer_rates())


def moved_offer_rows() -> list[mockcore.Row]:
    """Return the offer bearing the commissioning under the control station (counterfactual)."""
    found: list[Task] = []

    def gather(task: Task) -> Task:
        found.extend(child for child in task.children if child.number == N.COMMISSIONING)
        return task

    tasks = rewritten(offer(), gather)

    def move(task: Task) -> Task:
        if task.number == N.INSTALLATION:
            kept = tuple(child for child in task.children if child.number != N.COMMISSIONING)
            return replace(task, children=kept)
        if task.number == N.CONTROL_STATION:
            return replace(task, children=(*task.children, *found))
        return task

    return mockcore.core(rewritten(tasks, move), OFFER_MARKED.on, offer_rates())


def estimate_line(row: mockcore.Row) -> dict[str, JsonValue]:
    """Return the estimate line a row bears."""
    return cast("dict[str, JsonValue]", row.node["estimate_line"])


def is_provision(row: mockcore.Row) -> bool:
    """Whether a row is a line of provision: computed from its risk, never entered."""
    return row.kind == mockcore.ESTIMATE_LINE and estimate_line(row)["is_computed"] is True


def nature(row: mockcore.Row) -> str:
    """Return the nature of cost of a line: provision, labour by its hours, else disbursement."""
    if is_provision(row):
        return PROVISION
    return LABOR if estimate_line(row)["hours"] is not None else NON_LABOR


def reference_budget(rows: Iterable[mockcore.Row]) -> Decimal:
    """Return the reference budget: the budgeted amounts, but those of the provisions."""
    return sum(
        (
            row.amounts.budgeted
            for row in rows
            if row.kind == mockcore.ESTIMATE_LINE and not is_provision(row)
        ),
        Decimal(0),
    )


def reserve(rows: Iterable[mockcore.Row]) -> Decimal:
    """Return the reserve for risks of the reference: the sum of its lines of provision.

    The reserve keeps, at each new reference, the provision the risks that occurred or were
    dismissed before it bore in the previous one (WF-RIS-0050): the witness has a single
    reference, marked while its three risks were identified, so its lines are the whole of it.
    """
    return sum((row.amounts.base for row in rows if is_provision(row)), Decimal(0))


# --- The risks --------------------------------------------------------------------------------


def computed_fields(state: str) -> list[JsonValue]:
    """Return the fields of a risk the server computes, each with what it depends on.

    The severity and the provision, then, for a risk that occurred, its cost at occurrence
    (`Risk.computed_fields`, WF-IHM-0030): the provision of an identified risk from its severity
    and its probability, that of a risk occurred or dismissed from the reference revision
    (`provision_amount`), the cost at occurrence from its own estimate when it occurred.
    """
    provision = "severity_and_probability" if state == IDENTIFIED else "reference_provision"
    fields: list[JsonValue] = [
        {"field": "severity", "dependencies": ["own_estimate"]},
        {"field": "provision_amount", "dependencies": [provision]},
    ]
    if state == OCCURRED:
        fields.append({"field": "occurrence_cost", "dependencies": ["occurrence_estimate"]})
    return fields


def provision(risk: Risk) -> Decimal:
    """Return the provision of a risk today: its severity at its probability (WF-RIS-0010)."""
    return (risk.last.severity * risk.last.probability).quantize(Decimal("0.01"))


def provision_amount(risk: Risk) -> Decimal:
    """Return the provision a risk is read with (`Risk.provision_amount`, H-03).

    An identified risk its provision today; one that occurred or was dismissed, which bears no
    line any more, the provision it bore in the reference, nothing if it was not identified there
    (WF-RIS-0040, WF-RIS-0050): the line of the register sums to the totals.
    """
    return provision(risk) if risk.last.state == IDENTIFIED else reference_provision(risk)


def occurrence_cost(risk: Risk) -> Decimal | None:
    """Return the cost at occurrence of a risk that occurred, none for another (H-02).

    The total of its own estimate when it was declared occurred, which the review of its
    occurrence retains and which neither reestimation nor completion changes (WF-RIS-0010,
    WF-RIS-0050).
    """
    return risk.last.severity if risk.last.state == OCCURRED else None


def occurred_reestimated(risk: Risk, rows: Iterable[mockcore.Row] | None = None) -> Decimal | None:
    """Return the re-estimate of today of the lines a risk's occurrence merged, none if it did not.

    The re-estimated amounts, inflation included, of the lines of the current revision that bear
    the risk (`Node.origin_risk_id`), which the register shows beside the cost at occurrence,
    outside the coverage (`Risk.occurred_reestimated_amount`, WF-RIS-0050; #1761).
    """
    if risk.last.state != OCCURRED:
        return None
    origin = universe(risk.number)
    read = mockcore.current() if rows is None else rows
    return sum(
        (
            row.amounts.reestimated
            for row in read
            if row.kind == mockcore.ESTIMATE_LINE and row.node["origin_risk_id"] == origin
        ),
        Decimal(0),
    )


def is_cited(risk: Risk) -> bool:
    """Whether a marked revision cites the risk: one marked after it was identified."""
    identified = risk.reviews[0].at
    return any(
        marked is not None and marked.instant >= identified for _, marked in REVISIONS.values()
    )


def level(value: Decimal, bounds: Iterable[str]) -> int:
    """Return the level of a value on the bounds of the matrix, each bound its level's lower."""
    return 1 + sum(1 for bound in bounds if Decimal(bound) <= value)


def matrix_cell(risk: Risk, budget: Decimal) -> JsonObject:
    """Return the cell of a risk in the matrix, and the zone the installation gives the cell.

    Its probability on the bounds of probability; its severity, a share of the reference budget,
    on those of severity (WF-RIS-0040, WF-REF-0160) — at the lowest level on a budget of nothing,
    where the share is not computable (#1240).
    """
    settings = fixture("reference_settings")["risk_matrix"]
    probability = level(risk.last.probability, settings["probability_bounds"])
    severity = level(risk.last.severity / budget, settings["severity_bounds"]) if budget else 1
    count = len(settings["severity_bounds"]) + 1
    zone = settings["zones"][(probability - 1) * count + severity - 1]
    return {"probability_level": probability, "severity_level": severity, "zone": zone}


def matrix_point(risk: Risk, budget: Decimal) -> JsonObject:
    """Return a risk as the matrix places it, at its exact values (`RiskMatrixPoint`, #1053).

    Its probability, its severity in amount and as a share of the budget given, rounded, its
    provision, its state, and the zone of its cell, which classes the exact share (WF-RIS-0040,
    WF-REF-0160). On a budget of nothing, the share is not computable (#1240).
    """
    last = risk.last
    ratio: JsonObject = (
        {"is_computable": True, "value": str(share(last.severity / budget)), "reason": None}
        if budget
        else {"is_computable": False, "value": None, "reason": "no_reference_budget"}
    )
    return {
        "risk_id": universe(risk.number),
        "label": risk.label,
        "probability": str(last.probability),
        "severity_amount": money(last.severity),
        "severity_ratio": ratio,
        "provision_amount": money(provision_amount(risk)),
        "state": last.state,
        "zone": matrix_cell(risk, budget)["zone"],
    }


def commands(risk: Risk) -> list[JsonValue]:
    """Return the commands of a risk, in the order of `RiskCommand`, for a caller who may all.

    A risk that occurred is neither updated, reviewed nor deleted (`risk_not_occurred`); only an
    identified one occurs, or changes the category or the subproject of its provision
    (`risk_identified`, WF-RIS-0010); one a marked revision cites is not deleted
    (`risk_not_cited`). The project has a current revision: the occurrence creates none.
    """
    state = risk.last.state
    entries = (("update", ["risk_not_occurred"] if state == OCCURRED else []),)
    entries += (("update_provision", [] if state == IDENTIFIED else ["risk_identified"]),)
    entries += (("review", ["risk_not_occurred"] if state == OCCURRED else []),)
    entries += (("declare_occurrence", [] if state == IDENTIFIED else ["risk_identified"]),)
    deleted = (["risk_not_occurred"] if state == OCCURRED else []) + (
        ["risk_not_cited"] if is_cited(risk) else []
    )
    entries += (("delete", deleted),)
    return [
        {
            "command": command,
            "is_available": not missing,
            "missing_conditions": cast("list[JsonValue]", missing),
        }
        for command, missing in entries
    ]


def is_active_provision(category: str) -> bool:
    """Whether a risk's category is active and of the kind provision for risks.

    The flag `Risk.provision_cost_category_is_active` reads the flag of the category and the kind
    of its nature. Deactivating a nature deactivates its categories (WF-REF-0010; EP-14/L42s,
    C-291), so a category under a deactivated nature reads inactive, and an active one is always
    under an active nature. A category no line employs — that of a dismissed risk — may be moved
    to a nature of another kind (WF-REF-0030): it is then no longer among « les catégories
    actives de type provision pour risques » (WF-RIS-0010), and reads false (#747, point 4).
    The nature is read from the generator in memory, never from ``volume/cost_categories``, which
    the same run writes (#792).
    """
    nature = mockcategories.nature_of(category)
    return nature["is_active"] is True and nature["kind"] == "provision"


def _actor() -> JsonObject:
    """Return the user the witness's own examples name: the one who created the project."""
    return cast("JsonObject", fixture("project")["audit"]["created_by"])


def provision_task(risk: Risk, bearer: int | None = None) -> JsonObject | None:
    """Return the task that bears the line of provision of a risk, by its node and its label.

    The task of the main structure of the current revision its line is under — or the one given,
    for a line a write places —, while the risk is identified; none otherwise, the risk bearing no
    line (WF-RIS-0010, #786).
    """
    if risk.provision_line is None or risk.last.state != IDENTIFIED:
        return None
    rows = {row.number: row for row in mockcore.current()}
    number = rows[risk.provision_line].parent if bearer is None else bearer
    if number is None:
        message = f"the line of provision of the risk {risk.number} has no task"
        raise ValueError(message)
    return {"node_id": universe(number), "label": rows[number].label}


def risk_item(risk: Risk, budget: Decimal, bearer: int | None = None) -> JsonObject:
    """Return a risk as the register reads it in the current revision (`Risk`).

    The category and the subproject of its provision are named by their labels, resolved at the
    reading, and the task that bears its line by its node and its label (WF-RIS-0010,
    WF-ARC-0020): the parent of its line, or the task given (``bearer``).
    """
    last = risk.last
    actor = _actor()
    named = labels()
    cost = occurrence_cost(risk)
    reestimated = occurred_reestimated(risk)
    return {
        "risk_id": universe(risk.number),
        "label": risk.label,
        "description": risk.description,
        "mitigation_notes": risk.mitigation_notes,
        "probability": str(last.probability),
        "severity": money(last.severity),
        "provision_amount": money(provision_amount(risk)),
        "occurrence_cost": None if cost is None else money(cost),
        "occurred_reestimated_amount": None if reestimated is None else money(reestimated),
        "state": last.state,
        "structure_id": universe(risk.own_structure),
        "provision_node_id": None
        if risk.provision_line is None or last.state != IDENTIFIED
        else universe(risk.provision_line),
        "provision_cost_category_id": risk.provision_category,
        "provision_cost_category_label": named[risk.provision_category],
        "provision_cost_category_is_active": is_active_provision(risk.provision_category),
        "provision_subproject_id": risk.provision_subproject,
        "provision_subproject_label": None
        if risk.provision_subproject is None
        else named[risk.provision_subproject],
        "provision_task": provision_task(risk, bearer),
        "matrix_cell": matrix_cell(risk, budget),
        "last_review_on": last.at.date().isoformat(),
        "computed_fields": computed_fields(last.state),
        "available_commands": commands(risk),
        "audit": {
            "created_at": stamp(risk.reviews[0].at),
            "created_by": actor,
            "updated_at": stamp(last.at),
            "updated_by": actor,
        },
        "lock_version": len(risk.reviews) + 1,
    }


def totals(rows: list[mockcore.Row], retained: Iterable[Risk] | None = None) -> JsonObject:
    """Return the totals of the provisions (`ProvisionTotals`, WF-RIS-0040).

    The identified risks for their provision today; those that occurred and those dismissed for
    the provision the reference bore; their sum; and the reserve for risks of the reference. Of
    the risks retained, those the filters of the register retain (WF-IHM-0130).
    """
    by_state = {IDENTIFIED: Decimal(0), OCCURRED: Decimal(0), DISMISSED: Decimal(0)}
    for risk in REGISTER if retained is None else retained:
        by_state[risk.last.state] += provision_amount(risk)
    return {
        **{state: money(amount) for state, amount in by_state.items()},
        "total": money(sum(by_state.values(), Decimal(0))),
        "reserve": money(reserve(rows)),
    }


def matrix(rows: list[mockcore.Row], budget: Decimal) -> JsonObject:
    """Return the matrix of the risks: its levels, its cells counted, its points, the totals.

    Each identified risk counted in the cell its probability and its severity on the budget given
    place it in, as the bubbles draw it (#1395); every risk a point at its exact values, with its
    state, in the order of the register (`RiskMatrix`, #1053); the totals over the three states.
    """
    settings = fixture("reference_settings")["risk_matrix"]
    cells = [matrix_cell(risk, budget) for risk in REGISTER if risk.last.state == IDENTIFIED]

    def levels(bounds: list[str]) -> list[JsonValue]:
        lowers, uppers = ["0", *bounds], [*bounds, None]
        return [
            {"level": rank + 1, "lower": lower, "upper": upper}
            for rank, (lower, upper) in enumerate(zip(lowers, uppers, strict=True))
        ]

    probabilities, severities = settings["probability_bounds"], settings["severity_bounds"]
    zones = iter(settings["zones"])
    return {
        "probability_levels": levels(probabilities),
        "severity_levels": levels(severities),
        "cells": [
            {
                "probability_level": p,
                "severity_level": s,
                "count": sum(
                    1
                    for cell in cells
                    if (cell["probability_level"], cell["severity_level"]) == (p, s)
                ),
                "zone": next(zones),
            }
            for p in range(1, len(probabilities) + 2)
            for s in range(1, len(severities) + 2)
        ],
        "points": [matrix_point(risk, budget) for risk in REGISTER],
        "totals": totals(rows),
    }


def reviews(risk: Risk) -> list[JsonValue]:
    """Return the reviews of a risk, the latest first (`RiskReview`)."""
    actor = _actor()
    return [
        {
            "reviewed_on": review.at.date().isoformat(),
            "probability": str(review.probability),
            "severity": money(review.severity),
            "state": review.state,
            "actor": actor,
        }
        for review in reversed(risk.reviews)
    ]


def merged_lines(today: list[mockcore.Row]) -> list[mockcore.Row]:
    """Return the lines the occurrences of the risks merged into the current revision."""
    merged: set[int] = {risk.merged for risk in REGISTER if risk.merged is not None}
    for row in today:
        if row.parent in merged:
            merged.add(row.number)
    return [row for row in today if row.kind == mockcore.ESTIMATE_LINE and row.number in merged]


def readings() -> dict[str, JsonObject]:
    """Return the readings of the risks of the witness today, by name, in memory.

    The register, the matrix and the coverage: what the examples carry, and what the portfolio
    sums (``mockportfolio``), from one computation — never read back from the files the same
    command writes.
    """
    today, rows = mockcore.current(), reference_rows()
    budget = reference_budget(rows)
    return {
        "risks": {
            "items": [risk_item(risk, budget) for risk in REGISTER],
            "totals": totals(rows),
            "meta": {"limit": mocktext.PAGE, "offset": 0, "total": len(REGISTER)},
        },
        "risk_matrix": matrix(rows, budget),
        "risk_coverage": coverage(today, rows),
    }


def coverage(today: list[mockcore.Row], rows: list[mockcore.Row]) -> JsonObject:
    """Return the coverage of the risks in the current revision today (`RiskCoverage`).

    The reserve of the reference, against the provisions of the identified risks and the costs
    at occurrence of the risks that occurred — not the amounts of their merged lines, which
    reestimation and completion change (H-01) —; the difference, signed (WF-RIS-0050).
    """
    remaining = sum((row.amounts.base for row in today if is_provision(row)), Decimal(0))
    occurred = sum(
        (cost for risk in REGISTER if (cost := occurrence_cost(risk)) is not None), Decimal(0)
    )
    drifted = sum(
        (each for risk in REGISTER if (each := occurred_reestimated(risk, today)) is not None),
        Decimal(0),
    )
    kept = reserve(rows)
    return {
        "context": {
            "revision_id": CURRENT,
            "revision_status": "draft",
            "computed_at": stamp(TODAY),
            "scope": "project",
            "is_stored": False,
        },
        "reserve": money(kept),
        "remaining_provisions": money(remaining),
        "occurred_cost": money(occurred),
        "occurred_reestimated": money(drifted),
        "coverage_variance": money(kept - remaining - occurred),
    }


# --- The examples -----------------------------------------------------------------------------

_amount, _day = mocktext.amount, mocktext.day


def _percent(value: Decimal) -> str:
    return f"{mocktext.amount(value * 100, 0)} %"


def _share(value: Decimal, budget: Decimal) -> str:
    """Say a share of a budget in percent, to the hundredth; under a hundredth, said so."""
    share = (value / budget * 100).quantize(Decimal("0.01"))
    return f"{mocktext.amount(share)} %" if share else "moins de 0,01 %"


_VERBS = {
    "update": ("se modifie", "se modifient", "ne se modifie pas"),
    "update_provision": (
        "change la catégorie ou le sous-projet de sa provision",
        "changent la catégorie ou le sous-projet de leur provision",
        "ne change ni la catégorie ni le sous-projet de sa provision",
    ),
    "review": ("se réexamine", "se réexaminent", "ne se réexamine pas"),
    "declare_occurrence": (
        "se déclare survenu",
        "se déclarent survenus",
        "ne se déclare pas survenu",
    ),
    "delete": ("se supprime", "se suppriment", "ne se supprime pas"),
}
"""How a summary says each command of a risk: for one risk, for several, and refused."""


def _agreed(count: int, one: str, several: str) -> str:
    return one if count == 1 else several


def _named(labels: list[str]) -> str:
    """Name some risks as French lists them: « A », « B » et « C »."""
    return labels[0] if len(labels) == 1 else ", ".join(labels[:-1]) + " et " + labels[-1]


def _offering(items: list[JsonObject], command: str) -> list[str]:
    return [
        f"« {item['label']} »"
        for item in items
        for entry in cast("list[JsonObject]", item["available_commands"])
        if entry["command"] == command and entry["is_available"]
    ]


def _commands_text(items: list[JsonObject]) -> str:
    """Say which commands the risks of the register offer, from those they carry (WF-IHM-0090)."""
    parts: list[str] = []
    for command, (one, several, _) in _VERBS.items():
        offering = _offering(items, command)
        if not offering:
            parts.append(f"aucun ne {one}")
            continue
        parts.append(f"{_named(offering)} {_agreed(len(offering), one, several)}")
    return " ; ".join(parts) + " (WF-IHM-0090, WF-RIS-0020)"


def _risk_commands_text(item: JsonObject) -> str:
    """Say what a risk offers: the commands it takes, those it does not and what they lack."""
    entries = cast("list[JsonObject]", item["available_commands"])
    taken = [_VERBS[cast("str", e["command"])][0] for e in entries if e["is_available"]]
    refused = [
        f"{_VERBS[cast('str', e['command'])][2]} ("
        + ", ".join(f"`{c}`" for c in cast("list[str]", e["missing_conditions"]))
        + ")"
        for e in entries
        if not e["is_available"]
    ]
    said = f"Il {_named(taken)}" if taken else "Aucune de ses commandes n'est disponible : il"
    if refused:
        said += (" ; il " if taken else " ") + ", ".join(refused)
    return said + " (WF-IHM-0090, WF-RIS-0020)."


def _subproject_text(item: JsonObject) -> str:
    """Say the subproject the provision of a risk belongs to, or that it has none."""
    label = item["provision_subproject_label"]
    if label is None:
        return "hors sous-projet, aucun n'étant désigné"
    return f"au sous-projet « {label} »"


def _percents(bounds: list[str]) -> str:
    """Say bounds of the matrix as percents: 10, 30 et 60 %."""
    values = [mocktext.amount(Decimal(bound) * 100, 0) for bound in bounds]
    return f"{_named(values)} %"


def examples() -> dict[str, JsonObject]:
    """Return the named examples of the history of the witness, by file name."""
    today, rows = mockcore.current(), reference_rows()
    budget = reference_budget(rows)
    rework, delay, engineer = REGISTER
    read = readings()
    register = read["risks"]
    items = cast("list[JsonObject]", register["items"])
    sums = cast("dict[str, str]", register["totals"])
    page: JsonObject = {
        **register,
        "items": cast("list[JsonValue]", items[:RISKS_PAGE]),
        "meta": {"limit": RISKS_PAGE, "offset": 0, "total": len(items)},
    }
    covered = read["risk_coverage"]
    merged = " et ".join(_amount(row.amounts.reestimated) for row in merged_lines(today))
    reserve_text = (
        f"la réserve pour risques de la référence, {_amount(reserve(rows))} — les provisions "
        f"qu'elle portait au {_day(AMENDMENT_MERGED.on)} : "
        + ", ".join(
            f"{_amount(reference_provision(risk))} pour « {risk.label} »" for risk in REGISTER
        )
        + " —"
    )
    commands_text = _commands_text(items)
    counted = _agreed(len(items), "le seul", f"les {len(items)}")
    settings = fixture("reference_settings")["risk_matrix"]
    probabilities = cast("list[str]", settings["probability_bounds"])
    severities = cast("list[str]", settings["severity_bounds"])
    identified = sum(1 for item in items if item["state"] == IDENTIFIED)
    occurred = sum(1 for item in items if item["state"] == OCCURRED)
    identified_text = _agreed(
        identified,
        "du seul risque encore identifié",
        f"des {identified} risques encore identifiés",
    )
    occurred_text = _agreed(occurred, "du risque survenu", f"des {occurred} risques survenus")
    identified_counted = (
        "le seul encore identifié, "
        + _named([f"« {item['label']} »" for item in items if item["state"] == IDENTIFIED])
        if identified == 1
        else f"les {identified} encore identifiés"
    )
    scale = (
        f"la gravité lue sur le budget de référence de toute la structure, {_amount(budget)} : "
        + _named(
            [
                f"{_amount(risk.last.severity)} pour « {risk.label} », "
                f"{_share(risk.last.severity, budget)}, au niveau "
                f"{cast('dict[str, int]', item['matrix_cell'])['severity_level']}"
                for risk, item in zip(REGISTER, items, strict=True)
            ]
        )
    )
    return {
        "risks.json": mocktext.example(
            f"Le registre des risques de la révision courante, dans l'ordre de déclaration : "
            f"« {rework.label} », identifié, porté au devis et au reste à engager par sa ligne de "
            f"provision de {_amount(provision(rework))} ; « {delay.label} », survenu le "
            f"{_day(delay.last.at.date())}, son devis propre fusionné dans la révision en cours à "
            f"montant budgété nul et sa ligne de provision retirée, son coût à la survenance "
            f"gardé (WF-RIS-0060) ; « {engineer.label} », écarté le "
            f"{_day(engineer.last.at.date())}, les deux derniers lus pour la provision qu'ils "
            f"portaient dans la référence. Chacun dans sa "
            f"case de matrice, {scale} ; avec ses commandes — {commands_text} —, les trois "
            f"totaux de provisions — les survenus et les écartés pour la provision que portait "
            f"la référence — avec leur somme, et {reserve_text} en regard (WF-RIS-0040, "
            "WF-RIS-0050).",
            register,
        ),
        "risks_page.json": mocktext.example(
            f"Le même registre lu deux risques par page (limit={RISKS_PAGE}, offset=0) : "
            + _named([f"« {item['label']} »" for item in items[:RISKS_PAGE]])
            + f", les deux premiers des {len(items)} risques retenus, et les totaux de "
            f"provisions de tous les risques retenus — {_amount(Decimal(sums['total']))} au "
            f"total, la réserve à {_amount(Decimal(sums['reserve']))} —, pas de la seule page "
            "rendue "
            "(WF-IHM-0060, WF-IHM-0130, WF-RIS-0040, #1367).",
            page,
        ),
        "risk.json": mocktext.example(
            f"« {rework.label} », identifié : sa description, ses actions de mitigation, sa "
            f"gravité de {_amount(rework.last.severity)}, total de son devis propre, et sa "
            f"provision de {_amount(provision(rework))}, la gravité à "
            f"{_percent(rework.last.probability)} — ni l'une ni l'autre saisies (WF-RIS-0010). "
            f"Sa ligne de provision, portée par le "
            f"« {cast('JsonObject', items[0]['provision_task'])['label']} » (provision_task), "
            f"porte la catégorie qu'il a désignée, "
            f"« {items[0]['provision_cost_category_label']} », "
            f"{_subproject_text(items[0])} (WF-RIS-0010). "
            f"{_risk_commands_text(items[0])}",
            items[0],
        ),
        "risk_occurred_detail.json": mocktext.example(
            f"« {delay.label} », survenu le {_day(delay.last.at.date())} : son devis propre est "
            f"fusionné dans la structure principale de la révision en cours, ses lignes à "
            f"montant budgété nul et réestimées à {merged}, et sa ligne de provision est "
            f"retirée ; son coût à la survenance, le total de son devis propre ce jour-là, vaut "
            f"{_amount(cast('Decimal', occurrence_cost(delay)))}, que ni réestimation ni "
            f"terminaison ne changent ; sa provision, celle qu'il portait à la révision de "
            f"référence, {_amount(reference_provision(delay))}, reste comptée dans la réserve "
            f"pour risques (WF-RIS-0010, WF-RIS-0050, WF-RIS-0060). "
            f"{_risk_commands_text(items[1])}",
            items[1],
        ),
        "risk_dismissed_category_deactivated.json": mocktext.example(
            f"Variante contrefactuelle : « {engineer.label} », écarté le "
            f"{_day(engineer.last.at.date())}, tel que le registre le lit, la catégorie de sa "
            f"provision, « {items[2]['provision_cost_category_label']} », désactivée depuis : "
            f"le risque la nomme encore, mais ne la dit plus active et de type provision pour "
            f"risques (provision_cost_category_is_active), si bien que son retour à l'état "
            f"identifié en demande une autre (WF-RIS-0010, WF-REF-0030, #1384). La provision "
            f"pour risques du témoin est active.",
            {**items[2], "provision_cost_category_is_active": False},
        ),
        "risk_uncited.json": mocktext.example(
            f"Variante contrefactuelle : « {rework.label} », identifié, tel que le registre le "
            f"lit, qu'aucune révision marquée ne citerait : sa suppression est disponible, rien "
            f"ne lui manquant, et emporterait son devis propre et sa ligne de provision "
            f"(WF-RIS-0020, #1384). Le témoin le cite depuis le marquage de la référence.",
            {
                **items[0],
                "available_commands": [
                    {**each, "is_available": True, "missing_conditions": []}
                    if each["command"] == "delete"
                    else each
                    for each in cast("list[JsonObject]", items[0]["available_commands"])
                ],
            },
        ),
        "risk_matrix.json": mocktext.example(
            f"La matrice des risques de la révision courante : {len(probabilities) + 1} niveaux "
            f"de probabilité bornés à {_percents(probabilities)}, {len(severities) + 1} de "
            f"gravité bornés à {_percents(severities)} du budget de référence "
            f"(`reference_settings`) ; chaque case avec sa zone et le nombre de ses seuls "
            f"risques identifiés, comme les bulles, que le serveur compte — {identified_counted} "
            f"(#1395) — ; {counted} du registre, {scale}, chacun un point à ses valeurs exactes, "
            f"sa probabilité, sa gravité en montant et en part du budget, sa provision, son état "
            f"et la zone de sa case, que le graphique place sans rien calculer et que l'écran "
            f"filtre par état (#1053) ; et les totaux de provisions, sur les trois états "
            "(WF-RIS-0040, WF-REF-0160).",
            read["risk_matrix"],
        ),
        "risk_matrix_no_basis.json": mocktext.example(
            "Variante contrefactuelle : le registre du témoin lu sur une assiette nulle, comme "
            "sur un projet sans budget de référence dont le devis ne porte encore que des "
            "provisions. La gravité ne se rapporte à rien : la part de chaque risque n'est pas "
            "calculable (`no_reference_budget`), et chacun est au niveau de gravité le plus "
            "bas, dans la case de sa probabilité, qui ne compte que les risques identifiés "
            "(#1395) ; le graphique ne trace pas de bulle "
            "sans ordonnée. Les niveaux, les zones et les totaux de provisions sont ceux de la "
            "matrice du témoin (WF-RIS-0040, WF-REF-0160, #1240).",
            matrix(reference_rows(), Decimal(0)),
        ),
        "risk_reviews.json": mocktext.example(
            f"L'historique des réexamens de « {rework.label} », du plus récent au plus ancien : "
            f"identifié le {_day(rework.reviews[0].at.date())} à "
            f"{_percent(rework.reviews[0].probability)} et "
            f"{_amount(rework.reviews[0].severity)} — sa provision de "
            f"{_amount(reference_provision(rework))} au marquage de la référence —, sa gravité "
            f"portée à {_amount(rework.last.severity)} avec son devis propre le "
            f"{_day(rework.reviews[1].at.date())}, sa probabilité à "
            f"{_percent(rework.last.probability)} le {_day(rework.last.at.date())} "
            f"(WF-RIS-0010, WF-RIS-0040).",
            reviews(rework),
        ),
        "risk_coverage.json": mocktext.example(
            f"La couverture des risques du projet témoin au {_day(TODAY.date())}, dans la "
            f"révision courante : {reserve_text} face aux "
            f"{_amount(Decimal(cast('str', covered['remaining_provisions'])))} de provision "
            f"{identified_text} et aux "
            f"{_amount(Decimal(cast('str', covered['occurred_cost'])))} de coût à la survenance "
            f"{occurred_text}, que la terminaison de ses tâches fusionnées ne change pas ; "
            f"l'écart de couverture vaut "
            f"{_amount(Decimal(cast('str', covered['coverage_variance'])))} (WF-RIS-0050, "
            "WF-RAE-0020).",
            covered,
        ),
    }
