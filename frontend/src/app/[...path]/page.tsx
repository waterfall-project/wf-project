// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The page of every function of the navigation whose screen is still to come: the route of
 * each exists from the shell on (`functions.json`), and the lot of a screen replaces it by a
 * page of its own — a route written out wins over this one. An address that leads to no
 * function is not found, and neither is one whose project or revision the API does not find
 * — or does not let the user read, which it answers alike (WF-ADM-0110).
 */
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { serverClient } from "@/api/server";
import { ComingSoon } from "@/components/shell/coming-soon";
import { findScreen, type Screen } from "@/navigation/functions";
import { reach } from "@/session/request";

import { screenMetadata } from "../title";

/** The segments of the address. */
export interface ScreenParams {
  readonly path: readonly string[];
}

/**
 * Whether the project and the revision a screen reads in can be read: `false` when the API
 * answers either is not found. An API out of reach leaves the page to say so (US-0170).
 */
async function found({ projectId, revisionId }: Screen): Promise<boolean> {
  if (projectId === undefined) {
    return true;
  }
  const client = serverClient();
  const [project, revision] = await Promise.all([
    reach(() =>
      client.GET("/projects/{project_id}", { params: { path: { project_id: projectId } } }),
    ),
    revisionId === undefined
      ? undefined
      : reach(() =>
          client.GET("/projects/{project_id}/revisions/{revision_id}", {
            params: { path: { project_id: projectId, revision_id: revisionId } },
          }),
        ),
  ]);
  return project?.response.status !== 404 && revision?.response.status !== 404;
}

/** Title the tab with the function, and with its project when it reads in one. */
export async function generateMetadata({
  params,
}: {
  params: Promise<ScreenParams>;
}): Promise<Metadata> {
  const screen = findScreen((await params).path);
  return screen === undefined ? {} : screenMetadata(screen.fn.label, screen.projectId);
}

/** Render the function the address leads to, whose screen is to come. */
export default async function ScreenPage({ params }: { params: Promise<ScreenParams> }) {
  const screen = findScreen((await params).path);
  if (screen === undefined || !(await found(screen))) {
    notFound();
  }
  return <ComingSoon label={screen.fn.label} />;
}
