// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of a project (FBS-4.2, US-0210), under the banner of its reading context
 * (WF-IHM-0020): its inflation rate and its probability of winning, its sub-projects and its
 * contributors, each list a section of the screen under its own title — the ergonomics gathers
 * the leaves of the function on one screen. Read only: the forms that modify them belong to the
 * epic of their domain.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { SettingsFacts } from "@/components/projects/project-facts";
import { ContributorList, SubprojectList } from "@/components/projects/project-tables";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";

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

/** Render the settings of a project, its sub-projects and its contributors. */
export default async function SettingsPage(props: ProjectPageProps) {
  const address = await projectAddress(props, "settings");
  const path = { params: { path: { project_id: address.projectId } } };
  const client = serverClient();
  const [read, subprojects, contributors] = await Promise.all([
    readProjectScreen(address),
    readOrFail("listSubprojects", () => client.GET("/projects/{project_id}/subprojects", path)),
    readOrFail("listContributors", () => client.GET("/projects/{project_id}/contributors", path)),
  ]);
  return (
    <>
      <ContextBanner reading={read} />
      <Screen density={FUNCTION_DENSITY.project_settings}>
        <SettingsHeader />
        <SettingsFacts project={read.project} />
        <SubprojectList subprojects={subprojects} />
        <ContributorList contributors={contributors} />
      </Screen>
    </>
  );
}
