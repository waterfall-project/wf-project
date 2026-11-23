# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The own estimate of the risk 751 read as a differential of the main structure (US-3070/L2).

EP-30 makes the own estimate of a risk a differential of the main structure (WF-RIS-0030): whole in
the current revision, a copy of the main structure with its base, and pruned at the marking to what
it designates. The own estimate of the rework of the wiring, the structure 204 of the current
revision 102, is the main structure as today, without its provision lines — a risk's own estimate
bears none —, its wiring reworked: the « Reprise du câblage des armoires » added under the control
station after the wiring of the cabinets, subcontracted, which the commissioning now follows too;
the charge of the connection of the terminal blocks carried from 12.5 to 25 hours; the design
file, completed, abandoned, as the main structure would refuse. Its severity is that of the
register, 1,250,000.00 (``mockwitnessrisks``): the subcontracted rework is priced so that the gap
of the re-estimated totals of the own estimate and of its base is that severity, whatever the
other designations add or save (#4585, « à gravité égale »). Its nodes have identifiers of their
own (``own_id``): the node 5nn of the main structure is 20nn in it, a node drawn has its own
family; they share the lineages of the main structure's, by which the reading marks them (#421).

What the examples say of it is read from this description, never written by hand:

- ``nodes_risk_estimate``, the whole own estimate read by its differences alone, « Écarts
  seulement » — the first example served at its address (``wftools.mock``, #4409);
- ``nodes_risk_estimate_pruned``, a declared variant: the current revision marked today, the own
  estimate, whole and up to date, pruned to what it designates, its ancestors unchanged;
- ``structure_rebase_report_risk``: the suite of entries made today on the main structure that
  ``wftools.mockrebase`` declares puts it out of date, and the report of its update presents them,
  the charge of the connection of the terminal blocks kept (`kept`, ``fields``), with the severity
  and the provision the update would record; ``structure_rebase_report_risk_refused``, its refused
  variant, the main structure having besides made the wiring of the cabinets follow the
  commissioning, which closes a loop through the rework; ``structure_rebased_risk``, the own
  estimate once updated;
- ``structure_recomposed``, a declared variant: the revision 104 opened after that marking takes
  the own estimate over pruned, as the structure 209, and its recomposition makes it whole;
  ``structure_rebase_risk_pruned_refused``, the report of its update asked before, refused by
  ``own_estimate_whole``; ``structure_recompose_revision_marked``, the recomposition asked on the
  marked revision, refused by ``revision_draft``.

The occurrence of 751 (``mockriskwrites``) still reads the own estimate EP-08 described,
``mockwitness.REWORK_ESTIMATE``, as the loader of the witness does: their forms are rewritten by
the lots that rewrite them (US-3080, US-3100, US-3150).

Nothing here reads the clock or draws at random, nor a file the same command writes.
"""

from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from typing import TYPE_CHECKING, cast

from wftools import mockamendment, mockcore, mockdiff, mockrebase, mocktext
from wftools.mockcorrelations import correlation
from wftools.mockids import OWN_ESTIMATE_NODES, identifier, universe
from wftools.mocknonworking import CREATED_LABEL, CREATED_MANUAL
from wftools.mockstructure import described, money
from wftools.mockwitness import (
    GENERATED,
    PAYMENT_DELAY,
    SUBCONTRACTING,
    Line,
    Link,
    N,
    Task,
    fixture,
    lineage_id,
    rewritten,
)
from wftools.mockwitnessrisks import REWORK
from wftools.mockwrites import LABOUR_HOURS, RENAMED

if TYPE_CHECKING:
    from collections.abc import Iterable

    from wftools.mockstructure import JsonObject, JsonValue

STRUCTURE = 204
LABEL = "Risque de reprise du câblage"
"""The own estimate of the rework of the wiring in the current revision, as `structures` lists
it."""

OWN_OFFSET = 1500
"""What separates the identifier of a node of the own estimate from the number of its node in the
main structure: the node 5nn is 20nn in the own estimate (#421)."""

DESIGNED_HOURS = Decimal(25)
"""The charge of the connection of the terminal blocks in the own estimate: 25 hours, where the
main structure carries 12.5."""

ABANDONED = N.DESIGN_FILE
"""The task the own estimate abandons: the design file, completed, which no task follows."""

REWORK_DAYS = 15
SEVERITY = REWORK.last.severity
PROBABILITY = REWORK.last.probability
"""The duration of the rework the own estimate adds, the severity and the probability of 751."""

MARKED_REVISION, NEXT_REVISION, NEXT_STRUCTURE = 102, 104, 209
"""The declared variant: the current revision marked today, the revision opened after it, and the
copy of the own estimate there (#287)."""

RELINKING_WRITES = 2
"""The writes of the refused variant besides those of ``mockrebase``: the factory acceptance no
longer follows the wiring, and the wiring follows the commissioning."""

CYCLE = (N.WIRING, N.CABINETS_REWORK, N.COMMISSIONING)
"""The loop the refused variant closes in the own estimate, each task preceding the next."""


def own_id(number: int) -> str:
    """Return the identifier of the node of this number in the own estimate: 20nn for 5nn."""
    if number < GENERATED:
        return universe(number + OWN_OFFSET)
    return identifier(OWN_ESTIMATE_NODES, number - GENERATED)


@cache
def base() -> tuple[Task, ...]:
    """Return the main structure as the own estimate copies it: no attachment, no provision."""

    def copied(task: Task) -> Task:
        lines = tuple(line for line in task.lines if not line.is_provision)
        return replace(task, bears=None, inscriptions=(), lines=lines)

    return rewritten(described(), copied)


def designated(rework: Decimal) -> tuple[Task, ...]:
    """Return the own estimate described, its subcontracted rework priced at the amount given."""
    added = Task(
        N.CABINETS_REWORK,
        "Reprise du câblage des armoires",
        days=REWORK_DAYS,
        links=(Link(N.WIRING),),
        lines=(
            Line(
                N.CABINETS_REWORK_LINE,
                "Recâblage des armoires",
                SUBCONTRACTING,
                unit=rework,
                payment_delay_days=PAYMENT_DELAY,
            ),
        ),
    )
    budgets = {row.number: row.amounts.budgeted for row in rows(base())}

    def change(task: Task) -> Task:
        if task.number == N.CONTROL_STATION:
            children: list[Task] = []
            for child in task.children:
                children.append(child)
                if child.number == N.WIRING:
                    children.append(added)
            return replace(task, children=tuple(children))
        if task.number == N.WIRING:
            lines = tuple(
                replace(line, hours=DESIGNED_HOURS, budgeted=budgets[line.number])
                if line.number == N.LABOUR
                else line
                for line in task.lines
            )
            return replace(task, lines=lines)
        if task.number == N.COMMISSIONING:
            return replace(task, links=(*task.links, Link(N.CABINETS_REWORK)))
        return replace(
            task, children=tuple(each for each in task.children if each.number != ABANDONED)
        )

    return rewritten(base(), change)


def rows(roots: Iterable[Task]) -> list[mockcore.Row]:
    """Return a structure read today as an own estimate reads it: a completed task's lines open."""
    return mockcore.opened(mockcore.current(roots))


def _reestimated(roots: Iterable[Task]) -> Decimal:
    """Return the re-estimated total of a structure read today."""
    totals = cast("JsonObject", mockcore.whole(rows(roots))["totals"])
    return Decimal(cast("str", totals["reestimated_amount"]))


@cache
def rework_amount() -> Decimal:
    """Return the amount of the rework that gives the own estimate the severity of the register.

    The gap of the totals is linear in it: the rework, in 2026, is priced at its unit amount.
    """
    gap = _reestimated(designated(Decimal(0))) - _reestimated(base())
    amount = SEVERITY - gap
    if _reestimated(designated(amount)) - _reestimated(base()) != SEVERITY:
        message = "the rework is not priced at its unit amount: the severity is not kept"
        raise ValueError(message)
    return amount


@cache
def own_estimate() -> tuple[Task, ...]:
    """Return the own estimate described, at the severity of the register."""
    return designated(rework_amount())


@cache
def marked() -> list[JsonObject]:
    """Return the whole own estimate read today, marked against its base, under its own ids."""
    return mockamendment.marked(own_estimate(), base=base(), renamed=own_id)


def nodes_risk_estimate() -> JsonObject:
    """Return what listNodes answers of the whole own estimate read by its differences alone.

    ``difference=added,removed,modified``: what it designates, its ancestors with it; the totals
    those of the whole own estimate, which the filter does not restrict (`NodeTotals`).
    """
    return {
        **mockcore.whole(rows(own_estimate())),
        "items": cast("list[JsonValue]", mockdiff.differences(marked(), mockdiff.DIFFERENCES)),
    }


SUMMARISED = frozenset({"dates", "duration", "progress"})
"""What a summary task takes from its subordinates: a change of it is not a designation."""


def _designations() -> set[str]:
    """Return the nodes the own estimate designates: added, removed, or modified by their values.

    A summary whose dates move with what it holds is not designated: it is an ancestor.
    """
    found: set[str] = set()
    for node in marked():
        changes = set(cast("list[str]", node["changes"]))
        task = cast("JsonObject | None", node.get("task"))
        if task is not None and task["is_summary"]:
            changes -= SUMMARISED
        if node["difference"] in {mockdiff.ADDED, mockdiff.REMOVED} or changes:
            found.add(cast("str", node["node_id"]))
    return found


def _link_ends() -> set[str]:
    """Return the ends of the links the own estimate adds: the tasks on either side of each."""
    was = {
        row.number: {link.predecessor for link in _links(row.number, base())}
        for row in rows(base())
    }
    ends: set[int] = set()
    for task in _tasks(own_estimate()):
        added = {link.predecessor for link in task.links} - was.get(task.number, set())
        if added:
            ends |= {task.number, *added}
    return {own_id(number) for number in ends}


def _tasks(roots: Iterable[Task]) -> list[Task]:
    """Return every task of a description, in the order of the plan."""
    found: list[Task] = []

    def walk(task: Task) -> None:
        found.append(task)
        for child in task.children:
            walk(child)

    for root in roots:
        walk(root)
    return found


def _links(number: int, roots: Iterable[Task]) -> tuple[Link, ...]:
    """Return the links of a task of a description, none for a node that is not one of its tasks."""
    return next((task.links for task in _tasks(roots) if task.number == number), ())


def pruned_nodes() -> list[JsonObject]:
    """Return the nodes a marking keeps of the own estimate, as its pruned reading renders them.

    What it designates, the ends of the links it adds and their ancestors; a node it does not
    designate is rendered unchanged, the rows and the ranks counting the pruned tree, a link to a
    node it no longer bears left out (`NodeDifference`).
    """
    nodes = marked()
    parents = {cast("str", node["node_id"]): node["parent_id"] for node in nodes}
    designations = _designations()
    kept: set[str] = set()
    for start in designations | _link_ends():
        at: str | None = start
        while at is not None and at not in kept:
            kept.add(at)
            at = cast("str | None", parents[at])
    rendered = [dict(node) for node in nodes if node["node_id"] in kept]
    rows_of = {cast("str", node["node_id"]): at for at, node in enumerate(rendered, start=1)}
    ranks: dict[JsonValue, int] = {}
    for node in rendered:
        ranks[node["parent_id"]] = ranks.get(node["parent_id"], 0) + 1
        node["position"] = ranks[node["parent_id"]]
        node["row_number"] = rows_of[cast("str", node["node_id"])]
        if node["node_id"] not in designations:
            node["difference"], node["changes"] = mockdiff.UNCHANGED, []
        if "predecessors" in node:
            node["predecessors"] = [
                {
                    **link,
                    "predecessor_row_number": rows_of[link["predecessor_node_id"]],
                }
                for link in cast("list[JsonObject]", node["predecessors"])
                if link["predecessor_node_id"] in rows_of
            ]
    return rendered


def nodes_risk_estimate_pruned() -> JsonObject:
    """Return what listNodes answers of the own estimate pruned by a marking: what it designates.

    The totals are those of the pruned structure: the lines it bears, not the one it abandons.
    """
    return {**mockcore.whole(pruned_rows()), "items": cast("list[JsonValue]", pruned_nodes())}


def pruned_rows() -> list[mockcore.Row]:
    """Return the rows the pruned own estimate bears: what it keeps, not what it abandons."""
    numbers = {
        cast("str", node["node_id"])
        for node in pruned_nodes()
        if node["difference"] != mockdiff.REMOVED
    }
    return [row for row in rows(own_estimate()) if own_id(row.number) in numbers]


# --- The update -----------------------------------------------------------------------------------


def _labour_rate() -> Decimal:
    """Return the hourly rate of the connection of the terminal blocks in the main structure."""
    [row] = [row for row in mockcore.current() if row.number == N.LABOUR]
    amount = Decimal(
        cast("str", cast("JsonObject", row.node["estimate_line"])["reestimated_amount"])
    )
    return amount / row.hours


def updated_severity() -> Decimal:
    """Return the severity the update records on the project of today, after the writes declared.

    The writes of ``mockrebase`` reach the own estimate and its new base alike, but the charge of
    the connection, which the own estimate keeps at its hours while the base takes those of the main
    structure: the gap moves by that charge alone.
    """
    [line] = [row for row in mockcore.current() if row.number == N.LABOUR]
    return SEVERITY - (LABOUR_HOURS - line.hours) * _labour_rate()


def provision(severity: Decimal) -> Decimal:
    """Return the provision of a severity: weighted by the probability, to the cent, at least 0."""
    return max(Decimal(0), (severity * PROBABILITY).quantize(Decimal("0.01"), ROUND_HALF_UP))


def _counters() -> tuple[int, int]:
    """Return the counters the report reads: the main structure after its writes, the estimate."""
    main, _ = mockrebase.counters()
    return main, cast("int", listed()["lock_version"])


def report() -> JsonObject:
    """Return what getStructureRebaseReport answers of the own estimate of 751 out of date."""
    labels = mockrebase.node_labels()
    main, own = _counters()
    severity = updated_severity()
    difference = mockrebase.difference
    differences: list[JsonValue] = [
        difference("added", "task", CREATED_MANUAL, CREATED_LABEL, []),
        difference("updated", "task", N.WIRING, RENAMED, ["label"]),
        difference(
            "updated",
            "estimate_line",
            N.COMMISSIONING_LINE,
            labels[N.COMMISSIONING_LINE],
            ["hours"],
        ),
        difference("removed", "estimate_line", N.BLOCKS, labels[N.BLOCKS], []),
        difference("kept", "estimate_line", N.LABOUR, labels[N.LABOUR], ["hours"]),
    ]
    return {
        "main_structure_lock_version": main,
        "structure_lock_version": own,
        "differences": differences,
        "refusals": [],
        "severity": money(severity),
        "provision_amount": money(provision(severity)),
    }


def _labels() -> dict[int, str]:
    """Return the labels of the nodes of the own estimate after the update, by their number."""
    labels = mockrebase.node_labels()
    labels[N.WIRING] = RENAMED
    labels[N.CABINETS_REWORK] = "Reprise du câblage des armoires"
    return labels


def cycle() -> JsonObject:
    """Return the loop the refused variant closes, each task by its node in the own estimate."""
    labels = _labels()
    return {"cycle": [{"node_id": own_id(number), "label": labels[number]} for number in CYCLE]}


def report_refused() -> JsonObject:
    """Return the report of the refused variant: the links the main structure changes, the loop.

    A loop leaves the dates of the own estimate uncomputed: no severity is recorded, and none is
    announced.
    """
    labels = _labels()
    applicable = report()
    links: list[JsonValue] = [
        {
            "change": "added",
            "target": "link",
            "lineage_id": lineage_id(N.WIRING),
            "label": RENAMED,
            "predecessor_label": labels[N.COMMISSIONING],
            "fields": [],
        },
        {
            "change": "removed",
            "target": "link",
            "lineage_id": lineage_id(N.FACTORY_ACCEPTANCE),
            "label": labels[N.FACTORY_ACCEPTANCE],
            "predecessor_label": RENAMED,
            "fields": [],
        },
    ]
    differences = cast("list[JsonValue]", applicable["differences"])
    return {
        **applicable,
        "main_structure_lock_version": cast("int", applicable["main_structure_lock_version"])
        + RELINKING_WRITES,
        "differences": [*differences[:1], *links, *differences[1:]],
        "refusals": [{"code": "LINK_CYCLE", "params": cycle()}],
        "severity": None,
        "provision_amount": None,
    }


def listed() -> JsonObject:
    """Return the own estimate of 751 as `structures` lists it."""
    [own] = [
        each
        for each in cast("list[JsonObject]", fixture("structures"))
        if each["structure_id"] == universe(STRUCTURE)
    ]
    return own


def rebased() -> JsonObject:
    """Return the own estimate once updated: up to date, its counter advanced by the update."""
    own = listed()
    return {**own, "lock_version": cast("int", own["lock_version"]) + 1}


def recomposed() -> JsonObject:
    """Return the copy of the own estimate in the revision 104 once recomposed: whole, up to date.

    The copy taken over pruned has the counter of its copy, 1; the recomposition advances it.
    """
    return {
        **listed(),
        "structure_id": universe(NEXT_STRUCTURE),
        "revision_id": universe(NEXT_REVISION),
        "lock_version": 2,
    }


NEXT_MAIN = 210


def next_structures() -> list[JsonObject]:
    """Return the structures of the revision 104 opened after the marking, the own estimate pruned.

    The main structure is the current one, taken over; the own estimate of 751 is the copy
    ``recomposed`` makes whole, still pruned: its entry and its update wait for its recomposition,
    which is the command it lists.
    """
    [main] = [
        each for each in cast("list[JsonObject]", fixture("structures")) if each["kind"] == "main"
    ]
    waiting: list[JsonValue] = ["own_estimate_whole"]
    commands: list[JsonValue] = [
        {"command": name, "is_available": False, "missing_conditions": waiting}
        for name in ("edit_planning", "edit_estimate", "rebase")
    ]
    commands.append({"command": "recompose", "is_available": True, "missing_conditions": []})
    own: JsonObject = {
        **recomposed(),
        "is_pruned": True,
        "is_up_to_date": True,
        "available_commands": commands,
        "lock_version": 1,
    }
    return [
        {
            **main,
            "structure_id": universe(NEXT_MAIN),
            "revision_id": universe(NEXT_REVISION),
        },
        own,
    ]


def start_read_only() -> JsonObject:
    """Return what updateCostStructure answers to a planning start sent on an own estimate."""
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [{"pointer": "/planning_start_on", "code": "FIELD_READ_ONLY"}],
        "correlation_id": correlation("structure_update_own_start_read_only"),
    }


def examples() -> dict[str, JsonObject]:
    """Return the examples of the own estimate of 751 read as a differential, by file name."""
    labels = mockrebase.node_labels()
    whole = nodes_risk_estimate()
    pruned = nodes_risk_estimate_pruned()
    read, refused = report(), report_refused()
    main, own = _counters()
    severity, rework = mocktext.amount(SEVERITY), mocktext.amount(rework_amount())
    hours = mocktext.amount(DESIGNED_HOURS, 0)
    designations = (
        f"la « Reprise du câblage des armoires » ajoutée sous le « {labels[N.CONTROL_STATION]} », "
        f"après le « {labels[N.WIRING]} », sous-traitée pour {rework}, que la « "
        f"{labels[N.COMMISSIONING]} » suit désormais aussi ; la charge du « {labels[N.LABOUR]} » "
        f"portée de 12,5 à {hours} h, son montant réestimé seul modifié ; le « "
        f"{labels[ABANDONED]} », terminé, abandonné"
    )
    cycle_said = mocktext.listed(
        [f"« {each['label']} »" for each in cast("list[JsonObject]", cycle()["cycle"])]
    )
    marking = (
        f"Variante contrefactuelle : la révision courante {MARKED_REVISION} marquée aujourd'hui, "
        f"le devis "
        f"propre de « {LABEL} », entier et à jour, élagué par le marquage"
    )
    taken = (
        f"Variante contrefactuelle : la révision {NEXT_REVISION}, ouverte après le marquage de "
        f"nodes_risk_estimate_pruned, reprend le devis propre de « {LABEL} » élagué, structure "
        f"{NEXT_STRUCTURE}, ses écarts exacts contre la structure principale de la révision "
        f"{MARKED_REVISION}"
    )
    return {
        "nodes_risk_estimate.json": mocktext.example(
            f"Le devis propre de « {LABEL} », structure {STRUCTURE} de la révision courante, "
            f"entier, lu le {mocktext.day(mockcore.READ_ON)} par ses seuls écarts avec sa base, « "
            f"Écarts seulement » (difference=added,removed,modified) : {designations}, rendu à sa "
            f"place, en lecture seule ; leurs ancêtres modifiés par leur contenu. Copie de la "
            f"structure principale du jour, sous les lignées de celle-ci, il ne porte ni ligne de "
            f"provision ni lot, poste ou inscription. Le total réestimé du devis propre passe "
            f"celui de sa base de {severity}, la gravité du risque (risk) : la reprise est "
            f"chiffrée pour la tenir, ce que les autres désignations ajoutent ou retirent compris. "
            f"Les totaux sont ceux du devis propre entier, que le filtre ne restreint pas "
            f"(WF-RIS-0030, WF-RIS-0010, WF-REV-0100, #4585).",
            whole,
        ),
        "nodes_risk_estimate_pruned.json": mocktext.example(
            f"{marking} à ce qu'il désigne : la tâche et la ligne ajoutées, la ligne modifiée, la "
            f"tâche abandonnée rendue retirée à sa place, et les extrémités des liaisons ajoutées, "
            f"sous leurs ancêtres, présentés inchangés — et non le projet entier. Ses écarts sont "
            f"comparés par la lignée à la structure principale de la révision marquée ; les "
            f"numéros de ligne et les rangs comptent l'arbre élagué, une liaison vers un nœud "
            f"qu'il ne porte plus n'est pas rendue. Les totaux sont ceux de la structure élaguée, "
            f"sans la tâche abandonnée (WF-RIS-0030, WF-REV-0100, #4585).",
            pruned,
        ),
        "structure_rebase_report_risk.json": mocktext.example(
            f"Variante déclarée, les écritures de la structure principale de "
            f"structure_rebase_report, faites aujourd'hui : le devis propre de « {LABEL} », à jour "
            f"jusque-là (structures), est en retard, et le compte rendu préalable de sa mise à "
            f"jour présente ce qu'elle y reporterait, comme pour un différentiel : la tâche "
            f"ajoutée, le libellé et la charge de la mise en service modifiés, la ligne retirée. "
            f"La charge du « {labels[N.LABOUR]} », que le devis propre porte à {hours} h et que "
            f"la principale a réestimée à {mocktext.amount(LABOUR_HOURS, 0)} h, est gardée et "
            f"signalée (kept, ses champs) : la confirmation est demandée. La gravité recalculée "
            f"sur le projet du jour, {mocktext.amount(updated_severity())}, et la provision "
            f"qu'elle "
            f"donne à {mocktext.amount(PROBABILITY * 100, 0)} %, "
            f"{mocktext.amount(provision(updated_severity()))}, sont celles que la mise à jour "
            f"enregistrera. Les compteurs lus, que la confirmation renverra : celui de la "
            f"principale, {main}, et celui du devis propre, {own} (WF-RIS-0070, WF-REV-0110, "
            f"#4585).",
            read,
        ),
        "structure_rebase_report_risk_refused.json": mocktext.example(
            f"Variante déclarée de structure_rebase_report_risk : la structure principale a de "
            f"plus fait suivre le « {RENAMED} » à la « {labels[N.COMMISSIONING]} », et retiré la "
            f"liaison qui faisait suivre la « {labels[N.FACTORY_ACCEPTANCE]} » au « {RENAMED} ». "
            f"Reportée dans le devis propre, où la reprise suit le câblage et précède la mise en "
            f"service, la liaison fermerait une boucle : le motif la refuse, les tâches nommées "
            f"par leur nœud dans le devis propre et leur libellé, {cycle_said}, chacune précédant "
            f"la suivante ; les dates ne se calculant pas, ni gravité ni provision ne sont "
            f"annoncées. La confirmation n'est pas offerte ; l'utilisateur corrige le devis "
            f"propre, puis relance (WF-PLA-0030, WF-RIS-0070, #4585).",
            refused,
        ),
        "structure_rebased_risk.json": mocktext.example(
            f"Le devis propre de « {LABEL} » mis à jour, la confirmation de "
            f"structure_rebase_report_risk reçue avec ses compteurs : ce que la principale a reçu "
            f"y est écrit, ce qu'il désigne est inchangé, la gravité et la provision du compte "
            f"rendu enregistrées ; il est à jour, sa commande rebase n'a plus rien à reprendre "
            f"(structure_out_of_date), et son compteur passe à {rebased()['lock_version']}. La "
            f"structure principale n'est écrite que par sa ligne de provision, ce qui ne met en "
            f"retard aucun autre devis propre (WF-RIS-0070, #4585).",
            rebased(),
        ),
        "structure_recomposed.json": mocktext.example(
            f"{taken}. Recomposé à l'ouverture de sa grille, sans corps ni confirmation, il est "
            f"entier (is_pruned faux) : sa base et sa structure copiées de cette structure "
            f"principale, ce qu'il désigne posé dessus par la lignée — rien n'en change. La "
            f"structure principale de la révision {NEXT_REVISION} n'ayant rien reçu depuis, il est "
            f"à jour, et se saisit ; son compteur passe à 2 (WF-RIS-0030, #4585).",
            recomposed(),
        ),
        "structure_rebase_risk_pruned_refused.json": mocktext.example(
            f"{taken}. Le compte rendu de sa mise à jour demandé avant sa recomposition : un devis "
            f"propre élagué n'a pas de base ; refusé par la condition qui manque, "
            f"own_estimate_whole, comme la mise à jour elle-même ; l'écran le recompose d'abord "
            f"(structure_recomposed). Rien n'est écrit (WF-RIS-0070, #4585).",
            {
                "code": "STATE_FORBIDS_OPERATION",
                "status": 409,
                "params": {"missing_condition": "own_estimate_whole"},
                "correlation_id": correlation("structure_rebase_risk_pruned_refused"),
            },
        ),
        "structures_next_revision.json": mocktext.example(
            f"Les structures de la révision {NEXT_REVISION}, ouverte après le marquage de "
            f"nodes_risk_estimate_pruned : la principale, reprise, et le devis propre de « "
            f"{LABEL} », structure {NEXT_STRUCTURE}, élagué (is_pruned vrai) et non consommé. "
            f"Sa saisie et sa mise à jour manquent de own_estimate_whole, et sa recomposition "
            f"(recompose) est offerte : c'est la commande que l'écran lance à l'ouverture de la "
            f"grille (WF-RIS-0030, WF-RIS-0070, #4585).",
            cast("list[JsonValue]", next_structures()),
        ),
        "structure_update_own_start_read_only.json": mocktext.example(
            f"La date de début envoyée sur le devis propre de « {LABEL} », structure {STRUCTURE} : "
            f"refusée sur son champ, FIELD_READ_ONLY, inchangée ou non, le devis propre n'ayant "
            f"pas de date à lui, celle de la principale ; son libellé seul se modifie ici. Rien "
            f"n'est écrit (WF-RIS-0030, #4585).",
            start_read_only(),
        ),
        "structure_recompose_revision_marked.json": mocktext.example(
            f"{marking} (nodes_risk_estimate_pruned). Sa recomposition demandée sur cette révision "
            f"marquée, qui ne se modifie plus : refusée par la condition qui manque, "
            f"revision_draft ; c'est la révision suivante qui le recompose. Rien n'est écrit "
            f"(WF-DAT-0020, WF-RIS-0030, #4585).",
            {
                "code": "STATE_FORBIDS_OPERATION",
                "status": 409,
                "params": {"missing_condition": "revision_draft"},
                "correlation_id": correlation("structure_recompose_revision_marked"),
            },
        ),
    }
