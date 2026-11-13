// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the list of projects, the home, on, told as chips under the bar of its table
 * (WF-IHM-0130, #2916): the states retained — said, with the words « par défaut », while they are
 * the states by default, and lifted by naming that every state is retained (`states=all`), an
 * address that says nothing meaning the default — and the period of the last modification.
 */
"use client";

import { useTranslations } from "next-intl";

import { useChipKit } from "@/components/grid/chip-kit";
import type { FilterChip } from "@/components/grid/filter-chips";
import type { Period } from "@/components/grid/period";
import {
  EVERY_STATE_VALUE,
  isDefaultStates,
  type ProjectState,
  STATES_PARAMETER,
} from "@/navigation/home";

/** The chips of the filters of the list of projects that are on, in the order of the panel. */
export function useProjectChips(
  states: readonly ProjectState[] | undefined,
  period: Period | undefined,
): FilterChip[] {
  const t = useTranslations();
  const kit = useChipKit();
  if (states !== undefined && states.length > 0) {
    const told = states.map((state) => t(`enums.ProjectState.${state}`)).join(", ");
    kit.add(
      STATES_PARAMETER,
      t("grid.columns.state"),
      isDefaultStates(states) ? t("projectList.filter.defaultChip", { states: told }) : told,
      [STATES_PARAMETER],
    );
  }
  if (period !== undefined) {
    kit.period("period", t("grid.columns.updatedAt"), "day", period);
  }
  // A state lifted is every state: the address says it, as it says nothing for the default.
  return kit.chips.map((chip) =>
    chip.key === STATES_PARAMETER
      ? { ...chip, instead: { [STATES_PARAMETER]: EVERY_STATE_VALUE } }
      : chip,
  );
}
