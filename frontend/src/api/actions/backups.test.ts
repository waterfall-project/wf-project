// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { type FakeAnswers, type FakeClient, fakeClient, unreachable } from "@/test/fixtures";

import {
  completeBackupDeposit,
  openBackupDeposit,
  readLiveness,
  sendBackupPart,
  startBackup,
  startRestore,
} from "./backups";

const server = vi.hoisted((): { client: ApiClient | undefined; open: ApiClient | undefined } => ({
  client: undefined,
  open: undefined,
}));

vi.mock("@/api/server", () => ({
  serverClient: () => server.client,
  publicClient: () => server.open,
}));

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

const DEPOSIT = "01926f3a-7c00-7000-8000-000000000a02";
const PART = "PUT /chunked-uploads/{chunked_upload_id}/parts/{part_number}";

describe("the server actions of the backups", () => {
  it("ask a backup, which gives its task back queued: the request held no longer than its creation [WF-ARC-0090-A]", async () => {
    const client = serve({ "POST /backups": { status: 202, example: "task_backup_queued" } });
    expect(await startBackup()).toMatchObject({
      kind: "done",
      data: { kind: "backup", status: "queued" },
    });
    expect(client.calls.map(({ route }) => route)).toEqual(["POST /backups"]);
  });

  it("open a deposit by the name and size of the file, send a part as its bytes, and complete it with the date of the backup", async () => {
    const client = serve({
      "POST /chunked-uploads": { status: 201, example: "chunked_upload" },
      [PART]: { status: 200, example: "chunked_upload_part" },
      "POST /chunked-uploads/{chunked_upload_id}/completion": {
        status: 201,
        example: "chunked_upload_completed",
      },
    });
    expect(await openBackupDeposit("waterfall-2026-06-02.tar", 12_582_912)).toMatchObject({
      kind: "done",
      data: { part_size_bytes: 5_242_880, part_count: 3 },
    });
    const form = new FormData();
    form.set("part", new Blob(["the bytes of the part"]));
    expect(await sendBackupPart(DEPOSIT, 2, form)).toMatchObject({
      kind: "done",
      data: { received_parts: [1, 2] },
    });
    expect(await completeBackupDeposit(DEPOSIT)).toMatchObject({
      kind: "done",
      data: { purpose: "external_backup", backup_taken_at: "2026-06-02T01:00:00Z" },
    });
    expect(client.calls.map(({ path }) => path)).toEqual([
      "/chunked-uploads",
      `/chunked-uploads/${DEPOSIT}/parts/2`,
      `/chunked-uploads/${DEPOSIT}/completion`,
    ]);
    expect(client.calls[0]?.body).toEqual({
      filename: "waterfall-2026-06-02.tar",
      size_bytes: 12_582_912,
    });
    const sent = client.calls[1]?.body;
    expect(sent).toBeInstanceOf(Blob);
    expect(await (sent as Blob).text()).toBe("the bytes of the part");
  });

  it("refuse to send a form without its part", async () => {
    serve({});
    await expect(sendBackupPart(DEPOSIT, 1, new FormData())).rejects.toThrow(TypeError);
  });

  it("tell the refusal of a deposit whose archive does not say its date", async () => {
    serve({
      "POST /chunked-uploads/{chunked_upload_id}/completion": {
        problem: { code: "FILE_FORMAT_UNREADABLE", status: 422 },
      },
    });
    expect(await completeBackupDeposit(DEPOSIT)).toMatchObject({
      kind: "refused",
      problem: { code: "FILE_FORMAT_UNREADABLE" },
    });
  });

  it("restore a backup of the list or a deposit at the date the confirmation names", async () => {
    const client = serve({ "POST /restores": { status: 202, example: "task_restore_queued" } });
    expect(
      await startRestore(
        { backup_id: "01926f3a-7c00-7000-8000-000000000906" },
        "2026-06-02T01:00:00Z",
      ),
    ).toMatchObject({ kind: "done", data: { kind: "restore", status: "queued" } });
    await startRestore({ external_backup_upload_id: DEPOSIT }, "2026-06-02T01:00:00Z");
    expect(client.calls.map(({ body }) => body)).toEqual([
      {
        backup_id: "01926f3a-7c00-7000-8000-000000000906",
        acknowledged_backup_taken_at: "2026-06-02T01:00:00Z",
        confirmed: true,
      },
      {
        external_backup_upload_id: DEPOSIT,
        acknowledged_backup_taken_at: "2026-06-02T01:00:00Z",
        confirmed: true,
      },
    ]);
  });

  it("ask the probe without any token, and say the maintenance, its end, or the API out of reach", async () => {
    const open = fakeClient({
      "GET /health": [{ status: 200, example: "liveness_maintenance" }, "liveness"],
    });
    server.open = open;
    expect(await readLiveness()).toBe("maintenance");
    expect(await readLiveness()).toBe("ok");
    expect(open.calls.map(({ authorization }) => authorization)).toEqual([null, null]);
    server.open = unreachable();
    expect(await readLiveness()).toBe("unreachable");
  });
});
