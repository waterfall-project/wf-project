# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the actual costs of the witness: the invoices of its drawn tasks completed (EP-14/L45a).

They try the rules the invoices follow from the structure, not the Vérif of a requirement: none
cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

from datetime import date
from decimal import Decimal
from typing import Any, cast

from wftools import mockcore, mockcosts, mockids, mockstructure, mockwitness
from wftools.mockids import PREFIX, universe
from wftools.mockwitness import APRIL, APRIL_AGAIN, COSTS, GENERATED, MARCH, MAY, UNDATED

type Node = dict[str, Any]


def _tasks() -> dict[int, Node]:
    """Return the facet of each task of the structure of today, by its number."""
    return {
        row.number: cast("Node", row.node["task"])
        for row in mockcore.current()
        if row.kind == mockcore.TASK
    }


def test_each_drawn_work_task_completed_has_one_invoice_and_no_other_task_has_any() -> None:
    tasks = _tasks()
    completed = {
        number
        for number, task in tasks.items()
        if number >= GENERATED
        and task["progress"] == "completed"
        and not (task["is_summary"] or task["is_milestone"])
    }
    invoices = mockcosts.drawn()
    assert len(invoices) == len(completed) == 21
    # One invoice a task: its text names the task, each task once, dated the day it completed.
    labels = {tasks[number]["label"]: tasks[number]["completed_on"] for number in completed}
    assert sorted(line.text for line in invoices) == sorted(labels)
    for line in invoices:
        assert line.on.isoformat() == labels[line.text], line.text
        assert line.excluded is None
    # A task under way or not started today has received none.
    assert not any(
        tasks[number]["label"] in labels
        for number in tasks
        if number >= GENERATED and number not in completed
    )
    assert mockcosts.lines() == (*COSTS, *invoices)


def test_an_invoice_is_a_few_hundredths_off_the_amount_of_its_task() -> None:
    tasks = {task["label"]: (number, task) for number, task in _tasks().items()}
    shares: set[Decimal] = set()
    for line in mockcosts.drawn():
        number, task = tasks[line.text]
        amount = Decimal(task["base_amount"])
        drawn = mockstructure.draw(
            f"invoice/{number - GENERATED}", mockcosts.INVOICED_FROM, mockcosts.INVOICED_TO
        )
        share = Decimal(drawn) / 100
        shares.add(share)
        assert Decimal(mockcosts.INVOICED_FROM) <= drawn <= mockcosts.INVOICED_TO
        assert line.amount == (amount * share).quantize(Decimal("0.01"))
        # The bounds themselves, as the decision words them — from 90 to 110 % —, not the
        # constants: a bound moved would still agree with itself above.
        ratio = (line.amount / amount).quantize(Decimal("0.01"))
        assert Decimal("0.90") <= ratio <= Decimal("1.10")
    # Drawn, not fixed: the invoices are not all the estimate, nor all off it the same way.
    assert len(shares) > 1
    assert any(share < 1 for share in shares)
    assert any(share > 1 for share in shares)


def test_an_invoice_is_imputed_to_the_subproject_of_the_lot_of_its_task_by_its_code() -> None:
    rows = mockcore.current()
    by_number = {row.number: row for row in rows}
    subproject_of_task = {
        cast("int", row.parent): cast("Node", row.node["estimate_line"])["subproject_id"]
        for row in rows
        if row.kind == mockcore.ESTIMATE_LINE
    }
    tasks = {row.label: row.number for row in rows if row.kind == mockcore.TASK}
    codes = {entry["subproject_id"]: entry["code"] for entry in mockwitness.fixture("subprojects")}
    invoices = mockcosts.drawn()
    for line in invoices:
        subproject = subproject_of_task[tasks[line.text]]
        assert line.code == (None if subproject is None else codes[subproject]), line.text
        assert mockcosts.imputed(line) == subproject
        assert by_number[tasks[line.text]].number >= GENERATED
    # The lots « Ligne d'essais » and « Utilités » of the first phase have completed tasks; those
    # of the control station follow the factory acceptance of 30 June, and none has.
    assert {line.code for line in invoices} == {"SP-ESS", None}
    assert sum(1 for line in invoices if line.code == "SP-ESS") == 12
    assert all(line.code != "SP-CMD" for line in invoices)


def test_an_invoice_is_brought_by_the_imports_whose_period_holds_its_day_not_the_undated() -> None:
    # March to the extraction of March and to the re-extraction up to 30 April, which brought the
    # lines of March back; April to the extraction of April and to that re-extraction; May and
    # after to the extraction from 1 May, applied on 3 June; nothing to the file without a period,
    # and nothing after the day an import was applied.
    assert mockcosts.brought_by(date(2026, 3, 20)) == (MARCH, APRIL_AGAIN)
    assert mockcosts.brought_by(date(2026, 4, 30)) == (APRIL, APRIL_AGAIN)
    assert mockcosts.brought_by(date(2026, 5, 1)) == (MAY,)
    assert mockcosts.brought_by(date(2026, 6, 3)) == (MAY,)
    assert mockcosts.brought_by(date(2026, 6, 4)) == ()
    # The re-extraction up to 30 April declares no start: it holds every day up to its end.
    assert mockcosts.brought_by(date(2026, 2, 27)) == (APRIL_AGAIN,)
    assert UNDATED not in {entry for line in mockcosts.lines() for entry in line.imports}
    for line in mockcosts.drawn():
        assert line.imports == mockcosts.brought_by(line.on), line.document
        assert line.imports, line.document
    # The journal counts them: the extraction of May created the 21 invoices and the screens.
    created = {
        entry["period_from"]: entry["created_count"]
        for entry in cast("list[Node]", mockcosts.journal()["items"])
    }
    assert created["2026-05-01"] == 22


def test_an_invoice_has_an_identifier_of_its_own_family_and_a_number_of_its_own() -> None:
    hand = {line.number for line in COSTS}
    invoices = mockcosts.drawn()
    numbers = [line.number for line in invoices]
    assert numbers == list(range(GENERATED + 1, GENERATED + len(invoices) + 1))
    assert not hand & set(numbers)
    documents = [line.document for line in mockcosts.lines()]
    assert len(documents) == len(set(documents))
    [family] = [
        each for each in mockids.IDENTIFIERS if each.what == "lignes de coût réel engendrées"
    ]
    for line in invoices:
        identifier = mockcosts.cost_line_id(line.number)
        assert identifier == f"{PREFIX}0009{line.number - GENERATED:08d}"
        assert family.holds(identifier)
        assert line.document.startswith(f"FA-2026-{mockcosts.INVOICE_NUMBER_FROM // 1000}")
    assert mockcosts.cost_line_id(0xC01) == mockids.hex_identifier(0xC01)


def test_the_consultation_lists_the_invoices_with_the_lines_written_by_hand() -> None:
    consulted = cast("Node", mockcosts.values()["actual_costs"])
    items = cast("list[Node]", consulted["items"])
    dates = [item["document_date"] for item in items]
    assert dates == sorted(dates, reverse=True)
    assert len(items) == len(COSTS) + len(mockcosts.drawn()) == 27
    tracked = sum(Decimal(item["amount"]) for item in items if item["is_in_tracked_scope"])
    assert Decimal(cast("Node", consulted["totals"])["tracked"]) == tracked
    [screens] = [item for item in items if item["subproject_id"] == universe(801)]
    assert screens["document_number"] == "FA-2026-0521"
    tests = [item for item in items if item["subproject_id"] == universe(802)]
    assert len(tests) == 12
    assert all(item["subproject_code"] == "SP-ESS" for item in tests)
    # The tracked scope given alone: the lines written by hand, as the variant on the core reads.
    alone = mockcosts.tracked(COSTS)
    assert len(alone) == len(COSTS) - 1
    assert sum(amount for _, amount, _ in alone) == Decimal("105400.00")


def test_the_summary_of_the_consultation_says_no_invoice_when_no_drawn_task_has_completed() -> None:
    # The structure dated before the first drawn task completes: no invoice, said as such rather
    # than looked for among none.
    said = mockcosts.invoiced(())
    assert said.startswith("Aucune tâche tirée autour du cœur n'est terminée")
    assert "aucune n'a encore reçu la facture" in said
    invoices = mockcosts.drawn()
    told = mockcosts.invoiced(invoices)
    assert told.startswith(f"Les {len(invoices)} tâches tirées autour du cœur et terminées, du ")
    assert "SP-ESS" in told
    assert told in cast("str", mockcosts.examples()["actual_costs.json"]["summary"])
