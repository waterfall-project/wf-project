// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The list of projects, first step of the witness path of the end-to-end harness (US-0080).
 * Scaffolding: EP-02 replaces it and keeps the path (US-0210). It already carries the
 * empty states of the shell — no project, lifting the contributor filter of the contract
 * (`is_contributor=true` in the address) when that filter empties the list; and, above the
 * list, the prerequisites the minimum reference data lacks, which forbid creating a project
 * (WF-CYC-0120).
 */
import type { Metadata } from "next";
import Link from "next/link";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { NoProjects, ReferenceIncomplete } from "@/components/system/empty-states";
import { type PageSearchParams, pageSearch } from "@/navigation/context";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../title";

/** The address of the list of projects. */
const PROJECTS = "/projects";

/** Title the tab with the list of projects. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functionGroups.projects");
}

/** Render the projects the API lists, and what the reference data lacks, if anything. */
export default async function ProjectsPage({
  searchParams,
}: {
  readonly searchParams: Promise<PageSearchParams>;
}) {
  const contributor = pageSearch(await searchParams).get("is_contributor") === "true";
  const client = serverClient();
  const [projects, readiness, session] = await Promise.all([
    readOrFail("listProjects", () =>
      client.GET("/projects", { params: { query: contributor ? { is_contributor: true } : {} } }),
    ),
    readOrFail("getReferenceReadiness", () => client.GET("/reference/readiness")),
    requestSession(),
  ]);
  return (
    <main>
      <ReferenceIncomplete readiness={readiness} permissions={session?.permissions ?? []} />
      {projects.items.length === 0 ? (
        <NoProjects unfiltered={contributor ? PROJECTS : undefined} />
      ) : (
        <ul>
          {projects.items.map((project) => (
            <li key={project.project_id}>
              <Link href={`${PROJECTS}/${project.project_id}`}>{project.label}</Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
