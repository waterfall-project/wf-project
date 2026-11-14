// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the actual costs on, told as chips under the bar of their table (WF-IHM-0130,
 * #2916): the scope, the sub-project and the period of the documents, as the address of the screen
 * says them (`address.ts`). A sub-project the project does not hold is told as the filter says it.
 */
"use client";

import { useTranslations } from "next-intl";

import { useChipKit } from "@/components/grid/chip-kit";
import type { FilterChip } from "@/components/grid/filter-chips";
import { UNASSIGNED } from "@/navigation/context";

import { type CostFilters, SCOPE, SUBPROJECT } from "./address";
import type { SubprojectChoice } from "./cost-filters";

/** The chips of the filters of the actual costs that are on, in the order of the panel. */
export function useCostChips(
  filters: CostFilters | undefined,
  subproject: string | undefined,
  subprojects: readonly SubprojectChoice[] | undefined,
): FilterChip[] {
  const t = useTranslations();
  const kit = useChipKit();
  if (filters === undefined) {
    return kit.chips;
  }
  if (filters.scope !== undefined) {
    kit.add(SCOPE, t("grid.columns.trackedScope"), t(`actualCosts.filters.${filters.scope}`), [
      SCOPE,
    ]);
  }
  if (subproject !== undefined) {
    const found = (subprojects ?? []).find((choice) => choice.id === subproject);
    let told: string;
    if (subproject === UNASSIGNED) {
      told = t("enums.SubprojectFilter.unassigned");
    } else if (found === undefined) {
      told = t("actualCosts.filters.unknownSubproject");
    } else {
      told = t("actualCosts.filters.subprojectChoice", { code: found.code, label: found.label });
    }
    kit.add(SUBPROJECT, t("grid.columns.subproject"), told, [SUBPROJECT]);
  }
  kit.period("period", t("grid.columns.documentDate"), "date", filters);
  return kit.chips;
}
