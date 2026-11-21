# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the check of the one implementation of each calculation (US-2780/L3, WF-ARC-0010).

The check holds the back by the table ``tools/implementations.toml``: the back of the repository
passes it, and each rule fails on a back built for the test.
"""

import pytest

from wftools import implementations
from wftools.implementations import TableError, check, parse

TABLE = """
[[implementation]]
calculation = "indicators"
file = "core/indicators/formulas/ratios.py"
names = ["cost_index", "zone_of"]

[[application]]
file = "core/portfolio/aggregation/ratios.py"
applies = ["cost_index"]
"""
OWNER = (
    "def cost_index(earned, actual):\n    return earned / actual\n\n\n"
    "def zone_of(index):\n    ...\n"
)
APPLYING = (
    "from waterfall.core.indicators.interface import cost_index\n\n\n"
    "def aggregate(earned, actual):\n    return cost_index(sum(earned), sum(actual))\n"
)


def sources() -> dict[str, str]:
    """Return a back that passes the table: the owner, its interface, the portfolio, the API."""
    return {
        "core/indicators/formulas/ratios.py": OWNER,
        "core/indicators/interface/__init__.py": (
            "from waterfall.core.indicators.formulas.ratios import cost_index as cost_index\n"
        ),
        "core/portfolio/aggregation/ratios.py": APPLYING,
        "api/indicators.py": "from waterfall.core.indicators.interface import cost_index\n",
    }


@pytest.mark.requirement("WF-ARC-0010-A")
def test_the_back_of_the_repository_holds_one_implementation_of_each_calculation() -> None:
    table = parse(implementations.TABLE.read_text(encoding="utf-8"))
    found, _ = check(table, implementations.read_sources(implementations.PACKAGE))
    assert found == []
    assert {each.calculation for each in table.implementations} == implementations.CALCULATIONS


@pytest.mark.requirement("WF-ARC-0010-A")
def test_a_back_built_to_pass_passes() -> None:
    assert check(parse(TABLE), sources()) == ([], [])


@pytest.mark.requirement("WF-ARC-0010-A")
@pytest.mark.parametrize(
    ("file", "text"),
    [
        ("api/indicators.py", "def cost_index(earned, actual):\n    return earned / actual\n"),
        ("worker/marking.py", "class Totals:\n    def cost_index(self):\n        return 1\n"),
        ("api/indicators.py", "def view():\n    def cost_index():\n        return 1\n"),
        ("core/portfolio/folding.py", "cost_index = lambda earned, actual: earned / actual\n"),
        ("core/portfolio/folding.py", "cost_index: object = None\n"),
        ("witness/loader.py", "cost_index, other = 1, 2\n"),
    ],
)
def test_a_second_implementation_in_the_api_the_worker_or_the_portfolio_is_refused(
    file: str, text: str
) -> None:
    found = check(parse(TABLE), sources() | {file: text})[0]
    assert len(found) == 1
    assert found[0].startswith(f"{file}:")
    assert "defines cost_index, a second implementation of the indicators" in found[0]


@pytest.mark.requirement("WF-ARC-0010-A")
@pytest.mark.parametrize(
    ("file", "text"),
    [
        ("api/indicators.py", "from waterfall.platform.formulas import cost_index\n"),
        ("api/indicators.py", "from waterfall.core.estimate.interface import cost_index as ci\n"),
        ("worker/marking.py", "def run():\n    from waterfall.api.indicators import cost_index\n"),
        ("core/portfolio/folding.py", "from .aggregation.ratios import cost_index\n"),
    ],
)
def test_a_calculation_imported_from_elsewhere_than_its_module_of_the_core_is_refused(
    file: str, text: str
) -> None:
    found = check(parse(TABLE), sources() | {file: text})[0]
    assert len(found) == 1
    assert found[0].startswith(f"{file}:")
    assert "not from waterfall.core.indicators" in found[0]


@pytest.mark.requirement("WF-ARC-0010-A")
def test_a_relative_import_is_judged_by_the_module_it_reaches() -> None:
    reaching = "from ...indicators.interface import cost_index\n"
    assert check(parse(TABLE), sources() | {"core/portfolio/aggregation/x.py": reaching})[0] == []


def test_the_other_modules_of_the_core_and_the_migrations_are_out_of_the_check() -> None:
    # A detail of the check, which reprises no Vérif: it cites no requirement.
    other = {
        "core/risk_settings/matrix.py": "def zone_of(matrix, probability, severity):\n    ...\n",
        "migrations/versions/0001.py": "def cost_index():\n    ...\n",
    }
    assert check(parse(TABLE), sources() | other)[0] == []


@pytest.mark.requirement("WF-ARC-0010-A")
@pytest.mark.parametrize(
    "text",
    [
        (
            "from waterfall.core.indicators.interface import cost_index\n\n\n"
            "def aggregate():\n    ...\n"
        ),
        "def aggregate(earned, actual):\n    return sum(earned) / sum(actual)\n",
    ],
)
def test_a_portfolio_that_does_not_apply_the_formula_of_ep10_to_sums_is_refused(text: str) -> None:
    found = check(parse(TABLE), sources() | {"core/portfolio/aggregation/ratios.py": text})[0]
    assert found == [
        (
            "core/portfolio/aggregation/ratios.py: does not apply cost_index of"
            " core/indicators/formulas/ratios.py: it must import it from the module that owns"
            " it and call it, never write it again"
        )
    ]


@pytest.mark.requirement("WF-ARC-0010-A")
def test_a_name_its_file_no_longer_defines_fails_the_table() -> None:
    found = check(parse(TABLE), sources() | {"core/indicators/formulas/ratios.py": "x = 1\n"})[0]
    assert found == [
        (
            "core/indicators/formulas/ratios.py: no longer defines cost_index, which the table"
            " gives it (indicators)"
        ),
        (
            "core/indicators/formulas/ratios.py: no longer defines zone_of, which the table gives"
            " it (indicators)"
        ),
    ]


HOMONYM = """
[[homonym]]
name = "zone_of"
module = "waterfall.core.risk_settings"
reason = "the zone of a cell of the matrix"
"""
DUPLICATE = """
[[duplicate]]
name = "zone_of"
file = "core/portfolio/aggregation/periods.py"
reason = "copied"
"""


@pytest.mark.requirement("WF-ARC-0010-A")
def test_a_homonym_of_another_module_of_the_core_may_be_imported_from_it_alone() -> None:
    matrix = {"core/risk_settings/matrix.py": "def zone_of(matrix, cell):\n    ...\n"}
    risking = "from waterfall.core.risk_settings.interface import zone_of\n"
    elsewhere = "from waterfall.core.risks.interface import zone_of\n"
    table = parse(TABLE + HOMONYM)
    assert check(table, sources() | matrix | {"core/portfolio/risking.py": risking})[0] == []
    assert check(table, sources() | matrix | {"core/portfolio/risking.py": elsewhere})[0] == [
        (
            "core/portfolio/risking.py:1: imports zone_of from waterfall.core.risks.interface, not"
            " from waterfall.core.indicators, the module of the core that owns it"
        )
    ]
    assert check(table, sources())[0] == [
        "waterfall.core.risk_settings: defines no zone_of any more: remove its [[homonym]] entry"
    ]


@pytest.mark.requirement("WF-ARC-0010-A")
def test_a_known_duplicate_is_said_without_failing_until_it_is_gone() -> None:
    periods = {"core/portfolio/aggregation/periods.py": "def zone_of(index):\n    ...\n"}
    exported = {
        "core/portfolio/aggregation/__init__.py": (
            "from waterfall.core.portfolio.aggregation.periods import zone_of as zone_of\n"
        )
    }
    table = parse(TABLE + DUPLICATE)
    assert check(table, sources() | periods | exported) == (
        [],
        ["core/portfolio/aggregation/periods.py:1: defines zone_of, a known duplicate: copied"],
    )
    assert check(table, sources())[0] == [
        (
            "core/portfolio/aggregation/periods.py: no longer defines zone_of: remove its"
            " [[duplicate]] entry"
        )
    ]


@pytest.mark.requirement("WF-ARC-0010-A")
@pytest.mark.parametrize(
    ("table", "message"),
    [
        (
            TABLE.replace('"indicators"', '"risks"'),
            "core/indicators/formulas/ratios.py: 'risks' is not a calculation WF-ARC-0010 names",
        ),
        (
            TABLE + '[[implementation]]\ncalculation = "planning"\nfile = "core/planning/x.py"\n'
            'names = ["zone_of"]\n',
            "zone_of has two owners: core/indicators/formulas/ratios.py and core/planning/x.py",
        ),
        (
            TABLE.replace("core/indicators/formulas", "core/portfolio/aggregation", 1),
            (
                "core/portfolio/aggregation/ratios.py is not a file of a module of the core that"
                " computes"
            ),
        ),
        (
            TABLE + DUPLICATE.replace('"zone_of"', '"margin"'),
            "core/portfolio/aggregation/periods.py: margin is not a name of the table",
        ),
        (TABLE.replace('["cost_index", "zone_of"]', "[]"), "names must be a list of names, not []"),
    ],
)
def test_a_malformed_table_is_refused(table: str, message: str) -> None:
    with pytest.raises(TableError) as raised:
        parse(table)
    assert str(raised.value) == message


def test_the_check_reports_on_the_repository(capsys: pytest.CaptureFixture[str]) -> None:
    # A detail of the command, which reprises no Vérif: it cites no requirement.
    assert implementations.main() == 0
    assert "0 finding(s)" in capsys.readouterr().out
