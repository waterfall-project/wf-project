// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { type FakeAnswers, type FakeClient, fakeClient, unreachable } from "@/test/fixtures";

import { GET } from "./route";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));

const TASK = "01926f3a-7c00-7000-8000-000000000905";
const RESULT = "GET /tasks/{task_id}/result";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** Ask the front for the result of the task. */
function download(): Promise<Response> {
  return GET(new Request(`http://front.invalid/tasks/${TASK}/result`), {
    params: Promise.resolve({ taskId: TASK }),
  });
}

beforeEach(() => {
  server.client = undefined;
});

describe("the result of a task, downloaded", () => {
  it("is the file the API gives, handed on as it comes, with its media type", async () => {
    const file = new Blob(["<Project/>"]);
    const client = serve({
      [RESULT]: { body: file, type: "application/octet-stream", status: 200 },
    });
    const response = await download();
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("application/octet-stream");
    expect(await response.text()).toBe("<Project/>");
    expect(client.calls.map((call) => call.path)).toEqual([`/tasks/${TASK}/result`]);
  });

  it("answers the refusal of the API with its status, and no file", async () => {
    serve({ [RESULT]: { problem: { code: "NOT_FOUND", status: 404 } } });
    const missing = await download();
    expect([missing.status, await missing.text()]).toEqual([404, ""]);
    serve({ [RESULT]: { problem: { code: "STATE_FORBIDS_OPERATION", status: 409 } } });
    expect((await download()).status).toBe(409);
  });

  it("answers a bad gateway when the API cannot be reached", async () => {
    server.client = unreachable();
    expect((await download()).status).toBe(502);
  });
});
