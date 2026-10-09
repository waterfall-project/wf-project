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
 * names none. The work breakdown is a tree in the order entered, searched on its labels and filtered
 * on its kinds by the server (`breakdown_search`, `breakdown_kinds`). Read only: the forms that
 * modify them belong to the epic of their domain — and a work breakdown read narrowed is never the
 * whole one to write back (`setWorkBreakdown`).
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import type { Project } from "@/components/context/reading";
import { readBoolean, readValues } from "@/components/grid/filters";
import { PendingAddress } from "@/components/grid/pending-address";
import { asked, readGridQuery, searched } from "@/components/grid/query";
import { SettingsFacts } from "@/components/projects/project-facts";
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
} from "@/components/projects/settings-grids";
import {
  ContributorList,
  SubprojectList,
  WorkBreakdownList,
} from "@/components/projects/settings-lists";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
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

/** The title of the screen, with the icon of its function, and the state of the project. */
function SettingsHeader({ project }: { readonly project: Project }) {
  const t = useTranslations();
  return (
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
  return (
    <>
      <ContextBanner reading={read} />
      <Screen density={FUNCTION_DENSITY.project_settings}>
        {/* The searches, the sorts and the filters of the grids compose their changes. */}
        <PendingAddress>
          <SettingsHeader project={read.project} />
          <SettingsFacts project={read.project} />
          <WorkBreakdownList
            breakdown={breakdown}
            project={address.projectId}
            kinds={breakdownKinds}
            shown={{
              query: breakdownQuery,
              preferences: grids?.[BREAKDOWN_GRID_KEY] ?? undefined,
            }}
          />
          <SubprojectList
            subprojects={subprojects}
            actualCosts={actualCosts}
            shown={{
              query: subprojectQuery,
              preferences: grids?.[SUBPROJECT_GRID_KEY] ?? undefined,
            }}
          />
          <ContributorList
            contributors={contributors.items}
            kinds={kinds}
            active={active}
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
