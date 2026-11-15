// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The pieces of the list of projects, the home (US-0090, US-0210, #522), on the side of the
 * server: the projects themselves, in the dense grid, or, when the server holds none, that it holds
 * none; or, when the server refuses the period asked (422), that the list is not read, the filters
 * staying to be changed. Its filter on the projects the user contributes to — never a restriction
 * of reading (WF-PRJ-0060) — is a filter by default of the grid (US-2130): told by its chip while it
 * applies and lifted by removing it, to a session that may read every project
 * (`all_projects_read`, WF-ADM-0110); for anyone else, lifted, the list would show the same
 * projects, and the card of the list says it instead (WF-IHM-0090).
 */
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { Period } from "@/components/grid/period";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import { NoProjects } from "@/components/system/empty-states";
import type { ProjectState } from "@/navigation/home";

import type { ListedProjectPage, ListedProjectRow, ListedProjectSort } from "./project-list-grid";
import { ProjectListGrid } from "./project-list-view";

/** What the list of projects shows: a page of the projects the server retained. */
export interface ProjectListProps {
  readonly projects: readonly ListedProjectRow[];
  readonly page: ListedProjectPage;
  readonly filtered: boolean;
  /**
   * Whether the list is filtered on the projects the user contributes to, as its chip tells it;
   * `undefined` for a session that may not lift the filter, which has no chip.
   */
  readonly mine: boolean | undefined;
  /** Whether the list is narrowed besides its filter: by states, a period or a search. */
  readonly narrowed: boolean;
  readonly query: GridQuery<ListedProjectSort>;
  readonly preferences: GridPreferences | undefined;
  /** The states and the period the address filters the list on, told as chips under the bar. */
  readonly states: readonly ProjectState[];
  readonly period: Period;
  /** The filters of the list, which the bar of its grid folds into its panel. */
  readonly panel: ReactNode;
}

/**
 * The projects of a page of the list, or that there is none: only when the list holds none at
 * all, and nothing narrows it — a page asked beyond its end is no empty list, and leads back into
 * it; a list emptied by a filter its chips tell (the states by default, the projects the user
 * contributes to, for a session that may lift it), a period or a search keeps its grid, whose bar,
 * filters and chips change them. A session that may not lift the filter on the contributor reads
 * that it contributes to no project.
 */
export function ProjectList({
  projects,
  page,
  filtered,
  mine,
  narrowed,
  query,
  preferences,
  states,
  period,
  panel,
}: ProjectListProps) {
  if (page.total === 0 && !narrowed && mine !== true) {
    // No grid to hold the bar: the filters stand above the notice, as they always did.
    return (
      <>
        {panel}
        <NoProjects filtered={filtered} />
      </>
    );
  }
  return (
    <ProjectListGrid
      projects={projects}
      page={page}
      query={query}
      preferences={preferences}
      mine={mine}
      states={states}
      period={period}
      panel={panel}
    />
  );
}

/** What stands for the grid of a list whose period the server refused (422), the list unread. */
export function ProjectsRefused() {
  const t = useTranslations("projectList");
  return <p className="text-sm text-destructive">{t("periodRefused")}</p>;
}
