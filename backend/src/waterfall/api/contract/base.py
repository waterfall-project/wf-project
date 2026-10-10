# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The base of every model of the contract, and the text the service accepts: never a NUL.

PostgreSQL refuses a text that holds the NUL character, in a column as in a ``jsonb`` value: a
NUL that reached the database would be a failure of the database, a 500. Every text the service
receives is refused first, as a value its field refuses (422 ``VALIDATION_FAILED``, at the
pointer of the field, or of its item that holds the NUL): a parameter by the type ``Text``, a
body by the base of the models ``make generate-server-models`` engenders, which looks for a NUL
in each of their fields — a text, an item of a list, a key or a value of an object.
"""

from collections.abc import Iterable, Mapping
from typing import Annotated, cast

from pydantic import AfterValidator, BaseModel, RootModel, field_validator
from pydantic_core import PydanticCustomError

# The type of the fault: the gatherer of faults says it ``VALIDATION_FAILED``.
NUL_FAULT = "string_nul"


# Where a NUL lies under the value of a field: the rank of an item of a list, the key of a value.
NulPath = tuple[int | str, ...]


def nul_path(value: object) -> NulPath | None:
    """Give where the first NUL of a value lies, at any depth, or ``None`` if it holds none.

    The path is that of the item that holds it under the value: a text in a list is pointed at
    its rank, a value of an object at its key, as any other fault of an item is; a NUL in a key,
    or in a set, which has no rank, is pointed at the object or the set that holds it.
    """
    if isinstance(value, str):
        return () if "\x00" in value else None
    if isinstance(value, RootModel):
        return nul_path(cast("RootModel[object]", value).root)
    if isinstance(value, Mapping):
        entries = cast("Mapping[object, object]", value).items()
        if any(nul_path(key) is not None for key, _ in entries):
            return ()
        return _first_nul(((str(key),), item) for key, item in entries)
    if isinstance(value, list | tuple | set | frozenset):
        ranked = isinstance(value, list | tuple)
        items = enumerate(cast("Iterable[object]", value))
        return _first_nul((((rank,) if ranked else ()), item) for rank, item in items)
    return None


def _first_nul(items: Iterable[tuple[NulPath, object]]) -> NulPath | None:
    """Give the path of the first NUL among items, each under the path that leads to it."""
    for place, item in items:
        below = nul_path(item)
        if below is not None:
            return (*place, *below)
    return None


def refuse_nul[T](value: T) -> T:
    """Give the value back, or refuse it if it holds a NUL, saying where in ``path``."""
    path = nul_path(value)
    if path is not None:
        raise PydanticCustomError(NUL_FAULT, "a text holds the NUL character", {"path": path})
    return value


# A text the service receives, in a parameter of a query or of a path.
Text = Annotated[str, AfterValidator(refuse_nul)]


class ContractModel(BaseModel):
    """A model of the contract: each of its fields refuses a NUL, wherever it holds a text."""

    @field_validator("*", mode="after")
    @classmethod
    def _refuse_nul(cls, value: object) -> object:
        return refuse_nul(value)
