// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configuration of the grid of the spending projection (WF-DEV-0100, US-2050): a tree from the
 * cost type to its category, read only, in the order of the API — no header sorts, nothing is
 * searched —; the label of each row under the icon of its nature; then one column for each month of
 * the projection, headed by the month, and the total of the row; the totals of the months, and that
 * of the projection, at the foot as the API sums them. Each column with its definition, which the
 * grid and the help of its screen both read.
 *
 * Neither server nor client: the grid renders it in the browser; `help/read.ts` reads its columns
 * on the server, their titles and definitions only.
 */
import { Layers, Tag } from "lucide-react";
import { useTranslations } from "next-intl";

import type { GridColumn, GridConfig } from "@/components/grid/columns";

import { SPENDING_GRID_KEY, type SpendingRow, type SpendingTotals } from "./spending-rows";

/** A column of the grid of the projection: it sorts nothing. */
type SpendingColumn = GridColumn<SpendingRow, never, SpendingTotals>;

/** The icon of the nature of a row, named for it: a cost type, a cost category. */
function SpendingNature({ kind }: { readonly kind: SpendingRow["kind"] }) {
  const t = useTranslations("spending");
  const Icon = kind === "cost_type" ? Layers : Tag;
  return (
    <Icon
      role="img"
      aria-label={kind === "cost_type" ? t("costType") : t("costCategory")}
      className="size-3.5 shrink-0 text-muted-foreground"
    />
  );
}

/** The column of a month: its amount in each row, as the API gives it, its total at the foot. */
function monthColumn(month: string, heading: string): SpendingColumn {
  return {
    key: `month_${month}`,
    label: "month",
    heading,
    help: "spendingDetail.month",
    format: "money",
    width: 112,
    value: (row) => row.months[month],
    total: (totals) => totals.months[month],
  };
}

/**
 * The grid of the projection, a column for each month of it, headed as `heading` writes the month
 * in the language of the interface.
 */
export function spendingGrid(
  months: readonly string[],
  heading: (month: string) => string,
): GridConfig<SpendingRow, never, SpendingTotals> {
  return {
    key: SPENDING_GRID_KEY,
    name: "spendingDetail",
    searched: false,
    sorts: false,
    rowKey: (row) => row.key,
    tree: {
      level: (row) => (row.kind === "cost_type" ? 1 : 2),
      nature: (row) => <SpendingNature kind={row.kind} />,
      emphasis: (row) => (row.kind === "cost_type" ? "strong" : undefined),
      parent: (row) => row.parent,
    },
    columns: [
      {
        key: "label",
        label: "label",
        help: "spendingDetail.label",
        format: "text",
        width: 280,
        pinned: true,
        value: (row) => row.label,
      },
      {
        key: "total",
        label: "total",
        help: "spendingDetail.total",
        format: "money",
        width: 128,
        value: (row) => row.total,
        total: (totals) => totals.total,
      },
      ...months.map((month) => monthColumn(month, heading(month))),
    ],
  };
}
