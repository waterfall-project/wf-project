// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A backup, downloaded (`downloadBackup`, WF-ADM-0150), under the permission of the restoration
 * (`platform_restore`), which the server judges. The server of Next hands it on as a stream, never
 * held whole in memory — a backup weighs gigabytes —, out of the queue of the server actions
 * (`relay.ts`): bytes, the one type the contract declares, under the name the API gives it
 * (`Content-Disposition`, which the contract requires: `waterfall-backup-`, the instant of the backup
 * and the extension of its archive, EP-14/L42h), of its length when the body comes as it was sent,
 * not encoded, `fetch` handing it on decoded.
 *
 * What the route cannot hand on — a refusal of the API (403; 404, a backup unknown or not readable
 * alike, WF-ADM-0110; 409, a backup not yet verified, as its command said), the API out of reach,
 * another type than bytes or a file the API does not name (502) — sends the browser back
 * to the screen of the backups (`from`), the backup and the refusal in its address
 * (`backup-address.ts`). An address that names no backup asks the API nothing.
 */
import { attachmentName } from "@/api/disposition";
import { BAD_GATEWAY, handedOn, mediaType, readFile, sentBack } from "@/api/relay";
import { serverClient } from "@/api/server";
import { downloadRefusedHref } from "@/components/admin/backup-address";
import { FROM } from "@/components/tasks/result-refusal";
import { isIdentifier } from "@/navigation/context";

/** The one type the contract declares for a backup. */
const BYTES = "application/octet-stream";

/** Hand on a backup, read from the API, or send the browser back to say why not. */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ backupId: string }> },
): Promise<Response> {
  const { backupId } = await params;
  if (!isIdentifier(backupId)) {
    return new Response(null, { status: 404 });
  }
  const from = new URL(request.url).searchParams.get(FROM);
  const { outcome, headers } = await readFile(() =>
    serverClient().GET("/backups/{backup_id}/content", {
      params: { path: { backup_id: backupId } },
      parseAs: "stream",
    }),
  );
  if (outcome.kind !== "done") {
    return sentBack(downloadRefusedHref(from, backupId, outcome));
  }
  const type = headers?.get("content-type") ?? BYTES;
  const file = named(headers);
  if (mediaType(type) !== BYTES || file === undefined) {
    await outcome.data?.cancel();
    return sentBack(downloadRefusedHref(from, backupId, BAD_GATEWAY));
  }
  return handedOn(outcome.data ?? null, { ...file, type });
}

/**
 * The name of a backup, as the API gives it, and its length when the body comes as it was sent, not
 * encoded; none when the API names no file, against the contract.
 */
function named(
  headers: Headers | undefined,
): { readonly name: string; readonly length: string | undefined } | undefined {
  const disposition = headers?.get("content-disposition");
  const name = disposition == null ? undefined : attachmentName(disposition);
  if (name === undefined) {
    return undefined;
  }
  const length = headers?.get("content-length");
  return {
    name,
    length: length != null && headers?.get("content-encoding") == null ? length : undefined,
  };
}
