// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a grid asks the server, as the address carries it (EP-02, « Contexte de lecture » : the
 * address is the truth): the sort, by the parameters of the contract — `sort_by`, a column,
 * and `sort_order`, its direction —, and the search on the labels, `search`. The server
 * component reads them and asks the API with them; a header clicked, a search entered only
 * change the address. The rows come back in the order the server gives, with the totals of
 * what it retained: the front orders nothing, sums nothing, filters nothing (WF-ARC-0020).
 *
 * Pure, and neither server nor client: the page reads, the grid writes.
 */
import type { components } from "@/api/generated/schema";
import type { SearchParameters } from "@/navigation/context";

/** The direction of a sort, as the contract names it. */
export type SortOrder = components["schemas"]["SortOrder"];

/** A sort the server is asked for: a column of the contract, and its direction. */
export interface GridSort<Sort extends string> {
  readonly column: Sort;
  readonly order: SortOrder;
}

/** What a grid asks the server, besides its reading context. */
export interface GridQuery<Sort extends string> {
  readonly sort: GridSort<Sort> | undefined;
  /** The search on the labels; none when the address holds none. */
  readonly search: string | undefined;
}

/** The parameters of the address a grid writes, as the contract names them. */
export const SORT_BY = "sort_by";
export const SORT_ORDER = "sort_order";
export const SEARCH = "search";

/** The longest search the contract accepts. */
export const SEARCH_LENGTH = 200;

/** The sort a grid keeps in the preferences of the account, as the contract gives it. */
export interface KeptSort {
  readonly column: string;
  readonly order: string;
}

/** A column the grid sorts, and a direction of the contract, or no sort. */
function sortOf<Sort extends string>(
  sortable: readonly Sort[],
  by: string | null | undefined,
  order: string | null | undefined,
): GridSort<Sort> | undefined {
  const column = sortable.find((candidate) => candidate === by);
  return column === undefined ? undefined : { column, order: order === "desc" ? "desc" : "asc" };
}

/**
 * Read what the address asks of a grid: a sort by one of the columns the grid sorts, ascending
 * unless the address says descending — the default of the contract —; a search of the length
 * the contract accepts. Anything else in the address is not asked: the API would refuse it.
 * The address is the truth of the screen: the sort the account keeps for the grid serves only
 * when the address asks none (WF-IHM-0060).
 */
export function readGridQuery<Sort extends string>(
  search: SearchParameters,
  sortable: readonly Sort[],
  kept?: KeptSort | null,
): GridQuery<Sort> {
  const text = search.get(SEARCH) ?? "";
  return {
    sort:
      sortOf(sortable, search.get(SORT_BY), search.get(SORT_ORDER)) ??
      sortOf(sortable, kept?.column, kept?.order),
    search: text === "" || text.length > SEARCH_LENGTH ? undefined : text,
  };
}

/**
 * The address of the same screen with the sort changed — or lifted, back to the order of the
 * plan —, the rest of its query kept: the reading context, the search.
 */
export function sortHref<Sort extends string>(
  pathname: string,
  query: URLSearchParams,
  sort: GridSort<Sort> | undefined,
): string {
  const next = new URLSearchParams(query);
  next.delete(SORT_BY);
  next.delete(SORT_ORDER);
  if (sort !== undefined) {
    next.set(SORT_BY, sort.column);
    next.set(SORT_ORDER, sort.order);
  }
  return address(pathname, next);
}

/** The address of the same screen with the search changed — or lifted when empty —, the rest kept. */
export function searchHref(pathname: string, query: URLSearchParams, search: string): string {
  const next = new URLSearchParams(query);
  const text = search.trim();
  if (text === "") {
    next.delete(SEARCH);
  } else {
    next.set(SEARCH, text);
  }
  return address(pathname, next);
}

/** A path and its query. */
function address(pathname: string, query: URLSearchParams): string {
  const text = query.toString();
  return text === "" ? pathname : `${pathname}?${text}`;
}
