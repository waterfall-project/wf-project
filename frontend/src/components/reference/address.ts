// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screens of the reference data read in their address besides the sort, the search and the
 * page of each grid: the filters of each list on its columns (WF-IHM-0130) — an identifier chosen
 * (`identifierOf`), a text or a depth —, and the state each list shows (WF-REF-0150, `stateOf`): a
 * filter by default of its grid, the active objects alone unless the address — or, the address
 * naming none, the account (`GridPreferences.filters`) — says the deactivated ones alone, or every
 * object (`EVERY_STATE`), as the states of the list of the projects are (#1747). The screen has no
 * switch of its own: `include_inactive` in its address is no longer read (#3076). The deactivated
 * ones are asked only of a session that may modify that part of the reference — the contract refuses
 * `include_inactive` and `is_active=false` without the permission of modification (`*.write`, 403,
 * C-01) —, which reads the active ones alone, the filter not offered. And what a list shows of a page
 * whose bounds the API refused (`shownPage`); and what a page asks of the API for a list, as the
 * address asks it (`stateQuery`, `given`).
 *
 * Pure, and neither server nor client: the page reads, the filters write.
 */
import type { ExpectedRefusal, ReadOrRefused } from "@/api/problem";
import { type RefusedBounds, refusedBounds } from "@/components/grid/filters";
import { type GridAddress, pagedList } from "@/components/grid/query";
import { isUuid, type SearchParameters } from "@/navigation/context";
import type { ListPage } from "@/navigation/pages";
import type { Account, Permission } from "@/session/request";

/** The parameter of the contract that filters a list of the reference data on the state. */
export const IS_ACTIVE = "is_active";

/** The text of the state by default of a list, as the address writes it: the active objects alone. */
export const ACTIVE_STATE = "true";

/** The text of the state of a list that the address writes for its deactivated objects alone. */
export const INACTIVE_STATE = "false";

/**
 * The text of the state of a list that says every object, active and deactivated — the filter
 * lifted —: written, as `states=all` of the home is, so that neither the account nor the default
 * takes its place.
 */
export const EVERY_STATE = "all";

/**
 * The state a list shows, under the name of its filter in the address: the active objects alone
 * (`true`), the deactivated ones alone (`false`), or every object (none). The address says it; one
 * that names none, what the account kept for the grid (`kept`, as the address writes it); else the
 * active objects alone, the state by default (WF-REF-0150). A session without the permission of
 * modification reads the active ones alone and is offered no filter: none, nothing said of the state.
 */
export function stateOf(
  search: SearchParameters,
  name: string,
  kept: string | null | undefined,
  permissions: readonly Permission[],
  permission: Permission,
): boolean | undefined {
  if (!permissions.includes(permission)) {
    return undefined;
  }
  const text = search.get(name) ?? kept ?? ACTIVE_STATE;
  if (text === EVERY_STATE) {
    return undefined;
  }
  return text !== INACTIVE_STATE;
}

/**
 * What a list asks of the state of its objects, under the names of the contract: `is_active` for the
 * active or the deactivated ones alone, `include_inactive` for every one; nothing for a session that
 * may not read the deactivated ones (`editable` false), the contract then listing the active alone.
 */
export function stateQuery(
  state: boolean | undefined,
  editable: boolean,
): { readonly is_active?: boolean; readonly include_inactive?: true } {
  if (!editable) {
    return {};
  }
  return state === undefined ? { include_inactive: true } : { is_active: state };
}

/**
 * What a grid of the reference data keeps of its filters with its settings (WF-IHM-0060), for a
 * session offered the filter of its state: that state alone, recorded once it differs from the state
 * by default — the search is not kept (`GridConfig.filters`, `kept-filters.ts`).
 */
export function keptState(name: string): {
  readonly filters: readonly string[];
  readonly defaulted: Readonly<Record<string, string>>;
  readonly searchKept: false;
} {
  return { filters: [name], defaulted: { [name]: ACTIVE_STATE }, searchKept: false };
}

/** An identifier the address names under a parameter, if it is a `Uuid` the API takes. */
export function identifierOf(search: SearchParameters, name: string): string | undefined {
  const value = search.get(name);
  return value !== null && isUuid(value) ? value : undefined;
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
 * The parameters of the address a list of the reference data reads: the sort, the search and the
 * page of its grid, and its own filters, its state among them — what a refusal of a reactivation is
 * told on (`Reactivations`). A list without a grid of its own reads none.
 */
export function listReads(address?: GridAddress, ...filters: readonly string[]): string[] {
  return [
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
