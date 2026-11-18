# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the correlations of the examples of errors: one each, derived from its name (#1007).

Every example under the fixtures is read, the volumes included, so that no example of an error
escapes the rule wherever it is written.
"""

import json
import re
from collections import defaultdict

import pytest

from wftools import mockids, mockwitness
from wftools.mockcorrelations import NUMBERED, correlation
from wftools.mockids import PREFIX, universe

_CORRELATIONS = tuple(
    family
    for family in mockids.IDENTIFIERS
    if family.what.startswith("corrélations") and not family.generated
)
"""The ranges of the correlations numbered by hand, before the rule."""


def _errors() -> dict[str, str]:
    """Return the correlation of every example of an error, by its name: its file less ``.json``."""
    errors: dict[str, str] = {}
    for path in sorted(mockwitness.FIXTURES.rglob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))["value"]
        if isinstance(value, dict) and "correlation_id" in value:
            name = path.relative_to(mockwitness.FIXTURES).with_suffix("").as_posix()
            errors[name] = value["correlation_id"]
    return errors


@pytest.fixture(scope="module")
def errors() -> dict[str, str]:
    """Read every example of an error once."""
    return _errors()


def _misnumbered(errors: dict[str, str]) -> dict[str, str]:
    """Return the examples of errors, not numbered before the rule, whose correlation is not theirs.

    The correlation an example carries is named beside the one its name gives; one its name gives
    that a family of hand-written or generated identifiers holds is named too: it would name
    another object, and the example is to be renamed.
    """
    found: dict[str, str] = {}
    for name, value in errors.items():
        if name in NUMBERED:
            continue
        if value != correlation(name):
            found[name] = f"{value}, not {correlation(name)}"
        elif any(family.holds(value) for family in mockids.IDENTIFIERS):
            found[name] = f"{value}, held by a family of mockids: rename the example"
    return found


def test_each_correlation_is_told_by_one_example_alone(errors: dict[str, str]) -> None:
    told: dict[str, list[str]] = defaultdict(list)
    for name, value in errors.items():
        told[value].append(name)
    assert {key: names for key, names in told.items() if len(names) > 1} == {}


@pytest.mark.story("US-2520")
def test_an_example_of_an_error_not_numbered_before_carries_the_correlation_its_name_gives(
    errors: dict[str, str],
) -> None:
    assert _misnumbered(errors) == {}


@pytest.mark.story("US-2520")
def test_a_new_example_numbered_by_hand_is_refused() -> None:
    derived = correlation("node_create_refused_anew")
    assert _misnumbered({"node_create_refused_anew": derived}) == {}
    # The next number free of the last range, as two lots in parallel would both take it.
    assert _misnumbered({"node_create_refused_anew": universe(1999)}) == {
        "node_create_refused_anew": f"{universe(1999)}, not {derived}"
    }
    # A name numbered before the rule keeps its number, and only it.
    assert _misnumbered({"internal_error": universe(1999)}) == {}


@pytest.mark.story("US-2520")
def test_the_correlation_of_a_name_is_the_prefix_then_twelve_digits_of_its_digest() -> None:
    # The first twelve hexadecimal digits of the SHA-256 of « internal_error ».
    assert correlation("internal_error") == f"{PREFIX}90a3760eb444"
    assert re.fullmatch(rf"{PREFIX}[0-9a-f]{{12}}", correlation("a_refusal"))
    assert correlation("a_refusal") != correlation("a_refusal_anew")


@pytest.mark.story("US-2520")
def test_the_examples_numbered_before_the_rule_keep_their_number(errors: dict[str, str]) -> None:
    # The frozen names are those of examples of errors still: a name removed leaves the list.
    assert errors.keys() >= NUMBERED
    # Each keeps a number of the ranges of the correlations, not the one its name would give.
    assert {
        name: errors[name]
        for name in NUMBERED
        if not any(family.holds(errors[name]) for family in _CORRELATIONS)
    } == {}
    # No name is added to the list: a new example takes the correlation its name gives.
    assert len(NUMBERED) <= 369
