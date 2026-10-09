// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The home, which is the list of projects (US-0090, US-0210, #522): filtered by default on the
 * projects the user contributes to, by the filter of the contract (`is_contributor`), which the
 * screen shows and a link lifts for a session that may read every project — a filter, never a
 * restriction of reading (WF-PRJ-0060) —, and which stays applied, without a link, for any other;
 * filtered by state and by the period of the last modification — local days, sent as instants —,
 * sorted and searched — on the label and the code — as the address asks, under the names of the
 * contract (`states`, `from`, `to`, `sort_by`, `sort_order`, `search`), the server filtering,
 * sorting and searching; the page after the first asked by its `offset`, and a page beyond the end
 * of the list leading back into it. An address that names no state asks every state, and the filter
 * by state shows every state pressed: the address is the truth of the filter. A period the server
 * refuses (422) — an end before the start — is said at its field, the list unread, the filters kept
 * to be changed. The projects show in the dense grid, its columns, widths and sort kept in the
 * settings of the account (WF-ADM-0040). Above the list, in every case, the prerequisites the
 * minimum reference data lacks, which forbid creating a project (WF-CYC-0120); and, when the list
 * holds no project, that it is.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { ApiClient } from "@/api/client";
import { readOrFail, readOrRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import { readValues } from "@/components/grid/filters";
import { PendingAddress } from "@/components/grid/pending-address";
import { readPeriod, refusedPeriod } from "@/components/grid/period";
import { readGridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import { homeQuery } from "@/components/projects/home-list";
import {
  ContributorFilter,
  ProjectList,
  ProjectsRefused,
} from "@/components/projects/project-list";
import {
  listedProject,
  PROJECT_LIST_GRID,
  PROJECT_LIST_SORT_COLUMNS,
} from "@/components/projects/project-list-grid";
import { ProjectPeriodFilter, ProjectStateFilter } from "@/components/projects/project-list-view";
import { GROUP_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { ReferenceIncomplete } from "@/components/system/empty-states";
import { type PageSearchParams, pageSearch, searchQuery } from "@/navigation/context";
import {
  isContributorFiltered,
  mayLiftContributorFilter,
  PROJECT_STATES,
  STATES_PARAMETER,
} from "@/navigation/home";
import { OFFSET_PARAMETER, offsetOf } from "@/navigation/pages";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../title";

/** Title the tab with the list of projects. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functionGroups.projects");
}

/** The refusal of a period the server cannot apply — its end before its start (422). */
const PERIOD_REFUSED = [{ status: 422, code: "VALIDATION_FAILED" }] as const;

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

/** Read the page of the projects the address asks; or the refusal of its period (422). */
function readProjects(client: ApiClient, query: Parameters<typeof homeQuery>[0]) {
  return readOrRefused("listProjects", PERIOD_REFUSED, () =>
    client.GET("/projects", { params: { query: homeQuery(query) } }),
  );
}

/** What the API answered for the projects: a page of them, or the refusal of its period. */
type ProjectsRead = Awaited<ReturnType<typeof readProjects>>;

/**
 * The filters of the list and its projects: the states the address names pressed — none named,
 * every state —, the period, a side refused said at its field; and the grid, or, the list unread,
 * why.
 */
function ProjectsShown({
  projects,
  asked,
  preferences,
}: {
  readonly projects: ProjectsRead;
  readonly asked: Parameters<typeof homeQuery>[0];
  readonly preferences: GridPreferences | undefined;
}) {
  const { states, period, query } = asked;
  // Narrowed by what the address asks besides its filter: an empty list keeps its grid.
  const narrowed =
    states.length > 0 ||
    period.from !== undefined ||
    period.to !== undefined ||
    query.search !== undefined;
  return (
    <>
      <div className="flex flex-wrap items-start gap-x-6 gap-y-2">
        <ProjectStateFilter states={states} />
        <ProjectPeriodFilter
          period={period}
          refused={
            projects.kind === "refused" ? refusedPeriod(projects.problem.fields ?? []) : undefined
          }
        />
      </div>
      {projects.kind === "refused" ? (
        <ProjectsRefused />
      ) : (
        <ProjectList
          projects={projects.data.items.map(listedProject)}
          page={projects.data.meta}
          filtered={asked.filtered}
          narrowed={narrowed}
          query={query}
          preferences={preferences}
        />
      )}
    </>
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
  const client = serverClient();
  const session = await requestSession();
  const permissions = session?.permissions ?? [];
  // Without the permission to read every project, the list lifted is the list filtered: it is
  // filtered whatever the address says, and no link promises otherwise (WF-IHM-0090, #522).
  const mayLift = mayLiftContributorFilter(permissions);
  const filtered = isContributorFiltered(search) || !mayLift;
  const kept = session?.user.display_preferences?.grids?.[PROJECT_LIST_GRID.key] ?? undefined;
  const asked = {
    filtered,
    states: readValues(search, STATES_PARAMETER, PROJECT_STATES),
    period: readPeriod(search, "day"),
    query: readGridQuery(search, PROJECT_LIST_SORT_COLUMNS, kept?.sort),
    offset: offsetOf(search.get(OFFSET_PARAMETER)),
  };
  const [projects, readiness] = await Promise.all([
    readProjects(client, asked),
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
        <ProjectsShown projects={projects} asked={asked} preferences={kept} />
      </Screen>
    </PendingAddress>
  );
}
