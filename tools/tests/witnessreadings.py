# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the core of the witness share: the numbers of its nodes, how to read them."""

from typing import Any, cast

type Node = dict[str, Any]

STUDIES, DETAILED_STUDIES, DESKS, REVIEW, ACCEPTANCE, FILE = 521, 522, 523, 524, 525, 526
CONTROL_STATION, WIRING, LABOUR, BLOCKS, PROVISION, MILESTONE = 551, 552, 553, 554, 555, 556
OCCURRED, REMINDER, REMINDER_LINE, TRANSPORT, TRANSPORT_LINE = 541, 542, 543, 544, 545
INSTALLATION, MOUNTING, COMMISSIONING = 561, 562, 565


def nodes(reading: Any) -> dict[int, Node]:
    """Return the nodes of a reading by the number of their identifier."""
    items = cast("list[Node]", reading["items"])
    return {int(node["node_id"][-4:]): node for node in items}


def facet(node: Node) -> Node:
    """Return the facet of a node, the one its kind names."""
    return cast("Node", node[node["kind"]])
