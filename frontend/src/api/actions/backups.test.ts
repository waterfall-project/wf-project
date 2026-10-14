// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { startPlatformBackup } from "./backups";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

describe("the server actions of the backups", () => {
  it("ask a backup, which the worker takes [WF-ADM-0150-A]", async () => {
    const client = serve({ "POST /backups": { status: 202, example: "task_backup_queued" } });
    expect(await startPlatformBackup()).toMatchObject({
      kind: "done",
      data: { kind: "backup", status: "queued" },
    });
    expect(client.calls.map(({ route }) => route)).toEqual(["POST /backups"]);
  });
});
