// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A project, second step of the witness path (US-0080): the banner of its reading context
 * (WF-IHM-0020), its label, and its revisions — or, when it has none yet, that it has none,
 * with the way to the function of its revisions when the session may read them. A project the API does not find is not
 * found, as at the other screens of a project. Scaffolding: EP-02 replaces it and keeps the
 * path (US-0210).
 */
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { readProjectContext } from "@/components/context/reading";
import { NoRevisions } from "@/components/system/empty-states";
import { type PageSearchParams, pageSearch, readContext } from "@/navigation/context";
import { functionHref, functionOf } from "@/navigation/functions";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../title";

/** The route parameters of a project. */
export interface ProjectParams {
  readonly projectId: string;
}

/** Title the tab with the project. */
export async function generateMetadata({
  params,
}: {
  params: Promise<ProjectParams>;
}): Promise<Metadata> {
  const { projectId } = await params;
  return screenMetadata("functionGroups.projects", projectId);
}

/** Render a project and links to its revisions. */
export default async function ProjectPage({
  params,
  searchParams,
}: {
  params: Promise<ProjectParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [{ projectId }, search] = await Promise.all([params, searchParams]);
  const pathname = `/projects/${projectId}`;
  // An address that names no project is not found before the API is asked anything.
  const context = readContext(pathname, pageSearch(search));
  if (context === undefined) {
    notFound();
  }
  const [revisions, read, session] = await Promise.all([
    readOrFail("listRevisions", () =>
      serverClient().GET("/projects/{project_id}/revisions", {
        params: { path: { project_id: projectId } },
      }),
    ),
    readProjectContext(pathname, context),
    requestSession(),
  ]);
  // The way to the revisions is offered as the navigation offers them: to a session that
  // may read them.
  const mayReadRevisions = session?.permissions.includes("revisions.read") === true;
  if (read === "not_found") {
    notFound();
  }
  return (
    <>
      <ContextBanner reading={read} />
      <main>
        <h1>{read.project.label}</h1>
        {revisions.items.length === 0 ? (
          <NoRevisions
            revisions={
              mayReadRevisions ? functionHref(functionOf("revisions"), read.context) : undefined
            }
          />
        ) : (
          <ul>
            {revisions.items.map((revision) => (
              <li key={revision.revision_id}>
                <Link href={`/projects/${projectId}/revisions/${revision.revision_id}`}>
                  {revision.version_name ?? revision.revision_id}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </main>
    </>
  );
}
