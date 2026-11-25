# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric examples of the WBS element of a line of actual costs (US-2780/L1), without a base.

The rows of an extraction read by ``read_lines`` against a ``Reading`` of the headers (WF-CRE-0020),
from the fixture ``wbs_element_imputation.json``. What a line is imputed to — the project or one
of its subprojects, by their codes — is the application's, which reads the subprojects of the
project; this file replays the element each line is read with and the lines rejected for it.

The specification 1.0.7 changes WF-CRE-0020 (the element compared whole, the slash no longer a
separator; issue #3966, US-3270): the element ``A.ABC.26001/10001`` is that of a subproject of that
code, ``A.ABC.26001/10002`` that of none (US-3270/L5, #4022). What the report says of each rejected
element and of the number of its lines, the reimport and the imputation itself take a database.
"""

from datetime import date
from typing import TYPE_CHECKING, cast
from uuid import uuid4

import pytest

from waterfall.core.costs.extraction import Known, Reading, read_lines

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
    known = Known(cast("str", data["project_code"]), {})
    read = read_lines([_row(element, "4500000001")], READING, known)
    assert read.rejected == ()
    assert [(each.document_number, each.subproject_code) for each in read.lines] == [
        ("4500000001", None)
    ]


@pytest.mark.requirement("WF-CRE-0020-A")
def test_a_line_of_the_element_of_a_subproject_is_imputed_to_that_subproject(
    example: Callable[[str], Example],
) -> None:
    # « [...] une ligne d'élément A.ABC.26001/10001 est imputée à ce sous-projet. » The element is
    # compared whole: the slash separates nothing, and the line of the project keeps none.
    data = example("WF-CRE-0020-A#327d63bf4748")
    code = cast("str", data["subproject_code"])
    known = Known(cast("str", data["project_code"]), {code: uuid4()})
    rows = [_row(cast("str", data["project_element"]), "4500000001"), _row(code, "4500000002")]
    read = read_lines(rows, READING, known)
    assert read.rejected == ()
    assert [(each.document_number, each.subproject_code) for each in read.lines] == [
        ("4500000001", None),
        ("4500000002", code),
    ]


@pytest.mark.requirement("WF-CRE-0020-A")
def test_the_lines_of_an_element_of_no_subproject_or_of_a_bare_code_or_of_no_element_are_rejected(
    example: Callable[[str], Example],
) -> None:
    # « Une ligne d'élément A.ABC.26001/10002, une ligne d'élément 10001, une ligne d'élément
    # A.ABC.26002 et une ligne d'élément vide sont rejetées [...]. » On a project that bears the
    # subproject A.ABC.26001/10001 only; the report naming each element and the number of its
    # lines is the application's.
    data = example("WF-CRE-0020-A#80d94ea6d2fe")
    elements = cast("list[str]", data["rejected_elements"])
    subprojects = {cast("str", data["subproject_code"]): uuid4()}
    known = Known(cast("str", data["project_code"]), subprojects)
    rows = [_row(element or None, f"450000000{rank}") for rank, element in enumerate(elements)]
    read = read_lines(rows, READING, known)
    assert read.lines == ()
    assert read.read_count == len(elements)
    assert [each.params["wbs_element"] for each in read.rejected] == elements
    assert [each.row for each in read.rejected] == [2, 3, 4, 5]
