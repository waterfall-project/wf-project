// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of a grid of the structure by a lot or by a post of the work breakdown — the planning
 * (WF-PLA-0080), the estimate (WF-DEV-0050) —, as the address carries it, under the names of the
 * contract: `work_package_id` for a lot, `order_item_id` for a post, one at a time. The server
 * retains the subtree of the task that bears the lot or the post, and the ancestors of what it
 * retains (`listNodes`, WF-PLA-0170); the front selects nothing. The lots and the posts it is
 * chosen among are those of the work breakdown read whole (`getWorkBreakdown`, `breakdownItems`),
 * never a list written here.
 *
 * Pure, and neither server nor client: the page reads the address, the filter writes it.
 */
import { isUuid, type SearchParameters } from "@/navigation/context";

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
 * when it writes —: what the grid sends is what its filter shows. A value that is no identifier
 * of the contract (`Uuid`) is not read, as if the address named nothing: the API would refuse it.
 */
export function readBreakdownFilter(search: SearchParameters): BreakdownFilter | undefined {
  for (const kind of ["work_package", "order_item"] as const) {
    const name = BREAKDOWN_PARAMETERS[kind];
    const value = search.get(name);
    if (value !== null && isUuid(value)) {
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
 * The filter active, as the banner of the context shows it (WF-IHM-0020): the lot or the post —
 * none found when the work breakdown does not have it, the identifier of the address shown —, and
 * its parameters being those a link lifts it by (`BREAKDOWN_PARAMETERS`).
 */
export interface BreakdownChip {
  readonly filter: BreakdownFilter;
  readonly item: BreakdownItem | undefined;
}

/**
 * The chip of the filter the address names, its item found among `items` — none given when the work breakdown could not be read.
 */
export function breakdownChip(
  filter: BreakdownFilter | undefined,
  items: readonly BreakdownItem[] | undefined,
): BreakdownChip | undefined {
  if (filter === undefined) {
    return undefined;
  }
  return {
    filter,
    item: items?.find((item) => item.id === filter.value && item.kind === filter.kind),
  };
}
