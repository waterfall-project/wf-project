// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A planning the account of the run writes in the service, for the paths of the grid and of the
 * Gantt that play against it (US-1470): the witness holds no task in the service before its filler
 * (US-1480), and the account of the run is no contributor of PRJ-001 (#2193), so each path writes a
 * project of its own, as a user does — the project made from the home, its revision opened — and its
 * first tasks by the API, under the token of its creator. The same tasks every time, in the order of
 * the plan:
 *
 *   1 Études (summary)            2 Études de détail   3 Revue de conception   4 Réception des études
 *   5 Installation sur site       6 Mise en service
 */
import { type APIRequestContext, type Browser, expect, type Page } from "@playwright/test";

import { createOwnProject, openRevision, type OwnProject } from "./own-project";
import { API, frontToken, type LocalPerson } from "./service/realm";

/** The labels of the planning seeded, by row number. */
export const SEEDED = {
  1: "Études",
  2: "Études de détail",
  3: "Revue de conception",
  4: "Réception des études",
  5: "Installation sur site",
  6: "Mise en service",
} as const;

/** What a path keeps of the planning it seeded. */
export interface Seeded {
  readonly own: OwnProject;
  /** The address of the revision in progress, under which the screens are. */
  readonly revision: string;
  /** The address of its planning. */
  readonly planning: string;
  /** The identifiers of the project, of the revision and of the main structure. */
  readonly ids: { readonly project: string; readonly revision: string; readonly structure: string };
  /** The identifier of each task, by row number. */
  readonly nodes: Readonly<Record<number, string>>;
  /** The headers of the creator of the project, to write by the API as she does. */
  readonly headers: { readonly Authorization: string };
}

interface Created {
  nodes: { node_id: string }[];
}

/** The tasks, each by its place: the row of its parent (0, none), and its duration in days. */
const TASKS: readonly (readonly [parent: number, label: string, days: string])[] = [
  [0, SEEDED[1], "1"],
  [1, SEEDED[2], "5"],
  [1, SEEDED[3], "3"],
  [1, SEEDED[4], "0"],
  [0, SEEDED[5], "10"],
  [0, SEEDED[6], "2"],
];

/**
 * Create a project from the home, open its revision, and write the six tasks of the planning under
 * the token of its creator. The sequence of the tasks is the order of the plan: each is created after
 * the last of its siblings.
 */
export async function seedPlanning(
  page: Page,
  browser: Browser,
  calls: APIRequestContext,
  creator: LocalPerson | undefined,
  prefix: string,
): Promise<Seeded> {
  if (creator === undefined) {
    throw new Error("the manager of the worker is made against the service");
  }
  const own = await createOwnProject(page, prefix);
  await openRevision(page, own);
  // The address of the revision opened names it by `revision_id`, on the screen of the revisions.
  const opened = new URL(page.url()).searchParams.get("revision_id");
  if (opened === null) {
    throw new Error("the revision opened is not named by its address");
  }
  const revision = `${own.path}/revisions/${opened}`;
  const ids = {
    project: own.path.split("/").at(-1) ?? "",
    revision: revision.split("/").at(-1) ?? "",
    structure: "",
  };
  const headers = { Authorization: `Bearer ${await frontToken(browser, creator)}` };
  const structures = await calls.get(
    `${API}/projects/${ids.project}/revisions/${ids.revision}/structures`,
    { headers },
  );
  expect(structures.status(), "GET structures").toBe(200);
  const main = ((await structures.json()) as { structure_id: string; kind: string }[]).find(
    ({ kind }) => kind === "main",
  );
  if (main === undefined) {
    throw new Error("a revision opened has a main structure");
  }
  const structure = main.structure_id;
  const nodes: Record<number, string> = {};
  let row = 0;
  // The summary comes before its subordinates in the plan, which the order of TASKS keeps; a task
  // created under a leaf makes it a summary, so the order of the rows is that of the plan.
  for (const [parent, label, days] of TASKS) {
    row += 1;
    const created = await calls.post(
      `${API}/projects/${ids.project}/revisions/${ids.revision}/structures/${structure}/nodes`,
      {
        headers,
        data: {
          kind: "task",
          parent_id: parent === 0 ? null : (nodes[parent] ?? null),
          task: { label, duration: { value: days, unit: "d" } },
        },
      },
    );
    expect(created.status(), `POST nodes ${label}`).toBe(201);
    const body = (await created.json()) as Created;
    const node = body.nodes[0];
    if (node === undefined) {
      throw new Error("a node created is answered");
    }
    nodes[row] = node.node_id;
  }
  return {
    own,
    revision,
    planning: `${revision}/planning`,
    ids: { ...ids, structure },
    nodes,
    headers,
  };
}
