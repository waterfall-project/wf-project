// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The result of a background task, downloaded (`getBackgroundTaskResult`): the file an export
 * made, on demand and never kept (WF-DAT-0120). The browser calls no API (§4.3.1): the server of
 * Next reads the file and hands it on as a stream, as it comes — never held whole in memory, the
 * contract bounding no result, and out of the one queue of the server actions of Next, which a
 * long download would hold up (#416). It goes with the media type of its kind — one the contract
 * declares for a result, none other —, as the attachment named by the base name the API gives
 * (`attachmentName`), never to be sniffed as another type, nor kept by a cache. Its length is not
 * handed on: `fetch` gives the body decoded, whose length is no longer the one the API sent
 * compressed.
 *
 * The browser follows this route as a link, from a screen it does not leave when the file comes.
 * What the route cannot hand on — a refusal of the API (404, 401, 409: the result expired or not
 * ready), the API out of reach, an answer that names no file, or a media type the contract does
 * not declare, which breaks it — sends the browser back to that screen (`from`), by a relative
 * address, with the refusal in its address, which the tracker tells by the entry of the task, or
 * by a notice of its panel when the task cannot be read again (`result-refusal.ts`). An address
 * that names no task asks the API nothing.
 */
import { attachmentName } from "@/api/disposition";
import { decode } from "@/api/problem";
import { serverClient } from "@/api/server";
import { FROM, refusedHref, type ResultRefusal } from "@/components/tasks/result-refusal";
import { isIdentifier } from "@/navigation/context";

/** An answer of the API that breaks the contract: the unexpected error of a bad gateway. */
const BAD_GATEWAY: ResultRefusal = {
  kind: "refused",
  problem: { code: "INTERNAL_ERROR", status: 502 },
  conflictingObjectId: null,
};

/** The media types the contract declares for the result of a task, by the kind of its export. */
const RESULT_TYPES: ReadonlySet<string> = new Set([
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/xml",
  "image/png",
]);

/** Neither the browser nor anything between keeps the file, nor the way back of a refusal. */
const NOT_KEPT = "private, no-store";

/** Whether a media type is one the contract declares for a result, its parameters aside. */
function declared(type: string | null): type is string {
  return type !== null && RESULT_TYPES.has(type.split(";")[0]?.trim().toLowerCase() ?? "");
}

/** A value of an extended parameter (RFC 8187): UTF-8, encoded in percent. */
function extended(name: string): string {
  return encodeURIComponent(name).replace(
    /['()*]/g,
    (letter) => `%${letter.charCodeAt(0).toString(16).toUpperCase()}`,
  );
}

/** The attachment of a file under its name, its ASCII equivalent first (RFC 6266). */
function attachment(name: string): string {
  const ascii = name.replace(/[^\x20-\x7e]|["\\]/g, "_");
  return `attachment; filename="${ascii}"; filename*=UTF-8''${extended(name)}`;
}

/** Hand on the result of a task, read from the API, or send the browser back to say why not. */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ taskId: string }> },
): Promise<Response> {
  const { taskId } = await params;
  if (!isIdentifier(taskId)) {
    return new Response(null, { status: 404 });
  }
  const from = new URL(request.url).searchParams.get(FROM);
  const back = (refusal: ResultRefusal) =>
    new Response(null, {
      status: 303,
      headers: { location: refusedHref(from, taskId, refusal), "cache-control": NOT_KEPT },
    });
  let headers: Headers | undefined;
  const outcome = await decode(async () => {
    const answer = await serverClient().GET("/tasks/{task_id}/result", {
      params: { path: { task_id: taskId } },
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
  const type = headers?.get("content-type") ?? null;
  if (name === undefined || !declared(type)) {
    await outcome.data?.cancel();
    return back(BAD_GATEWAY);
  }
  return new Response(outcome.data, {
    status: 200,
    headers: {
      "content-disposition": attachment(name),
      "content-type": type,
      "x-content-type-options": "nosniff",
      "cache-control": NOT_KEPT,
    },
  });
}
