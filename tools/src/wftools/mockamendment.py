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

On the reference 101, the amendment 2 is out of date: opened before the merge of the amendment 1,
which wrote the main structure and marked the reference, its base is no longer that structure, and
a marked revision is not updated (``structures_amendments``, #4034). Its merge asked there on 1
February, while the project has no current revision, is offered by its command, which does not
judge the state, but its report and its merge are refused by ``structure_up_to_date``
(``merge_reference_out_of_date_refused``); the merge that applies is shown on the current revision,
which took the amendment over out of date and updated it (``structure_merge_report``, #4174).
"""

from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockcore, mockdiff, mocktext
from wftools.mockcorrelations import correlation
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


def marked(roots: Iterable[Task] | None = None) -> list[JsonObject]:
    """Return the whole differential read today, marked against the main structure.

    The main structure as the differential copies it, so that a node removed renders as a node of
    the differential would; the marks are those of its values alone (``mockdiff``); every node
    named by its identifier in the differential (``own_id``). The differential as described, or
    as a write leaves it (``roots``).
    """
    before, after = mockcore.opened(mockcore.current(_copied(described()))), rows(roots)
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
        task = cast("JsonObject | None", node.get("task"))
        if task is not None:
            # A copy: the facet is shared by every reading of the structure it was read from.
            node["task"] = {
                **task,
                "link_conflicts": [
                    {
                        **conflict,
                        "predecessor_node_id": own[cast("str", conflict["predecessor_node_id"])],
                        "successor_node_id": own[cast("str", conflict["successor_node_id"])],
                        "manual_node_id": own[cast("str", conflict["manual_node_id"])],
                    }
                    for conflict in cast("list[JsonObject]", task["link_conflicts"])
                ],
            }
    return nodes


def rows(roots: Iterable[Task] | None = None) -> list[mockcore.Row]:
    """Return the differential read today, its lines after the review of the reference.

    As described, or as a write leaves it (``roots``); its lines of a task completed accept their
    fields, the amendment rebudgeting them (WF-REV-0050; F-01, #1766).
    """
    return mockcore.opened(mockcore.current(amendment() if roots is None else roots))


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


def nodes_amendment_differences() -> JsonObject:
    """Return what listNodes answers of the whole differential read by its differences alone.

    ``difference=added,removed,modified``, « Écarts seulement » (#1398): the nodes it adds,
    withdraws or modifies, their ancestors with them; the totals those of the whole differential,
    which the filter does not restrict (`NodeTotals`).
    """
    return {
        **mockcore.whole(rows()),
        "items": cast("list[JsonValue]", mockdiff.differences(marked(), mockdiff.DIFFERENCES)),
    }


# --- The report before the merge -----------------------------------------------------------------

DESIGNATED = {N.COMMISSIONING: ["duration", "parent"], N.COMMISSIONING_LINE: ["hours"]}
"""The nodes the amendment changes, and what it changes of them: the columns (`NodeColumn`), and
the parent of the commissioning, moved under the trials on site, which no column presents
(`ImportDifference.fields`, #1194)."""

RELINKED = (N.COMMISSIONING, N.MOUNTING, N.TESTS_RESUMED)
"""The task whose predecessor the amendment changes, its predecessor before, and after."""

ADDED_LINKED = (N.TESTS_RESUMED, N.MOUNTING)
"""The task the amendment adds and links, and its predecessor: the link comes with the task."""


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


def is_task(node: JsonObject) -> bool:
    """Tell whether a node read is a task."""
    return node["kind"] == "task"


def _link(change: str, task: JsonObject, predecessor: JsonObject) -> JsonObject:
    """Return a link added or removed, named by its successor, whose predecessors present it.

    A task the amendment adds has no lineage in the main structure yet, nor has its link.
    """
    return {
        "change": change,
        "target": "link",
        "lineage_id": None if task["difference"] == mockdiff.ADDED else task["lineage_id"],
        "label": cast("JsonObject", task["task"])["label"],
        "predecessor_label": cast("JsonObject", predecessor["task"])["label"],
        "fields": [],
    }


def structure_merge_report() -> JsonObject:
    """Return what getStructureMergeReport answers of the amendment 2 (WF-REV-0050).

    In the order of the service: the tasks added, the links added — that of the commissioning to
    the rework, and that of the rework to the mounting, the task the amendment adds being linked
    as it enters —, the lines added, then what is modified and what is withdrawn: the commissioning
    moved under the trials on site and its duration changed, the hours of its line changed, its
    link to the mounting withdrawn, the line withdrawn; no started task withdrawn, none completed;
    nothing refusing it. The counters of the two structures read, as `structures` lists them; the
    merge applies to the current revision, which it does not create (#790, #4276).
    """
    nodes = marked()
    by_id = {cast("str", node["node_id"]): node for node in nodes}
    task, before, after = (by_id[own_id(number)] for number in RELINKED)
    linked, predecessor = (by_id[own_id(number)] for number in ADDED_LINKED)
    added = [node for node in nodes if node["difference"] == mockdiff.ADDED]
    differences: list[JsonValue] = [_difference("added", node) for node in added if is_task(node)]
    differences.append(_link("added", task, after))
    differences.append(_link("added", linked, predecessor))
    differences.extend(_difference("added", node) for node in added if not is_task(node))
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
        "creates_current_revision": False,
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


MERGE = "merge_structure"


def revision_marked_merge_offered(reference: JsonObject) -> JsonObject:
    """Return the reference as ``revision_marked`` reads it, its merge offered.

    The project has no current revision then: the merge lacks no draft (WF-REV-0050, #790). The
    reading of the reference is passed, generated by the same command (``mocksnapshot``).
    """
    commands = cast("list[JsonObject]", reference["available_commands"])
    return {
        **reference,
        "available_commands": [
            {**each, "is_available": True, "missing_conditions": []}
            if each["command"] == MERGE
            else each
            for each in commands
        ],
    }


def merge_may_create_revision_refused() -> JsonObject:
    """Return the refusal of a merge that would create the current revision, for a reader.

    The refusal of ``merge_revision_marked_refused``, the condition being the one the command
    ``merge_structure`` lists after ``unmerged_amendment_exists`` to a session without
    ``revisions.write`` (WF-REV-0050).
    """
    refused = fixture("merge_revision_marked_refused")
    return {
        **refused,
        "params": {"missing_condition": "may_create_revision"},
        "correlation_id": universe(1562),
    }


REFERENCE_OUT_OF_DATE = "merge_reference_out_of_date_refused"
"""The refusal of the merge of the amendment 2 on the reference, out of date there (#4174)."""


def merge_reference_out_of_date_refused() -> JsonObject:
    """Return the refusal of the report and of the merge of the amendment 2 on the reference.

    On 1 February, the project without a current revision, by a session that may create it: the
    conditions of the command are met, and the last one, ``structure_up_to_date``, is missing — the
    amendment 2 is out of date on the reference, which no update reaches (WF-REV-0050, #4034).
    """
    return {
        "code": "STATE_FORBIDS_OPERATION",
        "status": 409,
        "params": {"missing_condition": "structure_up_to_date"},
        "correlation_id": correlation(REFERENCE_OUT_OF_DATE),
    }


def examples(reference: JsonObject) -> dict[str, JsonObject]:
    """Return the examples of the amendment 2, by file name, the reference read by getRevision."""
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
    linked, predecessor = (_label(whole, number) for number in ADDED_LINKED)
    amendment_id = structure("amendment")["structure_id"]
    report = structure_merge_report()
    differences_read = nodes_amendment_differences()
    differences = cast("list[JsonObject]", differences_read["items"])
    _, _, values, contents = mockdiff.grouped(differences)
    changed, content = (
        [f"« {cast('JsonObject', node[cast('str', node['kind'])])['label']} »" for node in nodes]
        for nodes in (values, contents)
    )
    return {
        "revision_marked_merge_offered.json": mocktext.example(
            "La révision de référence du projet le 1er février 2026, juste après le marquage par "
            "la fusion de l'avenant 1 et avant que le réexamen d'un risque n'ouvre la révision "
            "courante. Le projet n'a pas de révision en cours, et la référence porte l'avenant 2 "
            "« reprise des essais », non fusionné : sa commande de fusion y est offerte, la "
            "commande ne jugeant pas l'état de l'avenant. Or l'avenant 2 est en retard sur la "
            "référence 101 (structures_amendments) : compte rendu et fusion y sont refusés "
            "(merge_reference_out_of_date_refused). La fusion applicable se montre sur la "
            "révision en cours (structure_merge_report). Les autres commandes de modification "
            "restent indisponibles, la révision étant marquée (WF-REV-0050, WF-REV-0010, "
            "WF-REV-0100, #790, #4174).",
            revision_marked_merge_offered(reference),
        ),
        "merge_may_create_revision_refused.json": mocktext.example(
            "La fusion de l'avenant 2 demandée le 1er février 2026 sur la référence "
            "(revision_marked_merge_offered) par une session sans `revisions.write` : elle "
            "créerait la révision en cours, et la commande merge_structure nomme "
            "may_create_revision, après unmerged_amendment_exists. Rien n'est fusionné ni créé. "
            "L'avenant étant en retard sur la référence 101, une session qui peut la "
            "créer serait refusée par structure_up_to_date "
            "(merge_reference_out_of_date_refused ; WF-REV-0050, WF-REV-0010, WF-IHM-0090, #790, "
            "#4174).",
            merge_may_create_revision_refused(),
        ),
        f"{REFERENCE_OUT_OF_DATE}.json": mocktext.example(
            f"Le compte rendu de la fusion de « {LABEL} », ou sa fusion, demandés le "
            f"1er février 2026 sur la référence, quand le projet n'a pas de révision en cours "
            f"(revision_marked_merge_offered), par une session qui peut la créer : les "
            f"conditions de la commande sont réunies, mais l'avenant, ouvert avant la fusion de "
            f"l'avenant 1 qui a écrit la structure principale et marqué la référence, est en "
            f"retard sur la référence 101 (structures_amendments, is_up_to_date faux), et une "
            f"révision marquée ne se met pas à jour. Refusés par la condition qui manque, "
            f"structure_up_to_date, la dernière ; rien n'est lu ni fusionné, aucune révision "
            f"n'est créée. L'avenant se fusionne une fois repris par la révision en cours et mis "
            f"à jour (structure_merge_report ; WF-REV-0050, WF-REV-0100, #4034, #4174).",
            merge_reference_out_of_date_refused(),
        ),
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
        "nodes_amendment_differences.json": mocktext.example(
            f"Le différentiel « {LABEL} » (structure {amendment_id}) lu entier le "
            f"{mocktext.day(mockcore.READ_ON)} par ses seuls écarts, « Écarts seulement » "
            f"(difference=added,removed,modified) : {mocktext.count(len(differences))} nœuds des "
            f"{mocktext.count(len(whole))} de l'arbre marqué — les nœuds ajoutés, "
            f"{_said(differences, mockdiff.ADDED)} ; ceux retirés, à leur place, en lecture "
            f"seule, {_said(differences, mockdiff.REMOVED)} ; ceux modifiés par leurs propres "
            f"valeurs, {mocktext.listed(changed)} ; ceux modifiés par leur seul contenu, "
            f"`changes` vide, {mocktext.listed(content)} —, chaque ancêtre d'un nœud retenu "
            f"l'étant lui-même, si bien que l'arbre filtré reste un arbre sans aucun nœud "
            f"inchangé. Les totaux sont ceux du différentiel entier, sans la ligne retirée : "
            f"`difference` ne les restreint pas (WF-REV-0080, WF-REV-0100, C-361, #1398).",
            differences_read,
        ),
        "structure_merge_report.json": mocktext.example(
            f"Le compte rendu préalable de la fusion de l'avenant 2 du témoin, « {LABEL} », "
            f"différentiel non fusionné de la révision courante (nodes_amendment), repris puis "
            f"mis à jour : sa fusion s'applique ici, refusée sur la référence "
            f"(merge_reference_out_of_date_refused) ; "
            f"{_said(whole, mockdiff.ADDED)}, qu'il ajoute ; la « {relinked} » déplacée sous "
            f"les « {_label(whole, N.SITE_TESTS)} », liée à la « {after} » au lieu du "
            f"« {before} », sa durée et la charge de sa ligne modifiées ; la « {linked} » "
            f"ajoutée est liée au « {predecessor} » ; "
            f"{_said(whole, mockdiff.REMOVED)}, retirée ; aucune tâche démarrée retirée, aucune "
            f"terminée, aucun motif de "
            f"refus : la confirmation est offerte, qui renverra les compteurs lus — celui de la "
            f"structure principale, {report['main_structure_lock_version']}, et celui du "
            f"différentiel, {report['amendment_lock_version']}, comme `structures` les dit "
            f"(WF-REV-0050, WF-IHM-0110, #791, #1194, #4174).",
            report,
        ),
    }
