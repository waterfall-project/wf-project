# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The correlation identifier is taken from the caller if it has the form of the contract."""

import pytest
from jsonschema_path import SchemaPath
from support import CONTRACT

from waterfall.platform.correlation import FORM, correlation_id_from


@pytest.mark.parametrize("received", ["abc-123", "A.b_c-9", "x" * 64])
def test_an_identifier_of_the_form_of_the_contract_is_kept(received: str) -> None:
    assert correlation_id_from(received) == received


@pytest.mark.parametrize("received", [None, "", "x" * 65, "a b", "a/b", "é", "a\n"])
def test_any_other_identifier_is_replaced_by_one_that_has_the_form(received: str | None) -> None:
    made = correlation_id_from(received)
    assert made != received
    assert FORM.fullmatch(made)


def test_two_identifiers_made_in_a_row_differ() -> None:
    assert correlation_id_from(None) != correlation_id_from(None)


@pytest.mark.requirement("WF-OBS-0020-A")
def test_the_form_is_the_one_the_contract_gives_to_the_correlation_identifier() -> None:
    common = SchemaPath.from_file_path(str(CONTRACT.parent / "components" / "common.yaml"))
    pattern = (common / "Problem" / "properties" / "correlation_id" / "pattern").read_value()
    assert pattern == f"^{FORM.pattern}$"
