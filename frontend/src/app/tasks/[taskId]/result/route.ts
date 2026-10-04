// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The result of a background task, downloaded (`getBackgroundTaskResult`): the file an export
 * made, on demand and never kept (WF-DAT-0120). The browser calls no API (§4.3.1): the server of
 * Next reads the file and hands it on as it comes, with its media type, as an attachment — named
 * as the API names it, when it does: the contract does not promise it yet (#323) —, and never to
 * be sniffed as another type. Its length is not handed on: `fetch` gives the body decoded, whose
 * length is no longer the one the API sent compressed. The API judges whether the caller may read
 * it, and its refusal — the task unknown or not readable, its result not ready, no session — is
 * answered with the same status and no file; an address that names no task asks the API nothing.
 */
import { reach } from "@/api/problem";
import { serverClient } from "@/api/server";
import { isIdentifier } from "@/navigation/context";

/** Hand on the result of a task, read from the API. */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ taskId: string }> },
): Promise<Response> {
  const { taskId } = await params;
  if (!isIdentifier(taskId)) {
    return new Response(null, { status: 404 });
  }
  const answer = await reach(() =>
    serverClient().GET("/tasks/{task_id}/result", {
      params: { path: { task_id: taskId } },
      parseAs: "stream",
    }),
  );
  if (answer === undefined) {
    return new Response(null, { status: 502 });
  }
  const { response } = answer;
  if (!response.ok) {
    return new Response(null, { status: response.status });
  }
  const headers = new Headers({
    "content-disposition": response.headers.get("content-disposition") ?? "attachment",
    "x-content-type-options": "nosniff",
  });
  const type = response.headers.get("content-type");
  if (type !== null) {
    headers.set("content-type", type);
  }
  return new Response(answer.data ?? null, { status: 200, headers });
}
