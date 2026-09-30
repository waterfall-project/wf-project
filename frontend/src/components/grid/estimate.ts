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
 * Each column sorts by the column of the contract of the same name. The categories, roles and
 * sub-projects, which the answer names by identifier only, come with the reference data their
 * names are read from.
 *
 * A line is entered from the keyboard (WF-IHM-0040): its label, its quantity, its effort and its
 * unit disbursement, each written alone by `updateEstimateLine`, where the node does not name the
 * field among its computed fields (`estimateGrid`).
 */
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";

import { type EntryKind, type GridConfig, sortColumns } from "./columns";
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
    "label" | "quantity" | "hours" | "unit_disbursement"
  >
>;

/** How the grid of the estimate writes a field of a line: the row answered as the grid reads it. */
export interface EstimateWrites {
  readonly line: (node: EstimateNode, change: LineChange) => Promise<Outcome<EstimateNode>>;
}

/** The columns of a line that take an entry: what they take, and the field they write. */
const ENTERED: Readonly<
  Record<
    string,
    { readonly kind: EntryKind; readonly change: (value: string | null) => LineChange }
  >
> = {
  label: { kind: { type: "text" }, change: (value) => ({ label: value ?? "" }) },
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

/** Whether a node bears a line of the estimate. */
function bearsLine(node: EstimateNode): boolean {
  return node.estimate_line !== undefined && node.estimate_line !== null;
}

/**
 * The grid of the estimate, entered through `writes`: the label, the quantity, the effort and the
 * unit disbursement of a line, in the rows that bear one and where the server does not compute
 * the field — an entry starts from what the column shows.
 */
export function estimateGrid(
  writes: EstimateWrites,
): GridConfig<EstimateNode, NodeSortColumn, NodeTotals> {
  return {
    ...ESTIMATE_GRID,
    columns: ESTIMATE_GRID.columns.map((column) => {
      const entered = ENTERED[column.key];
      return entered === undefined
        ? column
        : {
            ...column,
            entry: {
              kind: entered.kind,
              in: (node) => bearsLine(node) && column.computed?.in(node) !== true,
              value: column.value,
              write: (node, value) => writes.line(node, entered.change(value)),
            },
          };
    }),
  };
}
