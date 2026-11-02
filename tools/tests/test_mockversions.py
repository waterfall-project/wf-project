# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the versions of the nodes across the examples: one node at one version, one content.

The readings of a structure and the answers of its writes must tell one witness (#287, #421), the
differential of the current revision included (#1102). They try the simplifications of the fake
back against one another, not the Vérif of a requirement: none cites one (WF-QUA-0010, « un test
qui ne couvre aucune exigence »).
"""

import json
from typing import Any, cast

from wftools import mockwitness

type Node = dict[str, Any]

COUNTERFACTUAL = "Variante contrefactuelle"
"""How the summary of a declared counterfactual variant opens: another structure, by its word."""

ELSEWHERE = {
    "comparison.json": "the reference 101 compared with the offer 100",
    "volume/comparison_volume.json": "the same comparison, of the whole structure (#1201)",
    "comparison_differences.json": "the same comparison, by its differences alone (#1398)",
}
"""The readings of nodes exempt from #421, besides the declared counterfactual variants: the
comparisons of two marked revisions, which name their nodes by the identifiers of the current
revision's, by the convention of #287 (C12), their removed nodes counted in `row_number`. The
comparison of the offer with itself, the variant with four levels and the Kanban of the wiring
supposed completed are counterfactual variants declared, their summaries opening with the word
(#1196)."""

NOT_WRITTEN = ("ancestors", "rescheduled", "reinflated")
"""What a write renders of the nodes it does not write: they evolve without changing version."""


def _rendered(value: Any, found: list[Node]) -> None:
    """Collect every node a value renders, but those a write renders without writing them."""
    if isinstance(value, list):
        for item in cast("list[Any]", value):
            _rendered(item, found)
    elif isinstance(value, dict):
        fields = cast("Node", value)
        if {"node_id", "lock_version", "kind"} <= fields.keys():
            found.append(fields)
            return
        for key, item in fields.items():
            if key not in NOT_WRITTEN:
                _rendered(item, found)


def _contradictions(one: Node, other: Node, path: str = "") -> list[str]:
    """Return the keys two renderings of a node both carry and give two values, facets included.

    A reading renders the fields it is asked (`fields`): what one leaves out, the other may say.
    """
    found: list[str] = []
    for key in sorted(one.keys() & other.keys()):
        mine, theirs = one[key], other[key]
        if isinstance(mine, dict) and isinstance(theirs, dict):
            found += _contradictions(cast("Node", mine), cast("Node", theirs), f"{path}{key}.")
        elif mine != theirs:
            found.append(f"{path}{key}")
    return found


def test_two_examples_never_render_one_node_at_one_version_with_two_contents() -> None:
    # #421: the readings of a structure and the answers of its writes render a node at a version
    # with one content. The nodes of a differential have identifiers of their own, its lineages
    # those of the main structure's (#1102): the key holds for every structure of the revision.
    rendered: dict[tuple[str, int], tuple[str, Node]] = {}
    clashes: list[tuple[str, str, str, list[str]]] = []
    for path in sorted(mockwitness.FIXTURES.rglob("*.json")):
        name = path.relative_to(mockwitness.FIXTURES).as_posix()
        example = json.loads(path.read_text(encoding="utf-8"))
        if name in ELSEWHERE or example["summary"].startswith(COUNTERFACTUAL):
            continue
        found: list[Node] = []
        _rendered(example["value"], found)
        for node in found:
            key = (node["node_id"], node["lock_version"])
            if key in rendered and (said := _contradictions(rendered[key][1], node)):
                clashes.append((node["node_id"], rendered[key][0], name, said))
            rendered.setdefault(key, (name, node))
    assert clashes == []
    # Each exemption names an example that is, and the readings of the differential are tried.
    for name in ELSEWHERE:
        assert (mockwitness.FIXTURES / name).exists(), name
    assert {"nodes_amendment.json", "volume/nodes_thousand.json"} <= {
        name for name, _ in rendered.values()
    }


def test_each_paste_and_the_reestimate_follow_the_entry_before_them() -> None:
    entered, applied = (
        mockwitness.fixture(name) for name in ("estimate_line_entered", "paste_applied")
    )
    updated, reestimated = (
        mockwitness.fixture(name) for name in ("estimate_line_updated", "remaining_reestimated")
    )
    amended, pasted = (
        mockwitness.fixture(name)
        for name in ("estimate_line_updated_amendment", "paste_applied_amendment")
    )
    for first, then in ((entered, applied), (updated, reestimated), (amended, pasted)):
        line = first["nodes"][0]
        follow = next(node for node in then["nodes"] if node["node_id"] == line["node_id"])
        assert follow["lock_version"] == line["lock_version"] + 1
        assert then["structure_lock_version"] == first["structure_lock_version"] + 1


def _revisions(value: Any) -> list[Node]:
    """Return every revision an example renders, however deep it lies."""
    if isinstance(value, list):
        return [found for each in cast("list[Any]", value) for found in _revisions(each)]
    if not isinstance(value, dict):
        return []
    fields = cast("Node", value)
    keys = {"revision_id", "status", "lock_version", "marked_at"}
    here = [fields] if keys <= fields.keys() else []
    return here + [found for each in fields.values() for found in _revisions(each)]


def test_two_examples_never_render_one_revision_at_one_version_in_two_states() -> None:
    # #421 for the revisions (#1352): a revision at a version has one content, so whichever
    # examples render it, its status and its marking agree. The marking bears a version of its own.
    states: dict[tuple[str, int], set[tuple[str, str | None]]] = {}
    for path in sorted(mockwitness.FIXTURES.rglob("*.json")):
        example = json.loads(path.read_text(encoding="utf-8"))
        for each in _revisions(example["value"]):
            key = (each["revision_id"], each["lock_version"])
            states.setdefault(key, set()).add((each["status"], each["marked_at"]))
    assert {key for key, found in states.items() if len(found) > 1} == set()
    assert states


def test_the_revisions_are_listed_from_the_most_recent_to_the_oldest() -> None:
    # listRevisions lists « de la plus récente à la plus ancienne » (contract).
    for name in ("revisions", "revisions_marked", "revisions_designation_open"):
        opened = [each["audit"]["created_at"] for each in mockwitness.fixture(name)["items"]]
        assert opened == sorted(opened, reverse=True), name
