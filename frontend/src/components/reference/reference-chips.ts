// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of the lists of the reference data on, told as chips under the bar of their table
 * (WF-IHM-0130, #2916): the nodes of the organisation, the resource roles, the calendars, the
 * natures and the categories of cost, as the address of each screen says them — a code, an object
 * chosen, a state, a type, the bounds of a column of figures. An object chosen is told by its code
 * and its name as the screen offers it; one the screen does not offer, by its identifier.
 */
"use client";

import { useTranslations } from "next-intl";

import { type ChipKit, useChipKit } from "@/components/grid/chip-kit";
import type { FilterChip } from "@/components/grid/filter-chips";
import type { Bounds } from "@/components/grid/filters";

import {
  CATEGORY_COST_TYPE,
  CATEGORY_STATE,
  COST_TYPE_KINDS,
  COST_TYPE_STATE,
  type CostTypeKind,
} from "./cost-grids";
import type { Choice } from "./kinds";
import { RATE_COLUMN, RATE_STATE, RATE_YEAR } from "./rate-columns";
import type { RateFilters } from "./cost-lists";
import type { OrgNodeFilters, RoleFilters } from "./resource-lists";
import {
  CALENDAR_STATE,
  ORG_CODE,
  ORG_LEVEL,
  ORG_STATE,
  ROLE_CALENDAR,
  ROLE_CODE,
  ROLE_COST_CATEGORY,
  ROLE_HEADCOUNT,
  ROLE_MONTHLY_HOURS,
  ROLE_ORG_NODE,
  ROLE_STATE,
} from "./resource-grids";

/** The chip of the state a list is filtered on, if it is. */
function useStateChip(): (kit: ChipKit, key: string, state: boolean | undefined) => void {
  const t = useTranslations();
  return (kit, key, state) => {
    if (state !== undefined) {
      kit.add(
        key,
        t("grid.columns.state"),
        state ? t("reference.stateFilter.active") : t("reference.stateFilter.inactive"),
        [key],
      );
    }
  };
}

/** An object chosen, told by its code and its name as the screen offers it, else its identifier. */
function useChosen(): (id: string, offered: readonly Choice[] | undefined) => string {
  const t = useTranslations("reference");
  return (id, offered) => {
    const found = offered?.find((choice) => choice.id === id);
    if (found === undefined) {
      return id;
    }
    return found.code === undefined || found.code === ""
      ? found.label
      : t("codedChoice", { code: found.code, label: found.label });
  };
}

/** The chips of the filters of the tree of the organisation that are on. */
export function useOrgNodeChips(filters: OrgNodeFilters | undefined): FilterChip[] {
  const t = useTranslations("grid.columns");
  const kit = useChipKit();
  const state = useStateChip();
  if (filters === undefined) {
    return kit.chips;
  }
  if (filters.code !== undefined) {
    kit.add(ORG_CODE, t("code"), filters.code, [ORG_CODE]);
  }
  if (filters.level !== undefined) {
    kit.add(ORG_LEVEL, t("level"), filters.level.toString(), [ORG_LEVEL]);
  }
  state(kit, ORG_STATE, filters.state);
  kit.bounds(ORG_LEVEL, t("level"), "level", filters.levels);
  return kit.chips;
}

/** The chips of the filters of the resource roles that are on. */
export function useRoleChips(
  filters: RoleFilters | undefined,
  offered: {
    readonly nodes?: readonly Choice[] | undefined;
    readonly categories?: readonly Choice[] | undefined;
    readonly calendars?: readonly Choice[] | undefined;
  },
): FilterChip[] {
  const t = useTranslations("grid.columns");
  const kit = useChipKit();
  const state = useStateChip();
  const chosen = useChosen();
  if (filters === undefined) {
    return kit.chips;
  }
  if (filters.code !== undefined) {
    kit.add(ROLE_CODE, t("code"), filters.code, [ROLE_CODE]);
  }
  const objects = [
    [ROLE_ORG_NODE, t("orgNode"), filters.orgNode, offered.nodes],
    [ROLE_COST_CATEGORY, t("costCategory"), filters.category, offered.categories],
    [ROLE_CALENDAR, t("calendar"), filters.calendar, offered.calendars],
  ] as const;
  for (const [key, name, id, list] of objects) {
    if (id !== undefined) {
      kit.add(key, name, chosen(id, list), [key]);
    }
  }
  state(kit, ROLE_STATE, filters.state);
  const figures: readonly [string, string, Bounds][] = [
    [ROLE_MONTHLY_HOURS, t("monthlyHours"), filters.monthlyHours],
    [ROLE_HEADCOUNT, t("headcount"), filters.headcount],
  ];
  for (const [column, name, bounds] of figures) {
    kit.bounds(column, name, "decimal", bounds);
  }
  return kit.chips;
}

/** The chips of the filter of the calendars that is on: their state. */
export function useCalendarChips(active: boolean | undefined): FilterChip[] {
  const kit = useChipKit();
  useStateChip()(kit, CALENDAR_STATE, active);
  return kit.chips;
}

/** The chips of the filters of the natures of cost that are on: their types, their state. */
export function useCostTypeChips(
  kinds: readonly CostTypeKind[] | undefined,
  active: boolean | undefined,
): FilterChip[] {
  const t = useTranslations();
  const kit = useChipKit();
  kit.values(
    COST_TYPE_KINDS,
    t("grid.columns.costTypeKind"),
    (kinds ?? []).map((kind) => t(`enums.CostTypeKind.${kind}`)),
  );
  useStateChip()(kit, COST_TYPE_STATE, active);
  return kit.chips;
}

/** The chips of the filters of the categories of cost that are on: their nature, their state. */
export function useCostCategoryChips(
  nature: string | undefined,
  natures: readonly Choice[] | undefined,
  active: boolean | undefined,
): FilterChip[] {
  const t = useTranslations("grid.columns");
  const kit = useChipKit();
  const chosen = useChosen();
  if (nature !== undefined) {
    kit.add(CATEGORY_COST_TYPE, t("costType"), chosen(nature, natures), [CATEGORY_COST_TYPE]);
  }
  useStateChip()(kit, CATEGORY_STATE, active);
  return kit.chips;
}

/**
 * The chips of the filters of the grid of the hourly rates that are on: the state of the
 * categories, and the bounds of the rate of a year — the one the address names, else the last of
 * the grid —, lifted together with that year.
 */
export function useRateChips(
  filters: RateFilters | undefined,
  years: readonly number[],
): FilterChip[] {
  const t = useTranslations("reference.rates.bounds");
  const kit = useChipKit();
  const state = useStateChip();
  if (filters === undefined) {
    return kit.chips;
  }
  state(kit, RATE_STATE, filters.state);
  const year = filters.year ?? years.at(-1);
  kit.bounds(RATE_COLUMN, t("chip", { year: year?.toString() ?? "" }), "money", filters.rate, {
    with: [RATE_YEAR],
  });
  return kit.chips;
}
