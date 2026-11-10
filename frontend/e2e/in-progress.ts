// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A project the account of the run takes In progress, by the operations of the service, under the
 * token of its creator: the way a user does it, which the paths of the remaining to commit need
 * (`importRemaining` is offered to a project in progress alone, WF-CYC-0030). The planning seeded
 * has a line of labour that employs the role of the witness, its revision is marked by the worker,
 * designated as the reference, the code of the project is entered, and the current revision is
 * opened from the reference.
 */
import { type APIRequestContext, expect } from "@playwright/test";

import { WORKING } from "./hydration";
import { API } from "./service/realm";
import type { Seeded } from "./planning-seed";

type Headers = Readonly<Record<string, string>>;

/** The identifiers of the current revision a project In progress opens, and of its main structure. */
export interface Successor {
  readonly revision: string;
  readonly structure: string;
}

/** How long the worker is given to mark: a task taken from the queue, one transaction. */
const MARKING = 60_000;

/** Read a counter of an object of the service, which a write must send back. */
async function lockOf(
  calls: APIRequestContext,
  headers: Headers,
  address: string,
): Promise<number> {
  const read = await calls.get(address, { headers });
  expect(read.status(), `GET ${address}`).toBe(200);
  return ((await read.json()) as { lock_version: number }).lock_version;
}

/**
 * Mark the revision seeded, designate it as the reference, enter the code of the project — which
 * takes it In progress — and open the current revision. The seeded revision must bear a task and a
 * line (`employRole`).
 */
export async function takeInProgress(
  calls: APIRequestContext,
  seeded: Seeded,
  code: string,
): Promise<Successor> {
  const { headers } = seeded;
  const project = `${API}/projects/${seeded.ids.project}`;
  const revision = `${project}/revisions/${seeded.ids.revision}`;

  const marked = await calls.post(`${revision}/mark`, {
    headers,
    data: { version_name: "v1.0", lock_version: await lockOf(calls, headers, revision) },
  });
  expect(marked.status(), "POST mark").toBe(202);
  const task = ((await marked.json()) as { task_id: string }).task_id;
  await expect(async () => {
    const read = await calls.get(`${API}/tasks/${task}`, { headers });
    expect(read.status(), "GET task").toBe(200);
    expect(((await read.json()) as { status: string }).status).toBe("succeeded");
  }).toPass({ timeout: MARKING });

  const designated = await calls.put(`${project}/reference-revision`, {
    headers,
    data: {
      revision_id: seeded.ids.revision,
      confirmed: true,
      lock_version: await lockOf(calls, headers, project),
    },
  });
  expect(designated.status(), "PUT reference-revision").toBe(200);
  const coded = await calls.patch(project, {
    headers,
    data: { code, lock_version: await lockOf(calls, headers, project) },
  });
  expect(coded.status(), "PATCH project").toBe(200);
  expect(((await coded.json()) as { state: string }).state).toBe("in_progress");

  const opened = await calls.post(`${project}/revisions`, { headers, data: {} });
  expect(opened.status(), "POST revisions").toBe(201);
  const successor = ((await opened.json()) as { revision_id: string }).revision_id;
  await expect(async () => {
    const structures = await calls.get(`${project}/revisions/${successor}/structures`, { headers });
    expect(structures.status(), "GET structures").toBe(200);
    const main = ((await structures.json()) as { structure_id: string; kind: string }[]).find(
      ({ kind }) => kind === "main",
    );
    expect(main).toBeDefined();
  }).toPass({ timeout: WORKING });
  const structures = await calls.get(`${project}/revisions/${successor}/structures`, { headers });
  const main = ((await structures.json()) as { structure_id: string; kind: string }[]).find(
    ({ kind }) => kind === "main",
  );
  return { revision: successor, structure: main?.structure_id ?? "" };
}
