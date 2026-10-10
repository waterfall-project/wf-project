# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the writes of the common settings: what each answer changes, what each refusal names.

They try the examples of `updateReferenceSettings` (EP-14/L42h, and L42m for #659) against the
reading of the settings they follow and against the contract, not the Vérif of a requirement: none
cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from wftools import REPOSITORY, mockwitness
from wftools.mockwitness import fixture

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"
SCHEMAS = API / "components" / "schemas"

ZERO, ONE = Decimal(0), Decimal(1)
"""The bounds, both excluded, of a threshold of an index (`IndexThreshold`, WF-REF-0170)."""
OUTSIDE = "THRESHOLD_NOT_BETWEEN_ZERO_AND_ONE"
"""The motive of a threshold that is not strictly between 0 and 1 (EP-14/L42m)."""
FEWEST, MOST_WEEKS = 1, 104
"""The bounds of the delay between two reviews, in weeks (`max_weeks_between_reviews`)."""

ZONE_OF_P1_G4 = 3
"""The rank of the cell of the lowest probability and the highest severity, p1/g4:
4 * (p - 1) + (g - 1), as `RiskMatrixSettings.zones` ranks them."""


def _block(text: str, schema: str) -> str:
    return text.split(f"\n{schema}:\n", 1)[1].split("\n\n", 1)[0]


def _pattern(path: Path, schema: str) -> re.Pattern[str]:
    block = _block(path.read_text(encoding="utf-8"), schema)
    found = re.search(r"pattern: '(?P<pattern>[^']+)'", block)
    assert found is not None, schema
    return re.compile(found["pattern"])


def _threshold_pattern() -> re.Pattern[str]:
    return _pattern(SCHEMAS / "reference.yaml", "IndexThreshold")


def _operation() -> str:
    text = (API / "paths" / "reference.yaml").read_text(encoding="utf-8")
    return text.split("operationId: updateReferenceSettings\n", 1)[1].split("\n/reference/", 1)[0]


# --- What each answer changes (#659, point 2) ---------------------------------------------------


def test_the_matrix_written_changes_its_bounds_and_one_zone_and_nothing_else() -> None:
    read, written = fixture("reference_settings"), fixture("reference_settings_matrix_updated")
    before, after = read["risk_matrix"], written["risk_matrix"]
    assert after["probability_bounds"] == ["0.1", "0.25", "0.5"]
    assert after["severity_bounds"] == ["0.02", "0.05", "0.1"]
    changed = {
        rank: (was, now)
        for rank, (was, now) in enumerate(zip(before["zones"], after["zones"], strict=True))
        if was != now
    }
    # The zone the form of the matrix changes in its test, so that the answer shows it in place of
    # the reading (#659).
    assert changed == {ZONE_OF_P1_G4: ("watch", "alert")}
    for key in ("currency_code", "default_language", "index_thresholds"):
        assert written[key] == read[key], key
    assert written["max_weeks_between_reviews"] == read["max_weeks_between_reviews"]
    assert written["lock_version"] == read["lock_version"] + 1


def test_the_thresholds_written_keep_the_matrix() -> None:
    read, written = fixture("reference_settings"), fixture("reference_settings_thresholds_updated")
    assert written["risk_matrix"] == read["risk_matrix"]
    assert written["lock_version"] == read["lock_version"] + 1


# --- The refusal of a value out of its range (#659, point 1) ------------------------------------


def test_a_threshold_outside_zero_and_one_and_a_delay_out_of_range_are_refused() -> None:
    # The threshold by its own motive, without parameter: an open interval has no bound admitted to
    # name; the delay by VALUE_OUT_OF_RANGE, its one bound crossed, an integer admitted.
    refused = fixture("reference_settings_out_of_range")
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    assert refused["fields"] == [
        {"pointer": "/index_thresholds/cost_watch", "code": OUTSIDE},
        {
            "pointer": "/max_weeks_between_reviews",
            "code": "VALUE_OUT_OF_RANGE",
            "params": {"minimum": FEWEST},
        },
    ]
    text = (API / "components" / "common.yaml").read_text(encoding="utf-8")
    codes = text.split("\nErrorCode:\n", 1)[1].split("\n\n", 1)[0]
    assert f"    - {OUTSIDE}\n" in codes


@pytest.mark.parametrize(
    "value",
    [
        "0",
        "0.0",
        "00",
        "-0.0",
        "1",
        "1.5",
        "-0.5",
        "-00.5",
        "0.5",
        "00.5",
        "000.875",
        "0.875",
        "0.001",
        "0.999",
    ],
)
def test_a_decimal_passes_the_pattern_of_a_threshold_exactly_when_it_lies_between_zero_and_one(
    value: str,
) -> None:
    # WF-REF-0170 fixes no precision: 0.875 is a threshold, and 00.5 too (EP-14/L42m, reviews 1, 3);
    # among the decimals of `Decimal`, the pattern of the threshold is exactly ]0, 1[.
    assert _pattern(API / "components" / "common.yaml", "Decimal").fullmatch(value)
    assert bool(_threshold_pattern().fullmatch(value)) == (ZERO < Decimal(value) < ONE)


@pytest.mark.parametrize("value", ["0", "0.0", "0.00", "1", "1.0", "1.5", "-0.5"])
def test_a_decimal_outside_zero_and_one_passes_the_form_and_fails_the_range(value: str) -> None:
    # Refused by the code of the range: a decimal (`Decimal`) the pattern of the threshold refuses.
    assert _pattern(API / "components" / "common.yaml", "Decimal").fullmatch(value)
    assert not _threshold_pattern().fullmatch(value)


@pytest.mark.parametrize("value", ["0.", ".5", "0,9"])
def test_a_threshold_that_is_no_decimal_fails_the_form_first(value: str) -> None:
    # Refused by NUMBER_INVALID: it fails already the pattern of `Decimal`, before any range.
    assert not _pattern(API / "components" / "common.yaml", "Decimal").fullmatch(value)


def _motive(threshold: str) -> str | None:
    """Return the motive a threshold is refused by, the form judged first; none if admitted."""
    if not _pattern(API / "components" / "common.yaml", "Decimal").fullmatch(threshold):
        return "NUMBER_INVALID"
    return None if _threshold_pattern().fullmatch(threshold) else OUTSIDE


@pytest.mark.parametrize(
    ("value", "motive"),
    [
        ("0.", "NUMBER_INVALID"),
        (".5", "NUMBER_INVALID"),
        ("0,9", "NUMBER_INVALID"),
        ("0", OUTSIDE),
        ("1", OUTSIDE),
        ("1.5", OUTSIDE),
        ("00.5", None),
        ("000.875", None),
        ("0.875", None),
    ],
)
def test_each_threshold_is_refused_by_its_one_motive_or_admitted(
    value: str, motive: str | None
) -> None:
    # #683, point 2: the form first, then the range, each by its pattern — `0.` is no decimal, and
    # `00.5`, written with zeros ahead, is a half, admitted (EP-14/L42m, review 3).
    assert _motive(value) == motive


def test_the_refusal_says_the_form_of_a_threshold_before_its_range() -> None:
    refusals = _operation().split("'422':", 1)[1].split("content:", 1)[0]
    form = refusals.index("NUMBER_INVALID")
    assert form < refusals.index("THRESHOLD_NOT_BETWEEN_ZERO_AND_ONE")
    assert "`/index_thresholds/<seuil>` par `NUMBER_INVALID`" in refusals


def test_the_bounds_of_the_delay_are_those_the_schemas_publish() -> None:
    text = (SCHEMAS / "reference.yaml").read_text(encoding="utf-8")
    for schema in ("ReferenceSettings", "ReferenceSettingsWrite"):
        block = _block(text, schema)
        found = re.search(r"max_weeks_between_reviews:(?P<rest>(?:.|\n)*?)lock_version", block)
        assert found is not None, schema
        assert re.search(rf"\bminimum: {FEWEST}\b", found["rest"]), schema
        assert re.search(rf"\bmaximum: {MOST_WEEKS}\b", found["rest"]), schema


def test_every_threshold_and_delay_of_the_examples_lies_within_its_range() -> None:
    pattern = _threshold_pattern()
    found: list[str] = []
    for path in sorted(
        [
            *mockwitness.FIXTURES.glob("reference_settings*.json"),
            *mockwitness.FIXTURES.glob("index_history*.json"),
        ]
    ):
        value: Entry = json.loads(path.read_text(encoding="utf-8"))["value"]
        thresholds = value.get("index_thresholds", value.get("thresholds"))
        if thresholds is None:
            continue
        found.append(path.name)
        for key, threshold in thresholds.items():
            assert pattern.fullmatch(threshold), (path.name, key)
            assert ZERO < Decimal(threshold) < ONE, (path.name, key)
        if "max_weeks_between_reviews" in value:
            assert FEWEST <= value["max_weeks_between_reviews"] <= MOST_WEEKS, path.name
    assert len(found) == 5, found


@pytest.mark.parametrize(
    "name",
    [
        "reference_settings_bounds_refused",
        "reference_settings_thresholds_refused",
        "reference_settings_out_of_range",
    ],
)
def test_each_refusal_is_an_example_of_the_operation(name: str) -> None:
    assert f"fixtures/api/{name}.json" in _operation()


def test_the_fake_back_still_serves_the_refusal_of_the_bounds_first() -> None:
    # Prism answers an invalid request by the first example of the 422: it stays the one it was.
    refusals = _operation().split("'422':", 1)[1]
    cited = re.findall(r"fixtures/api/(\w+)\.json", refusals)
    assert cited[0] == "reference_settings_bounds_refused"
    assert cited[-1] == "reference_settings_out_of_range"
