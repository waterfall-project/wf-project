// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The home, which is the list of projects (US-0090, US-0210, #522): filtered by default on the
 * projects the user contributes to, by the filter of the contract (`is_contributor`), which the
 * screen shows and a link lifts for a session that may read every project — a filter, never a
 * restriction of reading (WF-PRJ-0060) —, and which stays applied, without a link, for any other;
 * filtered by state, sorted and searched as the address asks, under the names of the contract
 * (`states`, `sort_by`, `sort_order`, `search`), the server filtering, sorting and searching; the
 * page after the first asked by its `offset`, and a page beyond the end of the list leading back
 * into it. An address that names no state asks every state. The projects show in the dense grid,
 * its columns, widths and sort kept in the settings of the account (WF-ADM-0040). Above the list,
 * in every case, the prerequisites the minimum reference data lacks, which forbid creating a
 * project (WF-CYC-0120); and, when the list holds no project, that it is.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { PendingAddress } from "@/components/grid/pending-address";
import { readGridQuery } from "@/components/grid/query";
import { ContributorFilter, ProjectList } from "@/components/projects/project-list";
import {
  listedProject,
  PROJECT_LIST_GRID,
  PROJECT_LIST_SORT_COLUMNS,
} from "@/components/projects/project-list-grid";
import { ProjectStateFilter } from "@/components/projects/project-list-view";
import { GROUP_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { ReferenceIncomplete } from "@/components/system/empty-states";
import { type PageSearchParams, pageSearch, searchQuery } from "@/navigation/context";
import {
  isContributorFiltered,
  mayLiftContributorFilter,
  PROJECT_STATES,
  readHomeStates,
} from "@/navigation/home";
import { OFFSET_PARAMETER, offsetOf } from "@/navigation/pages";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../title";

/** Title the tab with the list of projects. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functionGroups.projects");
}

/** The title of the list, with the icon of its block, and its filter at the right. */
function ProjectsHeader({ filter }: { readonly filter: ReactNode }) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functionGroups.projects")}
      icon={GROUP_ICONS["functionGroups.projects"]}
      actions={filter}
    />
  );
}

/** Render the projects the API lists, and what the reference data lacks, if anything. */
export default async function HomePage({
  searchParams,
}: {
  readonly searchParams: Promise<PageSearchParams>;
}) {
  const raw = await searchParams;
  const search = pageSearch(raw);
  const offset = offsetOf(search.get(OFFSET_PARAMETER));
  const states = readHomeStates(search);
  const client = serverClient();
  const session = await requestSession();
  const permissions = session?.permissions ?? [];
  // Without the permission to read every project, the list lifted is the list filtered: it is
  // filtered whatever the address says, and no link promises otherwise (WF-IHM-0090, #522).
  const mayLift = mayLiftContributorFilter(permissions);
  const filtered = isContributorFiltered(search) || !mayLift;
  const kept = session?.user.display_preferences?.grids?.[PROJECT_LIST_GRID.key] ?? undefined;
  const query = readGridQuery(search, PROJECT_LIST_SORT_COLUMNS, kept?.sort);
  const [projects, readiness] = await Promise.all([
    readOrFail("listProjects", () =>
      client.GET("/projects", {
        params: {
          query: {
            ...(filtered ? { is_contributor: true } : {}),
            // No state named, every state asked: the home lists every project the user may open.
            states: [...(states.length === 0 ? PROJECT_STATES : states)],
            ...(offset === undefined ? {} : { offset }),
            ...(query.search === undefined ? {} : { search: query.search }),
            ...(query.sort === undefined
              ? {}
              : { sort_by: query.sort.column, sort_order: query.sort.order }),
          },
        },
      }),
    ),
    readOrFail("getReferenceReadiness", () => client.GET("/reference/readiness")),
  ]);
  return (
    // The filters, the grid and its pages compose the changes they make to the address.
    <PendingAddress>
      <Screen density="dense" fill>
        <ProjectsHeader
          filter={
            <ContributorFilter filtered={filtered} mayLift={mayLift} query={searchQuery(raw)} />
          }
        />
        <ReferenceIncomplete readiness={readiness} permissions={permissions} />
        <ProjectStateFilter states={states} />
        <ProjectList
          projects={projects.items.map(listedProject)}
          page={projects.meta}
          filtered={filtered}
          narrowed={states.length > 0 || query.search !== undefined}
          query={query}
          preferences={kept}
        />
      </Screen>
    </PendingAddress>
  );
}
