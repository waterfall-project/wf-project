# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the examples of the WBS element compared whole and of the free code (US-3270/L1).

Each example is held to the operation that cites it, to the code and the shape the contract
declares for it, and to the readings it derives from (``wftools.mockfreecodes``). They try the
examples of the fake back, not the Vérif of a requirement: none cites one (WF-QUA-0010); the
criterion they bear is the US's own — the examples of the contract follow (US-3270, #3966).
"""

from functools import cache
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY, mockfreecodes
from wftools.mockexchanges import FIRST_ROW
from wftools.mockwitness import fixture

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"

pytestmark = pytest.mark.story("US-3270")


@cache
def _operations() -> dict[str, Entry]:
    """Return every operation of the contract, by its identifier."""
    found: dict[str, Entry] = {}
    for path in sorted((API / "paths").glob("*.yaml")):
        for item in cast("dict[str, Entry]", yaml.safe_load(path.read_text("utf-8"))).values():
            for operation in item.values():
                if isinstance(operation, dict) and "operationId" in operation:
                    found[cast("str", operation["operationId"])] = cast("Entry", operation)
    return found


def _cited(operation: str, status: str) -> list[str]:
    """Return the examples an answer of an operation cites, by the name of their file."""
    answer = _operations()[operation]["responses"][status]
    [content] = cast("dict[str, Entry]", answer["content"]).values()
    return [Path(each["$ref"]).stem for each in content["examples"].values()]


def _schema(file: str, name: str) -> Entry:
    path = API / "components" / "schemas" / file
    return cast("Entry", yaml.safe_load(path.read_text("utf-8"))[name])


def test_every_example_is_the_one_the_generator_writes_and_is_cited() -> None:
    cited = {
        "import_actual_costs_unknown_elements": [("getImport", "200")],
        "subproject_code_of_project": [("createSubproject", "422"), ("updateSubproject", "422")],
        "project_code_of_subproject": [("updateProject", "422")],
    }
    written = mockfreecodes.examples()
    assert sorted(written) == sorted(f"{name}.json" for name in cited)
    for name, answers in cited.items():
        assert fixture(name) == written[f"{name}.json"]["value"], name
        for operation, status in answers:
            assert name in _cited(operation, status), (name, operation)


def test_the_report_names_each_unknown_element_once_with_the_number_of_its_lines() -> None:
    # The Vérif of WF-CRE-0020-A as a report: the two codes of the project added, the four other
    # elements rejected for their element, each named once, in the order of the file.
    report = fixture("import_actual_costs_unknown_elements")["report"]
    assert report["unknown_wbs_elements"] == [
        {"wbs_element": "A.ABC.26001/10002", "line_count": 2},
        {"wbs_element": "10001", "line_count": 1},
        {"wbs_element": "A.ABC.26002", "line_count": 1},
        {"wbs_element": "", "line_count": 1},
    ]
    rejected = report["rejected"]
    assert {each["code"] for each in rejected} == {"WBS_ELEMENT_OUTSIDE_PROJECT"}
    assert [each["row"] for each in rejected] == list(range(FIRST_ROW + 2, FIRST_ROW + 7))
    # Each rejected line bears its element alone: the element is not cut (#3966).
    assert all(each["params"].keys() == {"wbs_element"} for each in rejected)
    counted = sum(each["line_count"] for each in report["unknown_wbs_elements"])
    assert counted == len(rejected)
    assert [each["label"] for each in report["differences"]] == ["FA-2026-0409", "FA-2026-0412"]
    assert report["read_count"] == len(rejected) + len(report["differences"])
    assert report["requires_confirmation_reasons"] == ["lines_outside_project"]


def test_the_unknown_elements_are_a_part_of_every_report_the_contract_requires() -> None:
    report = _schema("exchanges.yaml", "ImportReport")
    assert "unknown_wbs_elements" in report["required"]
    item = _schema("exchanges.yaml", "ImportUnknownWbsElement")
    assert item["required"] == ["wbs_element", "line_count"]
    assert item["properties"]["line_count"]["minimum"] == 1


def _shared_codes() -> dict[str, str]:
    """Return the code each refusal names: the witness's, then that of its first subproject."""
    return {
        "subproject_code_of_project": cast("str", fixture("project")["code"]),
        "project_code_of_subproject": cast("str", fixture("subprojects")[0]["code"]),
    }


@pytest.mark.parametrize("name", ["subproject_code_of_project", "project_code_of_subproject"])
def test_a_code_a_subproject_and_its_project_would_share_is_refused_without_a_parameter(
    name: str,
) -> None:
    refused = fixture(name)
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    assert refused["fields"] == [{"pointer": "/code", "code": "SUBPROJECT_CODE_INVALID"}]
    written = mockfreecodes.examples()[f"{name}.json"]
    assert _shared_codes()[name] in cast("str", written["summary"])
