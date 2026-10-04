// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the actual costs in the page: the dense grid, given its configuration here, on the
 * side of the browser — a configuration reads the rows by functions, which never cross from a
 * server component to a client one. The page hands it data only: the lines of a page of
 * `listActualCosts` as the grid reads them (`costRow`), the totals of the answer, what the address
 * asked and the settings the session read. Read only: no cell is entered.
 */
"use client";

import { useTranslations } from "next-intl";

import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";

import { COST_GRID, type CostRows, type CostSortColumn } from "./cost-grid";

/** What the grid of the actual costs shows. */
export interface CostsGridProps {
  /** The lines of the page, as the grid reads them, and the totals of every line retained. */
  readonly costs: CostRows;
  readonly query: GridQuery<CostSortColumn>;
  readonly preferences: GridPreferences | undefined;
}

/** Render the grid of the actual costs, its totals row the general total of the lines retained. */
export function CostsGrid({ costs, query, preferences }: CostsGridProps) {
  const t = useTranslations("actualCosts");
  return (
    <DenseGrid
      config={COST_GRID}
      rows={costs.items}
      totals={costs.totals}
      totalsCaption={() => t("generalTotal")}
      query={query}
      preferences={preferences}
    />
  );
}
