// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of the accounts reads of its address besides the sort, the search (`query.ts`)
 * and the page (`offset`) of its grid: the filters of the list (WF-IHM-0130), under the names of the
 * contract — the origins of the accounts, `origins`, its values separated by commas, the node of
 * organisation they come under, `org_node_id`, and whether the deactivated ones are listed,
 * `include_inactive`. A filter chosen only changes the address, back to
 * the first page, and the page reads anew: the server filters, never the front (WF-ARC-0020).
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
 * The parameter of the address that hides the deactivated accounts, as the contract names it:
 * `include_inactive`, which the screen asks `true` unless the address says `false` — a deactivated
 * account stays listed (WF-ADM-0060).
 */
export const INCLUDE_INACTIVE = "include_inactive";

/** Whether the address shows the deactivated accounts: unless it asks them hidden. */
export function showsInactive(search: SearchParameters): boolean {
  return search.get(INCLUDE_INACTIVE) !== "false";
}

/** The list of the accounts: its sort, its search and its filters. */
export const USERS_LIST: PagedList = pagedList(
  CONTRACT_ADDRESS,
  ORIGINS,
  ORG_NODE,
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
  readonly inactive: boolean;
  readonly offset: number | undefined;
}): UsersQuery {
  const { query, origins, orgNode, offset } = asked;
  return {
    include_inactive: asked.inactive,
    ...(offset === undefined ? {} : { offset }),
    ...(query.search === undefined ? {} : { search: query.search }),
    ...(origins.length === 0 ? {} : { origins: [...origins] }),
    ...(orgNode === undefined ? {} : { org_node_id: orgNode }),
    ...(query.sort === undefined
      ? {}
      : { sort_by: query.sort.column, sort_order: query.sort.order }),
  };
}
