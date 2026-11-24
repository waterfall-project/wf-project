# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The example of the codes a subproject may bear (WF-PRJ-0050; US-3270/L5, #4022), without a base.

From ``fixtures/projects/subproject_codes.json``: a code of a slash, a name Waterfall gives a tab of
its own, or forty characters is admitted by the core of the projects, and the workbook « Reste à
engager » gives it a tab named from it, whose head bears the code whole, by which the import
designates the subproject. The creation itself, with its database, is tried by
``test_a_free_code_is_created_as_it_is_sent`` (``test_subprojects``) and the acceptance of the
model by ``test_the_model_accepts_a_free_code`` (``test_contract_subproject_code``); the export and
the import of the file by ``test_remaining_export``.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from typing import TYPE_CHECKING, cast
from uuid import uuid4

import pytest
from openpyxl import load_workbook

from waterfall.core.estimate.remaining.excel.layout import (
    CODE_CELL,
    CODE_LABEL,
    LABEL_CELL,
    tab_names,
    tab_subprojects,
)
from waterfall.core.estimate.remaining.excel.model import RemainingTab, RemainingWorkbook
from waterfall.core.estimate.remaining.excel.writer import write_workbook
from waterfall.core.projects.interface import SUBPROJECT_CODE_LENGTH
from waterfall.core.projects.interface.subprojects import code_faults

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]


def _book(codes: list[str]) -> RemainingWorkbook:
    """Give the remaining of a revision whose subprojects bear the codes, without a task."""
    tabs = tuple(
        RemainingTab(code, f"Lot {rank}", Decimal(0), Decimal(0), Decimal(0), ())
        for rank, code in enumerate(codes, start=1)
    )
    return RemainingWorkbook(
        company="Exemple Industrie",
        client="Client Exemple",
        project="A.ABC.26001 Contrôle d'accès",
        revision="Revue",
        structure="Structure principale",
        review_date=date(2027, 2, 15),
        currency="EUR",
        exported_at=datetime(2027, 2, 15, 9, 30, tzinfo=UTC),
        hours_per_day=Decimal(8),
        natures=(),
        categories=(),
        roles=(),
        subprojects=tabs,
    )


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_no_code_of_a_slash_a_fixed_name_or_forty_characters_is_refused_for_its_form(
    example: Callable[[str], Example],
) -> None:
    # « Un sous-projet de code « A.ABC.26001/10001 », « Synthèse » ou de quarante caractères se
    # crée [...]. » The first half: no code is refused for its form, only a blank one is.
    data = example("WF-PRJ-0050-A#38958d887e9a")
    codes = cast("list[str]", data["codes"])
    assert [len(code) for code in codes] == [17, 8, 40]
    for code in codes:
        assert code_faults(code) == []
        assert len(code) <= SUBPROJECT_CODE_LENGTH
    assert code_faults("  ") != []


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_the_file_of_the_remaining_gives_such_a_subproject_a_tab_that_bears_its_code_at_the_head(
    example: Callable[[str], Example],
) -> None:
    # « [...] et le fichier de reste à engager lui donne un onglet qui porte son code en tête. »
    # The tab is named from the code (the slash replaced, 31 characters at most, numbered against
    # « Synthèse »), the code is whole in B1, and the import reads the subproject back from it.
    # The names of the ``tabs`` key come from the naming rule of the export (annex B,
    # ``tab_names``), not from the Vérif of WF-PRJ-0050-A, which says only that the tab bears the
    # code at its head.
    data = example("WF-PRJ-0050-A#38958d887e9a")
    codes = cast("list[str]", data["codes"])
    names = tab_names(codes)
    assert {code: names[code] for code in codes} == data["tabs"]
    book = load_workbook(BytesIO(write_workbook(_book(codes))))
    heads: dict[str, str | None] = {}
    for rank, code in enumerate(codes, start=1):
        sheet = book[names[code]]
        assert (sheet["A1"].value, sheet[CODE_CELL].value, sheet[LABEL_CELL].value) == (
            CODE_LABEL,
            code,
            f"Lot {rank}",
        )
        heads[names[code]] = sheet[CODE_CELL].value
    known = {code: uuid4() for code in codes}
    assert tab_subprojects(heads, known) == {names[code]: known[code] for code in codes}
