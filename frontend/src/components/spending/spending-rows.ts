// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the grid of the spending projection reads of it (WF-DEV-0100, US-2050): one row for each cost
 * type, in the order of the reference data the API gives, and under it one row for each of its
 * categories; the amount of each month and the total of each row as the API gives them, a month the
 * API leaves out of a row left blank, never filled with a zero. The totals of the months and the
 * total of the projection are the API's (`monthly_totals`, `total`). Nothing is summed, ordered nor
 * filtered here (WF-ARC-0020).
 *
 * The page reads them on the server and hands them to the grid as they are: data only. No module
 * here is a client one.
 */
import type { components } from "@/api/generated/schema";

/** The spending projection of a project, as the API computes it. */
export type SpendingPlan = components["schemas"]["SpendingProjection"];

/** The key under which the account keeps the settings of the grid of the projection. */
export const SPENDING_GRID_KEY = "spending_projection";

/** The amount of a row, by the month the API names (`2026-06`); a month without amount is absent. */
export type MonthAmounts = Readonly<Record<string, string>>;

/** A row of the projection: a cost type, or a category under it. */
export interface SpendingRow {
  /** The identity of the row: the cost type, or the cost type and the category. */
  readonly key: string;
  /** The cost type a category is under; none for a cost type. */
  readonly parent: string | null;
  readonly kind: "cost_type" | "category";
  readonly label: string;
  /** The total of the row, as the API sums it. */
  readonly total: string;
  readonly months: MonthAmounts;
}

/** The totals of the projection: those of its months, and its own, as the API sums them. */
export interface SpendingTotals {
  readonly months: MonthAmounts;
  readonly total: string;
}

/** The projection, as the grid reads it. */
export interface SpendingDetail {
  readonly rows: readonly SpendingRow[];
  /** The months of the projection, ascending and without gaps (`monthly_totals`): one column each. */
  readonly months: readonly string[];
  readonly totals: SpendingTotals;
}

/** The amounts of a list of months of the API, by their month. */
function byMonth(
  months: readonly { readonly month: string; readonly amount: string }[],
): MonthAmounts {
  return Object.fromEntries(months.map(({ month, amount }) => [month, amount]));
}

/**
 * The grid of a projection: each cost type, then its categories, in the order of the API; the
 * months of the projection and their totals, as the API gives them.
 */
export function spendingDetail(plan: SpendingPlan): SpendingDetail {
  return {
    rows: plan.cost_types.flatMap((type) => [
      {
        key: type.cost_type_id,
        parent: null,
        kind: "cost_type" as const,
        label: type.label,
        total: type.total,
        months: byMonth(type.months),
      },
      ...type.categories.map((category) => ({
        key: `${type.cost_type_id}:${category.cost_category_id}`,
        parent: type.cost_type_id,
        kind: "category" as const,
        label: category.label,
        total: category.total,
        months: byMonth(category.months),
      })),
    ]),
    months: plan.monthly_totals.map(({ month }) => month),
    totals: { months: byMonth(plan.monthly_totals), total: plan.total },
  };
}
