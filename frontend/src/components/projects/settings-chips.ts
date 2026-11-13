// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the lists of the settings of a project on, told as chips under the bar of their
 * table (WF-IHM-0130, #2916): the kinds of the work breakdown, whether the sub-projects are charged
 * with actual costs, the capacities and the accounts of the contributors, as the address of the
 * screen says them (`settings-grids.tsx`).
 */
"use client";

import { useTranslations } from "next-intl";

import { useChipKit } from "@/components/grid/chip-kit";
import type { FilterChip } from "@/components/grid/filter-chips";

import {
  BREAKDOWN_KIND_FILTER,
  type BreakdownKind,
  CONTRIBUTOR_ACTIVE,
  CONTRIBUTOR_KINDS,
  type ContributorKind,
  SUBPROJECT_ACTUAL_COSTS,
} from "./settings-grids";

/** The chip of the kinds the work breakdown is restricted to, if it is. */
export function useBreakdownChips(kinds: readonly BreakdownKind[] | undefined): FilterChip[] {
  const t = useTranslations();
  const kit = useChipKit();
  kit.values(
    BREAKDOWN_KIND_FILTER,
    t("grid.columns.breakdownKind"),
    (kinds ?? []).map((kind) => t(`enums.WorkBreakdownKind.${kind}`)),
  );
  return kit.chips;
}

/** The chip of whether the sub-projects are charged with actual costs, if the address says it. */
export function useSubprojectChips(actualCosts: boolean | undefined): FilterChip[] {
  const t = useTranslations();
  const kit = useChipKit();
  if (actualCosts !== undefined) {
    kit.add(
      SUBPROJECT_ACTUAL_COSTS,
      t("grid.columns.actualCosts"),
      actualCosts
        ? t("projectLists.subprojects.withActualCosts")
        : t("projectLists.subprojects.withoutActualCosts"),
      [SUBPROJECT_ACTUAL_COSTS],
    );
  }
  return kit.chips;
}

/** The chips of the capacities and of the state of the accounts the contributors are restricted to. */
export function useContributorChips(
  kinds: readonly ContributorKind[] | undefined,
  active: boolean | undefined,
): FilterChip[] {
  const t = useTranslations();
  const kit = useChipKit();
  kit.values(
    CONTRIBUTOR_KINDS,
    t("grid.columns.contributorKind"),
    (kinds ?? []).map((kind) => t(`enums.ContributorKind.${kind}`)),
  );
  if (active !== undefined) {
    kit.add(
      CONTRIBUTOR_ACTIVE,
      t("grid.columns.account"),
      active
        ? t("projectLists.contributors.activeAccounts")
        : t("projectLists.contributors.inactiveAccounts"),
      [CONTRIBUTOR_ACTIVE],
    );
  }
  return kit.chips;
}
