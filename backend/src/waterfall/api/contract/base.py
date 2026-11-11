# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
r"""The base of every model of the contract, and the text the service accepts: never a NUL.

PostgreSQL refuses a text that holds the NUL character, in a column as in a ``jsonb`` value: a
NUL that reached the database would be a failure of the database, a 500. Every text the service
receives is refused first, as a value its field refuses (422 ``VALIDATION_FAILED``, at the
pointer of the field, or of its item that holds the NUL): a parameter by the type ``Text``, a
body by the base of the models ``make generate-server-models`` engenders, which looks for a NUL
in each of their fields — a text, an item of a list, a key or a value of an object.

The same base reads a decimal as the contract writes it (WF-DAT-0100, #2238): the pattern of
``Decimal``, which ``Money`` and the types built on them carry, is one of JSON Schema, where
``\d`` is a digit of 0 to 9; the engendered models read it in Unicode, and would take ``12.50``
written in Arabic-Indic digits for ``12.50``. A value of such a type that holds another digit is
refused as its pattern would refuse it, at the pointer of the field or of its item. The types are
recognised by their pattern, without importing the engendered models, which import this base.
"""

from collections.abc import Callable, Iterable, Mapping
from typing import Annotated, cast

from pydantic import AfterValidator, BaseModel, RootModel, field_validator
from pydantic_core import PydanticCustomError

# The types of the faults: the gatherer of faults says each ``VALIDATION_FAILED``, at the item
# its ``path`` names under the field.
NUL_FAULT = "string_nul"
DIGIT_FAULT = "decimal_digit"
PLACED_FAULTS = frozenset({NUL_FAULT, DIGIT_FAULT})

# The pattern of ``Decimal`` in the contract (``components/common.yaml``), as the engendered models
# write it: alone for ``Decimal``, as the first of the lookaheads of a type that adds its own
# pattern to it (``Money``, ``IndexThreshold``, ``ProjectRatio``).
DECIMAL_PATTERN = r"^-?\d+(\.\d+)?$"
_DECIMAL_LOOKAHEAD = f"(?={DECIMAL_PATTERN})"


# Where a fault lies under the value of a field: the rank of an item of a list, the key of a value.
FaultPath = tuple[int | str, ...]


def is_decimal(model: type[BaseModel]) -> bool:
    """Tell a type of the contract whose root carries the pattern of ``Decimal`` or ``Money``.

    Its root is a text under that pattern, alone or among lookaheads, or a type that is one
    (``Percent``, ``Hours``: a ``Decimal``).
    """
    if not issubclass(model, RootModel):
        return False
    root = model.model_fields["root"]
    if isinstance(root.annotation, type) and issubclass(root.annotation, BaseModel):
        return is_decimal(root.annotation)
    patterns = [getattr(item, "pattern", None) for item in root.metadata]
    return any(
        isinstance(pattern, str)
        and (pattern == DECIMAL_PATTERN or pattern.startswith(_DECIMAL_LOOKAHEAD))
        for pattern in patterns
    )


def _holds_nul(value: object) -> bool:
    return isinstance(value, str) and "\x00" in value


def _holds_other_digit(value: object) -> bool:
    """Tell a decimal of the contract written with a digit that is not 0 to 9.

    Its pattern admits a sign, a point and digits alone: a character beyond ASCII is a digit of
    another script.
    """
    if not isinstance(value, RootModel):
        return False
    model = cast("RootModel[object]", value)
    return is_decimal(type(model)) and isinstance(model.root, str) and not model.root.isascii()


def fault_path(value: object, faulty: Callable[[object], bool]) -> FaultPath | None:
    """Give where the first faulty value lies under a value, at any depth, or ``None``.

    The path is that of the item that holds it under the value: an item of a list is pointed at
    its rank, a value of an object at its key, as any other fault of an item is; a fault in a key,
    or in a set, which has no rank, is pointed at the object or the set that holds it.
    """
    if faulty(value):
        return ()
    if isinstance(value, RootModel):
        return fault_path(cast("RootModel[object]", value).root, faulty)
    if isinstance(value, Mapping):
        entries = cast("Mapping[object, object]", value).items()
        if any(fault_path(key, faulty) is not None for key, _ in entries):
            return ()
        return _first_fault((((str(key),), item) for key, item in entries), faulty)
    if isinstance(value, list | tuple | set | frozenset):
        ranked = isinstance(value, list | tuple)
        items = enumerate(cast("Iterable[object]", value))
        return _first_fault(((((rank,) if ranked else ()), item) for rank, item in items), faulty)
    return None


def _first_fault(
    items: Iterable[tuple[FaultPath, object]], faulty: Callable[[object], bool]
) -> FaultPath | None:
    """Give the path of the first fault among items, each under the path that leads to it."""
    for place, item in items:
        below = fault_path(item, faulty)
        if below is not None:
            return (*place, *below)
    return None


def nul_path(value: object) -> FaultPath | None:
    """Give where the first NUL of a value lies, at any depth, or ``None`` if it holds none."""
    return fault_path(value, _holds_nul)


def refuse_nul[T](value: T) -> T:
    """Give the value back, or refuse it if it holds a NUL, saying where in ``path``."""
    path = nul_path(value)
    if path is not None:
        raise PydanticCustomError(NUL_FAULT, "a text holds the NUL character", {"path": path})
    return value


def refuse_other_digits[T](value: T) -> T:
    """Give the value back, or refuse it if a decimal in it holds a digit not of 0 to 9."""
    path = fault_path(value, _holds_other_digit)
    if path is not None:
        message = "a decimal holds a digit that is not 0 to 9"
        raise PydanticCustomError(DIGIT_FAULT, message, {"path": path})
    return value


# A text the service receives, in a parameter of a query or of a path.
Text = Annotated[str, AfterValidator(refuse_nul)]


class ContractModel(BaseModel):
    """A model of the contract: each of its fields refuses a NUL and a digit not of 0 to 9.

    A NUL wherever the field holds a text, a digit wherever it holds a decimal of the contract.
    """

    @field_validator("*", mode="after")
    @classmethod
    def _refuse_faults(cls, value: object) -> object:
        return refuse_other_digits(refuse_nul(value))
