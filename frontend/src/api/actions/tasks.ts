// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the follow-up of background tasks (`getBackgroundTask`,
 * `listBackgroundTasks`): the tracker of the shell asks the server of Next for the progress of a
 * task, or for the tasks of its user that still run, which calls the API (§4.3.1) and gets back
 * the outcome the one decoder makes of its answer (`decodeTask`, `decodeTasks`).
 */
"use server";

import { type BackgroundTask, decodeTask, decodeTasks, type Outcome } from "@/api/problem";
import { serverClient } from "@/api/server";

/**
 * Read the background tasks the caller started that still run — queued or running —, whatever
 * tab or workstation started them (WF-ARC-0090, WF-IHM-0080): the most recent first, the first
 * page, which holds more tasks than a user starts at once.
 */
export async function listRunningTasks(): Promise<Outcome<readonly BackgroundTask[]>> {
  return decodeTasks(() =>
    serverClient().GET("/tasks", { params: { query: { status: ["queued", "running"] } } }),
  );
}

/**
 * Read where a background task stands: queued, running and how far, succeeded, or failed with
 * its motive (WF-ARC-0090, WF-IHM-0080). The API judges whether the caller may read it.
 */
export async function readBackgroundTask(taskId: string): Promise<Outcome<BackgroundTask>> {
  return decodeTask(() =>
    serverClient().GET("/tasks/{task_id}", { params: { path: { task_id: taskId } } }),
  );
}
