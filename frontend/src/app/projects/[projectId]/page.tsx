// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A project (US-0210), second step of the witness path (US-0080): the banner of its reading
 * context (WF-IHM-0020), its label, what it is — its code, its state, its order, its
 * description —, and its revisions — or, when it has none yet, that it has none, with the way to
 * the function of its revisions when the session may read them. A project the API does not find
 * is not found, as at the other screens of a project. Nothing is offered to modify it: its form
 * belongs to the epic of its domain.
 */
import { FolderOpen, GitBranch } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useId } from "react";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import type { components } from "@/api/generated/schema";
import { ContextBanner } from "@/components/context/context-banner";
import { ProjectFacts } from "@/components/projects/project-facts";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { NoRevisions } from "@/components/system/empty-states";
import { functionHref, functionOf } from "@/navigation/functions";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../title";
import {
  type ProjectPageProps,
  type ProjectParams,
  projectAddress,
  readProjectScreen,
} from "./screen";

type RevisionSummary = Pick<
  components["schemas"]["Revision"],
  "revision_id" | "version_name" | "status"
>;

/** Title the tab with the project. */
export async function generateMetadata({
  params,
}: {
  params: Promise<ProjectParams>;
}): Promise<Metadata> {
  const { projectId } = await params;
  return screenMetadata("functionGroups.projects", projectId);
}

/** The revisions of a project, each a link to it, or that it has none. */
function Revisions({
  projectId,
  revisions,
  way,
}: {
  readonly projectId: string;
  readonly revisions: readonly RevisionSummary[];
  /** The way to the function of the revisions, when the session may read them. */
  readonly way: string | undefined;
}) {
  const t = useTranslations();
  const title = useId();
  return (
    <section aria-labelledby={title} className="space-y-2">
      <h2 id={title} className="flex items-center gap-2 text-base font-semibold">
        <GitBranch aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
        {t("projectFacts.revisions")}
      </h2>
      {revisions.length === 0 ? (
        <NoRevisions revisions={way} />
      ) : (
        <ul className="space-y-1 text-sm">
          {revisions.map((revision) => (
            <li key={revision.revision_id}>
              <Link
                href={`/projects/${projectId}/revisions/${revision.revision_id}`}
                className="underline-offset-4 hover:underline"
              >
                {revision.version_name ??
                  (revision.status === "draft"
                    ? t("contextBanner.currentRevision")
                    : t(`enums.RevisionStatus.${revision.status}`))}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** Render a project, what it is, and links to its revisions. */
export default async function ProjectPage(props: ProjectPageProps) {
  const address = await projectAddress(props);
  const [revisions, read, session] = await Promise.all([
    readOrFail("listRevisions", () =>
      serverClient().GET("/projects/{project_id}/revisions", {
        params: { path: { project_id: address.projectId } },
      }),
    ),
    readProjectScreen(address),
    requestSession(),
  ]);
  // The way to the revisions is offered as the navigation offers them: to a session that
  // may read them.
  const mayReadRevisions = session?.permissions.includes("revisions.read") === true;
  return (
    <>
      <ContextBanner reading={read} />
      <Screen>
        <PageHeader title={read.project.label} icon={FolderOpen} />
        <ProjectFacts project={read.project} />
        <Revisions
          projectId={address.projectId}
          revisions={revisions.items}
          way={mayReadRevisions ? functionHref(functionOf("revisions"), read.context) : undefined}
        />
      </Screen>
    </>
  );
}
