// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The background tasks of the report of a version (US-2300): the export of the planning of PRJ-001,
 * the analysis then the application of an import of eighteen thousand lines of actual costs, and
 * the marking of its revision — the volumes of §4.6.2 —, each asked as the user of the browser of
 * the measure, by the operations of the contract, and read at its task (`getBackgroundTask`), from
 * its submission to its end: the time the worker took, its wait in the queue included, not the
 * moment the measure happened to ask again. The import counts its two tasks, its analysis and its
 * application, without the time between them, which is the user's.
 *
 * An extraction is a workbook of the mapping of the witness (`in-progress.ts`), its lines spread
 * over the subprojects of the project, each pass's documents its own: a pass imports eighteen
 * thousand new lines, never lines an earlier pass imported, which the analysis would find
 * unchanged. The volume is therefore not constant from one pass to the next: the second pass
 * imports its eighteen thousand lines beside the eighteen thousand of the first, the third beside
 * thirty-six thousand, and the report says it as it is — each pass is a project that has received
 * more costs, as a project does. A marking freezes the revision it marks: the passes after the
 * first open the current revision again (`createRevision`, outside the measure), and mark it.
 */
import { type APIRequestContext, expect } from "@playwright/test";

import type { components } from "../../src/api/generated/schema";
import { HEADERS } from "../in-progress";
import { API } from "../service/realm";
import { workbook } from "../workbook";
import { momentOf } from "./report";
import { type TaskRead, taskSeconds } from "./version";

type Schemas = components["schemas"];

/** How many lines of actual costs an import carries: the most a project receives (§4.6.2). */
export const IMPORTED_LINES = 18_000;

/** How long a background task is waited for: past the five minutes of the slowest objective. */
const TASK_BOUND = 20 * 60_000;

/** How often a task is asked how it stands, in milliseconds. */
const ASKED_EVERY = 1_000;

/** The API as the user of the measure calls it, by a token it renews itself. */
export interface Caller {
  readonly get: <T>(path: string) => Promise<T>;
  readonly post: <T>(path: string, data: unknown) => Promise<T>;
  readonly upload: (name: string, content: Buffer) => Promise<string>;
}

/** The API under the token `token` gives at each call. */
export function caller(request: APIRequestContext, token: () => Promise<string>): Caller {
  const headers = async () => ({ Authorization: `Bearer ${await token()}` });
  return {
    get: async <T>(path: string) => {
      const answer = await request.get(`${API}${path}`, { headers: await headers() });
      expect(answer.status(), `GET ${path}: ${await answer.text()}`).toBe(200);
      return (await answer.json()) as T;
    },
    post: async <T>(path: string, data: unknown) => {
      const answer = await request.post(`${API}${path}`, { headers: await headers(), data });
      expect(answer.ok(), `POST ${path}: ${await answer.text()}`).toBe(true);
      return (await answer.json()) as T;
    },
    upload: async (name, content) => {
      const answer = await request.post(`${API}/file-uploads`, {
        headers: await headers(),
        multipart: {
          purpose: "import",
          file: {
            name,
            mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            buffer: content,
          },
        },
      });
      expect(answer.status(), `POST file-uploads: ${await answer.text()}`).toBe(201);
      return ((await answer.json()) as Schemas["FileUpload"]).upload_id;
    },
  };
}

/** A background task waited for until it ends, then how long it took, in seconds. */
async function ended(api: Caller, task: TaskRead): Promise<number> {
  let read = task;
  const asked = () => api.get<TaskRead>(`/tasks/${task.task_id}`);
  await expect
    .poll(
      async () => {
        read = await asked();
        return read.status === "succeeded" || read.status === "failed";
      },
      {
        message: `the background task ${task.task_id} ends`,
        timeout: TASK_BOUND,
        intervals: [ASKED_EVERY],
      },
    )
    .toBe(true);
  return taskSeconds(read, momentOf);
}

/**
 * The export of the planning of a revision, from its request to its file (`ms_project_schedule`).
 */
export async function exportPlanning(api: Caller, project: string, revision: string) {
  const task = await api.post<TaskRead>(`/projects/${project}/exports`, {
    kind: "ms_project_schedule",
    revision_id: revision,
  });
  return ended(api, task);
}

/**
 * The lines of an extraction of a pass: its WBS elements on the subprojects of the project in
 * turn (the code of a subproject is the whole element, the service compares it whole), its
 * documents its own, its dates within a month, its amounts in cents of every size.
 */
export function extraction(subprojects: readonly string[], pass: number) {
  return Array.from({ length: IMPORTED_LINES }, (_, line) => [
    subprojects[line % subprojects.length] ?? "",
    `MV${String(pass)}-${String(line + 1).padStart(5, "0")}`,
    null,
    `2026-10-${String((line % 28) + 1).padStart(2, "0")}`,
    (((line * 7919) % 500_000) + 100) / 100,
  ]);
}

/**
 * The analysis then the application of an import of the extraction of a pass, read at its tasks.
 */
export async function importCosts(api: Caller, project: string, pass: number) {
  const { code } = await api.get<Schemas["Project"]>(`/projects/${project}`);
  const subprojects = await api.get<Schemas["Subproject"][]>(`/projects/${project}/subprojects`);
  if (code === null || subprojects.length === 0) {
    throw new Error("PRJ-001 of the witness has a code and subprojects: the witness is not loaded");
  }
  const lines = extraction(
    subprojects.map((subproject) => subproject.code),
    pass,
  );
  const upload = await api.upload(`mesure-${String(pass)}.xlsx`, workbook([HEADERS, ...lines]));
  const opened = await api.post<{ import_id: string; task: TaskRead }>(
    `/projects/${project}/imports`,
    { kind: "actual_costs", upload_id: upload },
  );
  const analysis = await ended(api, opened.task);
  const applied = await api.post<TaskRead>(
    `/projects/${project}/imports/${opened.import_id}/apply`,
    { confirmed: true },
  );
  return analysis + (await ended(api, applied));
}

/**
 * The marking of the current revision of the project, read at its task; past the first pass, the
 * current revision opened first, outside the measure.
 */
export async function markRevision(api: Caller, project: string, version: string, pass: number) {
  if (pass > 0) {
    await api.post<Schemas["Revision"]>(`/projects/${project}/revisions`, {});
  }
  const { current_revision_id: current } = await api.get<Schemas["Project"]>(
    `/projects/${project}`,
  );
  if (current === null) {
    throw new Error("PRJ-001 has no current revision to mark");
  }
  const revision = await api.get<Schemas["Revision"]>(`/projects/${project}/revisions/${current}`);
  const task = await api.post<TaskRead>(`/projects/${project}/revisions/${current}/mark`, {
    version_name: `Mesure ${version} ${String(pass + 1)}`,
    lock_version: revision.lock_version,
  });
  return ended(api, task);
}
