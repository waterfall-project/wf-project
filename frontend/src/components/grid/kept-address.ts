// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The search and the filters of a grid kept with its settings (WF-IHM-0060, US-0380), as the address
 * writes them (`GridConfig.filters`), and the address that says nothing of the grid. The address is
 * the truth of the screen: the filters kept serve only when it says nothing of the grid — neither
 * sort, nor search, nor filter —, which the page then replaces, on the server, by the address of the
 * filters kept (`restoredAddress`), as the sort kept serves when the address says no sort
 * (`readGridQuery`). A reading lifted within the screen is said by the address itself: a change that
 * would leave it saying nothing of the grid writes the search, empty (`spokenHref`), as a sort lifted
 * writes `sort_by` empty.
 *
 * Pure, and neither server nor client: the page restores, the screen writes, the grid records
 * (`kept-filters.ts`).
 */
import type { SearchParameters } from "@/navigation/context";

import type { GridAddress } from "./query";

/** The filters of a reading, as the address writes them: each parameter, and its value. */
export type KeptFilters = Readonly<Record<string, string>>;

/** The parameters of the address a grid reads: its search, its filters, and its sort. */
export interface KeptReading {
  /** The parameter of the search, which says a reading lifted when empty. */
  readonly search: string;
  /** The search and the filters, kept with the settings of the grid. */
  readonly filters: readonly string[];
  /** The sort, which the settings keep apart (`GridPreferences.sort`). */
  readonly sort: readonly string[];
  /** The size of its pages, which the address carries and the settings keep apart (`page_size`). */
  readonly size: readonly string[];
}

/** The parameters a grid reads, under the names of its address, its filters besides its search. */
export function keptReading(address: GridAddress, filters: readonly string[]): KeptReading {
  return {
    search: address.search,
    filters: [address.search, ...filters],
    sort: [address.sortBy, address.sortOrder],
    size: [address.limit],
  };
}

/**
 * The search and the filters of a reading a source gives, each a text that says something — an empty
 * search is a reading lifted, which keeps nothing.
 */
export function keptFilters(reading: KeptReading, source: (name: string) => unknown): KeptFilters {
  return Object.fromEntries(
    reading.filters.flatMap((name) => {
      const value = source(name);
      return typeof value === "string" && value !== "" ? [[name, value]] : [];
    }),
  );
}

/** Whether two readings filter alike. */
export function sameFilters(one: KeptFilters, other: KeptFilters): boolean {
  const names = Object.keys(one);
  return names.length === Object.keys(other).length && names.every((n) => one[n] === other[n]);
}

/** Whether an address says nothing of a grid: neither its sort, nor its page size, nor its search, nor its filters. */
function silent(reading: KeptReading, has: (name: string) => boolean): boolean {
  return [...reading.filters, ...reading.sort, ...reading.size].every((name) => !has(name));
}

/**
 * The address of the filters kept, on the server, for a page opened at an address that says nothing
 * of its grid — the link of the navigation, from the screen itself too —; none when the address says
 * something of it, or when nothing is kept.
 */
export function restoredAddress(
  pathname: string,
  search: SearchParameters,
  reading: KeptReading,
  kept: Readonly<Record<string, unknown>> | null | undefined,
): string | undefined {
  if (!silent(reading, (name) => search.get(name) !== null)) {
    return undefined;
  }
  const filters = keptFilters(reading, (name) => kept?.[name]);
  return Object.keys(filters).length === 0
    ? undefined
    : `${pathname}?${new URLSearchParams(filters).toString()}`;
}

/**
 * An address the screen navigates to, saying a reading lifted when it would say nothing of the grid:
 * the search written empty, so that the page does not find the filters kept again.
 */
export function spokenHref(href: string, reading: KeptReading): string {
  const [pathname = "", query = ""] = href.split("?");
  const next = new URLSearchParams(query);
  if (!silent(reading, (name) => next.has(name))) {
    return href;
  }
  next.set(reading.search, "");
  return `${pathname}?${next.toString()}`;
}
