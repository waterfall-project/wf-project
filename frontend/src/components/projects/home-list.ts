// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the list of projects of the home reads of its address, and asks the server: its sort, its
 * search (`query.ts`), its filter by contributor (`is_contributor`), its states (`states`) and its
 * page (`offset`). The page asks `listProjects` by `homeQuery`, and its pages tell whether two
 * addresses read the same list by `HOME_LIST`: the one list of the parameters read, which a test
 * holds to the query sent.
 *
 * Pure, and neither server nor client: the page reads, the screen writes.
 */
import type { operations } from "@/api/generated/schema";
import { CONTRACT_ADDRESS, type GridQuery, pagedList } from "@/components/grid/query";
import {
  CONTRIBUTOR_PARAMETER,
  PROJECT_STATES,
  type ProjectState,
  STATES_PARAMETER,
} from "@/navigation/home";
import type { PagedList } from "@/navigation/pages";

/** The list of the projects: its sort, its search, its filter by contributor and by state. */
export const HOME_LIST: PagedList = pagedList(
  CONTRACT_ADDRESS,
  CONTRIBUTOR_PARAMETER,
  STATES_PARAMETER,
);

/** What the home asks `listProjects`: the query of the contract. */
type ProjectsQuery = NonNullable<operations["listProjects"]["parameters"]["query"]>;

/**
 * The query of the list of the projects, as the address asks it: no state named, every state asked —
 * the home lists every project the user may open.
 */
export function homeQuery<Sort extends NonNullable<ProjectsQuery["sort_by"]>>(asked: {
  readonly filtered: boolean;
  readonly states: readonly ProjectState[];
  readonly query: GridQuery<Sort>;
  readonly offset: number | undefined;
}): ProjectsQuery {
  const { query, states, offset } = asked;
  return {
    ...(asked.filtered ? { is_contributor: true } : {}),
    states: [...(states.length === 0 ? PROJECT_STATES : states)],
    ...(offset === undefined ? {} : { offset }),
    ...(query.search === undefined ? {} : { search: query.search }),
    ...(query.sort === undefined
      ? {}
      : { sort_by: query.sort.column, sort_order: query.sort.order }),
  };
}
