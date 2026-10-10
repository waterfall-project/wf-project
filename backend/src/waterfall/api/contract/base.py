# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The base of every model of the contract, and the text the service accepts: never a NUL.

PostgreSQL refuses a text that holds the NUL character, in a column as in a ``jsonb`` value: a
NUL that reached the database would be a failure of the database, a 500. Every text the service
receives is refused first, as a value its field refuses (422 ``VALIDATION_FAILED``, at the
pointer of the field): a parameter by the type ``Text``, a body by the base of the models
``make generate-server-models`` engenders, which looks for a NUL in each of their fields — a
text, an item of a list, a key or a value of an object.
"""

from collections.abc import Iterable, Mapping
from typing import Annotated, cast

from pydantic import AfterValidator, BaseModel, RootModel, field_validator
from pydantic_core import PydanticCustomError

# The type of the fault: the gatherer of faults says it ``VALIDATION_FAILED``.
NUL_FAULT = "string_nul"


def holds_nul(value: object) -> bool:
    """Tell a text that holds a NUL, at any depth of a list, an object or a model of one value."""
    if isinstance(value, str):
        return "\x00" in value
    if isinstance(value, RootModel):
        return holds_nul(cast("RootModel[object]", value).root)
    if isinstance(value, Mapping):
        entries = cast("Mapping[object, object]", value).items()
        return any(holds_nul(key) or holds_nul(item) for key, item in entries)
    if isinstance(value, list | tuple | set | frozenset):
        return any(holds_nul(item) for item in cast("Iterable[object]", value))
    return False


def refuse_nul[T](value: T) -> T:
    """Give the value back, or refuse it if it holds a NUL."""
    if holds_nul(value):
        raise PydanticCustomError(NUL_FAULT, "a text holds the NUL character")
    return value


# A text the service receives, in a parameter of a query or of a path.
Text = Annotated[str, AfterValidator(refuse_nul)]


class ContractModel(BaseModel):
    """A model of the contract: each of its fields refuses a NUL, wherever it holds a text."""

    @field_validator("*", mode="after")
    @classmethod
    def _refuse_nul(cls, value: object) -> object:
        return refuse_nul(value)
