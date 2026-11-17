# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The comparison of the two marked revisions of the witness, and its examples (WF-REV-0080).

The revisions are described by ``wftools.mockhistory``; here they are compared: the tree of the
later, its nodes marked against the earlier by lineage (``wftools.mockdiff``, C-361), the deltas
of the estimate by nature of cost and by subproject, and the examples that say them — the window
of a subtree (``comparison``), the whole structure (``comparison_volume``), the counterfactual
variants with a task moved under another summary (``comparison_moved``) and an offer compared
with itself (``comparison_identical``), and the current revision compared with the reference it
was opened from (``comparison_current``, EP-27). Each node modified renders the values its base
carried and the deltas of its dates, durations and amounts, and each comparison the totals of its
base and their delta (``base_totals``, ``totals_delta``). Split from ``mockhistory`` to keep it
under the thousand lines (``wftools.sources``).
"""

from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockcore, mockdiff, mocktext, mockwitness
from wftools.mockdating import Amounts
from wftools.mockhistory import (
    CURRENT,
    OFFER,
    REFERENCE,
    REVISIONS,
    estimate_line,
    moved_offer_rows,
    nature,
    offer,
    offer_pricing,
    offer_rows,
    reference_rows,
)
from wftools.mockstructure import (
    JsonObject,
    JsonValue,
    decimal,
    labels,
    money,
)
from wftools.mockwitness import (
    AMENDMENT_MERGED,
    CORE,
    OFFER_MARKED,
    RISK_751_REVIEWED,
    SCHEDULED_AT,
    N,
    by_identifier,
    fixture,
    rewritten,
)
from wftools.mockwitnessrisks import reference

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


def _totals(rows: list[mockcore.Row]) -> JsonObject:
    """Return the totals of some rows as `NodeTotals` counts them: tasks, lines, hours, amounts."""
    lines = [row for row in rows if row.kind == mockcore.ESTIMATE_LINE]
    return {
        "task_count": sum(1 for row in rows if row.kind == mockcore.TASK),
        "estimate_line_count": len(lines),
        "hours": decimal(sum((row.hours for row in lines), Decimal(0))),
        **sum((row.amounts for row in lines), Amounts()).rendered(),
    }


TOTALS_COUNTS = ("task_count", "estimate_line_count")
TOTALS_AMOUNTS = ("base_amount", "budgeted_amount", "reestimated_amount")


def totals_delta(totals: JsonObject, base: JsonObject) -> JsonObject:
    """Return the signed delta of two totals, the revision read less the base (`NodeTotalsDelta`).

    The counts in units, the hours exact, the amounts to the cent.
    """
    delta: JsonObject = {
        key: cast("int", totals[key]) - cast("int", base[key]) for key in TOTALS_COUNTS
    }
    delta["hours"] = decimal(
        Decimal(cast("str", totals["hours"])) - Decimal(cast("str", base["hours"]))
    )
    for key in TOTALS_AMOUNTS:
        delta[key] = money(Decimal(cast("str", totals[key])) - Decimal(cast("str", base[key])))
    return delta


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
    re-estimated amounts, of the lines the reading retains, those removed with them. The totals of
    the base are those of the same nodes as the base bears them, removed ones included, those
    added left out (``base_totals``), and their delta signed (``totals_delta``, EP-27).

    A line is retained by its parent in the later, where the marked tree renders it, and brings
    its whole delta, the later's amount less the earlier's, wherever it was: moved out of the
    subtree it counts nothing there, moved in it counts whole. A removed task reads the subtree it
    had, its nodes removed at their place: no line of the later, totals of none, the deltas of its
    removed lines (`amount_deltas`, `compareRevisions`).
    """
    nodes = mockdiff.marked(before, after, compared=True)
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

    totals = cast("JsonObject", answer["totals"])
    base_totals = _totals(retained(before))
    return {
        "from_revision_id": from_id,
        "to_revision_id": to_id,
        "items": cast("list[JsonValue]", nodes),
        "totals": totals,
        "base_totals": base_totals,
        "totals_delta": totals_delta(totals, base_totals),
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
    totals, those of the base and their delta, and the meta those of the reading without the
    filter; the deltas those of the lines it retains, its rows ``before`` and ``after``.
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


def _totals_text(compared: JsonObject) -> str:
    """Say the totals of the base and their delta, budgeted and re-estimated (`base_totals`)."""
    base = cast("JsonObject", compared["base_totals"])
    delta = cast("JsonObject", compared["totals_delta"])

    def said(totals: JsonObject) -> str:
        return (
            f"{_amount(Decimal(cast('str', totals['budgeted_amount'])))} budgétés et "
            f"{_amount(Decimal(cast('str', totals['reestimated_amount'])))} réestimés"
        )

    return f"{said(base)} (base_totals), un écart de {said(delta)} (totals_delta)"


def comparison_example(rows: list[mockcore.Row]) -> JsonObject:
    """Return the first example of compareRevisions: a window of the comparison, a subtree.

    The installation on site, read by ``subtree_of`` as ``listNodes`` reads the differential
    (``nodes_amendment``, #1193): it bears every mark — nodes added, removed, changed by their
    values —, the values of the base and their deltas, at the size of the readings of
    ``listNodes``.
    """
    compared = comparison(offer_rows(), rows, OFFER, REFERENCE, N.INSTALLATION)
    nodes = cast("list[JsonObject]", compared["items"])
    deltas = cast("list[JsonObject]", compared["amount_deltas"])
    added, removed, changed, content = mockdiff.grouped(nodes)
    lines = [node for node in changed if node["kind"] == mockcore.ESTIMATE_LINE]
    tasks = [node for node in changed if node["kind"] == mockcore.TASK]
    relinked = [node for node in tasks if "predecessors" in cast("JsonObject", node["base"])]
    rerated = (
        " : lignes de main-d'œuvre que l'avenant ne désigne pas, qui gardent le budget de "
        "l'offre, sont réestimées au taux de 2026 de leur catégorie — d'une année de référence à "
        "l'autre, le réestimé vient aussi des taux projetés ou mis à jour (WF-REV-0060, #1754) — "
        "et changent de sous-projet, leur montant aux taux de l'année de référence avec eux "
        "(`changes` : reestimated_amount, subproject, other ; #1751)"
        if all(entry["changes"] == ["reestimated_amount", "subproject", "other"] for entry in lines)
        else ""
    )
    own = (
        f" ; et {len(content)} tâches modifiées par leur seul contenu, {_quoted(content)}"
        if content
        else ""
    )
    return mocktext.example(
        f"De l'offre v1.0, marquée le {_day(OFFER_MARKED.on)}, à la révision de référence, "
        f"marquée le {_day(AMENDMENT_MERGED.on)} par la fusion de l'avenant 1, rapprochées par "
        f"lignée et lues sur le sous-arbre « {_label(nodes[0])} » (subtree_of), comme `listNodes` "
        f"lit une structure : {mocktext.count(len(nodes))} nœuds dans l'ordre du plan, chacun "
        f"marqué — {len(added)} ajoutés, {_quoted(added)} ; {len(removed)} retirés et rendus à "
        f"leur place, en lecture seule, {_quoted(removed)} ; {len(lines)} lignes modifiées par "
        f"leurs propres valeurs, {_quoted(lines)}{rerated} ; {len(tasks)} tâches modifiées par "
        f"leurs montants, ceux de leurs lignes (`changes` : other), {_quoted(tasks)}, "
        f"{_quoted(relinked)} aussi par son prédécesseur, que la réception usine ajoutée par "
        f"l'avenant remplace{own} (C-361). Chaque "
        f"nœud modifié rend les valeurs que l'offre portait de ce qui diffère (base) et l'écart "
        f"de chacune de ses dates, durées et montants, la référence moins l'offre (deltas) ; un "
        f"nœud ajouté ou retiré n'en rend aucun. Les totaux sont ceux du sous-arbre dans la "
        f"référence, sans les nœuds retirés ; ceux de la base, les mêmes nœuds dans l'offre, "
        f"retirés compris et ajoutés exclus, {_totals_text(compared)} ; les écarts des montants "
        f"budgétés et réestimés, inflation comprise, ceux de ses lignes, retirées comprises, par "
        f"nature — "
        f"{_deltas_text(deltas, 'cost_type')} — "
        f"et par sous-projet — {_deltas_text(deltas, 'subproject')} : l'offre n'en portait aucun, "
        f"les sous-projets ayant été déclarés après la commande, et ses lignes passent de "
        f"l'ensemble hors sous-projet au sien : chacune compte sous la clé qu'elle porte dans "
        f"chaque révision, son montant entier en moins hors sous-projet et en plus sous le sien, "
        f"même inchangé, si bien que la somme des écarts par sous-projet égale celle par nature "
        f"(WF-REV-0080, WF-DAT-0030, WF-PRJ-0050, #1193, #1751).",
        compared,
    )


def comparison_current() -> JsonObject:
    """Return the current revision compared with the reference it was opened from (EP-27).

    The revision read in progress, dated at the instant of the witness as any reading of such a
    structure; the reference for base, marked; the window of the first example, the installation
    on site (``subtree_of``). What the review of the remaining to commit wrote on its lines since
    the reference was marked marks them, and the provision of the risk 753, dismissed the day
    after, is removed (WF-RIS-0010).
    """
    compared = comparison(reference_rows(), mockcore.current(), REFERENCE, CURRENT, N.INSTALLATION)
    nodes = cast("list[JsonObject]", compared["items"])
    deltas = cast("list[JsonObject]", compared["amount_deltas"])
    _, removed, changed, content = mockdiff.grouped(nodes)
    lines = [node for node in changed if node["kind"] == mockcore.ESTIMATE_LINE]
    tasks = [node for node in changed if node["kind"] == mockcore.TASK]
    previous = sorted(
        {
            key
            for node in lines
            for key in cast("JsonObject", cast("JsonObject", node["base"])["estimate_line"])
        }
    )
    return mocktext.example(
        f"La révision en cours du témoin, ouverte le {_day(RISK_751_REVIEWED.on)} et lue "
        f"aujourd'hui, comparée à la révision de référence dont elle est issue, marquée le "
        f"{_day(AMENDMENT_MERGED.on)}, rapprochées par lignée et lues sur le sous-arbre "
        f"« {_label(nodes[0])} » (subtree_of), comme le premier exemple : la révision lue est en "
        f"cours, la base marquée. {mocktext.count(len(nodes))} nœuds dans l'ordre du plan — "
        f"{len(removed)} retiré et rendu à sa place, en lecture seule, {_quoted(removed)}, le "
        f"risque 753 ayant été écarté à l'ouverture de la révision en cours ; "
        f"{len(lines)} lignes modifiées par ce que la revue du reste à engager y a écrit depuis, "
        f"le reste à engager précédent, nul dans la base ({', '.join(previous)} ; `changes` : "
        f"other), {_quoted(lines)} ; {len(tasks)} tâches modifiées par leurs montants, sans la "
        f"provision retirée, {_quoted(tasks)} ; et {len(content)} tâche modifiée par son seul "
        f"contenu, {_quoted(content)} (C-361). Chaque nœud modifié rend les valeurs de la base "
        f"de ce qui diffère (base) et l'écart de ses dates, durées et montants, la révision en "
        f"cours moins la référence, nul quand l'une des deux valeurs l'est (deltas). Les totaux "
        f"sont ceux du sous-arbre aujourd'hui, ceux de la base {_totals_text(compared)} ; les "
        f"écarts des montants, par nature — {_deltas_text(deltas, 'cost_type')} — et par "
        f"sous-projet — {_deltas_text(deltas, 'subproject')}. Les dates sont calculées à "
        f"l'instant du témoin, comme toute lecture d'une révision en cours (WF-REV-0080, "
        f"WF-DAT-0020, WF-DAT-0030, EP-27).",
        compared,
    )


PLANNING_DELAY_DAYS = 2
"""The days the design file is lengthened by in the variant of the planning."""
PLANNING_EXTRA_HOURS = Decimal(10)
"""The hours the labour line of the wiring is raised by in that variant."""


def _planned(task: mockwitness.Task) -> mockwitness.Task:
    """Return a task of the reference as the variant of the planning reads it, if it changes.

    The design file lasts two more days, the wiring of the cabinets bears ten more hours on its
    labour line and no longer bears its provision, which the risk dismissed took away.
    """
    if task.number == N.DESIGN_FILE:
        return replace(task, days=task.days + PLANNING_DELAY_DAYS)
    if task.number == N.WIRING:
        return replace(
            task,
            lines=tuple(
                replace(line, hours=cast("Decimal", line.hours) + PLANNING_EXTRA_HOURS)
                if line.number == N.LABOUR
                else line
                for line in task.lines
                if line.number != N.PROVISION
            ),
        )
    return task


def comparison_planning() -> JsonObject:
    """Return the variant where a task finishes later than its base says (EP-27, #3778).

    The core alone, the reference as marked for base and, for the revision read, the same
    reference, read the same day, where three things changed: the design file lasts two more
    days, so that its finish is shifted from its base's (``base.task.finish``,
    ``deltas.task.finish``), the labour line of
    the wiring bears ten more hours, which changes its amounts and those of its task and summary,
    and the line of provision of the wiring is no longer there, removed and rendered at its place.
    The installation on site, every node of it, and the nodes of the studies and of the control
    station this leaves alone are unchanged: whole branches, summary included, without a
    difference, for the screen to fold them.
    """
    base = mockcore.core(reference(CORE), AMENDMENT_MERGED.on)
    later = mockcore.core(rewritten(reference(CORE), _planned), AMENDMENT_MERGED.on)
    compared = comparison(base, later, REFERENCE, CURRENT)
    nodes = cast("list[JsonObject]", compared["items"])
    _, removed, _, _ = mockdiff.grouped(nodes)
    modified = [node for node in nodes if node["difference"] == mockdiff.MODIFIED]
    unchanged = [node for node in nodes if node["difference"] == mockdiff.UNCHANGED]
    [delayed] = [node for node in nodes if "dates" in cast("list[str]", node["changes"])]
    summaries = [
        node
        for node in unchanged
        if node["kind"] == mockcore.TASK and cast("JsonObject", node["task"])["is_summary"]
    ]
    said = ", ".join(cast("list[str]", delayed["changes"]))
    finish_delta = cast("JsonObject", cast("JsonObject", delayed["deltas"])["task"])["finish"]
    return mocktext.example(
        f"Variante contrefactuelle : la révision en cours, comparée à la révision de référence "
        f"marquée le {_day(AMENDMENT_MERGED.on)}, sur le cœur du témoin seul — "
        f"{mocktext.count(len(nodes))} nœuds dans l'ordre du plan —, comme si le dossier de "
        f"conception durait {PLANNING_DELAY_DAYS} jours de plus : « {_label(delayed)} » finit "
        f"plus tard que sa base ne le dit (`changes` : {said} ; "
        f"`base.task.finish`, `deltas.task.finish`), son écart de fin de "
        f"{finish_delta} jours ; la ligne de "
        f"provision du câblage n'y est plus, {_quoted(removed)} rendue à sa place, en lecture "
        f"seule, sans base ; la ligne de raccordement des borniers porte {PLANNING_EXTRA_HOURS} "
        f"heures de plus, donc un montant modifié, de même que ceux de sa tâche et de sa "
        f"récapitulative ; les ancêtres des nœuds modifiés le sont aussi, {len(modified)} nœuds "
        f"modifiés en tout, {_quoted(modified)}"
        f". {mocktext.count(len(unchanged))} nœuds inchangés, sans base ni écart, dont "
        f"la récapitulative {_quoted(summaries)}, sa branche entière sans écart ; la lecture se "
        f"fait le jour de la base, si bien que nul avancement n'en diffère "
        f"(WF-REV-0080, WF-IHM-0160, C-361, EP-27).",
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
    read = mockdiff.read_with_fields(nodes, VOLUME_FIELDS)
    # A count of none is not written: no task of the volume is modified by its content alone.
    by_content = (
        f"{mocktext.count(len(content))} tâches modifiées par leur seul contenu et "
        if content
        else "et "
    )
    return mocktext.example(
        f"De l'offre v1.0 à la révision de référence, rapprochées par lignée sur toute la "
        f"structure du témoin aux volumes du §4.6.2, lue entière, sans filtre, comme l'écran de la "
        f"comparaison la lit, chaque nœud réduit par `fields` à ce que l'écran en montre — "
        f"{', '.join(VOLUME_FIELDS)} — et à ce qui est toujours rendu, sa marque comprise, ses "
        f"valeurs de base et ses écarts réduits de même, vides quand aucun libellé ne change : "
        f"{mocktext.count(len(nodes))} nœuds dans l'ordre du plan, dont "
        f"{mocktext.count(len(added))} ajoutés, {mocktext.count(len(removed))} retirés et rendus "
        f"à leur place, {mocktext.count(len(changed))} modifiés par leurs propres valeurs — une "
        f"tâche par ses montants, ceux de ses lignes —, {by_content}"
        f"{mocktext.count(unchanged)} inchangés (C-361). Les totaux et la meta sont ceux de "
        f"`listNodes` sur la référence entière, ceux de la base ceux de l'offre entière, "
        f"{_totals_text(compared)} ; les écarts des montants budgétés et réestimés ceux "
        f"de toute la structure, {_amount(budgeted)} et {_amount(reestimated)} en tout "
        f"(WF-REV-0080, WF-DAT-0030, #1193, #1201).",
        {**compared, "items": cast("list[JsonValue]", read)},
    )


def comparison_differences(rows: list[mockcore.Row]) -> JsonObject:
    """Return the comparison read whole by its additions and its withdrawals alone (#1398).

    ``difference=added,removed``: two of the three marks, to say that they combine and that the
    ancestors come with the nodes retained, modified; the totals, those of the base and their
    delta those of the whole reference and offer, the deltas those of the lines retained.
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
        f"et leurs ancêtres, {len(ancestors)} tâches modifiées, par leur contenu et par leurs "
        f"montants, {_quoted(ancestors)}, si bien que l'arbre filtré reste un arbre. Aucun nœud "
        f"inchangé n'est rendu, ni aucun nœud modifié qui ne soit l'ancêtre d'un ajout ou d'un "
        f"retrait. Les totaux sont ceux de la référence entière, ceux de la base ceux de l'offre "
        f"entière, que `difference` ne restreint pas, {_totals_text(compared)} ; les écarts des "
        f"montants budgétés et réestimés, ceux des seules lignes retenues, par nature — "
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
        f"({said(summary)}) ; les nœuds retirés, à leur place dans cette offre. Les totaux, ceux "
        f"de la base et leur écart, et les écarts du devis sont ceux du premier exemple "
        f"(WF-REV-0080, C-361).",
        compared,
    )


def examples() -> dict[str, JsonObject]:
    """Return the named examples of the comparison of the witness, by file name."""
    rows = reference_rows()
    core = mockcore.core(offer(CORE), OFFER_MARKED.on, offer_pricing())
    identical = mocktext.count(len(core))
    return {
        "comparison.json": comparison_example(rows),
        "comparison_current.json": comparison_current(),
        "comparison_differences.json": comparison_differences(rows),
        "comparison_moved.json": comparison_moved(rows),
        "comparison_planning.json": comparison_planning(),
        "comparison_identical.json": mocktext.example(
            "Variante contrefactuelle : l'offre v1.0 comparée à elle-même, son cœur lu seul, "
            "comme si la structure ne portait que lui — les études, le lot « Poste de commande » "
            "et l'installation sur site —, lue entière, sans filtre, comme `listNodes` lit une "
            "structure. Identique par construction, la comparaison rend chaque nœud de l'arbre, "
            f"{identical}, inchangé, sans valeur de base ni écart, les totaux de l'offre, ceux "
            "de la base égaux, un écart de totaux nul et aucun écart de montant ; jamais un refus "
            "(WF-REV-0080, C-361, #1193).",
            comparison(core, core, OFFER, OFFER),
        ),
    }
