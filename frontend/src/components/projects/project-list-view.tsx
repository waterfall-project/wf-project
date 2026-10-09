// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The parts of the list of projects, the home (#522), on the side of the browser: the filter by
 * state, a button for each state of the contract, pressed as the address names them, and one for
 * every state, pressed when it names none; the filter by the period of the last modification, the
 * one column of dates of the list, local days drawn as instants (`from`, `to`), a side the server
 * refuses said at its field (`PeriodFilter`); and the grid of the projects of a page, with the way
 * through its pages. A state chosen, a period, a sort, a search or a page turned only change the
 * address, under the names of the contract, from the address last asked (`usePendingAddress`); the
 * page reads the projects anew, which the server filters, sorts and searches (`listProjects`,
 * WF-IHM-0130). The front filters nothing. The configuration of the grid reads the rows by
 * functions, which never cross from a server component to a client one: the page hands it data
 * only.
 */
"use client";

import { useTranslations } from "next-intl";

import { DenseGrid } from "@/components/grid/dense-grid";
import { ListPages } from "@/components/grid/list-pages";
import { type GridQuery, OFFSET } from "@/components/grid/query";
import type { Period, PeriodRefusals } from "@/components/grid/period";
import { PeriodFilter } from "@/components/grid/period-filter";
import type { GridPreferences } from "@/components/grid/settings";
import { ValuesFilter } from "@/components/grid/values-filter";
import { PROJECT_STATES, type ProjectState, STATES_PARAMETER } from "@/navigation/home";

import { HOME_LIST } from "./home-list";
import {
  type ListedProjectPage,
  type ListedProjectRow,
  type ListedProjectSort,
  PROJECT_LIST_GRID,
} from "./project-list-grid";
import { ProjectStateBadge } from "./project-state-badge";

/** Render the filter of the list by state, each by its badge, those the address names pressed. */
export function ProjectStateFilter({ states }: { readonly states: readonly ProjectState[] }) {
  const t = useTranslations("projectList.filter");
  return (
    <ValuesFilter
      name={STATES_PARAMETER}
      label={t("states")}
      every={t("everyState")}
      values={PROJECT_STATES.map((state) => ({
        value: state,
        text: <ProjectStateBadge state={state} />,
      }))}
      chosen={states}
      page={OFFSET}
    />
  );
}

/**
 * Render the filter of the list by the period of the last modification of its projects, two local
 * days, both included — sent as the start of the first and the start of the day after the last —,
 * back to its first page; a side the server refused said at its field.
 */
export function ProjectPeriodFilter({
  period,
  refused,
}: {
  readonly period: Period;
  readonly refused: PeriodRefusals | undefined;
}) {
  const t = useTranslations("projectList.filter");
  return (
    <PeriodFilter label={t("period")} kind="day" period={period} refused={refused} page={OFFSET} />
  );
}

/** What the grid of the list shows. */
export interface ProjectListGridProps {
  readonly projects: readonly ListedProjectRow[];
  /** Where the page stands in the projects retained, whose number the totals row says. */
  readonly page: ListedProjectPage;
  readonly query: GridQuery<ListedProjectSort>;
  readonly preferences: GridPreferences | undefined;
}

/** Render the grid of the projects of a page, its totals row the number retained, and its pages. */
export function ProjectListGrid({ projects, page, query, preferences }: ProjectListGridProps) {
  const t = useTranslations("projectList");
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      <DenseGrid
        config={PROJECT_LIST_GRID}
        rows={projects}
        totals={page}
        totalsCaption={(retained) => t("count", { count: retained.total })}
        query={query}
        preferences={preferences}
      />
      <ListPages list={HOME_LIST} texts="portfolio.pages" page={page} shown={projects.length} />
    </div>
  );
}
