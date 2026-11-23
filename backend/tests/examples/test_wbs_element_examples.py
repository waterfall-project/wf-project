# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric examples of the WBS element of a line of actual costs (US-2780/L1), without a base.

The rows of an extraction read by ``read_lines`` against a ``Reading`` of the headers (WF-CRE-0020),
from the fixture ``wbs_element_imputation.json``. What a line is imputed to — the project or one
of its subprojects, by their codes — is the application's, which reads the subprojects of the
project; this file replays the element each line is read with and the lines rejected for it.

The specification 1.0.7 changes WF-CRE-0020 (the element compared whole, the slash no longer a
separator; issue #3966, the core not yet changed): what the sentences of the examples say of an
element with a slash — a subproject of code ``A.ABC.26001/10001``, a code ``/10002`` known or
created, the reimport — is not replayed here, the core reading the part after the slash as the
code of the subproject. What the report says of each rejected element and of the number of its
lines, and the imputation itself, take a database.
"""

from datetime import date
from typing import TYPE_CHECKING, cast

import pytest

from waterfall.core.costs.extraction import Reading, read_lines

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]
READING = Reading(
    {"wbs_element": 0, "document_number": 1, "document_date": 2, "amount": 3}, kept=()
)
DAY = date(2026, 3, 2)


def _row(element: str | None, document: str) -> tuple[object, ...]:
    return element, document, DAY, 100.0


@pytest.mark.requirement("WF-CRE-0020-A")
def test_a_line_of_the_element_of_the_project_is_read_for_the_project_alone(
    example: Callable[[str], Example],
) -> None:
    # « Sur le projet de code A.ABC.26001 [...], une ligne d'élément A.ABC.26001 est importée et
    # imputée au seul projet [...]. » Only that half: the line is read without a subproject.
    data = example("WF-CRE-0020-A#327d63bf4748")
    element = cast("str", data["project_element"])
    read = read_lines([_row(element, "4500000001")], READING, cast("str", data["project_code"]))
    assert read.rejected == ()
    assert [(each.document_number, each.subproject_code) for each in read.lines] == [
        ("4500000001", None)
    ]


@pytest.mark.requirement("WF-CRE-0020-A")
def test_the_lines_of_an_element_of_another_project_or_of_a_bare_code_or_of_no_element_are_rejected(
    example: Callable[[str], Example],
) -> None:
    # « Une ligne d'élément A.ABC.26001/10002, une ligne d'élément 10001, une ligne d'élément
    # A.ABC.26002 et une ligne d'élément vide sont rejetées [...]. » The three elements the core
    # rejects without a database; the code of an unknown subproject is judged on the subprojects of
    # the project, and the report naming each element and its lines is the application's.
    data = example("WF-CRE-0020-A#80d94ea6d2fe")
    elements = cast("list[str]", data["rejected_elements"])
    rows = [_row(element or None, f"450000000{rank}") for rank, element in enumerate(elements)]
    read = read_lines(rows, READING, cast("str", data["project_code"]))
    assert read.lines == ()
    assert read.read_count == len(elements)
    assert [each.params["wbs_element"] for each in read.rejected] == elements
    assert [each.row for each in read.rejected] == [2, 3, 4]
