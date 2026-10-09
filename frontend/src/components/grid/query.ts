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
 * A grid alone on its screen writes them under the names of the contract; one among several — the
 * organisation, the roles and the calendars of the settings of the resources — writes them after
 * a prefix of its own (`prefixedAddress`), so that a sort or a search of one never reads as the
 * other's, and its page asks the API under the names of the contract.
 *
 * Pure, and neither server nor client: the page reads, the grid writes.
 */
import type { components } from "@/api/generated/schema";
import type { SearchParameters } from "@/navigation/context";
import type { PagedList } from "@/navigation/pages";

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
/**
 * The place of the first row of a page of a list the server pages (`offset`, as the contract
 * names it): a sort or a search changed starts again from the first page.
 */
export const OFFSET = "offset";

/**
 * The names under which a grid writes its sort, its search and the first row of its page in the
 * address.
 */
export interface GridAddress {
  readonly search: string;
  readonly sortBy: string;
  readonly sortOrder: string;
  readonly offset: string;
}

/** The names of the contract, for a grid alone on its screen. */
export const CONTRACT_ADDRESS: GridAddress = {
  search: SEARCH,
  sortBy: SORT_BY,
  sortOrder: SORT_ORDER,
  offset: OFFSET,
};

/**
 * The names of a grid among several on its screen: those of the contract after its prefix —
 * `role_search`, `role_sort_by` for the prefix `role_` —, its page too (`role_offset`), so that a
 * sort or a search of one grid takes back to its first page only its own list.
 */
export function prefixedAddress(prefix: string): GridAddress {
  return {
    search: `${prefix}${SEARCH}`,
    sortBy: `${prefix}${SORT_BY}`,
    sortOrder: `${prefix}${SORT_ORDER}`,
    offset: `${prefix}${OFFSET}`,
  };
}

/**
 * A list a grid shows, which the server pages: its page, and what it reads of the address — its
 * search, its sort, and the filters given (`readingOf`).
 */
export function pagedList(address: GridAddress, ...filters: readonly string[]): PagedList {
  return {
    page: address.offset,
    reads: [address.search, address.sortBy, address.sortOrder, ...filters],
  };
}

/**
 * The search a list asks of the server, as the address asks it: alone for a list the server neither
 * sorts nor pages — the tree of the organisation.
 */
export function searched<Sort extends string>(query: GridQuery<Sort>) {
  return query.search === undefined ? {} : { search: query.search };
}

/**
 * What a list asks of the server, as the address asks it of its grid, under the names of the
 * contract: its search, its sort and its page.
 */
export function asked<Sort extends string>(query: GridQuery<Sort>, offset?: number) {
  return {
    ...searched(query),
    ...(query.sort === undefined
      ? {}
      : { sort_by: query.sort.column, sort_order: query.sort.order }),
    ...(offset === undefined ? {} : { offset }),
  };
}

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
 * when the address says nothing of the sort (WF-IHM-0060). A grid among several reads them under
 * its own names (`names`).
 */
export function readGridQuery<Sort extends string>(
  search: SearchParameters,
  sortable: readonly Sort[],
  kept?: KeptSort | null,
  names: GridAddress = CONTRACT_ADDRESS,
): GridQuery<Sort> {
  const text = search.get(names.search) ?? "";
  const by = search.get(names.sortBy);
  return {
    // `sort_by` empty is a sort lifted: the order of the plan, whatever the account keeps.
    sort:
      by === ""
        ? undefined
        : (sortOf(sortable, by, search.get(names.sortOrder)) ??
          sortOf(sortable, kept?.column, kept?.order)),
    search: text === "" || text.length > SEARCH_LENGTH ? undefined : text,
  };
}

/**
 * The address of the same screen with the sort changed, the rest of its query kept — the
 * reading context, the search —, back to its first page. A sort lifted, back to the order of the plan, keeps `sort_by`,
 * empty: the page then asks no sort, and does not fall back on the one the account keeps,
 * whether or not the preference has been written yet.
 */
export function sortHref<Sort extends string>(
  pathname: string,
  query: URLSearchParams,
  sort: GridSort<Sort> | undefined,
  names: GridAddress = CONTRACT_ADDRESS,
): string {
  const next = new URLSearchParams(query);
  next.delete(names.sortBy);
  next.delete(names.sortOrder);
  next.delete(names.offset);
  next.set(names.sortBy, sort?.column ?? "");
  if (sort !== undefined) {
    next.set(names.sortOrder, sort.order);
  }
  return address(pathname, next);
}

/**
 * The address of the same screen with the search changed — or lifted when empty —, back to its
 * first page, the rest kept.
 */
export function searchHref(
  pathname: string,
  query: URLSearchParams,
  search: string,
  names: GridAddress = CONTRACT_ADDRESS,
): string {
  const next = new URLSearchParams(query);
  next.delete(names.offset);
  const text = search.trim();
  if (text === "") {
    next.delete(names.search);
  } else {
    next.set(names.search, text);
  }
  return address(pathname, next);
}

/** A path and its query. */
function address(pathname: string, query: URLSearchParams): string {
  const text = query.toString();
  return text === "" ? pathname : `${pathname}?${text}`;
}
