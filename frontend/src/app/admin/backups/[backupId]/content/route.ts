// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The archive of a backup, downloaded (`downloadBackup`, WF-ADM-0150): the copy out of the platform
 * that protects from its loss. The browser calls no API (§4.3.1): the server of Next reads the
 * archive and hands it on as a stream, as it comes — never held whole in memory, an archive being
 * as large as the platform —, as the attachment named by the base name the API gives, never sniffed
 * as another type, nor kept by a cache, as the result of a task is (`tasks/[taskId]/result`).
 *
 * The browser follows this route as a link from the screen of the backups, which it does not leave
 * when the archive comes. What the route cannot hand on — a refusal of the API, the API out of
 * reach, an answer that names no file — sends the browser back to that screen, with the refusal in
 * its address, which the screen tells. An address that names no backup asks the API nothing.
 */
import { attachment, attachmentName } from "@/api/disposition";
import { decode } from "@/api/problem";
import { serverClient } from "@/api/server";
import { BACKUPS_ROUTE, DOWNLOAD_REFUSAL } from "@/components/admin/backup-address";
import { type ResultRefusal, saidRefusal } from "@/components/tasks/result-refusal";
import { isIdentifier } from "@/navigation/context";

/** An answer of the API that breaks the contract: the unexpected error of a bad gateway. */
const BAD_GATEWAY: ResultRefusal = {
  kind: "refused",
  problem: { code: "INTERNAL_ERROR", status: 502 },
  conflictingObjectId: null,
};

/** Neither the browser nor anything between keeps the archive, nor the way back of a refusal. */
const NOT_KEPT = "private, no-store";

/** The screen of the backups, saying why the archive was not handed on. */
function back(refusal: ResultRefusal): Response {
  const query = new URLSearchParams({ [DOWNLOAD_REFUSAL]: saidRefusal(refusal) });
  return new Response(null, {
    status: 303,
    headers: { location: `${BACKUPS_ROUTE}?${query.toString()}`, "cache-control": NOT_KEPT },
  });
}

/** Hand on the archive of a backup, read from the API, or send the browser back to say why not. */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ backupId: string }> },
): Promise<Response> {
  const { backupId } = await params;
  if (!isIdentifier(backupId)) {
    return new Response(null, { status: 404 });
  }
  let headers: Headers | undefined;
  const outcome = await decode(async () => {
    const answer = await serverClient().GET("/backups/{backup_id}/content", {
      params: { path: { backup_id: backupId } },
      parseAs: "stream",
    });
    headers = answer.response.headers;
    return answer;
  });
  if (outcome.kind !== "done") {
    return back(outcome);
  }
  const disposition = headers?.get("content-disposition") ?? null;
  const name = disposition === null ? undefined : attachmentName(disposition);
  if (name === undefined) {
    await outcome.data?.cancel();
    return back(BAD_GATEWAY);
  }
  return new Response(outcome.data, {
    status: 200,
    headers: {
      "content-disposition": attachment(name),
      "content-type": "application/octet-stream",
      "x-content-type-options": "nosniff",
      "cache-control": NOT_KEPT,
    },
  });
}
