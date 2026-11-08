# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The hardened reader of an XML file a user deposited: the only one every XML format employs.

``lxml``, which validates against a schema where the standard library cannot (WF-QUA-0080), read
by a parser that resolves no entity, reaches no network, loads no DTD and refuses a tree too deep
or a text too long (EP-06, "Ce que le cadrage décide"): a file deposited by a user never makes the
service read a file of its own, call an address, or swell in memory. A format reads a document
by ``etree.fromstring(content, hardened_parser())`` and never builds a parser of its own; the
reviewer looks for one. A document that is not well formed raises ``etree.XMLSyntaxError``, which
the format turns into its refusal.
"""

from lxml import etree


def hardened_parser() -> etree.XMLParser:
    """Give a parser that resolves no entity, reaches no network, loads no DTD nor a huge tree."""
    return etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False, load_dtd=False)
