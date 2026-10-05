// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configuration of the grid of the actual costs (WF-CRE-0040): for each line of a page of the
 * list, its document — number, date —, its amount, signed, the sub-project it is charged to, or
 * none (WF-CRE-0020), whether it is in the tracked scope, why it is excluded, and the columns of
 * the file kept for information (WF-CRE-0010). The same dense grid as the planning and the risks:
 * another configuration, read only — the actual costs are imported and excluded by the epic of the
 * actual costs (EP-09). Every value is entered by the ERP, none computed here.
 *
 * The number, the date, the amount, the sub-project, the scope and the reason sort by the columns
 * of the contract of the same name, the server sorting — the most recent documents first when none
 * is asked —; the columns kept from the file, named by the file, have no sort in the contract. The
 * server searches nothing, and the bar of the grid offers no search. The totals row shows the general total of the lines retained the server gives, never
 * a sum of the page.
 */
import type { components, operations } from "@/api/generated/schema";
import { type GridConfig, sortColumns } from "@/components/grid/columns";

import { PassthroughCell, ScopeCell, SubprojectCell } from "./cost-cells";

/** A line of actual cost, as the contract gives it. */
type ActualCostLine = components["schemas"]["ActualCostLine"];

/** The three totals of the lines retained, as the server gives them. */
export type ActualCostTotals = components["schemas"]["ActualCostTotals"];

/** Where a page stands in the lines the server retained. */
export type ListPage = components["schemas"]["PaginationMeta"];

/** The column of the contract the server sorts the actual costs by. */
export type CostSortColumn = NonNullable<
  NonNullable<operations["listActualCosts"]["parameters"]["query"]>["sort_by"]
>;

/** What the grid reads of a line: the page hands it these fields alone. */
export const COST_FIELDS = [
  "cost_line_id",
  "document_number",
  "document_date",
  "amount",
  "subproject_code",
  "subproject_label",
  "is_in_tracked_scope",
  "excluded_reason",
  "passthrough",
] as const satisfies readonly (keyof ActualCostLine)[];

/** A line of actual cost as the grid reads it. */
export type CostRow = Pick<ActualCostLine, (typeof COST_FIELDS)[number]>;

/** What the server answers of a page of the actual costs, as the grid reads it. */
export interface CostRows {
  readonly items: readonly CostRow[];
  readonly totals: ActualCostTotals;
}

/**
 * The fields of a line the grid reads, and those alone: its project, its identifiers of
 * sub-project, its audit do not cross to the browser with the rows.
 */
export function costRow(line: ActualCostLine): CostRow {
  const { cost_line_id, document_number, document_date, amount, is_in_tracked_scope } = line;
  return {
    cost_line_id,
    document_number,
    document_date,
    amount,
    subproject_code: line.subproject_code,
    subproject_label: line.subproject_label,
    is_in_tracked_scope,
    ...(line.excluded_reason === undefined ? {} : { excluded_reason: line.excluded_reason }),
    ...(line.passthrough === undefined ? {} : { passthrough: line.passthrough }),
  };
}

/** The grid of the actual costs. */
export const COST_GRID: GridConfig<CostRow, CostSortColumn, ActualCostTotals> = {
  key: "actual_costs",
  name: "actualCosts",
  searched: false,
  rowKey: (line) => line.cost_line_id,
  columns: [
    {
      key: "document_number",
      label: "documentNumber",
      format: "text",
      width: 128,
      pinned: true,
      sortBy: "document_number",
      value: (line) => line.document_number,
    },
    {
      key: "document_date",
      label: "documentDate",
      format: "date",
      width: 104,
      sortBy: "document_date",
      value: (line) => line.document_date,
    },
    {
      key: "amount",
      label: "amount",
      format: "money",
      width: 120,
      sortBy: "amount",
      value: (line) => line.amount,
      total: (totals) => totals.overall,
    },
    {
      key: "subproject",
      label: "subproject",
      format: "text",
      width: 200,
      sortBy: "subproject",
      // The accessor of the sort alone: the cell names the sub-project, or that there is none.
      value: (line) => line.subproject_code,
      render: (line) => <SubprojectCell line={line} />,
    },
    {
      key: "tracked_scope",
      label: "trackedScope",
      format: "text",
      width: 112,
      sortBy: "in_tracked_scope",
      value: (line) => String(line.is_in_tracked_scope),
      render: (line) => <ScopeCell tracked={line.is_in_tracked_scope} />,
    },
    {
      key: "excluded_reason",
      label: "excludedReason",
      format: "text",
      width: 200,
      sortBy: "excluded_reason",
      value: (line) => line.excluded_reason,
    },
    {
      key: "passthrough",
      label: "passthrough",
      format: "text",
      width: 360,
      value: () => undefined,
      render: (line) => <PassthroughCell line={line} />,
    },
  ],
};

/** The columns of the contract the grid of the actual costs sorts by. */
export const COST_SORT_COLUMNS = sortColumns(COST_GRID);
