// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of a project (FBS-4.2, US-0210), under the banner of its reading context
 * (WF-IHM-0020): its inflation rate and its probability of winning, its work breakdown, its
 * sub-projects and its contributors, each list a section of the screen under its own title — the
 * ergonomics gathers the leaves of the function on one screen —, and a dense grid (#301), each with
 * its settings and its own names in the address: the sub-projects searched by the server
 * (`subproject_search`), the contributors filtered by it on their capacity (`contributor_kinds`),
 * asked under the names of the contract. The work breakdown is a tree in the order entered. Read
 * only: the forms that modify them belong to the epic of their domain.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { readValues } from "@/components/grid/filters";
import { PendingAddress } from "@/components/grid/pending-address";
import { readGridQuery } from "@/components/grid/query";
import { SettingsFacts } from "@/components/projects/project-facts";
import {
  BREAKDOWN_GRID_KEY,
  CONTRIBUTOR_GRID_KEY,
  CONTRIBUTOR_KINDS,
  KINDS,
  SUBPROJECT_ADDRESS,
  SUBPROJECT_GRID_KEY,
} from "@/components/projects/settings-grids";
import {
  ContributorList,
  SubprojectList,
  UNASKED,
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

/** The title of the screen, with the icon of its function. */
function SettingsHeader() {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.projectSettings")}
      icon={FUNCTION_ICONS.project_settings}
      density={FUNCTION_DENSITY.project_settings}
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
  const subprojectQuery = readGridQuery<never>(search, [], undefined, SUBPROJECT_ADDRESS);
  const kinds = readValues(search, CONTRIBUTOR_KINDS, KINDS);
  const path = { project_id: address.projectId };
  const client = serverClient();
  const [read, breakdown, subprojects, contributors] = await Promise.all([
    readProjectScreen(address),
    readOrFail("getWorkBreakdown", () =>
      client.GET("/projects/{project_id}/work-breakdown", { params: { path } }),
    ),
    readOrFail("listSubprojects", () =>
      client.GET("/projects/{project_id}/subprojects", {
        params: {
          path,
          query: subprojectQuery.search === undefined ? {} : { search: subprojectQuery.search },
        },
      }),
    ),
    readOrFail("listContributors", () =>
      client.GET("/projects/{project_id}/contributors", {
        params: { path, query: kinds.length === 0 ? {} : { kinds: [...kinds] } },
      }),
    ),
  ]);
  return (
    <>
      <ContextBanner reading={read} />
      <Screen density={FUNCTION_DENSITY.project_settings}>
        {/* The search of the sub-projects and the filter of the contributors compose their changes. */}
        <PendingAddress>
          <SettingsHeader />
          <SettingsFacts project={read.project} />
          <WorkBreakdownList
            breakdown={breakdown}
            project={address.projectId}
            shown={{ ...UNASKED, preferences: grids?.[BREAKDOWN_GRID_KEY] ?? undefined }}
          />
          <SubprojectList
            subprojects={subprojects}
            shown={{
              query: subprojectQuery,
              preferences: grids?.[SUBPROJECT_GRID_KEY] ?? undefined,
            }}
          />
          <ContributorList
            contributors={contributors.items}
            kinds={kinds}
            shown={{ ...UNASKED, preferences: grids?.[CONTRIBUTOR_GRID_KEY] ?? undefined }}
          />
        </PendingAddress>
      </Screen>
    </>
  );
}
