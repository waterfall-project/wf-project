// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of a project — created (`createProject`), its identity and its facts modified
 * (`updateProject`), taken out of its lifecycle (`exitProject`) —, of its sub-projects
 * (`writeSubproject`, `deleteSubproject`) and of its contributors (`setContributors`): the browser
 * asks the server of Next, which calls the API (§4.3.1), and gets back the outcome the one decoder
 * makes of its answer (`src/api/problem.ts`). A write answered reads the page anew, which lists what
 * the server now retains.
 */
"use server";

import { refresh } from "next/cache";

import type { components } from "@/api/generated/schema";
import { decode, type Outcome, type Settled, settled } from "@/api/problem";
import { serverClient } from "@/api/server";
import type { ProjectState } from "@/api/project-state";

type Schemas = components["schemas"];

/** What the exit of a project from its lifecycle takes: the state it goes to, confirmed. */
type ProjectExit = Schemas["ProjectExit"];

/** Read the page anew once the API has answered a write. */
function readAnew<T>(outcome: Outcome<T>): Outcome<T> {
  if (outcome.kind === "done") {
    refresh();
  }
  return outcome;
}

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
  return readAnew(
    await decode(() =>
      serverClient().PATCH("/projects/{project_id}", {
        params: { path: { project_id: projectId } },
        body: update,
      }),
    ),
  );
}

/**
 * Create a sub-project of a project (WF-PRJ-0050), or modify one from the version read: the API
 * answers it as it now is, or refuses a code another sub-project of the project bears (409).
 */
export async function writeSubproject(
  projectId: string,
  write:
    | { readonly id: undefined; readonly body: Schemas["SubprojectWrite"] }
    | { readonly id: string; readonly body: Schemas["SubprojectUpdate"] },
): Promise<Outcome<Schemas["Subproject"]>> {
  const client = serverClient();
  const project = { project_id: projectId };
  return readAnew(
    await decode(() =>
      write.id === undefined
        ? client.POST("/projects/{project_id}/subprojects", {
            params: { path: project },
            body: write.body,
          })
        : client.PATCH("/projects/{project_id}/subprojects/{subproject_id}", {
            params: { path: { ...project, subproject_id: write.id } },
            body: write.body,
          }),
    ),
  );
}

/**
 * Delete a sub-project (WF-PRJ-0050): refused (409) while a marked revision cites it or actual costs
 * are charged to it, or its project is terminal, the first condition it lacks named
 * (`params.missing_condition`).
 */
export async function deleteSubproject(projectId: string, subprojectId: string): Promise<Settled> {
  return readAnew(
    settled(
      await decode(() =>
        serverClient().DELETE("/projects/{project_id}/subprojects/{subproject_id}", {
          params: { path: { project_id: projectId, subproject_id: subprojectId } },
        }),
      ),
    ),
  );
}

/**
 * Write the whole list of the contributors of a project, each with its capacity, from the counter
 * of the list read whole (WF-PRJ-0060, WF-IHM-0110): the API answers the list with its next counter,
 * or refuses a list without a project manager (409), an account unknown or deactivated (422).
 */
export async function setContributors(
  projectId: string,
  list: Schemas["ContributorsWrite"],
): Promise<Outcome<Schemas["ContributorList"]>> {
  return readAnew(
    await decode(() =>
      serverClient().PUT("/projects/{project_id}/contributors", {
        params: { path: { project_id: projectId } },
        body: list,
      }),
    ),
  );
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
