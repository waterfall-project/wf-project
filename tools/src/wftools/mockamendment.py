# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The amendment 2 of the witness, « reprise des essais »: a differential not merged (#791).

The amendment 2 coexisted with the amendment 1 in the reference 101 without being merged; the
current revision 102 took it over, still not merged (WF-REV-0100, `structures`). It is the main
structure of 102 as today, its trials of the wiring on site resumed: under the installation on
site, a summary « Essais sur site » gathers the rework of the trials of the wiring, which the
mounting precedes, and the commissioning, moved under it, which follows the rework, lengthened to
fifteen days and its line to 120 hours; the assistance to the trials of the wiring, which the
rework replaces, is withdrawn from the mounting. No task of a differential bears a lot or a post,
nor an inscription to a timeline or to the time/time tracking: those are the main structure's
alone (WF-PLA-0170, WF-PLA-0060), and its tasks do not name them among the fields they accept.
Its nodes have identifiers of their own (``own_id``): the node 5nn of the main structure is 12nn
in the differential, a node drawn has its own family, and those it adds are numbered from 591, so
12nn from 1291. They share the lineages of the main structure's, by which the reading marks them
(6nn, and from 691 for those it adds): one identifier at one version names one content, whatever
the reading (#421).

What the examples say of it is read from this description, never written by hand: its reading,
the tree of the installation on site marked against the main structure (``nodes_amendment``,
``mockdiff``, C-361), and the report before its merge (``structure_merge_report``, WF-REV-0050),
whose differences are those the amendment designates — the dates its edits move elsewhere are
computed, not designated.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockcore, mockdiff, mocktext
from wftools.mockids import AMENDMENT_NODES, identifier, universe
from wftools.mockstructure import described
from wftools.mockwitness import (
    COMMISSIONING,
    COMMISSIONING_TECHNICIAN,
    GENERATED,
    SUBPROJECT_TESTS,
    Line,
    Link,
    N,
    Task,
    fixture,
    node_id,
    rewritten,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from wftools.mockstructure import JsonObject, JsonValue

LABEL = "Avenant 2 — reprise des essais"
"""The label of the amendment, as the structures of the revisions list it."""

COMMISSIONING_DAYS = 15
COMMISSIONING_HOURS = Decimal(120)
"""The commissioning lengthened by the amendment, and the hours of its line."""

TESTS_RESUMED = Task(
    N.TESTS_RESUMED,
    "Reprise des essais de câblage",
    days=5,
    links=(Link(N.MOUNTING),),
    lines=(
        Line(
            N.TESTS_RESUMED_LINE,
            "Assistance à la reprise des essais",
            COMMISSIONING,
            hours=Decimal(40),
            role=COMMISSIONING_TECHNICIAN,
            subproject=SUBPROJECT_TESTS,
        ),
    ),
)
"""The rework of the trials of the wiring, after the mounting, the commissioning technician
assisting it as he assisted the trials it replaces."""

MAIN_ONLY = ("task.order_item_id", "task.work_package_id", "task.tracking")
"""What a task of the main structure accepts and a task of a differential does not (#1065)."""

OWN_OFFSET = 700
"""What separates the identifier of a node of the differential from the number of its node in the
main structure: the node 5nn is 12nn in the differential (#421)."""

NODE_KEYS = ("node_id", "parent_id")
"""The keys of a node that name a node of its structure, besides its predecessors."""


def own_id(number: int) -> str:
    """Return the identifier of the node of this number in the differential: 12nn for 5nn.

    A node drawn has its own family; the lineage of either stays that of the main structure.
    """
    if number < GENERATED:
        return universe(number + OWN_OFFSET)
    return identifier(AMENDMENT_NODES, number - GENERATED)


def amendment(roots: Iterable[Task] | None = None) -> tuple[Task, ...]:
    """Return the differential described: the main structure given, its trials resumed.

    The whole structure of the current revision by default, as described today.
    """

    def change(task: Task) -> Task:
        task = replace(task, bears=None, inscriptions=())
        if task.number == N.MOUNTING:
            kept = tuple(line for line in task.lines if line.number != N.TESTS_LINE)
            return replace(task, lines=kept)
        if task.number == N.INSTALLATION:
            [mounting, commissioning] = task.children
            lengthened = replace(
                commissioning,
                days=COMMISSIONING_DAYS,
                links=(Link(N.TESTS_RESUMED),),
                lines=tuple(
                    replace(line, hours=COMMISSIONING_HOURS, budgeted=None)
                    for line in commissioning.lines
                ),
            )
            tests = Task(N.SITE_TESTS, "Essais sur site", children=(TESTS_RESUMED, lengthened))
            return replace(task, children=(mounting, tests))
        return task

    return rewritten(described() if roots is None else roots, change)


def _copied(roots: Iterable[Task]) -> tuple[Task, ...]:
    """Return a structure as a differential copies it: no attachment, no inscription."""
    return rewritten(roots, lambda task: replace(task, bears=None, inscriptions=()))


def marked() -> list[JsonObject]:
    """Return the whole differential read today, marked against the main structure.

    The main structure as the differential copies it, so that a node removed renders as a node of
    the differential would; the marks are those of its values alone (``mockdiff``); every node
    named by its identifier in the differential (``own_id``).
    """
    before, after = mockcore.current(_copied(described())), rows()
    nodes = mockdiff.marked(before, after)
    own = {node_id(row.number): own_id(row.number) for row in (*before, *after)}
    for node in nodes:
        fields = cast("list[JsonValue]", node["editable_fields"])
        node["editable_fields"] = [field for field in fields if field not in MAIN_ONLY]
        for key in NODE_KEYS:
            if node[key] is not None:
                node[key] = own[cast("str", node[key])]
        if "predecessors" in node:
            node["predecessors"] = [
                {**link, "predecessor_node_id": own[cast("str", link["predecessor_node_id"])]}
                for link in cast("list[JsonObject]", node["predecessors"])
            ]
    return nodes


def rows() -> list[mockcore.Row]:
    """Return the differential read today, its lines after the review of the reference."""
    return mockcore.current(amendment())


def nodes_amendment() -> JsonObject:
    """Return what listNodes answers of the installation on site, read on the differential.

    ``subtree_of``: the nodes under the installation, it included, marked, the line withdrawn at
    its place; the totals those of the differential, which no longer bears it (`NodeTotals`).
    """
    answer = mockcore.subtree(rows(), N.INSTALLATION)
    return {
        **answer,
        "items": cast("list[JsonValue]", mockdiff.window(marked(), own_id(N.INSTALLATION))),
    }


# --- The report before the merge -----------------------------------------------------------------

DESIGNATED = {N.COMMISSIONING: ["duration", "parent"], N.COMMISSIONING_LINE: ["hours"]}
"""The nodes the amendment changes, and what it changes of them: the columns (`NodeColumn`), and
the parent of the commissioning, moved under the trials on site, which no column presents
(`ImportDifference.fields`, #1194)."""

RELINKED = (N.COMMISSIONING, N.MOUNTING, N.TESTS_RESUMED)
"""The task whose predecessor the amendment changes, its predecessor before, and after."""


def structure(kind: str) -> JsonObject:
    """Return a structure of the current revision as `structures` lists it: the main, or this."""
    found = [
        each
        for each in cast("list[JsonObject]", fixture("structures"))
        if each["kind"] == kind and (kind == "main" or each["label"] == LABEL)
    ]
    [one] = found
    return one


def _difference(change: str, node: JsonObject, fields: list[str] | None = None) -> JsonObject:
    """Return a node added, updated or removed, as an import names it (`ImportDifference`)."""
    facet = cast("JsonObject", node[cast("str", node["kind"])])
    return {
        "change": change,
        "target": node["kind"],
        "lineage_id": None if change == "added" else node["lineage_id"],
        "label": facet["label"],
        "predecessor_label": None,
        "fields": cast("list[JsonValue]", fields or []),
    }


def _link(change: str, task: JsonObject, predecessor: JsonObject) -> JsonObject:
    """Return a link added or removed, named by its successor, whose predecessors present it."""
    return {
        "change": change,
        "target": "link",
        "lineage_id": task["lineage_id"],
        "label": cast("JsonObject", task["task"])["label"],
        "predecessor_label": cast("JsonObject", predecessor["task"])["label"],
        "fields": [],
    }


def structure_merge_report() -> JsonObject:
    """Return what getStructureMergeReport answers of the amendment 2 (WF-REV-0050).

    The tasks and the lines added, the link of the commissioning moved from the mounting to the
    rework, the commissioning moved under the trials on site and its duration changed, the hours
    of its line changed, the line withdrawn; no started task withdrawn, none completed; nothing
    refusing it. The counters of the two structures read, as `structures` lists them.
    """
    nodes = marked()
    by_id = {cast("str", node["node_id"]): node for node in nodes}
    task, before, after = (by_id[own_id(number)] for number in RELINKED)
    differences: list[JsonValue] = [
        _difference("added", node) for node in nodes if node["difference"] == mockdiff.ADDED
    ]
    differences.append(_link("added", task, after))
    differences.extend(
        _difference("updated", by_id[own_id(number)], fields)
        for number, fields in DESIGNATED.items()
    )
    differences.append(_link("removed", task, before))
    differences.extend(
        _difference("removed", node) for node in nodes if node["difference"] == mockdiff.REMOVED
    )
    return {
        "main_structure_lock_version": structure("main")["lock_version"],
        "amendment_lock_version": structure("amendment")["lock_version"],
        "differences": differences,
        "completed_tasks": [],
        "refusals": [],
    }


# --- The examples --------------------------------------------------------------------------------


def _label(nodes: list[JsonObject], number: int) -> str:
    """Return the label of a node of the witness among the nodes read, by its number."""
    [node] = [each for each in nodes if each["node_id"] == own_id(number)]
    return cast("str", cast("JsonObject", node[cast("str", node["kind"])])["label"])


def _said(nodes: list[JsonObject], mark: str) -> str:
    """Say the nodes of a mark by their label, in the order of the plan."""
    return mocktext.listed(
        [
            f"« {cast('JsonObject', node[cast('str', node['kind'])])['label']} »"
            for node in nodes
            if node["difference"] == mark
        ]
    )


def examples() -> dict[str, JsonObject]:
    """Return the examples of the amendment 2, by file name."""
    reading = nodes_amendment()
    items = cast("list[JsonObject]", reading["items"])
    whole = marked()
    moved = [node for node in whole if "parent" in cast("list[str]", node["changes"])]
    below = {cast("str", node["node_id"]) for node in items}
    outside = sum(
        1
        for node in whole
        if node["node_id"] not in below and node["difference"] != mockdiff.UNCHANGED
    )
    elsewhere = (
        f"{mocktext.count(outside)} nœuds hors de l'installation marqués par l'allongement"
        if outside
        else "rien d'autre de la structure n'en est redaté"
    )
    relinked, before, after = (_label(whole, number) for number in RELINKED)
    amendment_id = structure("amendment")["structure_id"]
    report = structure_merge_report()
    return {
        "nodes_amendment.json": mocktext.example(
            f"L'installation sur site lue sur le différentiel « {LABEL} » de la révision "
            f"courante (structure {amendment_id}, subtree_of) le {mocktext.day(mockcore.READ_ON)}, "
            f"chaque nœud marqué par son écart avec la structure principale, que le serveur rend "
            f"(difference, changes) : {_said(items, mockdiff.ADDED)} ajoutés ; "
            f"{_said(items, mockdiff.REMOVED)} retirée, rendue à sa place, en lecture seule ; "
            f"{_said(moved, mockdiff.MODIFIED)} déplacée sous les « Essais sur site » et allongée "
            f"à {COMMISSIONING_DAYS} jours, modifiée par son parent, sa durée et ses dates, sa "
            f"ligne portée à {COMMISSIONING_HOURS} h ; les récapitulatives dont le contenu change "
            f"modifiées ; {elsewhere}. Les tâches n'y portent ni lot, ni "
            f"poste, ni inscription, et ne les nomment pas parmi les champs qu'elles acceptent ; "
            f"les totaux sont ceux du sous-arbre lu, sans la ligne retirée (WF-REV-0080, "
            f"WF-REV-0100, WF-PLA-0170, C-361).",
            reading,
        ),
        "structure_merge_report.json": mocktext.example(
            f"Le compte rendu préalable de la fusion de l'avenant 2 du témoin, « {LABEL} », "
            f"différentiel non fusionné de la révision courante (nodes_amendment) : "
            f"{_said(whole, mockdiff.ADDED)}, qu'il ajoute ; la « {relinked} » déplacée sous "
            f"les « {_label(whole, N.SITE_TESTS)} », liée à la « {after} » au lieu du "
            f"« {before} », sa durée et la charge de sa ligne modifiées ; "
            f"{_said(whole, mockdiff.REMOVED)}, retirée ; aucune tâche démarrée retirée, aucune "
            f"terminée, aucun motif de "
            f"refus : la confirmation est offerte, qui renverra les compteurs lus — celui de la "
            f"structure principale, {report['main_structure_lock_version']}, et celui du "
            f"différentiel, {report['amendment_lock_version']}, comme `structures` les dit "
            f"(WF-REV-0050, WF-IHM-0110, #791, #1194).",
            report,
        ),
    }
