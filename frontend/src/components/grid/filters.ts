// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filters of a list on the values of a column, as the address carries them, besides the sort
 * and the search of its grid (`query.ts`): a list of values of the contract — the origins of the
 * accounts, the capacities of the contributors —, written in one parameter, its values separated by
 * commas, as the contract declares every list (`explode: false`). A filter chosen only changes the
 * address, and the page reads anew: the server filters, never the front (WF-ARC-0020). A list the
 * server pages starts again from its first page, the place of a row in the list shown meaning
 * nothing in the one filtered otherwise.
 *
 * Pure, and neither server nor client: the page reads, the filter writes.
 */
import type { SearchParameters } from "@/navigation/context";

/**
 * The values a parameter of the address filters a list on, in the order of the contract given,
 * each once; none when it names none — every value, the server reading no filter. A value the
 * contract does not know is not asked: the API would refuse it.
 */
export function readValues<Value extends string>(
  search: SearchParameters,
  name: string,
  values: readonly Value[],
): readonly Value[] {
  const asked = new Set((search.get(name) ?? "").split(","));
  return values.filter((value) => asked.has(value));
}

/**
 * The address of the same screen with one filter set — or lifted, for none —, the rest of its query
 * kept, and back to the first page of its list when the server pages it (`page`, the parameter of
 * its page).
 */
export function filterHref(
  pathname: string,
  query: URLSearchParams,
  name: string,
  value: string | undefined,
  page?: string,
): string {
  const next = new URLSearchParams(query);
  if (page !== undefined) {
    next.delete(page);
  }
  if (value === undefined || value === "") {
    next.delete(name);
  } else {
    next.set(name, value);
  }
  const text = next.toString();
  return text === "" ? pathname : `${pathname}?${text}`;
}

/**
 * The address of the same screen filtered on other values of a column — none, or every one, lifts
 * the filter, the list then holding every value —, written in the order of the contract, back to
 * the first page of a list the server pages.
 */
export function valuesHref<Value extends string>(
  pathname: string,
  query: URLSearchParams,
  filter: { readonly name: string; readonly values: readonly Value[]; readonly page?: string },
  chosen: readonly Value[],
): string {
  const kept = filter.values.filter((value) => chosen.includes(value));
  const every = kept.length === filter.values.length;
  return filterHref(pathname, query, filter.name, every ? undefined : kept.join(","), filter.page);
}
