// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configuration of the grid of the risks (WF-RIS-0040), the register of the risks of the
 * project as the revision read holds them: for each risk, its label, its probability, its
 * severity, the amount of its provision, its state and the date of its last review, and the cell
 * of the matrix that colours it. The same dense grid as the planning and the estimate: another
 * configuration, read only — a risk is entered by the epic of the risks (EP-08).
 *
 * Each column but the cell of the matrix sorts by the column of the contract of the same name, the
 * server sorting (WF-IHM-0130). The severity and the provision are computed (WF-RIS-0010,
 * WF-IHM-0030): columns computed whole, Σ in their header and in each cell, never entered; the
 * contract names no field of a node for them, so that their refusal says they are computed and no
 * more. The totals row shows the general total of the provisions the server gives, never a sum.
 */
import { Grid2x2 } from "lucide-react";

import type { components, operations } from "@/api/generated/schema";
import { type ComputedCells, type GridConfig, sortColumns } from "@/components/grid/columns";

import { RiskLabelCell, RiskStateCell, RiskZoneCell } from "./risk-cells";

/** A risk, as the contract gives it. */
type Risk = components["schemas"]["Risk"];

/** The totals of the provisions of the risks retained, as the server gives them. */
export type ProvisionTotals = components["schemas"]["ProvisionTotals"];

/** The column of the contract the server sorts the risks by. */
export type RiskSortColumn = NonNullable<
  NonNullable<operations["listRisks"]["parameters"]["query"]>["sort_by"]
>;

/** What the grid reads of a risk: the page hands it these fields alone. */
export const RISK_FIELDS = [
  "risk_id",
  "label",
  "probability",
  "severity",
  "provision_amount",
  "state",
  "last_review_on",
  "matrix_cell",
] as const satisfies readonly (keyof Risk)[];

/** A risk as the grid reads it. */
export type RiskRow = Pick<Risk, (typeof RISK_FIELDS)[number]>;

/** What the server answers of the risks of a revision, as the grid reads them. */
export interface RiskRows {
  readonly items: readonly RiskRow[];
  readonly totals: ProvisionTotals;
}

/**
 * The fields of a risk the grid reads, and those alone: a description, a mitigation note, an
 * audit do not cross to the browser with the rows.
 */
export function riskRow(risk: Risk): RiskRow {
  const { risk_id, label, probability, severity, provision_amount, state } = risk;
  return {
    risk_id,
    label,
    probability,
    severity,
    provision_amount,
    state,
    ...(risk.last_review_on === undefined ? {} : { last_review_on: risk.last_review_on }),
    ...(risk.matrix_cell === undefined ? {} : { matrix_cell: risk.matrix_cell }),
  };
}

/** A value the server computes in every risk, for which the contract names no field of a node. */
const COMPUTED_IN_EVERY_RISK: ComputedCells<RiskRow> = {
  whole: true,
  in: () => true,
  field: () => undefined,
};

/** The grid of the risks. */
export const RISK_GRID: GridConfig<RiskRow, RiskSortColumn, ProvisionTotals> = {
  key: "risks",
  name: "risks",
  rowKey: (risk) => risk.risk_id,
  columns: [
    {
      key: "label",
      label: "label",
      format: "text",
      width: 240,
      pinned: true,
      sortBy: "label",
      value: (risk) => risk.label,
      render: (risk) => <RiskLabelCell risk={risk} />,
    },
    {
      key: "probability",
      label: "probability",
      format: "percent",
      width: 88,
      sortBy: "probability",
      value: (risk) => risk.probability,
    },
    {
      key: "severity",
      label: "severity",
      format: "money",
      width: 120,
      computed: COMPUTED_IN_EVERY_RISK,
      sortBy: "severity",
      value: (risk) => risk.severity,
    },
    {
      key: "provision_amount",
      label: "provisionAmount",
      format: "money",
      width: 120,
      computed: COMPUTED_IN_EVERY_RISK,
      sortBy: "provision_amount",
      value: (risk) => risk.provision_amount,
      total: (totals) => totals.total,
    },
    {
      key: "state",
      label: "state",
      format: "text",
      width: 96,
      sortBy: "state",
      // The accessor of the sort alone: the cell names the state in the language of the interface.
      value: (risk) => risk.state,
      render: (risk) => <RiskStateCell state={risk.state} />,
    },
    {
      key: "last_review_on",
      label: "lastReview",
      format: "date",
      width: 104,
      sortBy: "last_review_on",
      value: (risk) => risk.last_review_on,
    },
    {
      key: "zone",
      label: "matrixCell",
      format: "text",
      align: "center",
      width: 44,
      icon: Grid2x2,
      // The server does not sort by the cell of the matrix: the column offers no sort.
      value: (risk) => risk.matrix_cell?.zone,
      render: (risk) => <RiskZoneCell risk={risk} />,
    },
  ],
};

/** The columns of the contract the grid of the risks sorts by. */
export const RISK_SORT_COLUMNS = sortColumns(RISK_GRID);
