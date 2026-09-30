// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of a project (`exitProject`): the browser asks the server of Next, which
 * calls the API (§4.3.1), and gets back the outcome the one decoder makes of its answer
 * (`src/api/problem.ts`).
 */
"use server";

import { refresh } from "next/cache";

import type { components } from "@/api/generated/schema";
import { decode, type Outcome } from "@/api/problem";
import { serverClient } from "@/api/server";

/** What the exit of a project from its lifecycle takes: the state it goes to, confirmed. */
type ProjectExit = components["schemas"]["ProjectExit"];

/** The state of the lifecycle of a project. */
type ProjectState = components["schemas"]["ProjectState"];

/**
 * Take a project out of its lifecycle, once the user has confirmed it (WF-CYC-0060, WF-CYC-0090):
 * the state the API answers it is in, and the page rendered again, which reads the project anew,
 * read only. An exit the state of the project forbids is a refusal of the API, told as such.
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
  if (outcome.kind !== "done") {
    return outcome;
  }
  refresh();
  return { kind: "done", data: outcome.data.state };
}
