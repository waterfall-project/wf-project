// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the backups and the restoration of the platform (US-0440): a backup asked
 * (`startBackup`), which the worker takes (WF-ADM-0150); the deposit of a backup copied out of a
 * platform, in parts (`openChunkedUpload`, `uploadChunk`, `completeChunkedUpload`, #350) — each part
 * under the bound of the body of a server action, which the whole file would pass —; the
 * restoration of a backup of the list or of a deposit, confirmed at its date (`startRestore`,
 * WF-ADM-0160); and the probe that says the maintenance of a restoration and its end
 * (`getLiveness`, #604), asked without a token: the restoration closes every session.
 */
"use server";

import type { components } from "@/api/generated/schema";
import { type BackgroundTask, decode, decodeTask, type Outcome, reach } from "@/api/problem";
import { publicClient, serverClient } from "@/api/server";

/** A deposit in parts, open: how the file is cut, and the parts received. */
export type ChunkedUpload = components["schemas"]["ChunkedUpload"];

/** A deposit completed: the backup it holds, and the date its manifest says. */
export type FileUpload = components["schemas"]["FileUpload"];

/** What a restoration replaces the platform with: a backup of the list, or a deposit. */
export type RestoreSource =
  { readonly backup_id: string } | { readonly external_backup_upload_id: string };

/** What the probe says of the platform: serving, under maintenance, or not answering at all. */
export type Liveness = "ok" | "maintenance" | "unreachable";

/** Ask a backup of the whole platform: the worker takes it, and the hand comes back at once. */
export async function startPlatformBackup(): Promise<Outcome<BackgroundTask>> {
  return decodeTask(() => serverClient().POST("/backups"));
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
 * Restore the platform from a backup, confirmed at the date the confirmation named — the API refuses
 * any other (WF-ADM-0160): the task is queued, and puts the platform under maintenance.
 */
export async function startPlatformRestore(
  source: RestoreSource,
  takenAt: string,
): Promise<Outcome<BackgroundTask>> {
  return decodeTask(() =>
    serverClient().POST("/restores", {
      body: { ...source, acknowledged_backup_taken_at: takenAt, confirmed: true },
    }),
  );
}

/** Ask the probe whether the platform is under maintenance, without any session (#604). */
export async function readLiveness(): Promise<Liveness> {
  const answer = await reach(() => publicClient().GET("/health"));
  return answer?.data?.status ?? "unreachable";
}
