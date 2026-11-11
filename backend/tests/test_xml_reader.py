# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The hardened reader of an XML file deposited, the one every XML format employs (EP-06).

A detail of the realization which reprises no Vérif (EP-06, "Ce que le cadrage décide"): a file a
user deposits never makes the service read one of its own files, nor expand an entity, nor follow a
tree as deep as it likes. The documents are read without a database.
"""

import pytest
from lxml import etree

from waterfall.core.exchanges.interface import hardened_parser

# A document that names a file of the server and an entity of its own.
ENTITIES = (
    b'<!DOCTYPE plan [<!ENTITY secret SYSTEM "file:///etc/hostname">'
    b'<!ENTITY name "expanded">]><plan><read>&secret;</read><named>&name;</named></plan>'
)
# Deeper than the 256 levels libxml2 keeps without its option for huge trees.
DEEP = b"<task>" * 300 + b"</task>" * 300


def test_a_deposited_document_expands_no_entity_and_reads_no_file_of_the_server() -> None:
    plan = etree.fromstring(ENTITIES, hardened_parser())
    read, named = plan.find("read"), plan.find("named")
    assert read is not None
    assert named is not None
    assert (read.text, named.text) == (None, None)
    assert [str(entity) for entity in (*read, *named)] == ["&secret;", "&name;"]


def test_a_deposited_document_deeper_than_the_bound_is_refused() -> None:
    with pytest.raises(etree.XMLSyntaxError, match="Excessive depth"):
        etree.fromstring(DEEP, hardened_parser())
