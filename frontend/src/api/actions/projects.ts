// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of a project — created (`createProject`), its identity and its facts modified
 * (`updateProject`), taken out of its lifecycle (`exitProject`) —: the browser asks the server of
 * Next, which calls the API (§4.3.1), and gets back the outcome the one decoder makes of its answer
 * (`src/api/problem.ts`).
 */
"use server";

import { refresh } from "next/cache";

import type { components } from "@/api/generated/schema";
import { decode, type Outcome } from "@/api/problem";
import { serverClient } from "@/api/server";
import type { ProjectState } from "@/api/project-state";

type Schemas = components["schemas"];

/** What the exit of a project from its lifecycle takes: the state it goes to, confirmed. */
type ProjectExit = Schemas["ProjectExit"];

/**
 * Create a project (WF-PRJ-0080): the API answers it, its creator its project manager
 * (WF-PRJ-0060), or refuses it — the minimum reference data incomplete, naming what it lacks
 * (WF-CYC-0120), a code another project bears (WF-PRJ-0010). Nothing is read anew: the screen leads
 * to the project created.
 */
export async function createProject(
  project: Schemas["ProjectCreate"],
): Promise<Outcome<Schemas["Project"]>> {
  return decode(() => serverClient().POST("/projects", { body: project }));
}

/**
 * Modify the identity and the facts of a project from the version read (WF-PRJ-0080): the API
 * answers the project as it now is, which the screen shows in place of what it read, and the page is
 * read anew — the banner, the commands the project offers.
 */
export async function updateProject(
  projectId: string,
  update: Schemas["ProjectUpdate"],
): Promise<Outcome<Schemas["Project"]>> {
  const outcome = await decode(() =>
    serverClient().PATCH("/projects/{project_id}", {
      params: { path: { project_id: projectId } },
      body: update,
    }),
  );
  if (outcome.kind === "done") {
    refresh();
  }
  return outcome;
}

/**
 * Take a project out of its lifecycle, once the user has confirmed it (WF-CYC-0060, WF-CYC-0090):
 * the state the API answers it is in, and the page rendered again, which reads the project anew,
 * read only. An exit the state of the project forbids is a refusal of the API, told as such —
 * and the page rendered again too, so that it no longer offers what the server refused.
 */
export async function exitProject(
  projectId: string,
  exit: ProjectExit,
): Promise<Outcome<ProjectState>> {
  const outcome = await decode(() =>
    serverClient().POST("/projects/{project_id}/exit", {
      params: { path: { project_id: projectId } },
      body: exit,
    }),
  );
  // Applied, or refused for the state of the project (409): the page reads the project anew,
  // and offers what the server offers now.
  if (outcome.kind === "done" || outcome.kind === "conflict") {
    refresh();
  }
  return outcome.kind === "done" ? { kind: "done", data: outcome.data.state } : outcome;
}
