// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The result of a background task, downloaded (`getBackgroundTaskResult`): the file an export
 * made, on demand and never kept (WF-DAT-0120). The browser calls no API (§4.3.1): the server of
 * Next reads the file and hands it on as it comes, with its media type and its name; the API
 * judges whether the caller may read it, and its refusal — the task unknown or not readable, its
 * result not ready, no session — is answered with the same status and no file.
 */
import { reach } from "@/api/problem";
import { serverClient } from "@/api/server";

/** The headers of the file the API gives that the browser needs to save it. */
const KEPT = ["content-type", "content-disposition", "content-length"] as const;

/** Hand on the result of a task, read from the API. */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ taskId: string }> },
): Promise<Response> {
  const { taskId } = await params;
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
  const headers = new Headers();
  for (const name of KEPT) {
    const value = response.headers.get(name);
    if (value !== null) {
      headers.set(name, value);
    }
  }
  return new Response(answer.data ?? null, { status: 200, headers });
}
