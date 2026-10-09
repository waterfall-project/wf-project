// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the revisions of a project (`markRevision`): the browser asks the
 * server of Next, which calls the API (§4.3.1), and gets back the outcome the one decoder makes
 * of its answer (`src/api/problem.ts`).
 */
"use server";

import type { components } from "@/api/generated/schema";
import { type BackgroundTask, decodeTask, type Outcome } from "@/api/problem";
import { serverClient } from "@/api/server";

/** What marking a revision takes: its version name, and the version of the revision read. */
type RevisionMark = components["schemas"]["RevisionMark"];

/**
 * Mark a revision under a version name (WF-REV-0020): the API hands the marking to the worker
 * and answers at once with the reference of the background task (WF-ARC-0090), which the
 * tracker of the shell follows. A version name already taken, a revision already marked or
 * read in an older version are refusals of the API, told as such.
 */
export async function markRevision(
  projectId: string,
  revisionId: string,
  mark: RevisionMark,
): Promise<Outcome<BackgroundTask>> {
  return decodeTask(() =>
    serverClient().POST("/projects/{project_id}/revisions/{revision_id}/mark", {
      params: { path: { project_id: projectId, revision_id: revisionId } },
      body: mark,
    }),
  );
}
