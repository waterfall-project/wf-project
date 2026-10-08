// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screens of the reference data read in their address besides the sort and the search of
 * each grid: whether their lists show the deactivated objects too (WF-REF-0150), under the name of
 * the contract, `include_inactive`, which the page asks only of a session that may read them — the
 * contract refuses `include_inactive` without the permission of reading of that part of the
 * reference (403), as the lists of the estimate do (#351).
 *
 * Pure, and neither server nor client: the page reads, the filters write.
 */
import type { GridAddress } from "@/components/grid/query";
import type { SearchParameters } from "@/navigation/context";
import type { Permission } from "@/session/request";

/** The parameter of the contract that asks for the deactivated objects too. */
export const INCLUDE_INACTIVE = "include_inactive";

/** An identifier of the address the API may know. */
const IDENTIFIER = /^[\w-]+$/;

/** Whether the address asks for the deactivated objects too. */
export function asksInactive(search: SearchParameters): boolean {
  return search.get(INCLUDE_INACTIVE) === "true";
}

/**
 * The query that asks for the deactivated objects too, when the address asks for them and the
 * session bears the permission the contract requires; nothing otherwise, the active ones alone.
 */
export function inactiveQuery(
  asked: boolean,
  permissions: readonly Permission[],
  permission: Permission,
): { readonly include_inactive?: true } {
  return asked && permissions.includes(permission) ? { include_inactive: true } : {};
}

/** An identifier the address names under a parameter, if the API may know it. */
export function identifierOf(search: SearchParameters, name: string): string | undefined {
  const value = search.get(name);
  return value !== null && IDENTIFIER.test(value) ? value : undefined;
}

/** The address of the same screen with one parameter set, or taken away for none. */
export function parameterHref(
  pathname: string,
  query: URLSearchParams,
  name: string,
  value: string | undefined,
): string {
  const next = new URLSearchParams(query);
  if (value === undefined) {
    next.delete(name);
  } else {
    next.set(name, value);
  }
  const text = next.toString();
  return text === "" ? pathname : `${pathname}?${text}`;
}

/**
 * The parameters of the address a list of the reference data reads: whether it shows the
 * deactivated objects, the sort, the search and the page of its grid, and its own filters — what a
 * refusal of a reactivation is told on (`Reactivations`). A list without a grid of its own reads the
 * first alone.
 */
export function listReads(address?: GridAddress, ...filters: readonly string[]): string[] {
  return [
    INCLUDE_INACTIVE,
    ...(address === undefined
      ? []
      : [address.search, address.sortBy, address.sortOrder, address.offset]),
    ...filters,
  ];
}
