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

import { useLocale, useTranslations } from "next-intl";
import { useMemo } from "react";

import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";

import { costGrid, type CostRows, type CostSortColumn, keptColumns } from "./cost-grid";

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
  // A column for each column kept from the file the lines carry: the same configuration as long
  // as the page carries the same.
  const locale = useLocale();
  const kept = keptColumns(costs.items, locale).join("\u0000");
  const config = useMemo(() => costGrid(kept === "" ? [] : kept.split("\u0000")), [kept]);
  return (
    <DenseGrid
      config={config}
      rows={costs.items}
      totals={costs.totals}
      totalsCaption={() => t("generalTotal")}
      query={query}
      preferences={preferences}
    />
  );
}
