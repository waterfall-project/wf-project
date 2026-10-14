// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
import { fakeClient, unreachable } from "@/test/fixtures";

import { GET } from "./route";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));

const BACKUP = "01926f3a-7c00-7000-8000-000000000907";

/** An API that answers the archive with the body and the headers given, as `fetch` hands it on. */
function answering(body: BodyInit, headers: Record<string, string>): void {
  server.client = createApiClient({
    address: "http://fake.invalid",
    fetch: () => Promise.resolve(new Response(body, { status: 200, headers })),
  });
}

/** Ask the front for the archive of a backup. */
function download(backupId = BACKUP): Promise<Response> {
  return GET(new Request(`http://front.invalid/admin/backups/${backupId}/content`), {
    params: Promise.resolve({ backupId }),
  });
}

/** Where a refusal sent the browser back to, which nothing keeps. */
function sentBackTo(response: Response): string {
  expect(response.status).toBe(303);
  expect(response.headers.get("cache-control")).toBe("private, no-store");
  return response.headers.get("location") ?? "";
}

describe("the archive of a backup", () => {
  it("is handed on as a stream, as the attachment the API names, kept by no cache [WF-ADM-0150-A]", async () => {
    answering("the archive", {
      "content-type": "application/octet-stream",
      "content-disposition": 'attachment; filename="waterfall-2026-06-03.tar"',
    });
    const response = await download();
    expect(response.status).toBe(200);
    expect(response.headers.get("content-disposition")).toBe(
      "attachment; filename=\"waterfall-2026-06-03.tar\"; filename*=UTF-8''waterfall-2026-06-03.tar",
    );
    expect(response.headers.get("content-type")).toBe("application/octet-stream");
    expect(response.headers.get("x-content-type-options")).toBe("nosniff");
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(await response.text()).toBe("the archive");
  });

  it("asks nothing of the API for an address that names no backup", async () => {
    const client = fakeClient({});
    server.client = client;
    expect((await download("..")).status).toBe(404);
    expect(client.calls).toEqual([]);
  });

  it("sends the browser back to the screen of the backups with the refusal of the API", async () => {
    server.client = fakeClient({
      "GET /backups/{backup_id}/content": { problem: { code: "NOT_FOUND", status: 404 } },
    });
    expect(sentBackTo(await download())).toBe("/admin/backups?download_refusal=404%3ANOT_FOUND");
    server.client = unreachable();
    expect(sentBackTo(await download())).toBe("/admin/backups?download_refusal=unreachable");
  });

  it("sends the browser back with the unexpected error when the API names no file", async () => {
    answering("the archive", { "content-type": "application/octet-stream" });
    expect(sentBackTo(await download())).toBe(
      "/admin/backups?download_refusal=502%3AINTERNAL_ERROR",
    );
  });
});
