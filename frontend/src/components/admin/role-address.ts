// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of the access roles reads of its address besides the sort and the search of its
 * grid (`query.ts`): the filters of the list (WF-IHM-0130, EP-02/L42f), under the names of the
 * contract — the kind of the roles, `is_predefined`, `true` for the predefined ones and `false` for
 * those composed since, and the bounds of the number of their holders, `holder_count_min` and
 * `holder_count_max`, both included, whole numbers from nought (`filters.ts`). A filter chosen only
 * changes the address, and the page reads anew: the server filters, never the front. The list is not
 * paged: no page needs to tell whether two addresses read the same list.
 *
 * Pure, and neither server nor client: the page reads, the filters write.
 */
import type { operations } from "@/api/generated/schema";
import type { Bounds } from "@/components/grid/filters";
import { asked, type GridQuery } from "@/components/grid/query";

/** The parameter of the address the kind of the roles goes by, as the contract names it. */
export const PREDEFINED = "is_predefined";

/** The column of the number of holders, whose bounds the address carries (`holder_count_min`). */
export const HOLDER_COUNT = "holder_count";

/** What the page asks `listAccessRoles`: the query of the contract. */
type RolesQuery = NonNullable<operations["listAccessRoles"]["parameters"]["query"]>;

/**
 * The query of the list of the roles, as the address asks it: its search, its sort, its kind and the
 * bounds of its holders, a count of the contract written as a number.
 */
export function rolesQuery<Sort extends NonNullable<RolesQuery["sort_by"]>>(filters: {
  readonly query: GridQuery<Sort>;
  readonly predefined: boolean | undefined;
  readonly holders: Bounds;
}): RolesQuery {
  const { query, predefined, holders } = filters;
  return {
    ...asked(query),
    ...(predefined === undefined ? {} : { is_predefined: predefined }),
    ...(holders.min === undefined ? {} : { holder_count_min: Number(holders.min) }),
    ...(holders.max === undefined ? {} : { holder_count_max: Number(holders.max) }),
  };
}
