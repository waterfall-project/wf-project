// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configuration of the grid of the estimate (WF-DEV-0050): the common tree of a structure
 * (`listNodes`), its tasks and the lines they bear, each row numbered and marked by the icon of
 * its nature; the label, the quantity, the effort, the unit disbursement, and the two amounts,
 * which the server computes and never lets anyone enter — the budgeted, fixed by the reference,
 * and the re-estimated (WF-DEV-0020, WF-DEV-0030). The figures of a provision are computed too,
 * from its risk, which its node says (`computed_fields`, WF-IHM-0030). The totals are those of
 * the answer: the hours and the amounts of the lines retained, never the amounts of the tasks,
 * which would count them twice.
 *
 * Each column sorts by the column of the contract of the same name. The category and the role of
 * a line, which the answer names by identifier only, are named by the reference data the page
 * reads with it (`listCostCategories`, `listResourceRoles`).
 *
 * A line is entered whole from the keyboard (WF-IHM-0040): its label, its category and its role,
 * chosen from their lists, its quantity, its effort and its unit disbursement, each written alone
 * by `updateEstimateLine`, where the node does not name the field among its computed fields; the
 * label of a task by `updateTaskFacet` (`estimateGrid`).
 */
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";

import {
  type CellValue,
  type Choice,
  type EntryKind,
  type GridColumn,
  type GridConfig,
  sortColumns,
} from "./columns";
import { computedAmount, computedWhereNamed } from "./computed-nodes";
import {
  type AnyNodeFields,
  LABEL_COLUMN,
  NODE_TREE,
  nodeKey,
  nodeNumber,
  type NodeSortColumn,
  type NodeTotals,
  type RowOf,
} from "./nodes";

/**
 * What the columns of the estimate read of a node, beyond what every grid reads: the amounts of
 * a task, the figures of a line — and its category, which each write of a line carries, the
 * contract requiring it (#178). The page hands the grid these alone (`projectNodes`).
 */
export const ESTIMATE_FIELDS = {
  node: [],
  task: ["budgeted_amount", "reestimated_amount"],
  line: [
    "cost_category_id",
    "quantity",
    "hours",
    "unit_disbursement",
    "budgeted_amount",
    "reestimated_amount",
  ],
} as const satisfies AnyNodeFields;

/** A node as the grid of the estimate reads it. */
export type EstimateNode = RowOf<typeof ESTIMATE_FIELDS>;

/** The grid of the estimate. */
export const ESTIMATE_GRID: GridConfig<EstimateNode, NodeSortColumn, NodeTotals> = {
  key: "estimate",
  name: "estimate",
  rowKey: nodeKey,
  rowNumber: nodeNumber,
  tree: NODE_TREE,
  columns: [
    LABEL_COLUMN,
    // A category and a role are named by the reference data (`estimateGrid`), their identifier
    // alone otherwise.
    {
      key: "cost_category",
      label: "category",
      format: "text",
      width: 160,
      sortBy: "cost_category",
      value: (node) => node.estimate_line?.cost_category_id,
    },
    {
      key: "resource_role",
      label: "role",
      format: "text",
      width: 160,
      sortBy: "resource_role",
      value: (node) => node.estimate_line?.resource_role_id,
    },
    {
      key: "quantity",
      label: "quantity",
      format: "decimal",
      width: 72,
      computed: computedWhereNamed("estimate_line.quantity"),
      sortBy: "quantity",
      value: (node) => node.estimate_line?.quantity,
    },
    {
      key: "hours",
      label: "hours",
      format: "decimal",
      width: 96,
      computed: computedWhereNamed("estimate_line.hours"),
      sortBy: "hours",
      value: (node) => node.estimate_line?.hours,
      total: (totals) => totals.hours,
    },
    {
      key: "unit_disbursement",
      label: "unitDisbursement",
      format: "money",
      width: 128,
      computed: computedWhereNamed("estimate_line.unit_disbursement"),
      sortBy: "unit_disbursement",
      value: (node) => node.estimate_line?.unit_disbursement,
    },
    {
      key: "budgeted_amount",
      label: "budgetedAmount",
      format: "money",
      width: 128,
      computed: computedAmount("budgeted_amount"),
      sortBy: "budgeted_amount",
      value: (node) => node.task?.budgeted_amount ?? node.estimate_line?.budgeted_amount,
      total: (totals) => totals.budgeted_amount,
    },
    {
      key: "reestimated_amount",
      label: "reestimatedAmount",
      format: "money",
      width: 128,
      computed: computedAmount("reestimated_amount"),
      sortBy: "reestimated_amount",
      value: (node) => node.task?.reestimated_amount ?? node.estimate_line?.reestimated_amount,
      total: (totals) => totals.reestimated_amount,
    },
  ],
};

/** The columns of the contract the grid of the estimate sorts by. */
export const ESTIMATE_SORT_COLUMNS = sortColumns(ESTIMATE_GRID);

/** The fields of a line of the estimate an entry writes, beyond those every write carries. */
export type LineChange = Partial<
  Pick<
    components["schemas"]["EstimateLineWrite"],
    "label" | "cost_category_id" | "resource_role_id" | "quantity" | "hours" | "unit_disbursement"
  >
>;

/**
 * How the grid of the estimate writes a cell: a field of a line, the label of a task — the row
 * answered as the grid reads it.
 */
export interface EstimateWrites {
  readonly line: (node: EstimateNode, change: LineChange) => Promise<Outcome<EstimateNode>>;
  readonly task: (node: EstimateNode, label: string) => Promise<Outcome<EstimateNode>>;
}

/** The reference data the grid names the categories and the roles of the lines by. */
export interface EstimateReference {
  readonly categories: readonly Choice[];
  readonly roles: readonly Choice[];
}

/** How a column of a line is entered: what it takes, the field it writes, what it starts from. */
interface Entered {
  readonly kind: EntryKind;
  readonly change: (value: string | null) => LineChange;
  /** The value of the contract an entry starts from; by default, what the column shows. */
  readonly read?: (node: EstimateNode) => CellValue;
}

/** The columns of a line that take an entry, the lists of a category and a role among them. */
function enteredColumns(reference: EstimateReference): Readonly<Record<string, Entered>> {
  return {
    // The contract takes a label of 1 to 300 characters.
    label: { kind: { type: "text", maxLength: 300 }, change: (value) => ({ label: value ?? "" }) },
    cost_category: {
      kind: { type: "choice", choices: reference.categories, nullable: false },
      change: (value) => (value === null ? {} : { cost_category_id: value }),
      read: (node) => node.estimate_line?.cost_category_id,
    },
    resource_role: {
      kind: { type: "choice", choices: reference.roles, nullable: true },
      change: (value) => ({ resource_role_id: value }),
      read: (node) => node.estimate_line?.resource_role_id,
    },
    quantity: {
      kind: { type: "decimal", nullable: false },
      change: (value) => (value === null ? {} : { quantity: value }),
    },
    hours: { kind: { type: "decimal", nullable: true }, change: (value) => ({ hours: value }) },
    unit_disbursement: {
      kind: { type: "money", nullable: true },
      change: (value) => ({ unit_disbursement: value }),
    },
  };
}

/** Whether a node bears a line of the estimate. */
function bearsLine(node: EstimateNode): boolean {
  return node.estimate_line !== undefined && node.estimate_line !== null;
}

/** The name of a choice, by its identifier, from the reference data. */
function namer(choices: readonly Choice[]): (id: CellValue) => CellValue {
  const names = new Map(choices.map((choice) => [choice.id, choice.label]));
  return (id) => (id === null || id === undefined ? id : names.get(id));
}

/** A column of the estimate, entered through `writes`: the fields of a line, and a task's label. */
function entered(
  column: GridColumn<EstimateNode, NodeSortColumn, NodeTotals>,
  spec: Entered | undefined,
  writes: EstimateWrites | undefined,
): GridColumn<EstimateNode, NodeSortColumn, NodeTotals> {
  if (spec === undefined || writes === undefined) {
    return column;
  }
  const label = column.key === "label";
  return {
    ...column,
    entry: {
      kind: spec.kind,
      in: (node) => (label || bearsLine(node)) && column.computed?.in(node) !== true,
      value: spec.read ?? column.value,
      write: (node, value) =>
        label && !bearsLine(node)
          ? writes.task(node, value ?? "")
          : writes.line(node, spec.change(value)),
    },
  };
}

/**
 * The grid of the estimate: its categories and roles named by the reference data, its cells
 * entered through `writes` — none, and the grid is read only. A line takes its label, category,
 * role, quantity, effort and unit disbursement, where the server does not compute the field; a
 * task, its label.
 */
export function estimateGrid(
  reference: EstimateReference,
  writes?: EstimateWrites,
): GridConfig<EstimateNode, NodeSortColumn, NodeTotals> {
  const specs = enteredColumns(reference);
  const names: Readonly<Record<string, (id: CellValue) => CellValue>> = {
    cost_category: namer(reference.categories),
    resource_role: namer(reference.roles),
  };
  return {
    ...ESTIMATE_GRID,
    columns: ESTIMATE_GRID.columns.map((column) => {
      const name = names[column.key];
      const named =
        name === undefined
          ? column
          : { ...column, value: (node: EstimateNode) => name(column.value(node)) };
      return entered(named, specs[column.key], writes);
    }),
  };
}
