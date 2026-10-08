// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  unreachable,
} from "@/test/fixtures";

import { GET } from "./route";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));

const TASK = "01926f3a-7c00-7000-8000-000000000935";
const RESULT = "GET /tasks/{task_id}/result";
const SHEET = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
/** The screen the download leaves from, with its context. */
const SCREEN = "/projects/p/revisions/r/exchanges?subproject_id=unassigned";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** An API that answers the result with the body and the headers given, as `fetch` hands it on. */
function answering(body: BodyInit, headers: Record<string, string>): void {
  server.client = createApiClient({
    address: "http://fake.invalid",
    fetch: () => Promise.resolve(new Response(body, { status: 200, headers })),
  });
}

/** Ask the front for the result of a task, from a screen. */
function download(taskId = TASK, from: string | null = SCREEN): Promise<Response> {
  const query = from === null ? "" : `?${new URLSearchParams({ from }).toString()}`;
  return GET(new Request(`http://front.invalid/tasks/${taskId}/result${query}`), {
    params: Promise.resolve({ taskId }),
  });
}

/**
 * Where a refusal sent the browser back to: the address of the redirection, a path of the front
 * and its query alone, which nothing keeps.
 */
function sentBackTo(response: Response): string {
  expect(response.status).toBe(303);
  expect(response.headers.get("cache-control")).toBe("private, no-store");
  const location = response.headers.get("location") ?? "";
  expect(location.startsWith("/")).toBe(true);
  return location;
}

beforeEach(() => {
  server.client = undefined;
});

describe("the result of a task, downloaded", () => {
  it("is the file the API gives, handed on as a stream, the attachment of the name it gives, never sniffed", async () => {
    const client = serve({
      [RESULT]: {
        body: new Blob(["devis"]),
        type: SHEET,
        status: 200,
        headers: { "Content-Disposition": example("task_result_disposition") as string },
      },
    });
    const response = await download();
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe(SHEET);
    expect(response.headers.get("content-disposition")).toBe(
      "attachment; filename=\"devis-poste-de-commande.xlsx\"; filename*=UTF-8''devis-poste-de-commande.xlsx",
    );
    expect(response.headers.get("x-content-type-options")).toBe("nosniff");
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(await response.text()).toBe("devis");
    expect(client.calls.map((call) => call.path)).toEqual([`/tasks/${TASK}/result`]);
  });

  it("hands the file on as it comes: answered before the API has sent the whole of it", async () => {
    // A body whose first piece comes, and whose end never does.
    const upstream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode("<Project>"));
      },
    });
    answering(upstream, {
      "content-type": "application/xml; charset=utf-8",
      "content-disposition": 'attachment; filename="planning.xml"',
    });
    const response = await download();
    expect(response.status).toBe(200);
    const reader = response.body?.getReader();
    const first = await reader?.read();
    expect(new TextDecoder().decode(first?.value)).toBe("<Project>");
    await reader?.cancel();
  });

  it("names the file by its base name alone, in UTF-8 and in its ASCII equivalent", async () => {
    answering("<Project/>", {
      "content-type": "application/xml",
      "content-disposition": "attachment; filename*=UTF-8''..%2Fplanning%20%C3%A9t%C3%A9's.xml",
    });
    const response = await download();
    expect(response.headers.get("content-disposition")).toBe(
      "attachment; filename=\"planning _t_'s.xml\"; filename*=UTF-8''planning%20%C3%A9t%C3%A9%27s.xml",
    );
  });

  it("sends the browser back to the screen it left, saying the refusal of the API: a result expired or not ready (#416)", async () => {
    serve({ [RESULT]: { problem: { code: "STATE_FORBIDS_OPERATION", status: 409 } } });
    // The path alone, relative: the browser resolves it on the front it is on.
    expect(sentBackTo(await download())).toBe(
      `/projects/p/revisions/r/exchanges?subproject_id=unassigned&refused_task=${TASK}&refusal=409%3ASTATE_FORBIDS_OPERATION`,
    );
    serve({ [RESULT]: { problem: { code: "NOT_FOUND", status: 404 } } });
    expect(sentBackTo(await download())).toContain("refusal=404%3ANOT_FOUND");
  });

  it.each([
    ["names no file", { "content-type": SHEET }],
    ["names a file it does not attach", { "content-type": SHEET, "content-disposition": "inline" }],
    ["says no media type", { "content-disposition": 'attachment; filename="devis.xlsx"' }],
    [
      "says a media type the contract does not declare for a result",
      { "content-type": "text/html", "content-disposition": 'attachment; filename="devis.xlsx"' },
    ],
  ])(
    "sends the browser back with the unexpected error of a bad gateway when the API %s",
    async (_, headers) => {
      answering(new Blob(["devis"]), headers);
      expect(sentBackTo(await download())).toContain("refusal=502%3AINTERNAL_ERROR");
    },
  );

  it("sends the browser back saying the API out of reach", async () => {
    server.client = unreachable();
    expect(sentBackTo(await download())).toContain("refusal=unreachable");
  });

  it("sends the browser back home rather than to another site, or without a screen", async () => {
    serve({ [RESULT]: { problem: { code: "NOT_FOUND", status: 404 } } });
    expect(sentBackTo(await download(TASK, "//evil.example/x"))).toMatch(/^\/\?refused_task=/);
    expect(sentBackTo(await download(TASK, null))).toMatch(/^\/\?refused_task=/);
  });

  it("asks the API nothing for an address that names no task", async () => {
    const client = serve({});
    expect((await download("..")).status).toBe(404);
    expect(client.calls).toEqual([]);
  });
});
