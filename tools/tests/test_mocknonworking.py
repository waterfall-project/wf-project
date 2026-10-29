# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of a date of a manual task on a day without hours of work (US-0470/L3, #1271, #1289).

They try the examples the fake back serves against the readings of the witness and the sentence
of WF-PLA-0020 they illustrate — « Sur un calendrier du lundi au vendredi, la date de début d'une
tâche manuelle saisie un samedi est refusée, et le refus nomme le lundi suivant ; la même date
importée d'un fichier MS Project est gardée et signalée au compte rendu » —, not the Vérif
itself, which the service proves (EP-06): none cites the requirement (WF-QUA-0010, « un test qui
ne couvre aucune exigence »).
"""

import json
import re
from datetime import timedelta
from decimal import Decimal
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY, mockcore, mockdata, mockdating, mocknonworking, mockwitness
from wftools.mockcalendar import Calendar
from wftools.mockstructure import described
from wftools.mockwitness import N
from wftools.mockwrites import amended, on_task

SATURDAY, MONDAY = mocknonworking.SATURDAY, mocknonworking.SATURDAY + timedelta(days=2)


def _json(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _answers(paths: str, name: str) -> str:
    text = (REPOSITORY / "docs" / "api" / "paths" / paths).read_text(encoding="utf-8")
    operation = text[text.index(f"operationId: {name}") :]
    end = operation.find("operationId:", len("operationId:"))
    operation = operation if end < 0 else operation[:end]
    return operation[operation.index("responses:") :]


def _cited(text: str, status: str) -> list[str]:
    answer = text[text.index(f"'{status}':") :]
    answer = answer[: answer.index("\n      '", 1)]
    return re.findall(r"fixtures/api/(\w+)\.json", answer)


def test_the_contract_cites_the_refusal_and_the_import_under_their_answers() -> None:
    assert "task_date_non_working_day" in _cited(
        _answers("revisions.yaml", "updateTaskFacet"), "422"
    )
    assert "import_planning_non_working_day" in _cited(
        _answers("exchanges.yaml", "getImport"), "200"
    )
    examples = mocknonworking.examples()
    assert "node_create_non_working_day" in _cited(_answers("revisions.yaml", "createNode"), "422")
    assert "structure_start_non_working_day" in _cited(
        _answers("revisions.yaml", "updateCostStructure"), "422"
    )
    assert set(examples) == {
        "task_date_non_working_day.json",
        "node_create_non_working_day.json",
        "structure_start_non_working_day.json",
        "import_planning_non_working_day.json",
    }
    assert set(examples) <= set(mockdata.named())


def test_the_commissioning_works_from_monday_to_friday() -> None:
    # The calendar the sentence of WF-PLA-0020 names: the start entered is a Saturday.
    calendar = mocknonworking.calendar()
    assert calendar == mockwitness.default_calendar()
    assert [calendar.hours_on(SATURDAY + timedelta(days=offset)) for offset in range(7)] == [
        0,
        0,
        *[Decimal(8)] * 5,
    ]
    assert SATURDAY.weekday() == 5
    # The Saturday before the Monday the commissioning starts on today, as its summary says.
    assert mockdating.schedule(described())[N.COMMISSIONING].start.day == MONDAY


def test_a_start_entered_on_a_saturday_is_refused_naming_the_next_monday() -> None:
    # « la date de début d'une tâche manuelle saisie un samedi est refusée, et le refus nomme le
    # lundi suivant » : on its field, nothing written — no node in the answer.
    refused = _json(mocknonworking.task_date_non_working_day())
    assert (refused["code"], refused["status"]) == ("VALIDATION_FAILED", 422)
    assert refused["fields"] == [
        {
            "pointer": "/start/date",
            "code": "NON_WORKING_DAY",
            "params": {"date": SATURDAY.isoformat(), "next_working_day": MONDAY.isoformat()},
        }
    ]
    assert "nodes" not in refused
    summary = str(mocknonworking.examples()["task_date_non_working_day.json"]["summary"])
    assert "le samedi 19 décembre 2026" in summary
    assert "le lundi 21 décembre 2026" in summary


def test_a_planning_start_on_a_saturday_is_refused_on_the_default_calendar() -> None:
    # The structure has no calendar of its own: its planning start is judged on the default one,
    # as the start of a task without a labour line is, and the refusal names the next Monday.
    refused = _json(mocknonworking.structure_start_non_working_day())
    assert (refused["code"], refused["status"]) == ("VALIDATION_FAILED", 422)
    assert refused["fields"] == [
        {
            "pointer": "/planning_start_on",
            "code": "NON_WORKING_DAY",
            "params": {"date": SATURDAY.isoformat(), "next_working_day": MONDAY.isoformat()},
        }
    ]
    assert mockwitness.default_calendar().hours_on(SATURDAY) == 0


def test_a_day_of_work_is_not_judged_and_any_day_without_names_the_next_with() -> None:
    assert mocknonworking.judged(MONDAY) is None
    sunday = SATURDAY + timedelta(days=1)
    assert mocknonworking.judged(sunday) == {
        "date": sunday.isoformat(),
        "next_working_day": MONDAY.isoformat(),
    }
    # On a week of four days, a Friday names the Monday; a week without hours names none.
    fitter = mockwitness.role_calendars()[mockwitness.CABLE_FITTER]
    friday = SATURDAY - timedelta(days=1)
    assert fitter.hours_on(friday) == 0
    assert fitter.next_working_day(friday) == MONDAY
    with pytest.raises(ValueError, match="grants no hour"):
        Calendar("none", (Decimal(0),) * 7).next_working_day(friday)


def test_the_same_date_imported_is_kept_and_signalled_naming_the_next_monday() -> None:
    # « la même date importée d'un fichier MS Project est gardée et signalée au compte rendu »,
    # by the motive and the parameters of the refusal: one sentence for both.
    imported = _json(mocknonworking.import_planning_non_working_day())
    report = imported["report"]
    assert (imported["kind"], imported["status"]) == ("ms_project_schedule", "analysed")
    [refused] = _json(mocknonworking.task_date_non_working_day())["fields"]
    lineage = mockcore.lineage(N.COMMISSIONING)
    assert report["signals"] == [
        {
            "lineage_id": lineage,
            "label": "Mise en service",
            "column": "start",
            "code": refused["code"],
            "params": refused["params"],
        }
    ]
    # Kept: nothing rejected, the start a difference like any other, at no hour once applied.
    assert (report["rejected"], report["refusals"], report["date_mismatches"]) == ([], [], [])
    [difference] = report["differences"]
    assert difference["lineage_id"] == lineage
    assert difference["fields"] == ["scheduling_mode", "start"]
    first, last = mocknonworking.imported_dates()
    roots = amended(mockwitness.CORE, on_task(N.COMMISSIONING, manual=(first, last)))
    placed = mockdating.schedule(roots)[N.COMMISSIONING]
    assert (placed.start.day, placed.start.hours) == (SATURDAY, 0)
    assert placed.finish.day == mockdating.schedule(described())[N.COMMISSIONING].finish.day
    assert report["read_count"] == len(mockdating.tasks_in_order(described()))


def test_a_milestone_on_a_day_without_hours_is_signalled_once_per_column() -> None:
    # The signal follows the cell, not the day (ImportSignal, DECISIONS.md, #1271): a milestone
    # whose start and finish are the same Saturday is signalled twice, like a task whose two
    # dates are; a day of work is not signalled.
    lineage = mockcore.lineage(N.COMMISSIONING)
    params = {"date": SATURDAY.isoformat(), "next_working_day": MONDAY.isoformat()}
    assert _json(mocknonworking.signals(lineage, "Jalon", (SATURDAY, SATURDAY))) == [
        {
            "lineage_id": lineage,
            "label": "Jalon",
            "column": column,
            "code": "NON_WORKING_DAY",
            "params": params,
        }
        for column in ("start", "finish")
    ]
    assert mocknonworking.signals(lineage, "Jalon", (MONDAY, MONDAY)) == []


def test_the_contract_holds_the_code_of_a_signal_to_the_one_signal_there_is() -> None:
    text = (REPOSITORY / "docs/api/components/schemas/exchanges.yaml").read_text(encoding="utf-8")
    code = yaml.safe_load(text)["ImportSignal"]["properties"]["code"]
    assert {"const": mocknonworking.CODE} in code["allOf"]
    assert {"$ref": "../common.yaml#/ErrorCode"} in code["allOf"]


def test_the_calendars_of_the_file_are_ignored_and_named() -> None:
    ignored = cast("dict[str, Any]", mocknonworking.calendars_ignored())
    labels = {entry["label"] for entry in mockwitness.fixture("calendars")["items"]}
    assert ignored["kind"] == "calendars"
    assert ignored["count"] == len(ignored["labels"]) == 2
    assert set(ignored["labels"]) <= labels


def test_no_hours_refused_on_the_entry_of_a_date_name_a_bound_of_none() -> None:
    # The refusal of hours past those of their day stays coherent with the motive: a day without
    # hours is refused by its date, so that no example of updateTaskFacet names a maximum of 0.
    text = _answers("revisions.yaml", "updateTaskFacet")
    for name in _cited(text, "422"):
        path = mockwitness.FIXTURES / f"{name}.json"
        value = json.loads(path.read_text(encoding="utf-8"))["value"]
        for field in value.get("fields", []):
            if field["code"] == "VALUE_OUT_OF_RANGE":
                assert field["params"] != {"maximum": "0"}, name
