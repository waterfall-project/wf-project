# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The parameters of a query that several operations of the API share, typed once."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Query

from waterfall.api.contract.base import Text
from waterfall.platform.errors import FieldError, UnprocessableError

VALIDATION_FAILED = "VALIDATION_FAILED"

# The parameter ``search`` of the contract, absent by default; a text, which refuses a NUL.
Search = Annotated[Text | None, Query(min_length=1, max_length=200)]


def listed[T](name: str, text: str | None, read: Callable[[str], T]) -> tuple[T, ...] | None:
    """Read a list of the query, its values separated by commas (``explode: false``).

    ``None`` when the parameter is absent. A value that ``read`` refuses (``ValueError``), an empty
    one included, refuses the parameter (422).
    """
    if text is None:
        return None
    try:
        return tuple(read(value) for value in text.split(","))
    except ValueError:
        fault = FieldError(f"/query/{name}", VALIDATION_FAILED)
        raise UnprocessableError(VALIDATION_FAILED, fields=(fault,)) from None
