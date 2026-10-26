# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The generated model of the code of a declared subproject keeps the bounds of the contract.

The pattern of ``DeclaredSubprojectCode`` bears a negative lookahead: the generated model must
compile it with ``re`` (``regex_engine="python-re"``), or pydantic's default engine would refuse
it at import or read it differently (EP-16/US-0610).
"""

import pytest
from pydantic import ValidationError

from waterfall.api.contract.models import DeclaredSubprojectCode


@pytest.mark.parametrize(
    "code",
    ["SYNTHÈSE", "synthèse", "HORS SOUS-PROJET", "SP/01", "SP:01", "", "   ", "x" * 32],
)
def test_the_model_refuses_a_code_that_cannot_name_a_tab(code: str) -> None:
    with pytest.raises(ValidationError):
        DeclaredSubprojectCode.model_validate(code)


@pytest.mark.parametrize("code", ["SP-CMD", "x" * 31, "Synthese", "Synthèse 2", "Hors lot"])
def test_the_model_accepts_a_code_that_names_a_tab(code: str) -> None:
    assert DeclaredSubprojectCode.model_validate(code).root == code
