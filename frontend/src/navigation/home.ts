// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The home, which is the list of projects (EP-02, « Contexte de lecture, accueil et pages
 * système »): filtered by default on the projects the user contributes to — the filter of the
 * contract, `is_contributor` —, a filter the user sees and lifts, never a restriction of what
 * they may read (WF-PRJ-0060). The address says whether it is lifted, under the name of the
 * contract: `is_contributor=false`.
 */
import type { SearchParameters } from "./context";

/** The address of the home: the projects the user contributes to. */
export const HOME = "/";

/** The parameter of the address that lifts the filter, as the contract names it. */
export const CONTRIBUTOR_PARAMETER = "is_contributor";

/** The address of the home with its filter lifted: all the projects the user may read. */
export const ALL_PROJECTS = `${HOME}?${CONTRIBUTOR_PARAMETER}=false`;

/** Whether the home is filtered on the projects the user contributes to: unless lifted. */
export function isContributorFiltered(search: SearchParameters): boolean {
  return search.get(CONTRIBUTOR_PARAMETER) !== "false";
}
