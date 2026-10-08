// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of the actual costs reads of its address, besides the sort of its grid
 * (`query.ts`) and the sub-project of its reading context (`subproject_id`): the filters of the
 * list (WF-CRE-0040) under the names of the contract — the scope, `in_tracked_scope`, and the
 * period of the documents, `from` and `to` —, and the page of each list the server pages: that of
 * the costs, `offset`, as the contract names it, and that of the journal of the imports,
 * `imports_offset`. A filter chosen, a page turned only change the address, and the page reads
 * anew: the front filters, sorts and pages nothing (WF-ARC-0020). And the line whose place in the
 * tracked scope is shown to be changed, `line` (WF-CRE-0040).
 *
 * Pure, and neither server nor client: the page reads, the screen writes.
 */
import { OFFSET } from "@/components/grid/query";
import { isPlanningDate } from "@/i18n/format";
import type { SearchParameters } from "@/navigation/context";

/** The parameter of the address the scope filtered on goes by, as the contract names it. */
export const SCOPE = "in_tracked_scope";
/** The parameters of the period of the documents, as the contract names them. */
export const FROM = "from";
export const TO = "to";
/** The parameter of the sub-project, that of the reading context. */
export const SUBPROJECT = "subproject_id";
/** The page of the costs, as the contract names it. */
export const COSTS_PAGE = OFFSET;
/** The page of the journal of the imports, which shares the screen with the costs. */
export const IMPORTS_PAGE = "imports_offset";

/** The line of the page whose place in the tracked scope the screen shows, to change it. */
export const LINE = "line";

/** The lines a scope retains: those tracked, those excluded; none, every line. */
export type Scope = "tracked" | "excluded";

/** The scopes, in the order the filter offers them. */
export const SCOPES: readonly Scope[] = ["tracked", "excluded"];

/** The filters of the list the address asks, besides its sub-project. */
export interface CostFilters {
  readonly scope: Scope | undefined;
  readonly from: string | undefined;
  readonly to: string | undefined;
}

/**
 * A date of the address the API may take, a day of the calendar as the contract writes it; none
 * otherwise — 30 February is not asked, the API would refuse it.
 */
function dateOf(search: SearchParameters, name: string): string | undefined {
  const value = search.get(name);
  return value !== null && isPlanningDate(value) ? value : undefined;
}

/** Read the filters the address asks of the list; a value the contract would refuse is not asked. */
export function readCostFilters(search: SearchParameters): CostFilters {
  const scope = search.get(SCOPE);
  return {
    scope: scope === "true" ? "tracked" : scope === "false" ? "excluded" : undefined,
    from: dateOf(search, FROM),
    to: dateOf(search, TO),
  };
}

/** The value of `in_tracked_scope` a scope asks; none for every line. */
export function scopeParameter(scope: Scope | undefined): boolean | undefined {
  return scope === undefined ? undefined : scope === "tracked";
}

/** The page of a list the address asks, from the place of its first row; the first page otherwise. */
export function readPage(search: SearchParameters, name: string): number {
  const value = search.get(name) ?? "";
  return /^\d{1,9}$/.test(value) ? Number(value) : 0;
}

/** The line the address names, when it names one by an identifier; none otherwise. */
export function readCostLine(search: SearchParameters): string | undefined {
  const line = search.get(LINE);
  return line !== null && /^[\w-]+$/.test(line) ? line : undefined;
}

/** A path and its query. */
function address(pathname: string, query: URLSearchParams): string {
  const text = query.toString();
  return text === "" ? pathname : `${pathname}?${text}`;
}

/** Set a parameter of a query, or remove it when it has no value. */
function put(query: URLSearchParams, name: string, value: string | undefined) {
  if (value === undefined || value === "") {
    query.delete(name);
  } else {
    query.set(name, value);
  }
}

/**
 * The address of the same screen with other filters — the sub-project among them, none lifting
 * it —, back to the first page of the costs, the rest of its query kept: the reading context,
 * the sort, the page of the journal.
 */
export function filtersHref(
  pathname: string,
  query: URLSearchParams,
  filters: CostFilters & { readonly subproject: string | undefined },
): string {
  const next = new URLSearchParams(query);
  put(next, SCOPE, scopeParameter(filters.scope)?.toString());
  put(next, FROM, filters.from);
  put(next, TO, filters.to);
  put(next, SUBPROJECT, filters.subproject);
  next.delete(COSTS_PAGE);
  return address(pathname, next);
}

/**
 * The address of the same screen showing a line to change its place in the tracked scope — or
 * none, `undefined` —, the rest of its query kept.
 */
export function lineHref(pathname: string, query: URLSearchParams, line: string | undefined) {
  const next = new URLSearchParams(query);
  put(next, LINE, line);
  return address(pathname, next);
}

/** The address of the same screen at another page of one of its lists, the rest of its query kept. */
export function pageHref(
  pathname: string,
  query: URLSearchParams,
  name: string,
  offset: number,
): string {
  const next = new URLSearchParams(query);
  put(next, name, offset > 0 ? String(offset) : undefined);
  return address(pathname, next);
}

/** A query without some of its parameters, in a stable order. */
function without(query: URLSearchParams, names: readonly string[]): string {
  const rest = new URLSearchParams(query);
  for (const name of names) {
    rest.delete(name);
  }
  rest.sort();
  return rest.toString();
}

/**
 * Whether two queries ask the same list but for the pages of the screen (`name`, and the page of
 * the other list, which reads nothing of the list): a page turned from a query that asks another
 * — a filter or a sort under way — starts that list from its first page, the place of a row in
 * the one shown meaning nothing in the other; the page of the journal turned meanwhile changes
 * nothing of the costs (#294).
 */
export function sameList(query: URLSearchParams, shown: URLSearchParams, name: string): boolean {
  const pages = [name, COSTS_PAGE, IMPORTS_PAGE];
  return without(query, pages) === without(shown, pages);
}
