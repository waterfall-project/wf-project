# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The text of an example the generators write: one line for each item of its lists.

Taken out of ``mockdata`` to keep that module under the size limit; ``mockdata.render`` is still
the name the tests and the generator read it by.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject, JsonValue

# The envelope of an example and its value are laid out; below them, one line per item.
_EXPANDED_DEPTH = 2
# Below them, an object that holds a list longer than this is laid out too, the list one line per
# item, even within an item: a point of the portfolio matrix, a task of a role (#1053, #3181).
_LONG_LIST = 50


def render(example: JsonObject) -> str:
    """Return the text of an example: one line for each item of its lists, for readable diffs."""
    return _render(example, 0) + "\n"


def _render(value: JsonValue, depth: int) -> str:
    indent = "  " * depth
    inner = indent + "  "
    if isinstance(value, list) and value:
        items = ",\n".join(inner + _render(item, depth + 1) for item in value)
        return f"[\n{items}\n{indent}]"
    if isinstance(value, dict) and (depth < _EXPANDED_DEPTH or _holds_long_list(value)):
        fields = ",\n".join(
            f"{inner}{_compact(key)}: {_render(item, depth + 1)}" for key, item in value.items()
        )
        return f"{{\n{fields}\n{indent}}}"
    return _compact(value)


def _holds_long_list(value: JsonObject) -> bool:
    return any(isinstance(item, list) and len(item) > _LONG_LIST for item in value.values())


def _compact(value: JsonValue) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
