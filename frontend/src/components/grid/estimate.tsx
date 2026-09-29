// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configuration of the grid of the estimate (WF-DEV-0050): the common tree of a structure
 * (`listNodes`), its tasks and the lines they bear, each row numbered and marked by the icon of
 * its nature; the label, the quantity, the effort, the unit disbursement, and the two amounts,
 * which the server computes and never lets anyone enter — the budgeted, fixed by the reference,
 * and the re-estimated (WF-DEV-0020, WF-DEV-0030). The totals are those of the answer: the
 * hours and the amounts of the lines retained, never the amounts of the tasks, which would
 * count them twice.
 *
 * Each column sorts by the column of the contract of the same name. The categories, roles and
 * sub-projects, which the answer names by identifier only, come with the reference data their
 * names are read from.
 */
import type { components, operations } from "@/api/generated/schema";

import { type GridConfig, sortColumns } from "./columns";
import { rowNature, RowNatureIcon } from "./row-nature";

/** A node of a structure, as the API reads it. */
export type Node = components["schemas"]["Node"];

/** The totals of a reading of the nodes, which the server computes. */
export type NodeTotals = components["schemas"]["NodeTotals"];

/** The answer of `listNodes`: the nodes, depth first, and their totals. */
export type NodeList = operations["listNodes"]["responses"][200]["content"]["application/json"];

/** A column of the contract the server sorts the nodes by. */
export type NodeSortColumn = NonNullable<
  NonNullable<operations["listNodes"]["parameters"]["query"]>["sort_by"]
>;

/** How the label of a node stands out: a summary in bold, a provision muted. */
function emphasis(node: Node): "strong" | "muted" | undefined {
  const nature = rowNature(node);
  if (nature === "summary") {
    return "strong";
  }
  return nature === "provision" ? "muted" : undefined;
}

/** The grid of the estimate. */
export const ESTIMATE_GRID: GridConfig<Node, NodeSortColumn, NodeTotals> = {
  key: "estimate",
  name: "estimate",
  rowKey: (node) => node.node_id,
  rowNumber: (node) => node.row_number,
  tree: {
    level: (node) => node.level,
    nature: (node) => <RowNatureIcon node={node} />,
    emphasis,
  },
  columns: [
    {
      key: "label",
      label: "label",
      format: "text",
      width: 320,
      pinned: true,
      sortBy: "label",
      value: (node) => node.task?.label ?? node.estimate_line?.label,
    },
    {
      key: "quantity",
      label: "quantity",
      format: "decimal",
      width: 72,
      sortBy: "quantity",
      value: (node) => node.estimate_line?.quantity,
    },
    {
      key: "hours",
      label: "hours",
      format: "decimal",
      width: 96,
      sortBy: "hours",
      value: (node) => node.estimate_line?.hours,
      total: (totals) => totals.hours,
    },
    {
      key: "unit_disbursement",
      label: "unitDisbursement",
      format: "money",
      width: 128,
      sortBy: "unit_disbursement",
      value: (node) => node.estimate_line?.unit_disbursement,
    },
    {
      key: "budgeted_amount",
      label: "budgetedAmount",
      format: "money",
      width: 128,
      computed: true,
      sortBy: "budgeted_amount",
      value: (node) => node.task?.budgeted_amount ?? node.estimate_line?.budgeted_amount,
      total: (totals) => totals.budgeted_amount,
    },
    {
      key: "reestimated_amount",
      label: "reestimatedAmount",
      format: "money",
      width: 128,
      computed: true,
      sortBy: "reestimated_amount",
      value: (node) => node.task?.reestimated_amount ?? node.estimate_line?.reestimated_amount,
      total: (totals) => totals.reestimated_amount,
    },
  ],
};

/** The columns of the contract the grid of the estimate sorts by. */
export const ESTIMATE_SORT_COLUMNS = sortColumns(ESTIMATE_GRID);
