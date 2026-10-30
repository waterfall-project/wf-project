# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the catalogues of the contract: no code nor condition that nothing renders (J-03, J-11).

Every code of `ErrorCode` is named by an operation or a schema beyond its own line of the
catalogue, and carried by an example; every value of `CommandCondition` is said by its
description and named by an operation, a schema or an example (US-0702/L1, #1610). None cites a
requirement: they hold the contract, not the Vérif of one (WF-QUA-0010).
"""

import json
import re
from collections.abc import Iterator
from typing import Any, cast

import yaml

from wftools import REPOSITORY

API = REPOSITORY / "docs" / "api"
COMPONENTS = API / "components"
FIXTURES = REPOSITORY / "fixtures" / "api"

AWAITING_EXAMPLE = frozenset(
    {
        "MALFORMED_REQUEST",
        "SESSION_REQUIRED",
        "ACCOUNT_DEACTIVATED",
        "ACCOUNT_NOT_ADMITTED",
        "NOT_CONTRIBUTOR",
        "FILE_TOO_LARGE",
        "NUMBER_INVALID",
        "DATE_INVALID",
        "UNKNOWN_CALENDAR",
        "WBS_ELEMENT_INVALID",
        "AMBIGUOUS_TASK_LABEL",
    }
)
"""Codes rendered by an operation that no example carries yet: the minor J-17 of the review, and
two motives of an imported line, left after the freeze as minors (decision of the author of the
2026-10-28) — the list shrinks, never grows."""


def _catalogue(name: str, path: str) -> tuple[list[str], str]:
    """Return the values of an enumeration of the contract, and its description."""
    schema = cast("dict[str, Any]", yaml.safe_load((COMPONENTS / path).read_text("utf-8")))[name]
    return cast("list[str]", schema["enum"]), cast("str", schema.get("description", ""))


def _texts() -> dict[str, str]:
    """Return the text of the contract by file, the catalogue of codes taken out of common.yaml."""
    files = [
        *sorted((API / "paths").glob("*.yaml")),
        *sorted((COMPONENTS / "schemas").glob("*.yaml")),
        COMPONENTS / "parameters.yaml",
        COMPONENTS / "responses.yaml",
    ]
    texts = {str(path.relative_to(API)): path.read_text("utf-8") for path in files}
    common = (COMPONENTS / "common.yaml").read_text("utf-8")
    start, end = common.index("\nErrorCode:"), common.index("\nFieldProblem:")
    texts["components/common.yaml"] = common[:start] + common[end:]
    return texts


def _named(value: str, texts: dict[str, str]) -> bool:
    word = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(value)}(?![A-Za-z0-9_])")
    return any(word.search(text) for text in texts.values())


def _codes(value: object) -> Iterator[str]:
    """Yield every value under a key `code` of an example, at any depth."""
    if isinstance(value, dict):
        for key, each in cast("dict[str, object]", value).items():
            if key == "code" and isinstance(each, str):
                yield each
            yield from _codes(each)
    elif isinstance(value, list):
        for each in cast("list[object]", value):
            yield from _codes(each)


def _examples() -> list[str]:
    return [path.read_text("utf-8") for path in sorted(FIXTURES.rglob("*.json"))]


def test_every_error_code_is_named_by_an_operation_or_a_schema() -> None:
    codes, _ = _catalogue("ErrorCode", "common.yaml")
    texts = _texts()
    assert [code for code in codes if not _named(code, texts)] == []


def test_every_error_code_is_carried_by_an_example_but_those_awaiting_one() -> None:
    codes, _ = _catalogue("ErrorCode", "common.yaml")
    carried = {code for text in _examples() for code in _codes(json.loads(text))}
    assert {code for code in codes if code not in carried} == AWAITING_EXAMPLE
    assert set(codes) >= AWAITING_EXAMPLE


def test_every_condition_is_said_by_its_description_and_named_beyond_it() -> None:
    conditions, description = _catalogue("CommandCondition", "schemas/projects.yaml")
    assert [each for each in conditions if f"`{each}`" not in description] == []
    texts = _texts()
    schemas = texts.pop("components/schemas/projects.yaml")
    start, end = schemas.index("\nCommandCondition:"), schemas.index("\nProjectCommand:")
    texts["components/schemas/projects.yaml"] = schemas[:start] + schemas[end:]
    examples = "\n".join(_examples())
    dead = [each for each in conditions if not _named(each, texts) and f'"{each}"' not in examples]
    assert dead == []


def test_a_code_nothing_renders_is_found() -> None:
    texts = {"paths.yaml": "description: refusé par `ALREADY_EXISTS`.\n"}
    assert _named("ALREADY_EXISTS", texts)
    assert not _named("EXISTS", texts)
    assert sorted(_codes({"code": "A", "fields": [{"code": "B", "params": {"code": 3}}]})) == [
        "A",
        "B",
    ]
