# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The elements of an MSPDI file as a plain tree, between the bytes and the model.

The reader parses the bytes by the hardened parser of the exchanges into this tree, then reads
it; the writer builds it in the order of the schema, then serialises it. Going through a tree of
its own keeps the reader and the writer to names and texts, the namespace being said once here.
"""

from collections import deque
from dataclasses import dataclass, field

from lxml import etree

from waterfall.core.exchanges.interface import hardened_parser
from waterfall.core.planning.msproject.model import UnreadableProjectError

NAMESPACE = "http://schemas.microsoft.com/project/2007"
"""The namespace of the schema of MS Project 2013, the one the writer writes, and valid against it.

MS Project writes the one without the year, which the reader takes too (``NAMESPACES``).
"""

NAMESPACES: frozenset[str] = frozenset({NAMESPACE, "http://schemas.microsoft.com/project"})
"""The namespaces of a planning the reader takes."""


def _no_children() -> list[Tag]:
    """Give the children of an element built without any."""
    return []


@dataclass(slots=True)
class Tag:
    """An element: its name without namespace, its text, and its child elements in order."""

    name: str
    text: str | None = None
    children: list[Tag] = field(default_factory=_no_children)

    def child(self, name: str) -> Tag | None:
        """Return the first child of that name, ``None`` without one."""
        return next((child for child in self.children if child.name == name), None)

    def every(self, name: str) -> list[Tag]:
        """Return the children of that name, in order."""
        return [child for child in self.children if child.name == name]

    def text_of(self, name: str) -> str | None:
        """Return the text of the first child of that name, ``None`` without one or without text."""
        child = self.child(name)
        return None if child is None else child.text


def tag(name: str, *children: Tag | None) -> Tag:
    """Build an element of the children given, those that are ``None`` left out."""
    return Tag(name, children=[child for child in children if child is not None])


def leaf(name: str, value: str | None) -> Tag | None:
    """Build an element that holds a text, ``None`` for a value the writer leaves out."""
    return None if value is None else Tag(name, value)


def parse(content: bytes) -> Tag:
    """Parse a file into its tree, refusing one that is not an MSPDI ``Project`` of the schema.

    Comments, instructions and entities left unresolved are no elements, and are not read.
    """
    try:
        root = etree.fromstring(content, hardened_parser())
    except etree.XMLSyntaxError as error:
        raise UnreadableProjectError(element="xml") from error
    name = etree.QName(root)
    if name.localname != "Project" or name.namespace not in NAMESPACES:
        raise UnreadableProjectError(element="Project")
    tree = Tag("Project", root.text)
    pending = deque([(root, tree)])
    while pending:
        element, parent = pending.popleft()
        for child in element:
            if isinstance(child.tag, str):
                node = Tag(etree.QName(child).localname, child.text)
                parent.children.append(node)
                pending.append((child, node))
    return tree


def serialise(tree: Tag) -> bytes:
    """Serialise a tree into an MSPDI file, every element in the namespace of the schema."""
    root = etree.Element(f"{{{NAMESPACE}}}{tree.name}", nsmap={None: NAMESPACE})
    pending = deque([(root, tree)])
    while pending:
        element, node = pending.popleft()
        element.text = node.text
        for child in node.children:
            pending.append((etree.SubElement(element, f"{{{NAMESPACE}}}{child.name}"), child))
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
