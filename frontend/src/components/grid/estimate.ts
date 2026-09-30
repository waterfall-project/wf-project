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
 */
import { type GridConfig, sortColumns } from "./columns";
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
 * a task, the figures of a line. The page hands the grid these alone (`projectNodes`).
 */
export const ESTIMATE_FIELDS = {
  node: [],
  task: ["budgeted_amount", "reestimated_amount"],
  line: ["quantity", "hours", "unit_disbursement", "budgeted_amount", "reestimated_amount"],
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
