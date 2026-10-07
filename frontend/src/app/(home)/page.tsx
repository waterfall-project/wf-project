// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The home, which is the list of projects (US-0090, US-0210): filtered by default on the
 * projects the user contributes to, by the filter of the contract (`is_contributor`), which the
 * screen shows and a link lifts — a filter, never a restriction of reading (WF-PRJ-0060). Above
 * the list, in every case, the prerequisites the minimum reference data lacks, which forbid
 * creating a project (WF-CYC-0120); and, when the list holds no project, that it is — the
 * filter shown above it lifts it. The page after the first is asked by its `offset`, as the
 * contract names it; a page beyond the end of the list leads back into it.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContributorFilter, ProjectList } from "@/components/projects/project-list";
import { GROUP_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { ReferenceIncomplete } from "@/components/system/empty-states";
import { type PageSearchParams, pageSearch } from "@/navigation/context";
import { isContributorFiltered } from "@/navigation/home";
import { OFFSET_PARAMETER, offsetOf } from "@/navigation/pages";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../title";

/** Title the tab with the list of projects. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functionGroups.projects");
}

/** The title of the list, with the icon of its block, and its filter at the right. */
function ProjectsHeader({ filtered }: { readonly filtered: boolean }) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functionGroups.projects")}
      icon={GROUP_ICONS["functionGroups.projects"]}
      actions={<ContributorFilter filtered={filtered} />}
    />
  );
}

/** Render the projects the API lists, and what the reference data lacks, if anything. */
export default async function HomePage({
  searchParams,
}: {
  readonly searchParams: Promise<PageSearchParams>;
}) {
  const search = pageSearch(await searchParams);
  const filtered = isContributorFiltered(search);
  const offset = offsetOf(search.get(OFFSET_PARAMETER));
  const client = serverClient();
  const [projects, readiness, session] = await Promise.all([
    readOrFail("listProjects", () =>
      client.GET("/projects", {
        params: {
          query: {
            ...(filtered ? { is_contributor: true } : {}),
            ...(offset === undefined ? {} : { offset }),
          },
        },
      }),
    ),
    readOrFail("getReferenceReadiness", () => client.GET("/reference/readiness")),
    requestSession(),
  ]);
  return (
    <Screen>
      <ProjectsHeader filtered={filtered} />
      <ReferenceIncomplete readiness={readiness} permissions={session?.permissions ?? []} />
      <ProjectList projects={projects.items} page={projects.meta} filtered={filtered} />
    </Screen>
  );
}
