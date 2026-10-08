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
import type { components } from "@/api/generated/schema";
import type { SearchParameters } from "@/navigation/context";

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
