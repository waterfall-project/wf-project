// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the list of the projects of the portfolio on, told as chips under the bar of its
 * grid (WF-IHM-0130-A, #2916): the zones of the indices, the code, the bounds of the columns of
 * figures and the period of the last marking, as the address says them (`address.ts`).
 */
"use client";

import { useTranslations } from "next-intl";

import { useChipKit } from "@/components/grid/chip-kit";
import type { FilterChip } from "@/components/grid/filter-chips";
import type { Bounds } from "@/components/grid/filters";

import {
  AMOUNT_COLUMNS,
  type AmountColumn,
  CODE,
  INDEX_COLUMNS,
  type IndexColumn,
  MARKED_PERIOD,
  type ProjectFilters,
  WIN_PROBABILITY,
  ZONES,
} from "./address";

/** A column of figures of the list the address bounds. */
export type BoundedColumn = AmountColumn | IndexColumn | typeof WIN_PROBABILITY;

/** The key of the heading of each bounded column in the catalogue of the columns of the grids. */
export const BOUNDED_HEADING = {
  reference_budget: "referenceBudget",
  current_estimate: "currentEstimate",
  project_manager_projection: "projectManagerProjection",
  delta_to_reference: "deltaToReference",
  win_probability: "winProbability",
  cost_index: "costIndex",
  schedule_index: "scheduleIndex",
} as const satisfies Readonly<Record<BoundedColumn, string>>;

/** The bounds the filters set on a column. */
export function boundsOf(filters: ProjectFilters, column: BoundedColumn): Bounds {
  if (column === WIN_PROBABILITY) {
    return filters.winProbability;
  }
  return column === "cost_index" || column === "schedule_index"
    ? filters.indices[column]
    : filters.amounts[column];
}

/** The chips of the filters of the list that are on, in the order of the panel. */
export function useProjectChips(filters: ProjectFilters | undefined): FilterChip[] {
  const t = useTranslations();
  const kit = useChipKit();
  if (filters === undefined) {
    return kit.chips;
  }
  kit.values(
    ZONES,
    t("portfolio.projects.zoneChip"),
    filters.zones.map((zone) => t(`enums.AlertZone.${zone}`)),
  );
  if (filters.code !== undefined) {
    kit.add(CODE, t("grid.columns.code"), filters.code, [CODE]);
  }
  for (const column of AMOUNT_COLUMNS) {
    kit.bounds(
      column,
      t(`grid.columns.${BOUNDED_HEADING[column]}`),
      "money",
      boundsOf(filters, column),
    );
  }
  kit.bounds(
    WIN_PROBABILITY,
    t(`grid.columns.${BOUNDED_HEADING[WIN_PROBABILITY]}`),
    "decimal",
    filters.winProbability,
  );
  for (const column of INDEX_COLUMNS) {
    kit.bounds(
      column,
      t(`grid.columns.${BOUNDED_HEADING[column]}`),
      "decimal",
      boundsOf(filters, column),
    );
  }
  kit.period("marked", t("grid.columns.lastMarkedAt"), "day", filters.marked, MARKED_PERIOD);
  return kit.chips;
}
