// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the backups (FBS-1.4, EP-02/L43c, US-0440): a backup started by hand
 * (`startBackup`), which the worker takes (WF-ADM-0150); a backup marked to be kept or no longer
 * (`retainBackup`); the deposit of a backup copied out of another installation, in parts
 * (`openChunkedUpload`, `uploadChunk`, `completeChunkedUpload`, #350) — each part under the bound of
 * the body of a server action, which the whole file would pass —; the platform restored from a
 * backup of the list or from a deposit, confirmed at its date (`startRestore`, WF-ADM-0160); the
 * schedule, the retention and the external copy of the backups set (`setBackupSchedule`,
 * EP-14/L43d), an external location tested (`testExternalBackupLocation`); and the probe that says
 * the maintenance of a restoration and its end (`getLiveness`, #604), asked without a token: the
 * restoration closes every session. The screen asks the server of Next, which calls the API
 * (§4.3.1), and gets back the outcome the one decoder makes of its answer (`src/api/problem.ts`). A
 * backup is downloaded by a route of the front, as a stream, never by an action, which would hold it
 * whole in memory (`app/admin/backups/[backupId]/content`). Nothing is deleted here: the rotation
 * alone deletes a backup (WF-ADM-0170).
 */
"use server";

import { refresh } from "next/cache";

import type { components } from "@/api/generated/schema";
import { type BackgroundTask, decode, decodeTask, type Outcome, reach } from "@/api/problem";
import { publicClient, serverClient } from "@/api/server";

/** A backup, as the server answers its marking. */
type Backup = components["schemas"]["Backup"];
/** The schedule of the backups, as it is written and answered whole. */
type BackupSchedule = components["schemas"]["BackupSchedule"];
/** The outcome of a test of an external location. */
type ExternalBackupLocationTest = components["schemas"]["ExternalBackupLocationTest"];

/** A deposit in parts, open: how the file is cut, and the parts received. */
export type ChunkedUpload = components["schemas"]["ChunkedUpload"];

/** A deposit completed: the backup it holds, and the date its manifest says. */
export type FileUpload = components["schemas"]["FileUpload"];

/** What a restoration replaces the platform with: a backup of the list, or a deposit. */
export type RestoreSource =
  { readonly backup_id: string } | { readonly external_backup_upload_id: string };

/** What the probe says of the platform: serving, under maintenance, or not answering at all. */
export type Liveness = "ok" | "maintenance" | "unreachable";

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

/** Open the deposit of a backup by its name and size: the server says how it is cut. */
export async function openBackupDeposit(
  filename: string,
  size: number,
): Promise<Outcome<ChunkedUpload>> {
  return decode(() =>
    serverClient().POST("/chunked-uploads", { body: { filename, size_bytes: size } }),
  );
}

/**
 * Send a part of a deposit, which the browser gives in a form: the API receives its bytes as they
 * are. A form without its part is no request of this front, and is not sent.
 */
export async function sendBackupPart(
  depositId: string,
  part: number,
  form: FormData,
): Promise<Outcome<ChunkedUpload>> {
  const bytes = form.get("part");
  if (!(bytes instanceof Blob)) {
    throw new TypeError("a part of a deposit is a file");
  }
  return decode(() =>
    serverClient().PUT("/chunked-uploads/{chunked_upload_id}/parts/{part_number}", {
      params: { path: { chunked_upload_id: depositId, part_number: part } },
      // The contract types a binary body as a string: the bytes go as they are.
      body: bytes as unknown as string,
      bodySerializer: (body) => body,
      headers: { "Content-Type": "application/octet-stream" },
    }),
  );
}

/** Complete a deposit whose parts are all received: the backup, and the date its manifest says. */
export async function completeBackupDeposit(depositId: string): Promise<Outcome<FileUpload>> {
  return decode(() =>
    serverClient().POST("/chunked-uploads/{chunked_upload_id}/completion", {
      params: { path: { chunked_upload_id: depositId } },
    }),
  );
}

/**
 * Restore the whole platform from a backup of the list or from a deposit (WF-ADM-0160), once the
 * user confirmed it: the request states the date of the backup as the confirmation stated it, which
 * the server checks against the backup named — any other is refused (400,
 * `CONFIRMATION_REQUIRED`). The API answers at once with the reference of the background task, which
 * puts the platform under maintenance.
 */
export async function startRestore(
  source: RestoreSource,
  takenAt: string,
): Promise<Outcome<BackgroundTask>> {
  return decodeTask(() =>
    serverClient().POST("/restores", {
      body: { ...source, acknowledged_backup_taken_at: takenAt, confirmed: true },
    }),
  );
}

/**
 * Set the schedule, the retention and the external copy of the backups (WF-ADM-0170), whole — the
 * operation is a `PUT`, and a copy left out is a copy withdrawn —, from the version read: the API
 * answers the schedule as it now is, which the screen shows in place of what it read, and the page is
 * read anew.
 */
export async function setBackupSchedule(
  schedule: BackupSchedule,
): Promise<Outcome<BackupSchedule>> {
  const outcome = await decode(() => serverClient().PUT("/backup-schedule", { body: schedule }));
  if (outcome.kind === "done") {
    refresh();
  }
  return outcome;
}

/**
 * Test an external location the installation declares (WF-ADM-0170): the server writes then erases a
 * witness file in it, at its root or in the folder given, and answers the outcome — succeeded, or the
 * motive of the failure. Nothing is kept, and nothing is read anew.
 */
export async function testExternalBackupLocation(
  location: string,
  path: string | undefined,
): Promise<Outcome<ExternalBackupLocationTest>> {
  return decode(() =>
    serverClient().POST("/external-backup-locations/{location_name}/test", {
      params: { path: { location_name: location } },
      body: path === undefined ? {} : { path },
    }),
  );
}

/** Ask the probe whether the platform is under maintenance, without any session (#604). */
export async function readLiveness(): Promise<Liveness> {
  const answer = await reach(() => publicClient().GET("/health"));
  return answer?.data?.status ?? "unreachable";
}
