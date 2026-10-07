# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the schemas of the contract: every gap says its sense (EP-02/L35, #466).

A margin and a gap read alike once signed: the contract says, for each, what it subtracts from
what. None cites a requirement: they hold the contract, not the Vérif of one (WF-QUA-0010).
"""

import re

from wftools import REPOSITORY

SCHEMAS = REPOSITORY / "docs" / "api" / "components" / "schemas"

GAP = re.compile(r"^(?P<indent> +)(?P<name>[a-z_]*variance[a-z_]*|delta[a-z_]*):(?P<rest>.*)$")


def undescribed(text: str) -> list[str]:
    """Return the properties named as a gap that bear no description, in a schema file."""
    lines = text.splitlines()
    missing: list[str] = []
    for index, line in enumerate(lines):
        found = GAP.match(line)
        if found is None:
            continue
        indent, rest = len(found["indent"]), found["rest"]
        if "description:" in rest:
            continue
        block: list[str] = []
        for following in lines[index + 1 :]:
            if following.strip() and len(following) - len(following.lstrip()) <= indent:
                break
            block.append(following)
        prefix = " " * (indent + 2) + "description:"
        if not any(each.startswith(prefix) for each in block):
            missing.append(found["name"])
    return missing


def test_every_gap_of_the_schemas_says_its_sense() -> None:
    missing = {
        path.name: names
        for path in sorted(SCHEMAS.glob("*.yaml"))
        if (names := undescribed(path.read_text(encoding="utf-8")))
    }
    assert missing == {}


def test_a_gap_without_a_description_is_found() -> None:
    text = (
        "Totals:\n  properties:\n    variance: { $ref: x }\n"
        "    delta_to_reference:\n      anyOf: [x]\n      description: >-\n        Said.\n"
        "    delta:\n      allOf: [x]\n    cost_variance: { $ref: x, description: Said. }\n"
        "  required: [variance, delta]\n"
    )
    assert undescribed(text) == ["variance", "delta"]
