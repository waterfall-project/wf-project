// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the risks in the page: the dense grid, given its configuration here, on the side of
 * the browser — a configuration reads the rows by functions, which never cross from a server
 * component to a client one. The page hands it data only: the risks of the answer of `listRisks`
 * as the grid reads them (`riskRow`), the totals of the answer, what the address asked and the
 * settings the session read. Read only: no cell is entered, and the computed ones refuse.
 */
"use client";

import { useTranslations } from "next-intl";

import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";

import { RISK_GRID, type RiskRows, type RiskSortColumn } from "./risk-grid";

/** What the grid of the risks shows. */
export interface RisksGridProps {
  /** The risks of the answer, as the grid reads them, and the totals of the answer. */
  readonly risks: RiskRows;
  readonly query: GridQuery<RiskSortColumn>;
  readonly preferences: GridPreferences | undefined;
}

/** Render the grid of the risks, its totals row the general total of the provisions retained. */
export function RisksGrid({ risks, query, preferences }: RisksGridProps) {
  const t = useTranslations("risks");
  return (
    <DenseGrid
      config={RISK_GRID}
      rows={risks.items}
      totals={risks.totals}
      totalsCaption={() => t("generalTotal")}
      query={query}
      preferences={preferences}
    />
  );
}
