// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The parts of the list of projects, the home (#522), on the side of the browser: the filter by
 * state, a button for each state of the contract, pressed as the address asks it, and one for
 * every state; and the grid of the projects of a page, with the way through its pages. A state
 * chosen, a sort, a search or a page turned only change the address, under the names of the
 * contract, from the address last asked (`usePendingAddress`); the page reads the projects anew,
 * which the server filters, sorts and searches (`listProjects`, WF-IHM-0130). The front filters
 * nothing. The configuration of the grid reads the rows by functions, which never cross from a
 * server component to a client one: the page hands it data only.
 */
"use client";

import { Circle, CircleCheck, ListFilter } from "lucide-react";
import { useTranslations } from "next-intl";

import { ListPages } from "@/components/costs/cost-pages";
import { DenseGrid } from "@/components/grid/dense-grid";
import { usePendingAddress } from "@/components/grid/pending-address";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import { parametersHref } from "@/components/portfolio/address";
import { Button } from "@/components/ui/button";
import {
  HOME,
  homeStatesValue,
  PROJECT_STATES,
  type ProjectState,
  readHomeStates,
  STATES_PARAMETER,
} from "@/navigation/home";

import {
  type ListedProjectPage,
  type ListedProjectRow,
  type ListedProjectSort,
  PROJECT_LIST_GRID,
} from "./project-list-grid";
import { ProjectStateBadge } from "./project-state-badge";

/** Render the filter of the list by state, the states the address retains pressed. */
export function ProjectStateFilter({ states }: { readonly states: readonly ProjectState[] }) {
  const t = useTranslations("projectList.filter");
  const { request } = usePendingAddress();
  /** Retain the states a change makes of those last asked, back to the first page. */
  const filter = (change: (asked: readonly ProjectState[]) => readonly ProjectState[]) => {
    request((query) =>
      parametersHref(HOME, query, {
        [STATES_PARAMETER]: homeStatesValue(change(readHomeStates(query))),
      }),
    );
  };
  const every = states.length === 0;
  return (
    <div role="group" aria-label={t("states")} className="flex flex-wrap items-center gap-1.5">
      <Button
        size="sm"
        variant={every ? "default" : "outline"}
        aria-pressed={every}
        onClick={() => {
          filter(() => []);
        }}
      >
        <ListFilter aria-hidden="true" className="size-4" />
        {t("everyState")}
      </Button>
      {PROJECT_STATES.map((state) => {
        // Pressed as the address shows it; a change goes on from the states last asked.
        const pressed = states.includes(state);
        const Icon = pressed ? CircleCheck : Circle;
        return (
          <Button
            key={state}
            size="sm"
            variant={pressed ? "default" : "outline"}
            aria-pressed={pressed}
            onClick={() => {
              filter((asked) =>
                asked.includes(state) ? asked.filter((each) => each !== state) : [...asked, state],
              );
            }}
          >
            <Icon aria-hidden="true" className="size-4" />
            <ProjectStateBadge state={state} />
          </Button>
        );
      })}
    </div>
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
      <ListPages list="projects" page={page} shown={projects.length} />
    </div>
  );
}
