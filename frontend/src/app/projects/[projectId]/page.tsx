// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A project, second step of the witness path (US-0080): its label, and its revisions.
 * Scaffolding without text of its own: EP-02 replaces it and keeps the path.
 */
import type { Metadata } from "next";
import Link from "next/link";

import { serverClient } from "@/api/server";

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
export default async function ProjectPage({ params }: { params: Promise<ProjectParams> }) {
  const { projectId } = await params;
  const client = serverClient();
  const path = { path: { project_id: projectId } };
  const [project, revisions] = await Promise.all([
    client.GET("/projects/{project_id}", { params: path }),
    client.GET("/projects/{project_id}/revisions", { params: path }),
  ]);
  return (
    <main>
      <h1>{project.data?.label}</h1>
      <ul>
        {revisions.data?.items.map((revision) => (
          <li key={revision.revision_id}>
            <Link href={`/projects/${projectId}/revisions/${revision.revision_id}`}>
              {revision.version_name ?? revision.revision_id}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
