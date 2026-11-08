# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The head of a file deposited: whether it opens a planning of MS Project (US-1430/L3).

The opening of an import reads only the head of a file (``Format.header_length``), which a parser
of XML cannot read whole: the root is found after what may precede it — a mark of the encoding,
the declaration, comments, instructions, blanks —, and recognised by its name, ``Project``, in a
namespace of MS Project that its own attributes declare, with its prefix if it has one. The whole
file is read by the reader at the analysis, which refuses what the head did not show.
"""

import re

from waterfall.core.planning.msproject.tree import NAMESPACES

PROLOG = re.compile(
    rb"(?:\xef\xbb\xbf)?(?:\s++|<\?.*?\?>|<!--.*?-->)*+"
    rb"<(?:(?P<prefix>[\w.-]+):)?Project(?P<attributes>[\s>/][^>]*)",
    re.DOTALL,
)
"""What may precede the root (an atomic run), then the root, its prefix, attributes."""

NAMESPACE_DECLARATION = re.compile(
    rb"""xmlns(?::(?P<prefix>[\w.-]+))?\s*=\s*["'](?P<uri>[^"']*)["']"""
)
"""A declaration of a namespace among the attributes of an element, its prefix if any."""


def recognised(head: bytes) -> bool:
    """Tell whether the head of a file opens a ``Project`` of the namespace of MS Project."""
    root = PROLOG.match(head)
    if root is None:
        return False
    prefix = root.group("prefix")
    for declared in NAMESPACE_DECLARATION.finditer(root.group("attributes")):
        if declared.group("prefix") == prefix:
            return declared.group("uri").decode(errors="replace") in NAMESPACES
    return False
