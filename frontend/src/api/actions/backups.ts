// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the backups (FBS-1.4, EP-02/L43c): a backup started by hand
 * (`startBackup`), a backup marked to be kept or no longer (`retainBackup`), the platform restored
 * from a backup of the list (`startRestore`). The screen asks the server of Next, which calls the
 * API (§4.3.1), and gets back the outcome the one decoder makes of its answer
 * (`src/api/problem.ts`). A backup is downloaded by a route of the front, as a stream, never by an
 * action, which would hold it whole in memory (`app/admin/backups/[backupId]/content`). Nothing is
 * deleted here: the rotation alone deletes a backup (WF-ADM-0170).
 */
"use server";

import { refresh } from "next/cache";

import type { components } from "@/api/generated/schema";
import { type BackgroundTask, decode, decodeTask, type Outcome } from "@/api/problem";
import { serverClient } from "@/api/server";

/** A backup, as the server answers its marking. */
type Backup = components["schemas"]["Backup"];

/**
 * Start a complete backup of the platform (WF-ADM-0150): the API hands it to the worker and answers
 * at once with the reference of the background task (WF-ARC-0090), which the tracker of the shell
 * follows; the backup joins the list once taken.
 */
export async function startBackup(): Promise<Outcome<BackgroundTask>> {
  return decodeTask(() => serverClient().POST("/backups"));
}

/**
 * Mark a backup to be kept, out of the rotation, or no longer (WF-ADM-0170): the API answers the
 * backup as it now is, and the page is read anew — the backup shown as answered meanwhile, the
 * backup having no counter to tell a newer reading by.
 */
export async function retainBackup(backupId: string, retained: boolean): Promise<Outcome<Backup>> {
  const outcome = await decode(() =>
    serverClient().PATCH("/backups/{backup_id}", {
      params: { path: { backup_id: backupId } },
      body: { is_retained: retained },
    }),
  );
  if (outcome.kind === "done") {
    refresh();
  }
  return outcome;
}

/**
 * Restore the whole platform from a backup of the list (WF-ADM-0160), once the user confirmed it:
 * the request states the date of the backup as the confirmation stated it, which the server checks
 * against the backup named. The API answers at once with the reference of the background task.
 */
export async function startRestore(
  backupId: string,
  takenAt: string,
): Promise<Outcome<BackgroundTask>> {
  return decodeTask(() =>
    serverClient().POST("/restores", {
      body: { backup_id: backupId, acknowledged_backup_taken_at: takenAt, confirmed: true },
    }),
  );
}
