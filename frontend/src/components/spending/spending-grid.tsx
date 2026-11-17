// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the spending projection (WF-DEV-0100, US-2050), under its chart: the dense grid, read
 * only, a tree from the cost type to the category that folds, a column for each month
 * (`spending-columns.tsx`), the total of each row after its label and the totals of the months at
 * the foot. It has no setting of its own: it reads the projection the chart reads, on the basis, the
 * date and the sub-project the screen chose — the server computes and orders, the grid sums nothing
 * (WF-ARC-0020). The page hands it data only.
 */
"use client";

import { useLocale, useTranslations } from "next-intl";
import { useMemo } from "react";

import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import { formatMonth } from "@/i18n/format";

import { spendingGrid } from "./spending-columns";
import type { SpendingDetail } from "./spending-rows";

/** What the grid asks of the address: nothing, it sorts and searches nothing. */
const UNASKED: GridQuery<never> = { sort: undefined, search: undefined, size: undefined };

/** What the grid of the projection shows. */
export interface SpendingGridProps {
  readonly detail: SpendingDetail;
  /** The revision the projection reads, for which the grid keeps its folds. */
  readonly revision: string;
  /** The settings of the grid the session read, if any. */
  readonly preferences: GridPreferences | undefined;
}

/** Render the grid of the spending projection. */
export function SpendingGrid({ detail, revision, preferences }: SpendingGridProps) {
  const t = useTranslations("spending");
  const locale = useLocale();
  const { months } = detail;
  const config = useMemo(
    () => spendingGrid(months, (month) => formatMonth(month, locale)),
    [months, locale],
  );
  return (
    <DenseGrid
      config={config}
      rows={detail.rows}
      totals={detail.totals}
      totalsCaption={() => t("gridTotals")}
      query={UNASKED}
      preferences={preferences}
      foldScope={revision}
      stacked
    />
  );
}
