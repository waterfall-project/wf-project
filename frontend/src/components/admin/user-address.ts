// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of the accounts reads of its address besides the sort, the search (`query.ts`)
 * and the page (`offset`) of its grid: the filters of the list (WF-IHM-0130), under the names of the
 * contract — the origins of the accounts, `origins`, its values separated by commas, the node of
 * organisation they come under, `org_node_id`, the access roles they hold, `access_role_ids`, an
 * account retained when it holds one at least of them, and their state, `is_active` — the active
 * ones alone, or the deactivated ones alone; none, every account, the deactivated ones listed by
 * default (WF-ADM-0060), the page always asking `include_inactive=true`. An address of before, which
 * hid the deactivated accounts by `include_inactive=false`, reads as the active ones alone, which it
 * showed (`readAccountState`). A filter chosen only changes the address, back to the first page, and
 * the page reads anew: the server filters, never the front (WF-ARC-0020).
 *
 * Pure, and neither server nor client: the page reads, the filters write.
 */
import type { components, operations } from "@/api/generated/schema";
import { CONTRACT_ADDRESS, type GridQuery, pagedList } from "@/components/grid/query";
import type { SearchParameters } from "@/navigation/context";
import type { PagedList } from "@/navigation/pages";

/** The origin of an account, as the contract names it. */
export type UserOrigin = components["schemas"]["UserOrigin"];

/** The parameter of the address the origins filtered on go by, as the contract names it. */
export const ORIGINS = "origins";

/** The parameter of the address the node filtered on goes by, as the contract names it. */
export const ORG_NODE = "org_node_id";

/** The parameter of the address the access roles filtered on go by, as the contract names it. */
export const ACCESS_ROLES = "access_role_ids";

/**
 * The parameter of the address the state filtered on goes by, as the contract names it: `true`, the
 * active accounts alone; `false`, the deactivated ones alone. It prevails over `include_inactive`.
 */
export const IS_ACTIVE = "is_active";

/**
 * Every origin of the contract, in the order of its enumeration: one the contract adds fails the
 * type check until it is here.
 */
const EVERY_ORIGIN: Readonly<Record<UserOrigin, number>> = {
  local: 0,
  directory: 1,
  identity_provider: 2,
};

/** The origins an account may have, in the order of the contract. */
export const USER_ORIGINS = Object.keys(EVERY_ORIGIN) as readonly UserOrigin[];

/**
 * The parameter of the contract that lists the deactivated accounts besides the active ones, which
 * the screen always asks: a deactivated account stays listed (WF-ADM-0060). The address no longer
 * writes it; one that says `false`, written before, is read as the active accounts alone, and a
 * state chosen lifts it.
 */
export const INCLUDE_INACTIVE = "include_inactive";

/**
 * The state the address restricts the accounts to: `is_active` as it names it; failing it, the
 * active ones alone for an address that hid the deactivated ones (`include_inactive=false`); none,
 * every account.
 */
export function readAccountState(search: SearchParameters): boolean | undefined {
  const value = search.get(IS_ACTIVE);
  if (value === "true" || value === "false") {
    return value === "true";
  }
  return search.get(INCLUDE_INACTIVE) === "false" ? true : undefined;
}

/** The list of the accounts: its sort, its search and its filters. */
export const USERS_LIST: PagedList = pagedList(
  CONTRACT_ADDRESS,
  ORIGINS,
  ORG_NODE,
  ACCESS_ROLES,
  IS_ACTIVE,
  INCLUDE_INACTIVE,
);

/** What the page asks `listUsers`: the query of the contract. */
type UsersQuery = NonNullable<operations["listUsers"]["parameters"]["query"]>;

/**
 * The query of the list of the accounts, as the address asks it: its sort, its search, its filters
 * and its page — every parameter but the page read from `USERS_LIST`, which says when two
 * addresses read the same list.
 */
export function usersQuery<Sort extends NonNullable<UsersQuery["sort_by"]>>(asked: {
  readonly query: GridQuery<Sort>;
  readonly origins: readonly UserOrigin[];
  readonly orgNode: string | undefined;
  /** The access roles the accounts are restricted to, by their identifiers; none, every account. */
  readonly accessRoles: readonly string[];
  /** The state the accounts are restricted to: active, deactivated; none, every account. */
  readonly active: boolean | undefined;
  readonly offset: number | undefined;
}): UsersQuery {
  const { query, origins, orgNode, accessRoles, active, offset } = asked;
  return {
    // Every account unless a state is chosen, which prevails: the contract hides the deactivated
    // ones by default.
    include_inactive: true,
    ...(offset === undefined ? {} : { offset }),
    ...(query.search === undefined ? {} : { search: query.search }),
    ...(origins.length === 0 ? {} : { origins: [...origins] }),
    ...(orgNode === undefined ? {} : { org_node_id: orgNode }),
    ...(accessRoles.length === 0 ? {} : { access_role_ids: [...accessRoles] }),
    ...(active === undefined ? {} : { is_active: active }),
    ...(query.sort === undefined
      ? {}
      : { sort_by: query.sort.column, sort_order: query.sort.order }),
  };
}
