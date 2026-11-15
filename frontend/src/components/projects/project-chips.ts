// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the list of projects, the home, on, told as chips under the bar of its table
 * (WF-IHM-0130, #2916): the projects the user contributes to, a filter by default (WF-IHM-0120,
 * US-2130) — said, with the words « par défaut », while it applies, and lifted by naming that it is
 * lifted (`is_contributor=false`), an address that says nothing meaning the default —; the states
 * retained — said, with the words « par défaut », while they are the states by default, and lifted
 * by naming that every state is retained (`states=all`), by the same mechanism —; and the period of
 * the last modification.
 *
 * The filter of the contributor is told only to a session that may lift it: for any other, the list
 * lifted is the list filtered (WF-ADM-0110, #522), and a chip would offer a cross that changes
 * nothing; the card of the list says it instead (`page.tsx`).
 */
"use client";

import { useTranslations } from "next-intl";

import { useChipKit } from "@/components/grid/chip-kit";
import type { FilterChip } from "@/components/grid/filter-chips";
import type { Period } from "@/components/grid/period";
import {
  CONTRIBUTOR_PARAMETER,
  EVERY_STATE_VALUE,
  isDefaultStates,
  LIFTED_CONTRIBUTOR_VALUE,
  type ProjectState,
  STATES_PARAMETER,
} from "@/navigation/home";

/** What lifting a chip writes in the place of a filter applied by default. */
const INSTEAD: Readonly<Partial<Record<string, Readonly<Record<string, string>>>>> = {
  [CONTRIBUTOR_PARAMETER]: { [CONTRIBUTOR_PARAMETER]: LIFTED_CONTRIBUTOR_VALUE },
  [STATES_PARAMETER]: { [STATES_PARAMETER]: EVERY_STATE_VALUE },
};

/**
 * The chips of the filters of the list of projects that are on, in the order of the panel: `mine`
 * says whether the list is filtered on the projects the user contributes to — `undefined` for a
 * session that may not lift it, which has no chip.
 */
export function useProjectChips(
  mine: boolean | undefined,
  states: readonly ProjectState[] | undefined,
  period: Period | undefined,
): FilterChip[] {
  const t = useTranslations();
  const kit = useChipKit();
  if (mine === true) {
    kit.add(
      CONTRIBUTOR_PARAMETER,
      t("projectList.filter.projects"),
      t("projectList.filter.mineChip"),
      [CONTRIBUTOR_PARAMETER],
    );
  }
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
  // A filter by default lifted is said by the address, as it says nothing for the default.
  return kit.chips.map((chip) => {
    const instead = INSTEAD[chip.key];
    return instead === undefined ? chip : { ...chip, instead };
  });
}
