// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of a project (FBS-4.2, US-0210), under the banner of its reading context
 * (WF-IHM-0020): the state of the project, by its badge, in its header; its inflation rate and its
 * probability of winning, its work breakdown, its sub-projects and its contributors, each list a
 * section of the screen under its own title — the ergonomics gathers the leaves of the function on
 * one screen —, and a dense grid (#301), each with its settings and its own names in the address,
 * asked under the names of the contract: the sub-projects searched, sorted and filtered on their
 * actual costs by the server (`subproject_search`, `subproject_sort_by`, `subproject_sort_order`,
 * `subproject_has_actual_costs`), the contributors searched, sorted and filtered by it on their
 * capacity and the state of their account (`contributor_search`, `contributor_sort_by`,
 * `contributor_sort_order`, `contributor_kinds`, `contributor_is_active`) — WF-IHM-0060,
 * WF-IHM-0130 —, the sort each grid keeps in the settings of the account serving when the address
 * names none. The work breakdown is a tree in the order entered, searched on its labels and
 * filtered on its kinds by the server (`breakdown_search`, `breakdown_kinds`), and edited in its
 * grid as the project lists `update_work_breakdown` (EP-14/L44c) — a work breakdown read narrowed
 * is never the whole one to write back (`setWorkBreakdown`): the page then reads it whole besides.
 * The identity and the facts of the project are modified in their form, as the project lists the
 * command (`ProjectIdentity`, EP-02/L44a); the sub-projects offer their commands as the project
 * lists `update` — a deletion the estimate lines of the revision in progress hold leading to its
 * estimate, to a session that reads it (EP-14/L53) —, the contributors theirs as it lists
 * `manage_contributors` (EP-02/L44b): to a session that may write them, the page reads the accounts
 * the server proposes (`listContributorSuggestions`, WF-PRJ-0070), and the list whole when the grid
 * reads it filtered — a reading filtered has no counter to write from. Once, under its header, the
 * screen says that the fake back keeps none of what any of these commands writes (`MockupNotice`).
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { type CommandOffer, findOffer } from "@/components/commands/offer";
import { ContextBanner } from "@/components/context/context-banner";
import type { Project } from "@/components/context/reading";
import { readBoolean, readValues } from "@/components/grid/filters";
import { PendingAddress } from "@/components/grid/pending-address";
import { asked, readGridQuery, searched } from "@/components/grid/query";
import type { ContributorReading, Suggestion } from "@/components/projects/contributor-commands";
import { estimatedRevision } from "@/components/projects/estimate-lead";
import { ProjectIdentity } from "@/components/projects/project-form";
import { ProjectStateBadge } from "@/components/projects/project-state-badge";
import {
  BREAKDOWN_ADDRESS,
  BREAKDOWN_GRID_KEY,
  BREAKDOWN_KIND_FILTER,
  BREAKDOWN_KINDS,
  CONTRIBUTOR_ACTIVE,
  CONTRIBUTOR_ADDRESS,
  CONTRIBUTOR_GRID_KEY,
  CONTRIBUTOR_KINDS,
  CONTRIBUTOR_SORT_COLUMNS,
  KINDS,
  SUBPROJECT_ACTUAL_COSTS,
  SUBPROJECT_ADDRESS,
  SUBPROJECT_GRID_KEY,
  SUBPROJECT_SORT_COLUMNS,
  type WorkBreakdown,
} from "@/components/projects/settings-grids";
import {
  ContributorList,
  SubprojectList,
  WorkBreakdownList,
} from "@/components/projects/settings-lists";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { MockupNotice } from "@/components/shell/mockup-notice";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { pageSearch } from "@/navigation/context";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../../title";
import {
  type ProjectParams,
  type ProjectPageProps,
  projectAddress,
  readProjectScreen,
} from "../screen";

/** Title the tab with the settings, and the project. */
export async function generateMetadata({
  params,
}: {
  params: Promise<ProjectParams>;
}): Promise<Metadata> {
  const { projectId } = await params;
  return screenMetadata("functions.projectSettings", projectId);
}

/**
 * The title of the screen, with the icon of its function, and the state of the project; under it,
 * when the screen writes, the notice that the fake back keeps nothing.
 */
function SettingsHeader({
  project,
  writes,
}: {
  readonly project: Project;
  readonly writes: boolean;
}) {
  const t = useTranslations();
  return (
    <>
      <PageHeader
        title={t("functions.projectSettings")}
        icon={FUNCTION_ICONS.project_settings}
        density={FUNCTION_DENSITY.project_settings}
        subtitle={
          <span className="inline-flex items-center gap-2">
            {t("projectFacts.state")}
            <ProjectStateBadge state={project.state} />
          </span>
        }
      />
      {writes ? <MockupNotice /> : null}
    </>
  );
}

/**
 * The commands the project lists: `update` for its identity and its sub-projects,
 * `update_work_breakdown` for its work breakdown — unavailable besides while a background task runs
 * (EP-14/L42s) —, `manage_contributors` for its contributors; whether the screen writes anything —
 * one of them available —, and says once that the fake back keeps nothing.
 */
function offersOf(project: Project) {
  const update = findOffer(project.available_commands, "update");
  const breakdown = findOffer(project.available_commands, "update_work_breakdown");
  const manage = findOffer(project.available_commands, "manage_contributors");
  return {
    update,
    breakdown,
    manage,
    writes: [update, breakdown, manage].some((offer) => offer?.is_available === true),
  };
}

/**
 * What the list of the contributors is written from, to a session the project lets write it: the
 * accounts the server proposes (WF-PRJ-0070), and the list read whole — the one shown, unless it is
 * filtered, without a counter to write from; nothing to any other session.
 */
async function readWritable(
  client: ReturnType<typeof serverClient>,
  projectId: string,
  manage: CommandOffer | undefined,
  shown: ContributorReading,
): Promise<readonly [readonly Suggestion[], ContributorReading | undefined]> {
  if (manage?.is_available !== true) {
    return [[], undefined];
  }
  const path = { project_id: projectId };
  return Promise.all([
    readOrFail("listContributorSuggestions", () =>
      client.GET("/projects/{project_id}/contributors/suggestions", { params: { path } }),
    ),
    shown.lock_version === null
      ? readOrFail("listContributors", () =>
          client.GET("/projects/{project_id}/contributors", { params: { path } }),
        )
      : shown,
  ]);
}

/**
 * What the work breakdown is written from, to a session the project lets write it: the reading the
 * grid shows when it is whole, the one read whole besides when it is filtered — without a counter to
 * write from —; nothing to any other session.
 */
async function readWholeBreakdown(
  client: ReturnType<typeof serverClient>,
  projectId: string,
  offer: CommandOffer | undefined,
  shown: WorkBreakdown,
): Promise<WorkBreakdown | undefined> {
  if (offer?.is_available !== true) {
    return undefined;
  }
  if (shown.lock_version !== null) {
    return shown;
  }
  return readOrFail("getWorkBreakdown", () =>
    client.GET("/projects/{project_id}/work-breakdown", {
      params: { path: { project_id: projectId } },
    }),
  );
}

/** Render the settings of a project, its work breakdown, its sub-projects and its contributors. */
export default async function SettingsPage(props: ProjectPageProps) {
  // An address that names no project is not found before anything is asked.
  const address = await projectAddress(props, "settings");
  const [search, session] = await Promise.all([
    props.searchParams.then((asked) => pageSearch(asked)),
    requestSession(),
  ]);
  const grids = session?.user.display_preferences?.grids ?? undefined;
  const breakdownQuery = readGridQuery<never>(search, [], undefined, BREAKDOWN_ADDRESS);
  const breakdownKinds = readValues(search, BREAKDOWN_KIND_FILTER, BREAKDOWN_KINDS);
  const subprojectQuery = readGridQuery(
    search,
    SUBPROJECT_SORT_COLUMNS,
    grids?.[SUBPROJECT_GRID_KEY]?.sort,
    SUBPROJECT_ADDRESS,
  );
  const actualCosts = readBoolean(search, SUBPROJECT_ACTUAL_COSTS);
  const contributorQuery = readGridQuery(
    search,
    CONTRIBUTOR_SORT_COLUMNS,
    grids?.[CONTRIBUTOR_GRID_KEY]?.sort,
    CONTRIBUTOR_ADDRESS,
  );
  const kinds = readValues(search, CONTRIBUTOR_KINDS, KINDS);
  const active = readBoolean(search, CONTRIBUTOR_ACTIVE);
  const path = { project_id: address.projectId };
  const client = serverClient();
  const [read, breakdown, subprojects, contributors] = await Promise.all([
    readProjectScreen(address),
    readOrFail("getWorkBreakdown", () =>
      client.GET("/projects/{project_id}/work-breakdown", {
        params: {
          path,
          query: {
            ...searched(breakdownQuery),
            ...(breakdownKinds.length === 0 ? {} : { kinds: [...breakdownKinds] }),
          },
        },
      }),
    ),
    readOrFail("listSubprojects", () =>
      client.GET("/projects/{project_id}/subprojects", {
        params: {
          path,
          query: {
            ...asked(subprojectQuery),
            ...(actualCosts === undefined ? {} : { has_actual_costs: actualCosts }),
          },
        },
      }),
    ),
    readOrFail("listContributors", () =>
      client.GET("/projects/{project_id}/contributors", {
        params: {
          path,
          query: {
            ...asked(contributorQuery),
            ...(kinds.length === 0 ? {} : { kinds: [...kinds] }),
            ...(active === undefined ? {} : { is_active: active }),
          },
        },
      }),
    ),
  ]);
  const offers = offersOf(read.project);
  const { update, manage, writes } = offers;
  const [[suggestions, whole], wholeBreakdown] = await Promise.all([
    readWritable(client, address.projectId, manage, contributors),
    readWholeBreakdown(client, address.projectId, offers.breakdown, breakdown),
  ]);
  return (
    <>
      <ContextBanner reading={read} />
      <Screen density={FUNCTION_DENSITY.project_settings}>
        {/* The searches, the sorts and the filters of the grids compose their changes. */}
        <PendingAddress>
          <SettingsHeader project={read.project} writes={writes} />
          {/* Keyed by the project: an answer of the server never outlives its project. */}
          <ProjectIdentity key={read.project.project_id} project={read.project} />
          <WorkBreakdownList
            breakdown={breakdown}
            project={address.projectId}
            kinds={breakdownKinds}
            shown={{
              query: breakdownQuery,
              preferences: grids?.[BREAKDOWN_GRID_KEY] ?? undefined,
            }}
            editing={{
              project: address.projectId,
              offer: offers.breakdown,
              counter: breakdown.lock_version,
              whole: wholeBreakdown,
            }}
          />
          <SubprojectList
            subprojects={subprojects}
            actualCosts={actualCosts}
            editing={{
              project: address.projectId,
              offer: update,
              estimated: estimatedRevision(read.project, session),
            }}
            shown={{
              query: subprojectQuery,
              preferences: grids?.[SUBPROJECT_GRID_KEY] ?? undefined,
            }}
          />
          <ContributorList
            contributors={contributors.items}
            kinds={kinds}
            active={active}
            editing={{
              project: address.projectId,
              offer: manage,
              counter: contributors.lock_version,
              whole,
              suggestions,
            }}
            shown={{
              query: contributorQuery,
              preferences: grids?.[CONTRIBUTOR_GRID_KEY] ?? undefined,
            }}
          />
        </PendingAddress>
      </Screen>
    </>
  );
}
