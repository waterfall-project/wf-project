// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The list of projects, first step of the witness path of the end-to-end harness (US-0080).
 * Scaffolding without text of its own: EP-02 replaces it and keeps the path.
 */
import type { Metadata } from "next";
import Link from "next/link";

import { serverClient } from "@/api/server";

import { screenMetadata } from "../title";

/** Title the tab with the list of projects. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functionGroups.projects");
}

/** Render the projects the API lists. */
export default async function ProjectsPage() {
  const { data } = await serverClient().GET("/projects");
  return (
    <main>
      <ul>
        {data?.items.map((project) => (
          <li key={project.project_id}>
            <Link href={`/projects/${project.project_id}`}>{project.label}</Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
