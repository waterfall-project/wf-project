// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
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

/**
 * An API that answers the result with the headers given, its body as `fetch` hands it on: decoded,
 * whatever encoding the API sent it in.
 */
function answering(body: string, headers: Record<string, string>): void {
  server.client = createApiClient({
    address: "http://fake.invalid",
    fetch: () => Promise.resolve(new Response(body, { status: 200, headers })),
  });
}

/** Ask the front for the result of a task. */
function download(taskId = TASK): Promise<Response> {
  return GET(new Request(`http://front.invalid/tasks/${taskId}/result`), {
    params: Promise.resolve({ taskId }),
  });
}

beforeEach(() => {
  server.client = undefined;
});

describe("the result of a task, downloaded", () => {
  it("is the file the API gives, handed on as it comes, the attachment it names, never sniffed", async () => {
    const disposition = 'attachment; filename="planning-poste-de-commande.xml"';
    let asked: string | undefined;
    server.client = createApiClient({
      address: "http://fake.invalid",
      fetch: (request) => {
        asked = new URL(request.url).pathname;
        const headers = { "content-type": "application/xml", "content-disposition": disposition };
        return Promise.resolve(new Response("<Project/>", { status: 200, headers }));
      },
    });
    const response = await download();
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("application/xml");
    expect(response.headers.get("content-disposition")).toBe(disposition);
    expect(response.headers.get("x-content-type-options")).toBe("nosniff");
    expect(await response.text()).toBe("<Project/>");
    expect(asked).toBe(`/api/v1/tasks/${TASK}/result`);
  });

  it("answers a bad gateway when the API names no file, which the contract promises", async () => {
    serve({ [RESULT]: { body: new Blob(["<Project/>"]), type: "application/xml", status: 200 } });
    const response = await download();
    expect([response.status, await response.text()]).toEqual([502, ""]);
  });

  it("hands on the whole of a file the API sent compressed, without the length it had then", async () => {
    answering("<Project><Tasks/></Project>", {
      "content-type": "application/xml",
      "content-disposition": 'attachment; filename="planning.xml"',
      "content-encoding": "gzip",
      "content-length": "12",
    });
    const response = await download();
    expect(response.headers.get("content-length")).toBeNull();
    expect(response.headers.get("content-encoding")).toBeNull();
    expect(await response.text()).toBe("<Project><Tasks/></Project>");
  });

  it("answers the refusal of the API with its status, and no file", async () => {
    serve({ [RESULT]: { problem: { code: "NOT_FOUND", status: 404 } } });
    const missing = await download();
    expect([missing.status, await missing.text()]).toEqual([404, ""]);
    serve({ [RESULT]: { problem: { code: "STATE_FORBIDS_OPERATION", status: 409 } } });
    expect((await download()).status).toBe(409);
  });

  it("asks the API nothing for an address that names no task", async () => {
    const client = serve({});
    expect((await download("..")).status).toBe(404);
    expect(client.calls).toEqual([]);
  });

  it("answers a bad gateway when the API cannot be reached", async () => {
    server.client = unreachable();
    expect((await download()).status).toBe(502);
  });
});
