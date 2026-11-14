// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the register of the risks on, told as chips under the bar of its table
 * (WF-IHM-0130, #2916): the states, the zones of the matrix, the bounds of the probability and of
 * the amounts, and the period of the last review, as the address of the screen says them
 * (`address.ts`).
 */
"use client";

import { useLocale, useTranslations } from "next-intl";

import { useChipKit } from "@/components/grid/chip-kit";
import type { FilterChip } from "@/components/grid/filter-chips";
import { formatPlanningDate, isPlanningDate } from "@/i18n/format";

import {
  AMOUNT_COLUMNS,
  PROBABILITY,
  REVIEW_PERIOD,
  type RiskFilters,
  type RiskState,
  STATES,
  ZONES,
} from "./address";

/** The key of the heading of each column of figures in the catalogue of the columns of the grids. */
const HEADING = {
  probability: "probability",
  severity: "severity",
  provision_amount: "provisionAmount",
  occurrence_cost: "occurrenceCost",
  occurred_reestimated_amount: "occurredReestimatedAmount",
} as const;

/** The chips of the filters of the register that are on, in the order of the panel. */
export function useRiskChips(
  states: readonly RiskState[] | undefined,
  filters: RiskFilters | undefined,
  lastMarkedOn?: string,
): FilterChip[] {
  const t = useTranslations();
  const locale = useLocale();
  const kit = useChipKit();
  kit.values(
    STATES,
    t("grid.columns.state"),
    (states ?? []).map((state) => t(`enums.RiskState.${state}`)),
  );
  if (filters === undefined) {
    return kit.chips;
  }
  kit.values(
    ZONES,
    t("risks.filters.zoneChip"),
    filters.zones.map((zone) => t(`enums.AlertZone.${zone}`)),
  );
  kit.bounds(
    PROBABILITY,
    t(`grid.columns.${HEADING[PROBABILITY]}`),
    "decimal",
    filters.probability,
  );
  for (const column of AMOUNT_COLUMNS) {
    kit.bounds(column, t(`grid.columns.${HEADING[column]}`), "money", filters.amounts[column]);
  }
  const { review } = filters;
  if (lastMarkedOn !== undefined && review.to === lastMarkedOn && review.from === undefined) {
    // A period typed by hand with this same bound and no start is named as the shortcut: the
    // address does not tell them apart, and the register they filter is the same (#3031).
    // The shortcut of the periodic review (WF-RIS-0020), told as what it asks.
    kit.add(
      "review",
      t("risks.filters.unreviewed"),
      isPlanningDate(lastMarkedOn) ? formatPlanningDate(lastMarkedOn, locale) : lastMarkedOn,
      [REVIEW_PERIOD.from, REVIEW_PERIOD.to],
    );
  } else {
    kit.period("review", t("grid.columns.lastReview"), "date", review, REVIEW_PERIOD);
  }
  return kit.chips;
}
