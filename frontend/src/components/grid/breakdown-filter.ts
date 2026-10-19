// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of a grid of the structure by a lot or by a post of the work breakdown — the planning
 * (WF-PLA-0080), the estimate (WF-DEV-0050) —, as the address carries it, under the names of the
 * contract: `work_package_id` for a lot, `order_item_id` for a post, one at a time. The server
 * retains the subtree of the task that bears the lot or the post, and the ancestors of what it
 * retains (`listNodes`, WF-PLA-0170); the front selects nothing. The lots and the posts it is chosen
 * among are those of the work breakdown read whole (`getWorkBreakdown`, `breakdownItems`), never a
 * list written here.
 *
 * Pure, and neither server nor client: the page reads the address, the filter writes it.
 */
import type { SearchParameters } from "@/navigation/context";

import { filterHref } from "./filters";
import type { NodeFilters } from "./nodes";
import type { BreakdownItem, BreakdownKind } from "./planning-attachment";

/** The parameter of `listNodes` that filters by an item of the work breakdown, by its kind. */
export const BREAKDOWN_PARAMETERS = {
  work_package: "work_package_id",
  order_item: "order_item_id",
} as const satisfies Record<BreakdownKind, keyof NodeFilters>;

/** A parameter of the address that filters a grid by a lot or by a post. */
export type BreakdownParameter = (typeof BREAKDOWN_PARAMETERS)[BreakdownKind];

/** The lot or the post the address filters a grid by, by the parameter that names it. */
export interface BreakdownFilter {
  readonly kind: BreakdownKind;
  readonly name: BreakdownParameter;
  readonly value: string;
}

/**
 * The lot or the post the address filters by: the lot when it names one, the post otherwise; none
 * when it names neither. One alone is read — the filter offers one at a time, and lifts the other
 * when it writes —: what the grid sends is what its filter shows.
 */
export function readBreakdownFilter(search: SearchParameters): BreakdownFilter | undefined {
  for (const kind of ["work_package", "order_item"] as const) {
    const name = BREAKDOWN_PARAMETERS[kind];
    const value = search.get(name);
    if (value !== null && value !== "") {
      return { kind, name, value };
    }
  }
  return undefined;
}

/** What a reading of the nodes asks of the server for the filter: its one parameter, or nothing. */
export function breakdownQuery(
  filter: BreakdownFilter | undefined,
): Pick<NodeFilters, BreakdownParameter> {
  return filter === undefined ? {} : { [filter.name]: filter.value };
}

/** The lots and the posts a grid is filtered by, and the one the address names. */
export interface BreakdownChoices {
  /** The lots and the posts of the work breakdown read whole, in its order. */
  readonly items: readonly BreakdownItem[];
  readonly filter: BreakdownFilter | undefined;
}

/**
 * The filter active, as the banner of the context shows it (WF-IHM-0020): the lot or the post — none
 * found when the work breakdown does not have it, the identifier of the address shown —, and the
 * address of the same screen without it, the rest of its query — search, sort, context — kept.
 */
export interface BreakdownChip {
  readonly filter: BreakdownFilter;
  readonly item: BreakdownItem | undefined;
  readonly lift: string;
}

/** The chip of the filter the address names, lifted by the address of `pathname` without it. */
export function breakdownChip(
  choices: BreakdownChoices | undefined,
  pathname: string,
  query: URLSearchParams,
): BreakdownChip | undefined {
  const filter = choices?.filter;
  if (filter === undefined) {
    return undefined;
  }
  return {
    filter,
    item: choices?.items.find((item) => item.id === filter.value && item.kind === filter.kind),
    // Both parameters lifted: one the filter does not read would take its place.
    lift: filterHref(pathname, query, filter.name, undefined, Object.values(BREAKDOWN_PARAMETERS)),
  };
}
