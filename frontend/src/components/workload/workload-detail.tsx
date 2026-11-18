// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The detail of the workload by role and by task (WF-DEV-0090, US-2040), under its chart: the dense
 * grid, read only, a tree from the role to the task that folds, a column for each month of the plan
 * (`detail-columns.tsx`). It has no setting of its own: it reads the plan the chart reads, on the
 * basis and under the node of organisation the screen chose — the server computes, filters and
 * orders, the grid sums nothing (WF-ARC-0070). A task leads to its row in the planning grid of the
 * revision the basis reads, which shows and aims at it (`planning-target.ts`). The page hands it
 * data only.
 */
"use client";

import { useLocale, useTranslations } from "next-intl";
import { useMemo } from "react";

import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import { formatMonth } from "@/i18n/format";

import { detailGrid } from "./detail-columns";
import type { WorkloadDetail } from "./detail-rows";

/** What the grid asks of the address: nothing, it sorts and searches nothing. */
const UNASKED: GridQuery<never> = { sort: undefined, search: undefined, size: undefined };

/** What the grid of the detail shows. */
export interface WorkloadDetailGridProps {
  readonly detail: WorkloadDetail;
  /** The revision the plan reads, for which the grid keeps its folds. */
  readonly revision: string;
  /** The settings of the grid the session read, if any. */
  readonly preferences: GridPreferences | undefined;
}

/** Render the grid of the detail of the workload. */
export function WorkloadDetailGrid({ detail, revision, preferences }: WorkloadDetailGridProps) {
  const t = useTranslations("workload");
  const locale = useLocale();
  const { months } = detail;
  const config = useMemo(
    () => detailGrid(months, (month) => formatMonth(month, locale)),
    [months, locale],
  );
  return (
    <DenseGrid
      config={config}
      rows={detail.rows}
      totals={detail.totals}
      totalsCaption={() => t("detailTotals")}
      query={UNASKED}
      preferences={preferences}
      foldScope={revision}
      stacked
    />
  );
}
