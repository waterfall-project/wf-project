// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the list of projects of the home reads of its address, and asks the server: its sort, its
 * search (`query.ts`), its filter by contributor (`is_contributor`), its states (`states`), the
 * period of the last modification (`from`, `to`, two instants drawn from local days, #522) and its
 * page (`offset`). The page asks `listProjects` by `homeQuery`, and its pages tell whether two
 * addresses read the same list by `HOME_LIST`: the one list of the parameters read, which a test
 * holds to the query sent. The address is the truth of the filter by state: the states it names are
 * those pressed, and none named is every state.
 *
 * Pure, and neither server nor client: the page reads, the screen writes.
 */
import type { operations } from "@/api/generated/schema";
import { PERIOD, type Period } from "@/components/grid/period";
import { CONTRACT_ADDRESS, type GridQuery, pagedList } from "@/components/grid/query";
import {
  CONTRIBUTOR_PARAMETER,
  PROJECT_STATES,
  type ProjectState,
  STATES_PARAMETER,
} from "@/navigation/home";
import type { PagedList } from "@/navigation/pages";

/**
 * The list of the projects: its sort, its search, its filter by contributor, by state and by
 * period.
 */
export const HOME_LIST: PagedList = pagedList(
  CONTRACT_ADDRESS,
  CONTRIBUTOR_PARAMETER,
  STATES_PARAMETER,
  PERIOD.from,
  PERIOD.to,
);

/** What the home asks `listProjects`: the query of the contract. */
type ProjectsQuery = NonNullable<operations["listProjects"]["parameters"]["query"]>;

/**
 * The query of the list of the projects, as the address asks it: no state named, every state asked —
 * the home lists every project the user may open, where the contract, without `states`, would list
 * the projects in progress alone (WF-PTF-0010).
 */
export function homeQuery<Sort extends NonNullable<ProjectsQuery["sort_by"]>>(asked: {
  readonly filtered: boolean;
  readonly states: readonly ProjectState[];
  readonly period: Period;
  readonly query: GridQuery<Sort>;
  readonly offset: number | undefined;
}): ProjectsQuery {
  const { query, states, period, offset } = asked;
  return {
    ...(asked.filtered ? { is_contributor: true } : {}),
    states: [...(states.length === 0 ? PROJECT_STATES : states)],
    ...(period.from === undefined ? {} : { from: period.from }),
    ...(period.to === undefined ? {} : { to: period.to }),
    ...(offset === undefined ? {} : { offset }),
    ...(query.search === undefined ? {} : { search: query.search }),
    ...(query.sort === undefined
      ? {}
      : { sort_by: query.sort.column, sort_order: query.sort.order }),
  };
}
