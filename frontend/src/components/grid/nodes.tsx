// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the grids of a structure share (EP-02, « Grille dense »): the planning and the estimate
 * read the same tree (`listNodes`), the same tasks seen from the side of time or of money
 * (§3.5.1). Both number a row as the API does, indent it by its level, mark it by the icon of
 * its nature and show its label: two configurations of one grid, which differ by their columns
 * alone — and by what they ask of the server, the planning without the lines.
 */
import type { components, operations } from "@/api/generated/schema";

import type { GridColumn, GridTree, RowPart, RowsWritten } from "./columns";
import { rowNature, RowNatureIcon } from "./row-nature";

/** A node of a structure, as the API reads it. */
export type Node = components["schemas"]["Node"];

/** The facet of a node that is a task. */
type TaskFacet = components["schemas"]["TaskFacet"];

/** The facet of a node that is a line of the estimate. */
type EstimateLineFacet = components["schemas"]["EstimateLineFacet"];

/** A field of the task of a node. */
export type TaskField = keyof TaskFacet;

/** A field of the line of the estimate of a node. */
export type LineField = keyof EstimateLineFacet;

/** The totals of a reading of the nodes, which the server computes. */
export type NodeTotals = components["schemas"]["NodeTotals"];

/**
 * What the API answers a write of a grid with: the nodes written, the tasks it rescheduled, the
 * lines and the tasks it moved in time, the ancestors of all recalculated, the totals of the
 * structure and the version it moved on to.
 */
export type NodesWritten = components["schemas"]["NodesWritten"];

/** The schedule of a task a write rescheduled without writing it. */
type NodeSchedule = components["schemas"]["NodeSchedule"];

/** The amounts of a line, or of a task, a write moved in time without writing it. */
type NodeInflation = components["schemas"]["NodeInflation"];

/** A column of a grid of a structure, as the contract names it. */
export type NodeColumn = components["schemas"]["NodeColumn"];

/** The answer of `listNodes`: the nodes, depth first, and their totals. */
export type NodeList = operations["listNodes"]["responses"][200]["content"]["application/json"];

/**
 * The structure a grid reads the nodes of: its project, its revision, the structure itself —
 * what a computed cell names, with its node, to ask what its value depends on.
 */
export type StructurePath = Omit<
  operations["getComputedValueDependencies"]["parameters"]["path"],
  "node_id"
>;

/**
 * What a reading of the nodes asks besides the fields it renders and its sort: the kinds it renders,
 * the search, the filters. A reading that asks any of them has totals of its own, which those of the
 * structure a write answers are not (`NodesWritten.totals`).
 */
export type NodeFilters = Omit<
  NonNullable<operations["listNodes"]["parameters"]["query"]>,
  "fields" | "sort_by" | "sort_order"
>;

/** A column of the contract the server sorts the nodes by. */
export type NodeSortColumn = NonNullable<
  NonNullable<operations["listNodes"]["parameters"]["query"]>["sort_by"]
>;

/** What a grid of a structure asks the server to render: the tasks, the lines. */
export type NodeKind = components["schemas"]["NodeKind"];

/** A field of a node itself, its facets aside: those are read field by field. */
export type NodeField = Exclude<keyof Node, "task" | "estimate_line">;

/**
 * The fields a grid reads of a node: of the node itself, of its task, of its line. A page asks
 * `listNodes` for these alone (`fields`, `nodeFieldNames`), and hands its grid these alone
 * (`projectNodes`): a thousand tasks and their lines whole would weigh some four megabytes, in
 * the answer and in the page, and cost the second of §4.6.2. The projection stays behind the
 * request: a server may render more than asked — the fake back renders its example whole —, and
 * what crosses to the browser is what the grid shows, whatever the answer held.
 */
export interface NodeFields<
  N extends NodeField,
  T extends keyof TaskFacet,
  L extends keyof EstimateLineFacet,
> {
  readonly node: readonly N[];
  readonly task: readonly T[];
  readonly line: readonly L[];
}

/** Any list of the fields a grid reads. */
export type AnyNodeFields = NodeFields<NodeField, keyof TaskFacet, keyof EstimateLineFacet>;

/**
 * The fields every grid of a structure reads: the identity and the version of a node, which an
 * entry sends back, the fields the server computes on it and those it accepts (#219), its number
 * and its level, its kind and the flags of its nature, its label.
 */
export const COMMON_FIELDS = {
  node: [
    "node_id",
    "lock_version",
    "computed_fields",
    "editable_fields",
    "row_number",
    "level",
    "kind",
  ],
  task: ["label", "is_summary", "is_milestone"],
  line: ["label", "is_computed", "resource_role_id"],
} as const satisfies AnyNodeFields;

/**
 * A node as a grid reads it: the fields every grid reads, and those `N` of the node, `T` of its
 * task and `L` of its line that its own columns read.
 */
export type NodeRow<
  N extends NodeField = never,
  T extends keyof TaskFacet = never,
  L extends keyof EstimateLineFacet = never,
> = Pick<Node, (typeof COMMON_FIELDS.node)[number] | N> & {
  readonly task?: Pick<TaskFacet, (typeof COMMON_FIELDS.task)[number] | T> | null;
  readonly estimate_line?: Pick<EstimateLineFacet, (typeof COMMON_FIELDS.line)[number] | L> | null;
};

/** A node as a grid reads it, by the fields its columns read. */
export type RowOf<F extends AnyNodeFields> = NodeRow<
  F["node"][number],
  F["task"][number],
  F["line"][number]
>;

/** A node as every grid of a structure reads it: what the tree, the number and the label read. */
export type GridNode = NodeRow;

/** The rows a grid shows, and the totals of the answer they come from. */
export interface NodeRows<Row> {
  readonly items: readonly Row[];
  readonly totals: NodeTotals;
}

/**
 * The names `listNodes` takes in `fields` for what a grid reads: the fields every grid reads and
 * those its columns read — of the node as they are, of its task and of its line prefixed by their
 * facet (`task.label`).
 */
export function nodeFieldNames(fields: AnyNodeFields): string[] {
  const facet = (name: "task" | "estimate_line", names: readonly string[]) =>
    names.map((field) => `${name}.${field}`);
  return [
    ...new Set([
      ...COMMON_FIELDS.node,
      ...fields.node,
      ...facet("task", [...COMMON_FIELDS.task, ...fields.task]),
      ...facet("estimate_line", [...COMMON_FIELDS.line, ...fields.line]),
    ]),
  ];
}

/**
 * Some fields of an object: those it has — a field the contract leaves optional and the answer
 * leaves out stays out, as it came.
 */
function pick<T extends object, K extends keyof T>(source: T, keys: readonly K[]): Pick<T, K> {
  const picked: Partial<Pick<T, K>> = {};
  for (const key of keys) {
    if (key in source) {
      picked[key] = source[key];
    }
  }
  // Each key the source has is copied; the others are optional in the contract.
  return picked as Pick<T, K>;
}

/** A node as a grid reads it: the fields every grid reads, and those its columns read. */
export function projectNode<
  N extends NodeField,
  T extends keyof TaskFacet,
  L extends keyof EstimateLineFacet,
>(node: Node, fields: NodeFields<N, T, L>): NodeRow<N, T, L> {
  const { task, estimate_line: line } = node;
  return {
    ...pick(node, [...COMMON_FIELDS.node, ...fields.node]),
    ...(task === undefined
      ? {}
      : { task: task === null ? null : pick(task, [...COMMON_FIELDS.task, ...fields.task]) }),
    ...(line === undefined
      ? {}
      : {
          estimate_line: line === null ? null : pick(line, [...COMMON_FIELDS.line, ...fields.line]),
        }),
  };
}

/**
 * The rows of an answer of `listNodes` as a grid reads them, in the order of the answer, with its
 * totals: what a page hands its grid.
 */
export function projectNodes<
  N extends NodeField,
  T extends keyof TaskFacet,
  L extends keyof EstimateLineFacet,
>(list: NodeList, fields: NodeFields<N, T, L>): NodeRows<NodeRow<N, T, L>> {
  return { items: list.items.map((node) => projectNode(node, fields)), totals: list.totals };
}

/**
 * The fields of the schedule of a task a write may reschedule without writing it
 * (`NodesWritten.rescheduled`), under their names on the task.
 */
const SCHEDULE = ["start", "finish", "total_float", "is_critical", "finish_overdue"] as const;

/**
 * A row a write rescheduled: the fields of its schedule the grid reads, as the server answered
 * them, the others as they were — a grid that shows no date takes nothing of it.
 */
function rescheduled<
  N extends NodeField,
  T extends keyof TaskFacet,
  L extends keyof EstimateLineFacet,
>(row: NodeRow<N, T, L>, schedule: NodeSchedule): NodeRow<N, T, L> {
  const { task } = row;
  if (task === undefined || task === null) {
    return row;
  }
  const read = SCHEDULE.filter((field) => field in task);
  return read.length === 0 ? row : { ...row, task: { ...task, ...pick(schedule, read) } };
}

/**
 * The fields of a line a write may move in time without writing it (`NodesWritten.reinflated`),
 * under their names on the line.
 */
const INFLATION = ["inflated_amount", "consumption_year"] as const;

/** The field of a task, not a summary, a write may move in time without writing it. */
const TASK_INFLATION = ["inflated_amount"] as const;

/**
 * A row a write moved in time — a line, or a task its lines moved —: the fields of its amounts the
 * grid reads, as the server answered them, the others as they were — a grid that shows no amount
 * takes nothing of it.
 */
function reinflated<
  N extends NodeField,
  T extends keyof TaskFacet,
  L extends keyof EstimateLineFacet,
>(row: NodeRow<N, T, L>, inflation: NodeInflation): NodeRow<N, T, L> {
  const { task, estimate_line: line } = row;
  if (line !== undefined && line !== null) {
    const read = INFLATION.filter((field) => field in line);
    return read.length === 0
      ? row
      : { ...row, estimate_line: { ...line, ...pick(inflation, read) } };
  }
  if (task !== undefined && task !== null) {
    const read = TASK_INFLATION.filter((field) => field in task);
    return read.length === 0 ? row : { ...row, task: { ...task, ...pick(inflation, read) } };
  }
  return row;
}

/**
 * The parts of rows a write answered, one by row: those of a same row — a task both rescheduled and
 * moved in time — laid one over the other, each setting its own fields.
 */
function composed<Row>(parts: readonly RowPart<Row>[]): RowPart<Row>[] {
  const byKey = new Map<string, RowPart<Row>["change"]>();
  for (const { key, change } of parts) {
    const before = byKey.get(key);
    byKey.set(key, before === undefined ? change : (row) => change(before(row)));
  }
  return [...byKey].map(([key, change]) => ({ key, change }));
}

/**
 * What a write of a grid answered, as the grid reads it (#218): the nodes written, each ancestor
 * recalculated whole, each task rescheduled by the part of its schedule the grid reads — none for
 * a grid that reads no date —, each line or task moved in time by the part of its amounts the grid reads —
 * none for a grid that reads none (#235) —, the totals of the structure when the grid reads it
 * whole — a filtered grid reads its own anew (`GridConfig.retotal`) —, in the order of the version
 * the structure moved on to, which each write moves on.
 */
export function nodesWritten<
  N extends NodeField,
  T extends keyof TaskFacet,
  L extends keyof EstimateLineFacet,
>(
  written: NodesWritten,
  fields: NodeFields<N, T, L>,
  whole: boolean,
): RowsWritten<NodeRow<N, T, L>, NodeTotals> {
  const schedule = new Set<string>(SCHEDULE);
  const dated = fields.task.some((field) => schedule.has(field));
  const inflation = new Set<string>(INFLATION);
  const priced = [...fields.line, ...fields.task].some((field) => inflation.has(field));
  return {
    rows: written.nodes.map((node) => projectNode(node, fields)),
    changed: written.ancestors.map((node) => projectNode(node, fields)),
    parts: composed([
      ...(dated
        ? written.rescheduled.map((schedule) => ({
            key: schedule.node_id,
            change: (row: NodeRow<N, T, L>) => rescheduled(row, schedule),
          }))
        : []),
      ...(priced
        ? written.reinflated.map((amounts) => ({
            key: amounts.node_id,
            change: (row: NodeRow<N, T, L>) => reinflated(row, amounts),
          }))
        : []),
    ]),
    totals: whole ? written.totals : undefined,
    order: written.structure_lock_version,
  };
}

/**
 * The columns of the contract, in its order (`NodeColumn`): the columns of the planning
 * (WF-PLA-0080), then those of the estimate and of the remaining to commit (WF-DEV-0050,
 * WF-RAE-0040), each in the order its grid presents them — the order a paste fills them in.
 */
export const NODE_COLUMNS = [
  "label",
  "description",
  "scheduling_mode",
  "duration",
  "start",
  "finish",
  "progress",
  "physical_progress",
  "total_float",
  "is_critical",
  "predecessors",
  "work_breakdown",
  "cost_category",
  "resource_role",
  "quantity",
  "hours",
  "unit_disbursement",
  "subproject",
  "payment_delay_days",
  "consumption_year",
  "base_amount",
  "budgeted_amount",
  "reestimated_amount",
  "inflated_amount",
  "previous_reestimated_amount",
] as const satisfies readonly NodeColumn[];

/** The columns of a task, from `label` to `work_breakdown`, as the contract ranges them. */
const TASK_COLUMNS: readonly NodeColumn[] = NODE_COLUMNS.slice(
  0,
  NODE_COLUMNS.indexOf("work_breakdown") + 1,
);

/** The columns of a line of the estimate: `label`, then from `cost_category` to the last. */
const LINE_COLUMNS: readonly NodeColumn[] = [
  "label",
  ...NODE_COLUMNS.slice(NODE_COLUMNS.indexOf("cost_category")),
];

/**
 * The columns a block pasted on a node fills, from a column (#200, #223): those of the facet of
 * the node, in the order of the contract, from that column on — whether the grid shows them or
 * not. None for a column out of the facet, which the contract does not range.
 */
export function pasteSpan(node: GridNode, column: NodeColumn): readonly NodeColumn[] | undefined {
  const facet = node.kind === "task" ? TASK_COLUMNS : LINE_COLUMNS;
  const from = facet.indexOf(column);
  return from < 0 ? undefined : facet.slice(from);
}

/** How the label of a node stands out: a summary in bold, a provision muted. */
function emphasis(node: GridNode): "strong" | "muted" | undefined {
  const nature = rowNature(node);
  if (nature === "summary") {
    return "strong";
  }
  return nature === "provision" ? "muted" : undefined;
}

/** The tree of a structure: the level the API computes, the icon of the nature of a node. */
export const NODE_TREE: GridTree<GridNode> = {
  level: (node) => node.level,
  nature: (node) => <RowNatureIcon node={node} />,
  emphasis,
};

/** The identity of a node, stable from one answer to the next. */
export function nodeKey(node: GridNode): string {
  return node.node_id;
}

/** The number of a node, as the API computes it at the reading. */
export function nodeNumber(node: GridNode): number {
  return node.row_number;
}

/**
 * The label of a node, pinned at the start: that of the task, or of the line. Each grid says how
 * it is entered, if it is: an entry answers the row a grid reads.
 */
export const LABEL_COLUMN: Omit<GridColumn<GridNode, NodeSortColumn, NodeTotals>, "entry"> = {
  key: "label",
  label: "label",
  format: "text",
  width: 320,
  pinned: true,
  sortBy: "label",
  value: (node) => node.task?.label ?? node.estimate_line?.label,
};
