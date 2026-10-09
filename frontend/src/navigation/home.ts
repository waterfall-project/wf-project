// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The home, which is the list of projects (EP-02, « Contexte de lecture, accueil et pages
 * système »): filtered by default on the projects the user contributes to — the filter of the
 * contract, `is_contributor` —, a filter the user sees and lifts, never a restriction of what
 * they may read (WF-PRJ-0060). The address says whether it is lifted, under the name of the
 * contract: `is_contributor=false`; and the states it retains, `states`, its values separated by
 * commas (`explode: false`), none naming every state.
 */
import type { components } from "@/api/generated/schema";
import type { ProjectState } from "@/api/project-state";

import type { SearchParameters } from "./context";

/** The state of a project, as the contract names it, declared once by the layer of the API. */
export type { ProjectState };

/** A permission of the catalogue, as a session carries it. */
type PermissionCode = components["schemas"]["PermissionCode"];

/** The address of the home: the projects the user contributes to. */
export const HOME = "/";

/** The parameter of the address that lifts the filter, as the contract names it. */
export const CONTRIBUTOR_PARAMETER = "is_contributor";

/** The parameter of the address that retains states, as the contract names it. */
export const STATES_PARAMETER = "states";

/** The address of the home with its filter lifted: all the projects the user may read. */
export const ALL_PROJECTS = `${HOME}?${CONTRIBUTOR_PARAMETER}=false`;

/**
 * Every state of the contract, in its order: a record, so that a state added to the contract
 * fails the type check until it is here.
 */
const EVERY_STATE: Readonly<Record<ProjectState, null>> = {
  created: null,
  pricing: null,
  in_progress: null,
  completed: null,
  lost: null,
  abandoned: null,
};

/** The states of a project, in the order of the contract, which the filter of the home offers. */
export const PROJECT_STATES = Object.keys(EVERY_STATE) as readonly ProjectState[];

/**
 * Whether a session may lift the filter: whether it reads the projects it does not contribute to
 * (`all_projects_read`, WF-ADM-0110). Without, the list lifted is the list filtered, and no link
 * promises the one or the other (WF-IHM-0090, #522).
 */
export function mayLiftContributorFilter(permissions: readonly PermissionCode[]): boolean {
  return permissions.includes("all_projects_read");
}

/** Whether the home is filtered on the projects the user contributes to: unless lifted. */
export function isContributorFiltered(search: SearchParameters): boolean {
  return search.get(CONTRIBUTOR_PARAMETER) !== "false";
}
