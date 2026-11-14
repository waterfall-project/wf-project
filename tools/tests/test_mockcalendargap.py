# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The calendar gap of an MS Project import, and its duration rule, on the contract (#2977).

`docs/api/DECISIONS.md`, « L'import en deux temps », the entry of #2977: the report says the gap
of a file whose constants or calendars differ from those of the installation, and the rule of its
durations, which ``setImportDurationRule`` changes, analysing the import again. The examples are
written by hand, but for the two refusals (``wftools.mockreview``): these tests hold them to the
contract that cites them, and to one another.
"""

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY
from wftools.mockwitness import fixture

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"
PATH = "/projects/{project_id}/imports/{import_id}/duration-rule"


def _paths() -> Entry:
    text = (API / "paths" / "exchanges.yaml").read_text(encoding="utf-8")
    return cast("Entry", yaml.safe_load(text))


def _cited(operation: Entry, status: str) -> list[str]:
    """Return the examples an answer of an operation cites, by the name of their file."""
    [content] = cast("dict[str, Entry]", operation["responses"][status]["content"]).values()
    return [Path(each["$ref"]).stem for each in content["examples"].values()]


def _reports() -> dict[str, Entry]:
    """Return every report the examples of the imports carry, by the name of their file."""
    found: dict[str, Entry] = {}
    for path in sorted((REPOSITORY / "fixtures" / "api").glob("import_*.json")):
        value = cast("Entry", fixture(path.stem))
        if isinstance(value.get("report"), dict):
            found[path.stem] = cast("Entry", value["report"])
    return found


@pytest.mark.requirement("WF-PLA-0160-A")
def test_a_file_whose_constants_or_calendars_differ_is_signalled_with_its_rule() -> None:
    # Vérif : « Un fichier MS Project dont les constantes ou le calendrier diffèrent de ceux de
    # l'installation est signalé au compte rendu […] »
    reports = _reports()
    for name, report in reports.items():
        assert "calendar_gap" in report, name
        if report["unit_constants"] is not None:
            assert report["calendar_gap"] is not None, name
    gaps = {name: report["calendar_gap"] for name, report in reports.items()}
    assert {name for name, gap in gaps.items() if gap is not None} == {
        "import_planning_calendar_gap",
        "import_planning_other_constants",
    }
    other = gaps["import_planning_other_constants"]
    assert other["tasks"] == []
    project, installation = other["project_calendar"], other["installation_calendar"]
    assert project["weekly_hours"] == installation["weekly_hours"]
    calendar = gaps["import_planning_calendar_gap"]
    assert calendar["project_calendar"]["weekly_hours"]["monday"] == "7"
    assert calendar["installation_calendar"]["weekly_hours"]["monday"] == "8"
    [task] = calendar["tasks"]
    assert task["label"] == "Fabrication"
    assert task["file_calendar"]["name"] == "Atelier"
    assert task["file_calendar"]["weekly_hours"] != task["weekly_hours"]


@pytest.mark.requirement("WF-INTF-0080-A")
def test_the_report_offers_the_two_rules_and_a_change_gives_a_new_report() -> None:
    # Vérif : « Pour un planning MS Project saisi sur un autre calendrier, le compte rendu propose
    # de garder les durées ou les dates ; changer d'option rend un nouveau compte rendu, et le
    # projet reste inchangé jusqu'à la confirmation. »
    gap = fixture("import_planning_calendar_gap")
    assert gap["report"]["calendar_gap"]["duration_rule"] == "keep_durations"
    operation = _paths()[PATH]["put"]
    assert operation["operationId"] == "setImportDurationRule"
    assert "planning_calendar_gap" in str(_paths()["/projects/{project_id}/imports/{import_id}"])
    [rerun] = _cited(operation, "202")
    analysing = fixture(rerun)
    assert (analysing["import_id"], analysing["status"]) == (gap["import_id"], "analysing")
    assert (analysing["report"], analysing["expires_at"]) == (None, None)
    assert analysing["task"]["task_id"] != gap["task"]["task_id"]
    assert analysing["task"]["status"] == "queued"
    [apply, _] = analysing["available_commands"]
    assert apply["missing_conditions"] == ["import_awaiting_decision"]
    [unchanged] = _cited(operation, "200")
    kept = fixture(unchanged)
    assert kept["status"] == "analysed"
    assert kept["report"]["calendar_gap"]["duration_rule"] == "keep_dates"
    assert kept["report"]["date_mismatches"] == []


def test_a_rule_is_refused_without_a_gap_and_once_the_import_awaits_no_decision() -> None:
    # #2977: the conditions of the 409, in their order, each with its example.
    operation = _paths()[PATH]["put"]
    said = " ".join(operation["responses"]["409"]["description"].split())
    assert said.index("`import_awaiting_decision`") < said.index("`import_calendar_gap`")
    conditions = {
        name: fixture(name)["params"]["missing_condition"] for name in _cited(operation, "409")
    }
    assert conditions == {
        "import_duration_rule_without_gap": "import_calendar_gap",
        "import_duration_rule_applied": "import_awaiting_decision",
    }
    for name in conditions:
        refused = fixture(name)
        assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    projects = (API / "components" / "schemas" / "projects.yaml").read_text(encoding="utf-8")
    enum = cast("Entry", yaml.safe_load(projects))["CommandCondition"]["enum"]
    assert "import_calendar_gap" in enum
    assert {"200", "202", "400", "403", "404", "409", "422"} <= set(operation["responses"])


@pytest.mark.requirement("WF-INTF-0040-A")
def test_the_calendars_of_a_file_in_gap_are_still_ignored_and_said() -> None:
    # Vérif : « […] aucune ressource et aucun calendrier présents dans le fichier n'a été créé dans
    # Waterfall, et l'utilisateur est informé que ces éléments ont été ignorés. »
    for name, report in _reports().items():
        gap = report["calendar_gap"]
        if gap is None:
            continue
        [calendars] = [each for each in report["ignored"] if each["kind"] == "calendars"]
        named = {gap["project_calendar"]["name"]} | {
            each["file_calendar"]["name"] for each in gap["tasks"]
        }
        assert named <= set(calendars["labels"]), name
