// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screens of the reference data read in their address besides the sort, the search and the
 * page of each grid: whether their lists show the deactivated objects too (WF-REF-0150), under the
 * name of the contract, `include_inactive`, which the page asks only of a session that may read them
 * — the contract refuses `include_inactive` without the permission of reading of that part of the
 * reference (403), as the lists of the estimate do (#351) —; and the filters of each list on its
 * columns (WF-IHM-0130): an identifier chosen (`identifierOf`), the state (`is_active`, which takes
 * precedence over `include_inactive`, under the same permission: `stateOf`), a text or a depth;
 * what a list shows of a page whose bounds the API refused (`shownPage`); and what a page asks of
 * the API for a list, as the address asks it (`searched`, `asked`, `given`).
 *
 * Pure, and neither server nor client: the page reads, the filters write.
 */
import type { ExpectedRefusal, ReadOrRefused } from "@/api/problem";
import { type RefusedBounds, refusedBounds } from "@/components/grid/filters";
import { type GridAddress, pagedList } from "@/components/grid/query";
import type { SearchParameters } from "@/navigation/context";
import type { ListPage } from "@/navigation/pages";
import type { Account, Permission } from "@/session/request";

/** The parameter of the contract that asks for the deactivated objects too. */
export const INCLUDE_INACTIVE = "include_inactive";

/** The parameter of the contract that filters a list of the reference data on the state. */
export const IS_ACTIVE = "is_active";

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

/**
 * The state the address filters a list on, under the name given — the active objects alone, or the
 * deactivated ones alone —; none when it names none. The deactivated ones alone are asked only of a
 * session that may read them, as `include_inactive` is: the contract refuses `is_active=false`
 * without the permission (403).
 */
export function stateOf(
  search: SearchParameters,
  name: string,
  permissions: readonly Permission[],
  permission: Permission,
): boolean | undefined {
  const value = search.get(name);
  if (value === "true") {
    return true;
  }
  return value === "false" && permissions.includes(permission) ? false : undefined;
}

/** A text of the address a filter of the contract takes, of its length at most; none otherwise. */
export function textOf(search: SearchParameters, name: string, length: number): string | undefined {
  const value = search.get(name)?.trim() ?? "";
  return value === "" || value.length > length ? undefined : value;
}

/** A whole number of the address from 1, a depth of the tree; none otherwise. */
export function levelOf(search: SearchParameters, name: string): number | undefined {
  const value = search.get(name) ?? "";
  return /^[1-9]\d{0,2}$/.test(value) ? Number(value) : undefined;
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
    ...(address === undefined ? [] : [...pagedList(address).reads, address.offset]),
    ...filters,
  ];
}

/** The settings of the grids the account keeps, by the key of each grid. */
export type KeptGrids = NonNullable<
  NonNullable<NonNullable<Account["display_preferences"]>["grids"]>
>;

/** A value of the address under the name of the contract: none when the address holds none. */
export function given<Name extends string, Value>(name: Name, value: Value | undefined) {
  return (value === undefined ? {} : { [name]: value }) as Partial<Record<Name, Value>>;
}

/** A page of a list the API did not read, its bounds refused: nothing in it. */
const UNREAD: ListPage = { limit: 0, offset: 0, total: 0 };

/**
 * What a list shows of a page whose bounds the API may have refused (422, #545): its rows and where
 * its page stands; or no row, and the parameters of the bounds refused, by their names in the
 * contract.
 */
export function shownPage<Row>(
  read: ReadOrRefused<{ readonly items: readonly Row[]; readonly meta: ListPage }, ExpectedRefusal>,
): {
  readonly rows: readonly Row[];
  readonly page: ListPage;
  readonly refused: RefusedBounds | undefined;
} {
  return read.kind === "read"
    ? { rows: read.data.items, page: read.data.meta, refused: undefined }
    : { rows: [], page: UNREAD, refused: refusedBounds(read.problem.fields ?? []) };
}
