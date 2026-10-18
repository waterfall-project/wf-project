// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The lifecycle of a project (FBS-4.9, US-0210), under the banner of its reading context
 * (WF-IHM-0020): its current state, the exits of its lifecycle the caller may exercise — each
 * available or naming what it lacks (WF-IHM-0090), and confirmed before it is applied, being
 * irreversible (WF-CYC-0090) —, its next state, the trigger that leads to it and the conditions it
 * still lacks, read without trying anything (WF-CYC-0050) — no command leads to pricing or in
 * progress (WF-CYC-0020) —, and the history of its states, dated (WF-CYC-0130).
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { LifecycleCommands } from "@/components/commands/object-commands";
import { ContextBanner } from "@/components/context/context-banner";
import type { Project } from "@/components/context/reading";
import { NextStateFacts } from "@/components/projects/next-state";
import { ProjectStateBadge } from "@/components/projects/project-state-badge";
import { TransitionList } from "@/components/projects/project-tables";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";

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
          <ProjectStateBadge state={project.state} />
        </span>
      }
      actions={<LifecycleCommands project={project} />}
    />
  );
}

/** Render the lifecycle of a project: its state, its exits, its next state, and its history. */
export default async function LifecyclePage(props: ProjectPageProps) {
  const address = await projectAddress(props, "lifecycle");
  const path = { project_id: address.projectId };
  const client = serverClient();
  const [read, next, transitions] = await Promise.all([
    readProjectScreen(address),
    readOrFail("getProjectNextState", () =>
      client.GET("/projects/{project_id}/next-state", { params: { path } }),
    ),
    readOrFail("listProjectStateTransitions", () =>
      client.GET("/projects/{project_id}/state-transitions", { params: { path } }),
    ),
  ]);
  return (
    <>
      <ContextBanner reading={read} />
      <Screen density={FUNCTION_DENSITY.lifecycle}>
        <LifecycleHeader project={read.project} />
        <NextStateFacts next={next} />
        <TransitionList transitions={transitions} />
      </Screen>
    </>
  );
}
