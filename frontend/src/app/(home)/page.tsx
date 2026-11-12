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
 * of the list leading back into it. An address that names no state asks the states by default,
 * Créé, Chiffrage and En cours, said as the filter of the contributor is, or those the account kept; it
 * asks every state by `states=all`, and the filter by state shows pressed the states retained.
 * A period the server refuses (422) — an end before the start — is said at its field, the list
 * unread, the filters kept to be changed. The projects show in the dense grid, its columns,
 * widths and sort kept in the settings of the account (WF-ADM-0040). Above the list, in every
 * case, the prerequisites the minimum reference data lacks, which forbid creating a project
 * (WF-CYC-0120), each named and leading to the reference data where the session may read it
 * (WF-IHM-0120); and, when the list holds no project and nothing narrows it, that it is — the
 * states by default count as a filter, so a home whose default states retain no project shows an
 * empty grid, not that notice. A session that holds the permission to create a project is offered
 * its creation in the header (`CreateProject`, WF-ADM-0100); no other session is.
 *
 * An account without `project_settings.read` cannot read the list: the home does not ask for it,
 * and says that the account opens no project, leading to the functions it holds, or to the role it
 * lacks (WF-IHM-0120, #2915).
 *
 * The page reads what the service serves, the list (`listProjects`) and the readiness of the
 * reference data (`getReferenceReadiness`) as they are (US-0920, #1004): it shows no note of the
 * mock-up, the list being filtered, sorted and paged by the server.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { ApiClient } from "@/api/client";
import { readOrFail, readOrRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import { FilterFields } from "@/components/grid/filter-fields";
import { PendingAddress } from "@/components/grid/pending-address";
import { readPeriod, refusedPeriod } from "@/components/grid/period";
import { CONTRACT_ADDRESS, readGridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import { platformOffer } from "@/components/commands/offer";
import { NoOpenableProject } from "@/components/projects/no-openable-project";
import { homeQuery } from "@/components/projects/home-list";
import { CreateProject } from "@/components/projects/project-form";
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
  readHomeStates,
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

/**
 * The title of the list, with the icon of its block, and at the right the creation of a project,
 * when the session may create one, and its filter.
 */
function ProjectsHeader({
  creates,
  ready,
  filter,
}: {
  readonly creates: boolean;
  /** Whether the minimum reference data is complete, which the creation requires (WF-CYC-0120). */
  readonly ready: boolean;
  readonly filter: ReactNode;
}) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functionGroups.projects")}
      icon={GROUP_ICONS["functionGroups.projects"]}
      actions={
        <>
          {creates ? <CreateProject ready={ready} /> : null}
          {filter}
        </>
      }
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
  // Narrowed by what the address asks besides its filter, the states by default included: an
  // empty list so narrowed keeps its grid.
  const narrowed =
    states.length > 0 ||
    period.from !== undefined ||
    period.to !== undefined ||
    query.search !== undefined;
  const panel = (
    <FilterFields hint={false}>
      <ProjectStateFilter states={states} />
      <ProjectPeriodFilter
        period={period}
        refused={
          projects.kind === "refused" ? refusedPeriod(projects.problem.fields ?? []) : undefined
        }
      />
    </FilterFields>
  );
  if (projects.kind === "refused") {
    // The list unread: the filters stand above the sentence that stands for the grid.
    return (
      <>
        {panel}
        <ProjectsRefused />
      </>
    );
  }
  return (
    <ProjectList
      projects={projects.data.items.map(listedProject)}
      page={projects.data.meta}
      filtered={asked.filtered}
      narrowed={narrowed}
      query={query}
      preferences={preferences}
      states={states}
      period={period}
      panel={panel}
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
  const client = serverClient();
  const session = await requestSession();
  const permissions = session?.permissions ?? [];
  // An account that cannot read any project is not refused: the list is not read (the API would
  // answer 404), and the home says so and leads to what the account holds (WF-IHM-0120, #2915).
  // Decided on the permission, never on the name of a role.
  if (session !== undefined && !permissions.includes("project_settings.read")) {
    const readiness = await readOrFail("getReferenceReadiness", () =>
      client.GET("/reference/readiness"),
    );
    return (
      <NoOpenableProject
        permissions={permissions}
        hasRole={session.access_role_ids.length > 0}
        readiness={readiness}
      />
    );
  }
  // Without the permission to read every project, the list lifted is the list filtered: it is
  // filtered whatever the address says, and no link promises otherwise (WF-IHM-0090, #522).
  const mayLift = mayLiftContributorFilter(permissions);
  const filtered = isContributorFiltered(search) || !mayLift;
  const creates = platformOffer(permissions, "project_create") !== undefined;
  const kept = session?.display_preferences?.grids?.[PROJECT_LIST_GRID.key] ?? undefined;
  const asked = {
    filtered,
    states: readHomeStates(search, kept?.filters?.[STATES_PARAMETER]),
    period: readPeriod(search, "day"),
    query: readGridQuery(
      search,
      PROJECT_LIST_SORT_COLUMNS,
      kept?.sort,
      CONTRACT_ADDRESS,
      kept?.page_size,
    ),
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
          creates={creates}
          ready={readiness.is_complete}
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
