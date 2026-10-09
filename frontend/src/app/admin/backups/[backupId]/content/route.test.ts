// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
import { type FakeAnswers, type FakeClient, fakeClient, unreachable } from "@/test/fixtures";

import { GET } from "./route";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));

const BACKUP = "01926f3a-7c00-7000-8000-000000000907";
const CONTENT = "GET /backups/{backup_id}/content";
/** The screen the download leaves from: the second page of the backups. */
const SCREEN = "/admin/backups?offset=50";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

/** An API that answers the backup with the body and the headers given, as `fetch` hands it on. */
function answering(body: BodyInit, headers: Record<string, string> = {}): void {
  server.client = createApiClient({
    address: "http://fake.invalid",
    fetch: () => Promise.resolve(new Response(body, { status: 200, headers })),
  });
}

/** Ask the front for a backup, from a screen. */
function download(backupId = BACKUP, from: string | null = SCREEN): Promise<Response> {
  const query = from === null ? "" : `?${new URLSearchParams({ from }).toString()}`;
  return GET(new Request(`http://front.invalid/admin/backups/${backupId}/content${query}`), {
    params: Promise.resolve({ backupId }),
  });
}

/** Where a refusal sent the browser back to: a path of the front and its query, kept by nothing. */
function sentBackTo(response: Response): string {
  expect(response.status).toBe(303);
  expect(response.headers.get("cache-control")).toBe("private, no-store");
  return response.headers.get("location") ?? "";
}

beforeEach(() => {
  server.client = undefined;
});

describe("a backup, downloaded", () => {
  it("is the content the API gives, as an attachment named after the backup, never sniffed nor kept [WF-ADM-0150-A]", async () => {
    const client = serve({
      [CONTENT]: { body: new Blob(["sauvegarde"]), type: "application/octet-stream", status: 200 },
    });
    const response = await download();
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("application/octet-stream");
    expect(response.headers.get("content-disposition")).toBe(
      `attachment; filename="backup-${BACKUP}"; filename*=UTF-8''backup-${BACKUP}`,
    );
    expect(response.headers.get("x-content-type-options")).toBe("nosniff");
    expect(response.headers.get("cache-control")).toBe("private, no-store");
    expect(await response.text()).toBe("sauvegarde");
    expect(client.calls.map((call) => call.path)).toEqual([`/backups/${BACKUP}/content`]);
  });

  it("hands the backup on as it comes, answered before the API has sent the whole of it", async () => {
    // A body whose first piece comes, and whose end never does: gigabytes are never held.
    const upstream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode("PGDMP"));
      },
    });
    answering(upstream, { "content-type": "application/octet-stream" });
    const response = await download();
    expect(response.status).toBe(200);
    const reader = response.body?.getReader();
    const first = await reader?.read();
    expect(new TextDecoder().decode(first?.value)).toBe("PGDMP");
    await reader?.cancel();
  });

  it("names the file as the API names it, and gives its length when the body comes as it was sent", async () => {
    answering("sauvegarde", {
      "content-type": "application/octet-stream",
      "content-length": "10",
      "content-disposition": 'attachment; filename="waterfall-2026-06-03.dump"',
    });
    const response = await download();
    expect(response.headers.get("content-disposition")).toBe(
      "attachment; filename=\"waterfall-2026-06-03.dump\"; filename*=UTF-8''waterfall-2026-06-03.dump",
    );
    expect(response.headers.get("content-length")).toBe("10");
  });

  it("gives no length for a body the API sent encoded, which fetch hands on decoded", async () => {
    answering("sauvegarde", {
      "content-type": "application/octet-stream",
      "content-length": "4",
      "content-encoding": "gzip",
    });
    expect((await download()).headers.get("content-length")).toBeNull();
  });

  it("sends the browser back to the screen of the backups, its page kept, saying a session that may not download them, without the permission of the restoration (403) [WF-ADM-0100-A]", async () => {
    serve({ [CONTENT]: { problem: { code: "PERMISSION_MISSING", status: 403 } } });
    expect(sentBackTo(await download())).toBe(
      `/admin/backups?offset=50&refused_backup=${BACKUP}&refusal=403%3APERMISSION_MISSING`,
    );
  });

  it("sends the browser back saying a backup unknown, or the backups not readable, alike (404) [WF-ADM-0110-A]", async () => {
    serve({ [CONTENT]: { problem: { code: "NOT_FOUND", status: 404 } } });
    expect(sentBackTo(await download())).toBe(
      `/admin/backups?offset=50&refused_backup=${BACKUP}&refusal=404%3ANOT_FOUND`,
    );
  });

  it("sends the browser back with the unexpected error of a bad gateway when the API answers another type than bytes, its body let go", async () => {
    const cancel = vi.fn();
    const upstream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new TextEncoder().encode("<html>"));
      },
      cancel,
    });
    answering(upstream, { "content-type": "text/html; charset=utf-8" });
    expect(sentBackTo(await download())).toBe(
      `/admin/backups?offset=50&refused_backup=${BACKUP}&refusal=502%3AINTERNAL_ERROR`,
    );
    expect(cancel).toHaveBeenCalledOnce();
  });

  it("takes an answer that says no type for bytes, the one type the contract declares", async () => {
    answering(new TextEncoder().encode("sauvegarde"));
    const response = await download();
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toBe("application/octet-stream");
    expect(await response.text()).toBe("sauvegarde");
  });

  it("sends the browser back saying the API out of reach", async () => {
    server.client = unreachable();
    expect(sentBackTo(await download())).toContain("refusal=unreachable");
  });

  it("sends the browser back to the screen of the backups alone, never another screen nor another site", async () => {
    serve({ [CONTENT]: { problem: { code: "NOT_FOUND", status: 404 } } });
    for (const from of ["//evil.example/admin/backups", "/admin/users", "/admin/backupsx", null]) {
      expect(sentBackTo(await download(BACKUP, from))).toMatch(
        /^\/admin\/backups\?refused_backup=/,
      );
    }
  });

  it("asks the API nothing for an address that names no backup", async () => {
    const client = serve({});
    expect((await download("..")).status).toBe(404);
    expect(client.calls).toEqual([]);
  });
});
