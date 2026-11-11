# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The name of a tab of an Excel workbook, as Excel admits it (US-1550/L1, #2190).

Excel refuses seven characters in a name, measures it in UTF-16 code units, compares two names
without regard to case, and reserves one. The model keeps its labels and its codes as they are;
the generation of the tabs is what turns a label into a name, and this function is the one every
format of workbook uses — the tabs of an estimate here, the subprojects of the remaining-to-commit
format in EP-09.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

# The longest name of a tab, in UTF-16 code units (not in Python characters: a character outside
# the Basic Multilingual Plane counts for two).
MAX_UNITS = 31
FORBIDDEN = frozenset(":\\/?*[]")
# The name Excel reserves for its own history tab, whatever the case.
RESERVED = ("History",)
# What stands for a label that leaves nothing once cleaned.
EMPTY_NAME = "Onglet"
REPLACEMENT = "_"
# The last code point of the Basic Multilingual Plane, and the first printable one.
LAST_BMP = 0xFFFF
FIRST_PRINTABLE = 0x20


def _units(char: str) -> int:
    """Count the UTF-16 code units of one character."""
    return 2 if ord(char) > LAST_BMP else 1


def _truncate(text: str, units: int) -> str:
    """Cut a text to at most ``units`` UTF-16 code units, never inside a surrogate pair."""
    kept: list[str] = []
    used = 0
    for char in text:
        used += _units(char)
        if used > units:
            break
        kept.append(char)
    return "".join(kept)


def _clean(label: str) -> str:
    """Replace the characters Excel refuses, and the C0 controls."""
    return "".join(
        REPLACEMENT if char in FORBIDDEN or ord(char) < FIRST_PRINTABLE else char for char in label
    )


def _edges(text: str) -> str:
    """Keep an apostrophe off both ends of a name."""
    if text.startswith("'"):
        text = REPLACEMENT + text[1:]
    if text.endswith("'"):
        text = text[:-1] + REPLACEMENT
    return text


def _key(name: str) -> str:
    """Give the form in which Excel compares two names."""
    return name.casefold()


def sheet_name(label: str, taken: Iterable[str] = ()) -> str:
    """Name a tab from a label: refused characters replaced, 31 UTF-16 units, unique.

    ``taken`` holds the names already given in the workbook, the fixed tabs included; the name
    returned differs from each of them without regard to case, by a suffix `` (2)``, `` (3)``…
    that the truncation leaves room for. The caller adds the name returned to what it passes next.
    """
    used = {_key(name) for name in taken} | {_key(name) for name in RESERVED}
    base = _edges(_truncate(_clean(label), MAX_UNITS).strip()) or EMPTY_NAME
    name = base
    number = 2
    while _key(name) in used:
        suffix = f" ({number})"
        name = _truncate(base, MAX_UNITS - len(suffix)).rstrip() + suffix
        number += 1
    return name
