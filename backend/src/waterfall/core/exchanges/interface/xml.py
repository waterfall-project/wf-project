# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The hardened reader of an XML file a user deposited: the only one every XML format employs.

``lxml``, which validates against a schema where the standard library cannot (WF-QUA-0080), read
by a parser that resolves no entity, reaches no network, loads no DTD and refuses a tree too deep
or a text too long (EP-06, "Ce que le cadrage décide"): a file deposited by a user never makes the
service read a file of its own, call an address, or swell in memory. A format reads a document
by ``etree.fromstring(content, hardened_parser())`` and never builds a parser of its own; the
reviewer looks for one. A document that is not well formed raises ``etree.XMLSyntaxError``, which
the format turns into its refusal. The opener of a workbook reads the XML of its members through
the same parser given a target, which counts what it reads and builds no tree
(``hardened_target_parser``, US-3190/L1b).
"""

from typing import TYPE_CHECKING, TypedDict

from lxml import etree

if TYPE_CHECKING:
    from lxml.etree import ParserTarget
    from lxml.etree._parser import CustomTargetParser


# The options of the hardening, written once: the two parsers below take them both.
class _Hardening(TypedDict):
    resolve_entities: bool
    no_network: bool
    huge_tree: bool
    load_dtd: bool


_HARDENING = _Hardening(resolve_entities=False, no_network=True, huge_tree=False, load_dtd=False)


def hardened_parser() -> etree.XMLParser:
    """Give a parser that resolves no entity, reaches no network, loads no DTD nor a huge tree."""
    return etree.XMLParser(**_HARDENING)


def hardened_target_parser(target: ParserTarget[None]) -> CustomTargetParser[None]:
    """Give the hardened parser, calling ``target`` as it reads, fed step by step, without a tree.

    What the target keeps is all the reading holds: no element, no text, unless it keeps them.
    """
    return etree.XMLParser(**_HARDENING, target=target)
