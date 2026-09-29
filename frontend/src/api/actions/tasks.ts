// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server action of the follow-up of background tasks (`getBackgroundTask`): the tracker
 * of the shell asks the server of Next for the progress of a task, which calls the API
 * (§4.3.1) and gets back the outcome the one decoder makes of its answer (`decodeTask`).
 */
"use server";

import { type BackgroundTask, decodeTask, type Outcome } from "@/api/problem";
import { serverClient } from "@/api/server";

/**
 * Read where a background task stands: queued, running and how far, succeeded, or failed with
 * its motive (WF-ARC-0090, WF-IHM-0080). The API judges whether the caller may read it.
 */
export async function readBackgroundTask(taskId: string): Promise<Outcome<BackgroundTask>> {
  return decodeTask(() =>
    serverClient().GET("/tasks/{task_id}", { params: { path: { task_id: taskId } } }),
  );
}
