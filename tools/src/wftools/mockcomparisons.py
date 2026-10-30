# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The comparison of the two marked revisions of the witness, and its examples (WF-REV-0080).

The revisions are described by ``wftools.mockhistory``; here they are compared: the tree of the
later, its nodes marked against the earlier by lineage (``wftools.mockdiff``, C-361), the deltas
of the estimate by nature of cost and by subproject, and the examples that say them — the window
of a subtree (``comparison``), the whole structure (``comparison_volume``), the counterfactual
variants with a task moved under another summary (``comparison_moved``) and an offer compared
with itself (``comparison_identical``). Split from ``mockhistory`` to keep it under the thousand
lines (``wftools.sources``).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockcore, mockdiff, mocktext
from wftools.mockhistory import (
    OFFER,
    REFERENCE,
    REVISIONS,
    estimate_line,
    moved_offer_rows,
    nature,
    offer,
    offer_rates,
    offer_rows,
    reference_rows,
)
from wftools.mockstructure import (
    JsonObject,
    JsonValue,
    labels,
    money,
)
from wftools.mockwitness import (
    AMENDMENT_MERGED,
    CORE,
    OFFER_MARKED,
    SCHEDULED_AT,
    N,
    by_identifier,
    fixture,
)

if TYPE_CHECKING:
    from collections.abc import Collection

_amount, _day = mocktext.amount, mocktext.day


def _deltas(before: list[mockcore.Row], after: list[mockcore.Row]) -> list[JsonValue]:
    """Return the deltas of the estimate by nature of cost and by subproject, each named.

    The delta of the budgeted amounts and that of the re-estimated amounts, inflation included,
    the later's less the earlier's (WF-REV-0080), a key whose two deltas are nil left out. In the
    order of the identifiers of the natures, then of the subprojects of the universe, those
    without subproject last (WF-IND-0020).
    """
    natures = {
        nature["cost_type_id"]: nature["label"]
        for nature in by_identifier("cost_types", "cost_type_id")
    }
    subprojects = [entry["subproject_id"] for entry in fixture("subprojects")]
    named = labels()
    nil = (Decimal(0), Decimal(0))
    by: dict[tuple[str, str], tuple[Decimal, Decimal]] = {}
    for rows, sign in ((before, -1), (after, 1)):
        for row in rows:
            if row.kind != mockcore.ESTIMATE_LINE:
                continue
            subproject = cast("str | None", estimate_line(row)["subproject_id"]) or "unassigned"
            for key in (("cost_type", nature(row)), ("subproject", subproject)):
                budgeted, reestimated = by.get(key, nil)
                by[key] = (
                    budgeted + sign * row.amounts.budgeted,
                    reestimated + sign * row.amounts.reestimated,
                )
    order = [("cost_type", key) for key in natures] + [
        ("subproject", key) for key in [*subprojects, "unassigned"]
    ]
    return [
        {
            "dimension": dimension,
            "key": key,
            "label": None
            if key == "unassigned"
            else (natures[key] if dimension == "cost_type" else named[key]),
            "budgeted_delta": money(by[dimension, key][0]),
            "reestimated_delta": money(by[dimension, key][1]),
        }
        for dimension, key in order
        if by.get((dimension, key), nil) != nil
    ]


def comparison(
    before: list[mockcore.Row],
    after: list[mockcore.Row],
    from_id: str,
    to_id: str,
    subtree_of: int | None = None,
) -> JsonObject:
    """Return the comparison of two revisions, matched by lineage (WF-REV-0080, WF-DAT-0030).

    Read as ``listNodes`` reads a structure (#1193), whole or by the subtree of a task: the tree
    of the later, its nodes marked against the earlier, those it no longer bears at the place they
    had (``mockdiff``, C-361); the totals and the meta of the later, as ``listNodes`` gives them,
    the nodes removed not counted, its dates computed when it was marked, after which nothing
    redates it (WF-DAT-0020, #1404), or at the instant of the witness for a revision still in
    progress, as any reading of such a structure; and the deltas of the budgeted and of the
    re-estimated amounts, of the lines the reading retains, those removed with them.

    A line is retained by its parent in the later, where the marked tree renders it, and brings
    its whole delta, the later's amount less the earlier's, wherever it was: moved out of the
    subtree it counts nothing there, moved in it counts whole. A removed task reads the subtree it
    had, its nodes removed at their place: no line of the later, totals of none, the deltas of its
    removed lines (`amount_deltas`, `compareRevisions`).
    """
    nodes = mockdiff.marked(before, after)
    if subtree_of is None:
        answer = mockcore.whole(after)
    else:
        answer = mockcore.subtree(after, subtree_of)
        ids = {row.number: cast("str", row.node["node_id"]) for row in [*before, *after]}
        nodes = mockdiff.window(nodes, ids[subtree_of])
    kept = {cast("str", node["node_id"]) for node in nodes}
    marked = REVISIONS[to_id][1]
    scheduled_at = SCHEDULED_AT if marked is None else marked.instant

    def retained(rows: list[mockcore.Row]) -> list[mockcore.Row]:
        return [row for row in rows if row.node["node_id"] in kept]

    return {
        "from_revision_id": from_id,
        "to_revision_id": to_id,
        "items": cast("list[JsonValue]", nodes),
        "totals": answer["totals"],
        "meta": {
            **cast("JsonObject", answer["meta"]),
            "scheduled_at": mockcore.stamp(scheduled_at),
        },
        "amount_deltas": _deltas(retained(before), retained(after)),
    }


def by_differences(
    compared: JsonObject,
    before: list[mockcore.Row],
    after: list[mockcore.Row],
    asked: Collection[str],
) -> JsonObject:
    """Return a comparison read by its differences alone, the filter ``difference`` (#1398).

    The nodes whose mark is one of those asked, their ancestors with them (``mockdiff``); the
    totals and the meta those of the reading without the filter; the deltas those of the lines it
    retains, its rows ``before`` and ``after``.
    """
    nodes = mockdiff.differences(cast("list[JsonObject]", compared["items"]), asked)
    kept = {cast("str", node["node_id"]) for node in nodes}

    def retained(rows: list[mockcore.Row]) -> list[mockcore.Row]:
        return [row for row in rows if row.node["node_id"] in kept]

    return {
        **compared,
        "items": cast("list[JsonValue]", nodes),
        "amount_deltas": _deltas(retained(before), retained(after)),
    }


def _label(node: JsonObject) -> str:
    """Return the label of a node rendered whole, from its facet."""
    return cast("str", cast("JsonObject", node[cast("str", node["kind"])])["label"])


def _quoted(nodes: list[JsonObject]) -> str:
    """Name some nodes by their labels, as French lists them: « A », « B » et « C »."""
    return mocktext.listed([f"« {_label(node)} »" for node in nodes])


def _deltas_text(deltas: list[JsonObject], dimension: str) -> str:
    """Say the deltas of one dimension, each by the label of its key, in the order rendered."""
    return mocktext.listed(
        [
            f"{_amount(Decimal(cast('str', entry['budgeted_delta'])))} budgétés et "
            f"{_amount(Decimal(cast('str', entry['reestimated_delta'])))} réestimés pour "
            + (
                "ce qui ne relève d'aucun sous-projet"
                if entry["label"] is None
                else f"« {entry['label']} »"
            )
            for entry in deltas
            if entry["dimension"] == dimension
        ]
    )


def comparison_example(rows: list[mockcore.Row]) -> JsonObject:
    """Return the first example of compareRevisions: a window of the comparison, a subtree.

    The installation on site, read by ``subtree_of`` as ``listNodes`` reads the differential
    (``nodes_amendment``, #1193): it bears every mark — nodes added, removed, changed by their
    values and by their content alone —, at the size of the readings of ``listNodes``.
    """
    compared = comparison(offer_rows(), rows, OFFER, REFERENCE, N.INSTALLATION)
    nodes = cast("list[JsonObject]", compared["items"])
    deltas = cast("list[JsonObject]", compared["amount_deltas"])
    added, removed, changed, content = mockdiff.grouped(nodes)
    rerated = (
        ", lignes de main-d'œuvre que l'avenant ne désigne pas, qui gardent le budget de l'offre "
        "et sont réestimées au taux de 2026 de leur catégorie"
        if all(entry["changes"] == ["reestimated_amount"] for entry in changed)
        else ""
    )
    return mocktext.example(
        f"De l'offre v1.0, marquée le {_day(OFFER_MARKED.on)}, à la révision de référence, "
        f"marquée le {_day(AMENDMENT_MERGED.on)} par la fusion de l'avenant 1, rapprochées par "
        f"lignée et lues sur le sous-arbre « {_label(nodes[0])} » (subtree_of), comme `listNodes` "
        f"lit une structure : {mocktext.count(len(nodes))} nœuds dans l'ordre du plan, chacun "
        f"marqué — {len(added)} ajoutés, {_quoted(added)} ; {len(removed)} retirés et rendus à "
        f"leur place, en lecture seule, {_quoted(removed)} ; {len(changed)} modifiés par leurs "
        f"propres valeurs, {_quoted(changed)}{rerated} ; et {len(content)} tâches modifiées par "
        f"leur seul contenu, {_quoted(content)} (C-361). Les totaux sont ceux du sous-arbre dans "
        f"la référence, sans les nœuds retirés ; les écarts des montants budgétés et réestimés, "
        f"inflation comprise, ceux de ses lignes, retirées comprises, par nature — "
        f"{_deltas_text(deltas, 'cost_type')} — "
        f"et par sous-projet — {_deltas_text(deltas, 'subproject')} : l'offre n'en portait aucun, "
        f"les sous-projets ayant été déclarés après la commande, et ses lignes passent de "
        f"l'ensemble hors sous-projet au sien (WF-REV-0080, WF-DAT-0030, WF-PRJ-0050, #1193).",
        compared,
    )


VOLUME_FIELDS = ("kind", "task.label", "estimate_line.label")
"""What the screen of the comparison shows of a node besides its mark: its kind and its label."""


def comparison_volume() -> JsonObject:
    """Return the volume of compareRevisions: the comparison read whole, with `fields` (#1201).

    The offer and the reference over the whole structure, read without a filter as the screen of
    the comparison reads it, each node reduced to what the screen shows (`VOLUME_FIELDS`) besides
    what a marked tree always renders: the scale its bound of time is tried on (US-0500/L4).
    """
    compared = comparison(offer_rows(), reference_rows(), OFFER, REFERENCE)
    nodes = cast("list[JsonObject]", compared["items"])
    added, removed, changed, content = mockdiff.grouped(nodes)
    unchanged = len(nodes) - len(added) - len(removed) - len(changed) - len(content)
    deltas = cast("list[JsonObject]", compared["amount_deltas"])
    by_nature = [entry for entry in deltas if entry["dimension"] == "cost_type"]
    budgeted, reestimated = (
        sum((Decimal(cast("str", entry[key])) for entry in by_nature), Decimal(0))
        for key in ("budgeted_delta", "reestimated_delta")
    )
    read = mockcore.with_fields(nodes, VOLUME_FIELDS, mockdiff.ALWAYS)
    return mocktext.example(
        f"De l'offre v1.0 à la révision de référence, rapprochées par lignée sur toute la "
        f"structure du témoin aux volumes du §4.6.2, lue entière, sans filtre, comme l'écran de la "
        f"comparaison la lit, chaque nœud réduit par `fields` à ce que l'écran en montre — "
        f"{', '.join(VOLUME_FIELDS)} — et à ce qui est toujours rendu, sa marque comprise : "
        f"{mocktext.count(len(nodes))} nœuds dans l'ordre du plan, dont "
        f"{mocktext.count(len(added))} ajoutés, {mocktext.count(len(removed))} retirés et rendus "
        f"à leur place, {mocktext.count(len(changed))} modifiés par leurs propres valeurs, "
        f"{mocktext.count(len(content))} tâches modifiées par leur seul contenu et "
        f"{mocktext.count(unchanged)} inchangés (C-361). Les totaux et la meta sont ceux de "
        f"`listNodes` sur la référence entière, les écarts des montants budgétés et réestimés ceux "
        f"de toute la structure, {_amount(budgeted)} et {_amount(reestimated)} en tout "
        f"(WF-REV-0080, WF-DAT-0030, #1193, #1201).",
        {**compared, "items": cast("list[JsonValue]", read)},
    )


def comparison_differences(rows: list[mockcore.Row]) -> JsonObject:
    """Return the comparison read whole by its additions and its withdrawals alone (#1398).

    ``difference=added,removed``: two of the three marks, to say that they combine and that the
    ancestors come with the nodes retained, modified by their content; the totals those of the
    whole reference, the deltas those of the lines retained.
    """
    before = offer_rows()
    compared = by_differences(
        comparison(before, rows, OFFER, REFERENCE),
        before,
        rows,
        (mockdiff.ADDED, mockdiff.REMOVED),
    )
    nodes = cast("list[JsonObject]", compared["items"])
    deltas = cast("list[JsonObject]", compared["amount_deltas"])
    added, removed, changed, content = mockdiff.grouped(nodes)
    ancestors = [node for node in nodes if node in changed or node in content]
    return mocktext.example(
        f"De l'offre v1.0 à la révision de référence, rapprochées par lignée sur toute la "
        f"structure, lues par leurs seuls ajouts et retraits (difference=added,removed) : "
        f"{mocktext.count(len(nodes))} nœuds dans l'ordre du plan — {len(added)} ajoutés, "
        f"{_quoted(added)} ; {len(removed)} retirés et rendus à leur place, {_quoted(removed)} ; "
        f"et leurs ancêtres, {len(ancestors)} tâches modifiées par leur contenu, "
        f"{_quoted(ancestors)}, si bien que l'arbre filtré reste un arbre. Aucun nœud inchangé "
        f"n'est rendu, ni aucun nœud modifié qui ne soit l'ancêtre d'un ajout ou d'un retrait. "
        f"Les totaux sont ceux de "
        f"la référence entière, que `difference` ne restreint pas ; les écarts des montants "
        f"budgétés et réestimés, ceux des seules lignes retenues, par nature — "
        f"{_deltas_text(deltas, 'cost_type')} — et par sous-projet — "
        f"{_deltas_text(deltas, 'subproject')} (WF-REV-0080, C-361, #1398).",
        compared,
    )


def comparison_moved(rows: list[mockcore.Row]) -> JsonObject:
    """Return the comparison of a counterfactual offer, a task moved under another summary."""
    compared = comparison(moved_offer_rows(), rows, OFFER, REFERENCE, N.INSTALLATION)
    nodes = cast("list[JsonObject]", compared["items"])
    [moved] = [node for node in nodes if "parent" in cast("list[str]", node["changes"])]
    [summary] = [node for node in nodes if node["node_id"] == moved["parent_id"]]
    named = {row.number: row.label for row in rows}

    def said(node: JsonObject) -> str:
        return ", ".join(cast("list[str]", node["changes"]))

    return mocktext.example(
        f"Variante contrefactuelle : la comparaison de l'offre v1.0 à la révision de référence, "
        f"lue sur le même sous-arbre « {_label(summary)} » que le premier exemple, comme si "
        f"l'offre avait porté « {_label(moved)} » sous la récapitulative "
        f"« {named[N.CONTROL_STATION]} » et que l'avenant 1 l'avait déplacée sous "
        f"« {_label(summary)} », où la référence la porte : "
        f"{mocktext.count(len(nodes))} nœuds dans l'ordre du plan. La tâche déplacée est rendue "
        f"une fois, à sa nouvelle place, modifiée, son rattachement nommé parmi ce qui change "
        f"d'elle (`changes` : {said(moved)}) ; la récapitulative qui la reçoit, modifiée "
        f"({said(summary)}) ; les nœuds retirés, à leur place dans cette offre. Les totaux et "
        f"les écarts du devis sont ceux du premier exemple (WF-REV-0080, C-361).",
        compared,
    )


def examples() -> dict[str, JsonObject]:
    """Return the named examples of the comparison of the witness, by file name."""
    rows = reference_rows()
    core = mockcore.core(offer(CORE), OFFER_MARKED.on, offer_rates())
    identical = mocktext.count(len(core))
    return {
        "comparison.json": comparison_example(rows),
        "comparison_differences.json": comparison_differences(rows),
        "comparison_moved.json": comparison_moved(rows),
        "comparison_identical.json": mocktext.example(
            "Variante contrefactuelle : l'offre v1.0 comparée à elle-même, son cœur lu seul, "
            "comme si la structure ne portait que lui — les études, le lot « Poste de commande » "
            "et l'installation sur site —, lue entière, sans filtre, comme `listNodes` lit une "
            "structure. Identique par construction, la comparaison rend chaque nœud de l'arbre, "
            f"{identical}, inchangé, les totaux de l'offre et aucun écart de montant ; jamais un "
            "refus (WF-REV-0080, C-361, #1193).",
            comparison(core, core, OFFER, OFFER),
        ),
    }
