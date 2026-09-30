// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The lifecycle of a project (FBS-4.9, US-0210), under the banner of its reading context
 * (WF-IHM-0020): its current state, the exits of its lifecycle the caller may exercise — each
 * available or naming what it lacks (WF-IHM-0090), and confirmed before it is applied —, and the
 * history of its states, dated (WF-CYC-0130). The exits are the one command a screen of a project
 * exercises: the other commands of the project belong to the forms of their domain.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { LifecycleCommands } from "@/components/commands/object-commands";
import { ContextBanner } from "@/components/context/context-banner";
import type { Project } from "@/components/context/reading";
import { TransitionList } from "@/components/projects/project-tables";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { Badge } from "@/components/ui/badge";

import { screenMetadata } from "../../../title";
import {
  type ProjectParams,
  type ProjectPageProps,
  projectAddress,
  readProjectScreen,
} from "../screen";

/** Title the tab with the lifecycle, and the project. */
export async function generateMetadata({
  params,
}: {
  params: Promise<ProjectParams>;
}): Promise<Metadata> {
  const { projectId } = await params;
  return screenMetadata("functions.lifecycle", projectId);
}

/** The title of the screen, the current state of the project, and its exits at the right. */
function LifecycleHeader({ project }: { readonly project: Project }) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.lifecycle")}
      icon={FUNCTION_ICONS.lifecycle}
      density={FUNCTION_DENSITY.lifecycle}
      subtitle={
        <span className="inline-flex items-center gap-2">
          {t("projectFacts.state")}
          <Badge>{t(`enums.ProjectState.${project.state}`)}</Badge>
        </span>
      }
      actions={<LifecycleCommands project={project} />}
    />
  );
}

/** Render the lifecycle of a project: its state, its exits, and its history. */
export default async function LifecyclePage(props: ProjectPageProps) {
  const address = await projectAddress(props, "lifecycle");
  const [read, transitions] = await Promise.all([
    readProjectScreen(address),
    readOrFail("listProjectStateTransitions", () =>
      serverClient().GET("/projects/{project_id}/state-transitions", {
        params: { path: { project_id: address.projectId } },
      }),
    ),
  ]);
  return (
    <>
      <ContextBanner reading={read} />
      <Screen density={FUNCTION_DENSITY.lifecycle}>
        <LifecycleHeader project={read.project} />
        <TransitionList transitions={transitions} />
      </Screen>
    </>
  );
}
