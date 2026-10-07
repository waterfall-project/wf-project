# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The answers of the writes of the grids, generated from what each write changes (EP-02/L22).

A write of a grid answers what it changed (`NodesWritten`): the nodes written; the tasks it
redated, by their schedule (`rescheduled`); the lines and the tasks whose amount corrected for
inflation it moved, by their amounts (`reinflated`); the summaries above all of them, whole
(`ancestors`); the totals of the whole structure, and the version the structure moved on to
(WF-IHM-0040, WF-PLA-0020, WF-DEV-0040). Here each answer is the difference between two
readings of one structure, before and after the write, never written by hand (#287).

The writes of the witness are made on its core: its description (``wftools.mockwitness``) is
amended, dated and priced again (``wftools.mockcore``), and read whole. Those the journeys make
on the structure of a thousand tasks the fake back serves first (``wftools.mockstructure``) are
made on it: a duration lengthened, a label entered, a block pasted. And the plans of a paste
and its refusal are read from the block and from the reference data, as the server reads them.
"""

from __future__ import annotations

import copy
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from wftools import REPOSITORY, mockcore, mocktext
from wftools.mockstructure import (
    CATEGORY_LABELS,
    REFERENCE_YEAR,
    JsonObject,
    JsonValue,
    emitted,
    inflated,
    money,
    planned,
    schedule,
    structure,
)
from wftools.mockwitness import (
    CABLE_FITTER,
    CORE,
    FACTORY_ACCEPTANCE,
    LABOUR,
    NODES,
    WIRING,
    Line,
    Link,
    Task,
    fixture,
    identifier,
    universe,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

type Node = dict[str, Any]

SCHEDULE = ("start", "finish", "total_float", "is_critical", "finish_overdue")
"""The fields of a task a write may redate without writing it (`NodeSchedule`)."""

INFLATION = ("inflated_amount", "consumption_year")
"""The fields of a line or a task a write may move in time without writing it (`NodeInflation`)."""

_AMOUNTS = ("base_amount", "reestimated_amount", "inflated_amount")
"""The amounts a quantity entered changes: the budget is the reference's (WF-DEV-0020)."""


def written(
    before: JsonObject,
    after: JsonObject,
    writes: Sequence[str],
    *,
    deleted: Sequence[str] = (),
    structure_version: int = 2,
) -> JsonObject:
    """Return what a write answers, from the readings of the whole structure before and after.

    The nodes written, whole, their version one further; the tasks, not summaries, whose
    schedule changed without being written; the lines and the tasks, not summaries, whose
    amount corrected for inflation or year of consumption changed, but those the ancestors
    render whole; the ancestors of the nodes written, of the node deleted — read before, as it
    is gone after — and of the tasks redated, whole. Each list in the order of the plan, each
    node once (`NodesWritten`).
    """
    was, now = _by_id(before), _by_id(after)
    moved = [
        node_id
        for node_id, node in now.items()
        if node_id not in writes
        and _is_activity(node)
        and _changed(node["task"], was[node_id]["task"], SCHEDULE)
    ]
    above = _ancestors(now, [*writes, *moved]) | _ancestors(was, deleted)
    reinflated: list[JsonValue] = []
    for node_id, node in now.items():
        if node_id in writes or node_id in above or not (_is_activity(node) or _is_line(node)):
            continue
        facet, old = _facet(node), _facet(was[node_id])
        if _changed(facet, old, INFLATION):
            reinflated.append(
                {
                    "node_id": node_id,
                    "inflated_amount": facet["inflated_amount"],
                    "consumption_year": facet.get("consumption_year"),
                }
            )
    return {
        "nodes": [
            {**now[node_id], "lock_version": was[node_id]["lock_version"] + 1} for node_id in writes
        ],
        "ancestors": [node for node_id, node in now.items() if node_id in above],
        "rescheduled": [
            {"node_id": node_id, **{key: now[node_id]["task"].get(key) for key in SCHEDULE}}
            for node_id in moved
        ],
        "reinflated": reinflated,
        "totals": after["totals"],
        "structure_lock_version": structure_version,
    }


def _by_id(answer: JsonObject) -> dict[str, Node]:
    """Return the nodes of an answer by their identifier, in the order of the plan."""
    return {node["node_id"]: node for node in cast("list[Node]", answer["items"])}


def _facet(node: Node) -> Node:
    return cast("Node", node[node["kind"]])


def _is_activity(node: Node) -> bool:
    """Whether a node is a task that is not a summary: one a write may redate."""
    return node["kind"] == "task" and not node["task"]["is_summary"]


def _is_line(node: Node) -> bool:
    return node["kind"] == "estimate_line"


def _changed(facet: Node, old: Node, keys: Iterable[str]) -> bool:
    return any(facet.get(key) != old.get(key) for key in keys)


def _ancestors(nodes: dict[str, Node], of: Iterable[str]) -> set[str]:
    """Return the ancestors of some nodes, each once."""
    found: set[str] = set()
    for node_id in of:
        parent = nodes[node_id]["parent_id"]
        while parent is not None:
            found.add(parent)
            parent = nodes[parent]["parent_id"]
    return found


# --- The writes of the witness, made on its core ----------------------------------------------


def amended(
    roots: Iterable[Task],
    task: Callable[[Task], Task] = lambda each: each,
    line: Callable[[Line], Line | None] = lambda each: each,
) -> tuple[Task, ...]:
    """Return the description of the core with each task and each line changed, or a line gone."""

    def walk(each: Task) -> Task:
        lines = tuple(kept for kept in (line(below) for below in each.lines) if kept is not None)
        return task(
            replace(each, lines=lines, children=tuple(walk(child) for child in each.children))
        )

    return tuple(walk(root) for root in roots)


def on_task(number: int, **changes: Any) -> Callable[[Task], Task]:
    """Change the fields of the task of a number, and of no other."""
    return lambda each: replace(each, **changes) if each.number == number else each


def on_line(number: int, **changes: Any) -> Callable[[Line], Line | None]:
    """Enter fields of the line of a number, and of no other.

    Its budget stays the one the reference revision gave it, whatever is entered: the
    re-estimate follows the quantities, the budget does not (WF-DEV-0020).
    """

    def entered(each: Line) -> Line:
        budgeted = mockcore.price(each, REFERENCE_YEAR).budgeted
        return replace(each, budgeted=budgeted, **changes)

    return lambda each: entered(each) if each.number == number else each


def removed(number: int) -> Callable[[Line], Line | None]:
    """Remove the line of a number."""
    return lambda each: None if each.number == number else each


def core_write(
    roots: Iterable[Task], writes: Sequence[int], deleted: Sequence[int] = ()
) -> JsonObject:
    """Return what a write of the core answers: the core read whole today, then as amended."""
    before = mockcore.whole(mockcore.core())
    after = mockcore.whole(mockcore.core(roots))
    return written(
        before,
        after,
        [universe(number) for number in writes],
        deleted=[universe(number) for number in deleted],
    )


MILESTONE = FACTORY_ACCEPTANCE
CONTROL_STATION, BLOCKS = 551, 554
MOUNTING, WIRING_ON_SITE, COMMISSIONING_TASK, COMMISSIONING_LINE = 562, 563, 565, 566
"""The nodes of the core the writes are about (``mockwitness``)."""

RENAMED = "Câblage et repérage des armoires"
SITE_DELAY = 2
"""The working days the cabinets take to reach the site, after the factory acceptance."""
LABOUR_HOURS = Decimal(14)
REESTIMATED_HOURS = Decimal(10)


def task_renamed() -> JsonObject:
    """Return what updateTaskFacet answers when the wiring of the cabinets is renamed."""
    return core_write(amended(CORE, on_task(WIRING, label=RENAMED)), [WIRING])


def estimate_line_updated() -> JsonObject:
    """Return what updateEstimateLine answers when the labour of the wiring takes 14 hours."""
    return core_write(amended(CORE, line=on_line(LABOUR, hours=LABOUR_HOURS)), [LABOUR])


def remaining_reestimated() -> JsonObject:
    """Return what setLineRemaining answers when the labour of the wiring is re-estimated at 10 h.

    The re-estimate follows the figures entered, the budget the reference fixed does not
    (WF-RAE-0040, WF-DEV-0020).
    """
    return core_write(amended(CORE, line=on_line(LABOUR, hours=REESTIMATED_HOURS)), [LABOUR])


COMPLETION_CORRELATION = universe(965)


def completion_date_required() -> JsonObject:
    """Return what setLineRemaining answers to a re-estimate that completes its task undated.

    The last open line of the wiring of the cabinets set to nothing completes the task, at a
    date the validation asks for (WF-RAE-0040, WF-PLA-0130): without one, the entry is refused,
    the task named, and nothing is written.
    """
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [
            {
                "pointer": "/completed_on",
                "code": "COMPLETION_DATE_REQUIRED",
                "params": {"task_node_id": universe(WIRING)},
            }
        ],
        "correlation_id": COMPLETION_CORRELATION,
    }


def node_deleted() -> JsonObject:
    """Return what deleteNode answers when the terminal blocks are deleted from the estimate."""
    return core_write(amended(CORE, line=removed(BLOCKS)), [], [BLOCKS])


def predecessor_set() -> JsonObject:
    """Return what setPredecessors answers when the mounting waits two days after the acceptance.

    The predecessors of the mounting on site, not started, set anew: the factory acceptance,
    finish to start, two days later — the cabinets on their way to the site (WF-PLA-0030).
    """
    links = (Link(MILESTONE, lag=SITE_DELAY),)
    return core_write(amended(CORE, on_task(MOUNTING, links=links)), [MOUNTING])


def estimate_line_redated() -> JsonObject:
    """Return what updateEstimateLine answers when the wiring on site goes to the cable fitter.

    The mounting then has two roles on two calendars, and works the days both work, the fewest
    hours of each (WF-PLA-0010): it finishes later, and the commissioning after it.
    """
    roots = amended(CORE, line=on_line(WIRING_ON_SITE, role=CABLE_FITTER))
    return core_write(roots, [WIRING_ON_SITE])


# --- The writes the journeys make on the structure of a thousand tasks -----------------------

LENGTHENED = "Revue 3.1.27"
"""The work task whose duration the example lengthens: it finishes on 29 December 2026, with
33 working days of float, and its one successor in its chain, « Reprise 3.1.30 », starts the
next day."""

LENGTHENED_BY = 2
"""The working days the duration grows by: the task finishes on 31 December, and its successor
starts on the first working day of 2027 — its lines are consumed a year later, corrected anew at
the inflation of the witness project (WF-DEV-0040) —, within the float: the milestone of the lot
does not move, nor anything after it."""


def task_lengthened() -> JsonObject:
    """Return what updateTaskFacet answers when the duration of LENGTHENED grows by its days."""
    roots, activities = planned()
    before = emitted(roots).nodes
    task = next(each for each in activities if each.label == LENGTHENED)
    task.duration += LENGTHENED_BY
    schedule(roots, activities)
    return written(before, emitted(roots).nodes, [identifier(NODES, task.row)])


LINE_4 = identifier(NODES, 4)
"""The first line of the structure, « Heures d'ingénierie », on which the journeys enter a label
and paste a block (`test_the_marks_the_journeys_read`)."""

ENTERED = "Heures de câblage"


def estimate_line_entered() -> JsonObject:
    """Return what updateEstimateLine answers to the label of the first line entered.

    The structure is at its third version: the line and the structure were written twice since
    they were read, and this answer is the second (#178).
    """
    before = structure().nodes
    after = copy.deepcopy(before)
    _by_id(after)[LINE_4]["estimate_line"]["label"] = ENTERED
    return written(before, after, [LINE_4], structure_version=3)


BLOCK = (
    ("Heures de câblage et repérage", "Ingénierie électrique", "Ingénieur électricien", "1"),
    ("Heures d'essais", "Mise en service", "Technicien de mise en service", "1"),
    ("Matériel de câblage", "Matériel électrique", "", "24"),
)
"""A block of three rows and four columns — label, category, role, quantity —, as a spreadsheet
copies it, pasted on the label of the first line: the rows of the journeys and of the tests."""

UNKNOWN_CATEGORY = (BLOCK[0], ("Heures d'essais", "Essais", "", "1"), BLOCK[2])
"""The same block, its second row naming a category the reference data does not know."""

PASTES = (universe(911), universe(912))
TOO_WIDE_CORRELATION = universe(913)


def _known() -> tuple[dict[str, str], dict[str, str]]:
    """Return the categories and the roles of the universe by their label."""
    roles = {role["label"]: role["resource_role_id"] for role in fixture("resource_roles")}
    return {label: key for key, label in CATEGORY_LABELS.items()}, roles


def paste_plan(block: Sequence[Sequence[str]], paste_id: str) -> JsonObject:
    """Return what previewPaste answers for a block: each row accepted, or refused by its cell.

    A category or a role the reference data does not name is refused, its row and its column
    named; an empty role writes nothing (WF-IHM-0050).
    """
    categories, roles = _known()
    rejected: list[JsonValue] = []
    for row, (_, category, role, _) in enumerate(block):
        if category not in categories:
            rejected.append(
                {"row": row, "column": "cost_category", "code": "UNKNOWN_COST_CATEGORY"}
            )
        elif role and role not in roles:
            rejected.append(
                {"row": row, "column": "resource_role", "code": "UNKNOWN_RESOURCE_ROLE"}
            )
    return {"paste_id": paste_id, "accepted": len(block) - len(rejected), "rejected": rejected}


def paste_applied() -> JsonObject:
    """Return what applyPaste answers for the block: its rows written on the lines under LINE_4.

    Each line takes the label, the category, the role and the quantity of its row; its amount
    follows its quantity, its budget, the reference's, does not (WF-DEV-0020); its task and the
    summaries above follow its amount, and the totals.
    """
    before = structure().nodes
    after = copy.deepcopy(before)
    items = cast("list[Node]", after["items"])
    first = next(index for index, node in enumerate(items) if node["node_id"] == LINE_4)
    targets = items[first : first + len(BLOCK)]
    categories, roles = _known()
    labels = {key: label for label, key in [*categories.items(), *roles.items()]}
    nodes = _by_id(after)
    for node, (label, category, role, quantity) in zip(targets, BLOCK, strict=True):
        line = node["estimate_line"]
        old = {key: Decimal(line[key]) for key in _AMOUNTS}
        line["label"] = label
        line["cost_category_id"] = categories[category]
        line["cost_category_label"] = labels[categories[category]]
        line["resource_role_id"] = roles.get(role)
        line["resource_role_label"] = role or None
        line["quantity"] = quantity
        each = (
            Decimal(line["hours"]) * mockcore.LABOUR_RATES[line["cost_category_id"]]
            if line["hours"] is not None
            else Decimal(line["unit_disbursement"])
        )
        amount = Decimal(quantity) * each
        line["base_amount"] = line["reestimated_amount"] = money(amount)
        line["inflated_amount"] = money(inflated(amount, line["consumption_year"]))
        delta = {key: Decimal(line[key]) - old[key] for key in _AMOUNTS}
        for above in [nodes[parent] for parent in _ancestors(nodes, [node["node_id"]])]:
            _add(above["task"], delta)
        _add(cast("Node", after["totals"]), delta)
    return written(before, after, [node["node_id"] for node in targets])


def _add(amounts: Node, delta: dict[str, Decimal]) -> None:
    for key, value in delta.items():
        amounts[key] = money(Decimal(amounts[key]) + value)


NODE_COLUMNS = REPOSITORY / "docs" / "api" / "components" / "schemas" / "revisions.yaml"
"""Where the contract lists the columns of the grids, in the order a paste fills them."""


def node_columns(text: str | None = None) -> list[str]:
    """Return the columns of the grids, in their order (`NodeColumn`), read from the contract."""
    lines = (NODE_COLUMNS.read_text(encoding="utf-8") if text is None else text).splitlines()
    start = lines.index("NodeColumn:")
    enum = next(index for index in range(start, len(lines)) if lines[index].strip() == "enum:")
    columns: list[str] = []
    for line in lines[enum + 1 :]:
        if not line.startswith("    - "):
            break
        columns.append(line.removeprefix("    - ").strip())
    return columns


def line_width(columns: Sequence[str]) -> int:
    """Return how many columns a line of the estimate offers from its label (`NodeColumn`).

    Its label, then those from the category to the last: the columns of a line.
    """
    return 1 + len(columns) - columns.index("cost_category")


def paste_too_wide() -> JsonObject:
    """Return what previewPaste answers to a block one column wider than a line from its label."""
    return {
        "code": "PASTE_TOO_WIDE",
        "status": 422,
        "params": {"max_columns": line_width(node_columns())},
        "correlation_id": TOO_WIDE_CORRELATION,
    }


# --- The examples ------------------------------------------------------------------------------


def _node(answer: JsonObject, number: int, key: str = "ancestors") -> Node:
    """Return a node of the core an answer renders, by its number, in one of its lists."""
    return next(
        node for node in cast("list[Node]", answer[key]) if node["node_id"] == universe(number)
    )


def _money(value: JsonValue) -> str:
    return mocktext.amount(Decimal(str(value)))


def _on(instant: JsonValue) -> str:
    return mocktext.day(date.fromisoformat(cast("dict[str, str]", instant)["date"]))


def _totals(answer: JsonObject) -> str:
    """Say the totals of the structure an answer gives: its lines, hours and amounts."""
    totals = cast("dict[str, str]", answer["totals"])
    return (
        f"les totaux de la structure, {mocktext.count(int(totals['estimate_line_count']))} "
        f"lignes, {totals['hours'].replace('.', ',')} h, {_money(totals['base_amount'])} à "
        f"l'année de référence, dont {_money(totals['budgeted_amount'])} budgétés"
    )


def writes() -> dict[str, JsonObject]:
    """Return the named examples of the writes of the grids, by file name."""
    return {**_core_writes(), **_volume_writes()}


def _core_writes() -> dict[str, JsonObject]:
    renamed, updated = task_renamed(), estimate_line_updated()
    reestimated = remaining_reestimated()
    [reestimated_line] = cast("list[Node]", reestimated["nodes"])
    deleted, linked, redated = node_deleted(), predecessor_set(), estimate_line_redated()
    [line] = cast("list[Node]", updated["nodes"])
    [mounting] = cast("list[Node]", linked["nodes"])
    moved = {entry["node_id"]: entry for entry in cast("list[Node]", linked["rescheduled"])}
    later = {entry["node_id"]: entry for entry in cast("list[Node]", redated["rescheduled"])}
    priced = {entry["node_id"]: entry for entry in cast("list[Node]", redated["reinflated"])}
    commissioning = universe(COMMISSIONING_TASK)
    before = {row.number: row for row in mockcore.core()}
    mounted = cast("Node", before[MOUNTING].node["task"])
    acceptance = cast("Node", before[MILESTONE].node["task"])
    return {
        "task_renamed.json": mocktext.example(
            f"La tâche « {before[WIRING].label} » renommée « {RENAMED} » ; une version de plus. "
            f"Avec elle, sa récapitulative « {before[CONTROL_STATION].label} », dont rien ne "
            f"change, et {_totals(renamed)}, inchangés (WF-PLA-0130, WF-IHM-0040).",
            renamed,
        ),
        "estimate_line_updated.json": mocktext.example(
            f"La ligne de main-d'œuvre du devis, « {before[LABOUR].label} », dont la charge "
            f"passe de {mocktext.amount(before[LABOUR].hours, 1)} à "
            f"{LABOUR_HOURS} h : le montant réestimé recalculé depuis ses grandeurs, "
            f"{_money(line['estimate_line']['reestimated_amount'])}, le budgété inchangé, "
            f"{_money(line['estimate_line']['budgeted_amount'])}, fixé par la référence ; une "
            f"version de plus. Avec elle, sa tâche « {before[WIRING].label} », portée à "
            f"{_money(_node(updated, WIRING)['task']['base_amount'])}, la récapitulative "
            f"« {before[CONTROL_STATION].label} » au-dessus, à "
            f"{_money(_node(updated, CONTROL_STATION)['task']['base_amount'])}, et "
            f"{_totals(updated)}, le budgété inchangé (WF-DEV-0020, WF-DEV-0030, "
            f"WF-DEV-0050).",
            updated,
        ),
        "remaining_reestimated.json": mocktext.example(
            f"La réestimation de la ligne de main-d'œuvre « {before[LABOUR].label} », budgétée à "
            f"{mocktext.amount(before[LABOUR].hours, 1)} h : une charge de "
            f"{REESTIMATED_HOURS} h donne un montant réestimé de "
            f"{_money(reestimated_line['estimate_line']['reestimated_amount'])}, recalculé "
            f"depuis ses grandeurs et jamais saisi, le budgété inchangé, "
            f"{_money(reestimated_line['estimate_line']['budgeted_amount'])}, fixé par la "
            f"référence ; une version de plus. Avec elle, sa tâche « {before[WIRING].label} », "
            f"à {_money(_node(reestimated, WIRING)['task']['reestimated_amount'])} réestimés, "
            f"la récapitulative « {before[CONTROL_STATION].label} » au-dessus, à "
            f"{_money(_node(reestimated, CONTROL_STATION)['task']['reestimated_amount'])}, et "
            f"{_totals(reestimated)}, le budgété inchangé (WF-RAE-0040, WF-DEV-0020).",
            reestimated,
        ),
        "remaining_completion_date_required.json": mocktext.example(
            f"Variante contrefactuelle déclarée : la charge de « {before[LABOUR].label} » mise à "
            f"zéro, les borniers et la provision du risque 751 supposés déjà réestimés à zéro, "
            f"sans date de terminaison. La saisie terminerait le « {before[WIRING].label} », "
            f"démarré, à une date que la validation demande : elle est refusée sur "
            f"`/completed_on`, la tâche nommée, et rien n'est écrit ; l'écran demande la date, "
            f"proposée au jour courant, et rejoue la saisie (WF-RAE-0040, WF-PLA-0130).",
            completion_date_required(),
        ),
        "node_deleted.json": mocktext.example(
            f"La ligne de débours « {before[BLOCKS].label} », "
            f"{mocktext.amount(before[BLOCKS].amounts.base)}, supprimée du devis du lot "
            f"« {before[CONTROL_STATION].label} » : rien à rendre d'elle, sa tâche "
            f"« {before[WIRING].label} » recalculée à "
            f"{_money(_node(deleted, WIRING)['task']['base_amount'])} et la récapitulative "
            f"au-dessus à {_money(_node(deleted, CONTROL_STATION)['task']['base_amount'])}, "
            f"{_totals(deleted)}, et le compteur de la structure, passé à 2 (WF-DEV-0050, "
            f"WF-IHM-0110).",
            deleted,
        ),
        "predecessor_set.json": mocktext.example(
            f"Les prédécesseurs du montage des armoires sur site, non démarré, saisis à nouveau : "
            f"la réception usine du {_on(acceptance['finish'])}, en fin à début, avec "
            f"{SITE_DELAY} jours ouvrés de décalage, le temps d'acheminer les armoires. Le "
            f"montage, écrit, part le {_on(mounting['task']['start'])} et finit le "
            f"{_on(mounting['task']['finish'])} ; une version de plus. Sans être écrites, les "
            f"tâches qu'il redate : la mise en service qui le suit, du "
            f"{_on(moved[commissioning]['start'])} au {_on(moved[commissioning]['finish'])}, "
            f"démarrée encore en 2026 — aucun montant corrigé de l'inflation ne change —, et, la "
            f"fin du cœur repoussée, les tâches sans successeur, dont seule la marge grandit. "
            f"Aucune date passée ne bouge : la réception usine reste au 30 juin. Les "
            f"récapitulatives au-dessus, entières ; les totaux de la structure ne changent pas "
            f"(WF-PLA-0020, WF-PLA-0030, WF-PLA-0100).",
            linked,
        ),
        "estimate_line_redated.json": mocktext.example(
            f"La ligne « {before[WIRING_ON_SITE].label} » du montage des armoires sur site "
            f"confiée au monteur câbleur, sur la semaine de quatre jours de dix heures ; une "
            f"version de plus, ses montants inchangés. Le montage, dont l'autre ligne reste au "
            f"technicien de mise en service sur la semaine standard, ne travaille plus que les "
            f"jours de ses deux rôles, à huit heures (WF-PLA-0010) : il finit le "
            f"{_on(later[universe(MOUNTING)]['finish'])} au lieu du "
            f"{_on(mounted['finish'])}, et la mise en service qui le suit "
            f"démarre le {_on(later[commissioning]['start'])} (rescheduled). Consommée en 2027, "
            f"sa ligne, « {before[COMMISSIONING_LINE].label} », est corrigée de l'inflation de "
            f"3 % du projet, {_money(priced[universe(COMMISSIONING_LINE)]['inflated_amount'])} "
            f"au lieu de {mocktext.amount(before[COMMISSIONING_LINE].amounts.inflated)}, et la "
            f"mise en service avec elle (reinflated) ; leur montant à l'année de référence ne "
            f"change pas. Avec la fin du cœur, les marges des tâches sans successeur grandissent ; "
            f"le montage et les récapitulatives au-dessus des tâches redatées, entiers ; les "
            f"totaux, dont le seul montant corrigé change (WF-PLA-0010, WF-PLA-0020, "
            f"WF-DEV-0040).",
            redated,
        ),
    }


def _volume_writes() -> dict[str, JsonObject]:
    applied = paste_applied()
    [_, _, third] = cast("list[Node]", applied["nodes"])
    line = third["estimate_line"]
    columns = node_columns()
    return {
        "estimate_line_entered.json": mocktext.example(
            f"La ligne 4 de la structure des volumes, « Heures d'ingénierie », dont le libellé "
            f"est saisi « {ENTERED} » : rien d'autre ne change, pas même ses montants ; une "
            f"version de plus. Avec elle, ses trois ancêtres, inchangés, les totaux de la "
            f"structure, et son compteur, passé à 3 après deux écritures. Le faux back la rend à "
            f"toute écriture d'une ligne, qui ne garde rien de ce qu'on lui envoie (WF-DEV-0020, "
            f"WF-IHM-0040).",
            estimate_line_entered(),
        ),
        "paste_plan.json": mocktext.example(
            "Un bloc de trois lignes et quatre colonnes — libellé, catégorie, rôle, quantité — "
            "collé sur le libellé de la ligne 4 de la structure des volumes : les trois lignes "
            "seront écrites, aucune n'est refusée ; rien n'est encore écrit (WF-IHM-0050).",
            paste_plan(BLOCK, PASTES[0]),
        ),
        "paste_plan_unknown_category.json": mocktext.example(
            f"Le même bloc, dont la deuxième ligne porte une catégorie qu'aucune du référentiel "
            f"ne nomme, « {UNKNOWN_CATEGORY[1][1]} » : cette ligne est refusée, sa cellule nommée "
            f"par sa colonne, et les deux autres seraient écrites ; un collage partiellement "
            f"invalide ne s'applique pas (WF-IHM-0050).",
            paste_plan(UNKNOWN_CATEGORY, PASTES[1]),
        ),
        "paste_too_wide.json": mocktext.example(
            f"Un bloc de {mocktext.count(line_width(columns) + 1)} colonnes collé sur le libellé "
            f"d'une ligne de devis, quand sa facette n'en a que "
            f"{mocktext.count(line_width(columns))} à partir de lui (NodeColumn) : le collage est "
            f"refusé, et rien n'est écrit (WF-IHM-0050).",
            paste_too_wide(),
        ),
        "paste_applied.json": mocktext.example(
            f"Le bloc de trois lignes et quatre colonnes appliqué sur les lignes 4 à 6 de la "
            f"structure des volumes : leurs libellés « {BLOCK[0][0]} », « {BLOCK[1][0]} » et "
            f"« {BLOCK[2][0]} », la quantité de la troisième portée à {line['quantity']} et son "
            f"montant réestimé recalculé, {_money(line['reestimated_amount'])} — "
            f"{line['quantity']} fois {_money(line['unit_disbursement'])} —, le budgété inchangé, "
            f"{_money(line['budgeted_amount'])}, fixé par la référence ; une version de plus "
            f"chacune. Avec elles, leurs trois ancêtres, dont le montant réestimé suit, les "
            f"totaux de la structure, et le compteur de la structure, passé à 2. Le faux back les "
            f"rend à tout collage confirmé, qui ne garde rien de ce qu'on lui envoie "
            f"(WF-IHM-0050, WF-DEV-0020).",
            applied,
        ),
    }
