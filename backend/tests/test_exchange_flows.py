# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The back offers no exchange outside the closed list of the contract (WF-INTF-0150, US-2780/L3).

An import is served by the format its kind registers, an export by its exporter: what the API and
the worker register is all that the back can read from or write to a file of a project. Each kind is
one of the enumerations of the contract, ``ExchangeKind`` and ``ExportKind``, which a test of the
tools (``tools/tests/test_exchange_flows.py``) confronts with the table of the flows of the
specification: the formats and the exporters registered are exactly those, and none is the
portfolio's. That every entry point registers them all, ``test_registries.py`` proves.
"""

import importlib

import pytest

from waterfall.api.contract import models
from waterfall.core.exchanges.interface import exporters, formats

# What registers the formats and the exporters: the entry points of the API and of the worker.
ENTRY_POINTS = ("waterfall.api.app", "waterfall.worker.main")


@pytest.fixture(scope="module", autouse=True)
def registered() -> None:
    for each in ENTRY_POINTS:
        importlib.import_module(each)


@pytest.mark.requirement("WF-INTF-0150-A")
def test_each_import_the_back_serves_is_a_kind_of_the_closed_list_of_the_contract() -> None:
    assert sorted(formats()) == sorted(member.value for member in models.ExchangeKind)


@pytest.mark.requirement("WF-INTF-0150-A")
def test_each_export_the_back_serves_is_a_kind_of_the_closed_list_of_the_contract() -> None:
    assert sorted(exporters()) == sorted(member.value for member in models.ExportKind)


@pytest.mark.requirement("WF-INTF-0150-A")
def test_no_format_nor_exporter_is_the_portfolios() -> None:
    owners = {type(each).__module__ for each in (*formats().values(), *exporters().values())}
    assert owners
    assert not any(owner.startswith("waterfall.core.portfolio") for owner in owners)
