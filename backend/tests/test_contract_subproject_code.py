# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The generated model of the code of a declared subproject keeps the bounds of the contract.

Since the specification 1.0.7, the code of a subproject is free (#3966): from 1 to 100 characters,
never blank, a slash, the characters a tab refuses and the names of the tabs Waterfall writes
included. The generated model compiles its pattern with ``re`` (``regex_engine="python-re"``), as
it did the former one (EP-16/US-0610).
"""

import pytest
from pydantic import ValidationError

from waterfall.api.contract.models import DeclaredSubprojectCode

pytestmark = pytest.mark.requirement("WF-PRJ-0050-A")

LONGEST = 100
"""The most characters the code of a subproject holds (`DeclaredSubprojectCode`, #3966)."""


@pytest.mark.parametrize("code", ["", "   ", "x" * (LONGEST + 1)])
def test_the_model_refuses_a_code_blank_or_too_long(code: str) -> None:
    with pytest.raises(ValidationError):
        DeclaredSubprojectCode.model_validate(code)


@pytest.mark.parametrize(
    "code",
    [
        "SP-CMD",
        "A.ABC.26001/10001",
        "Synthèse",
        "HORS SOUS-PROJET",
        "SP:01",
        "x" * 40,
        "x" * LONGEST,
    ],
)
def test_the_model_accepts_a_free_code(code: str) -> None:
    # « Un sous-projet de code « A.ABC.26001/10001 », « Synthèse » ou de quarante caractères se
    # crée » : the contract no longer refuses them; the service follows (US-3270/L2).
    assert DeclaredSubprojectCode.model_validate(code).root == code
