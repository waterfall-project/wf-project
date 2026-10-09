// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import { signOut } from "./session";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

beforeEach(() => {
  server.client = undefined;
});

describe("the server action of the session", () => {
  it("closes the sessions of the account, and holds the user signed out when there was none left", async () => {
    const client = serve({ "DELETE /me/sessions": { status: 204 } });
    expect(await signOut()).toEqual({ kind: "done", data: null });
    expect(client.calls.map((call) => call.route)).toEqual(["DELETE /me/sessions"]);

    serve({ "DELETE /me/sessions": { problem: { code: "SESSION_EXPIRED", status: 401 } } });
    expect(await signOut()).toEqual({ kind: "done", data: null });
  });

  it("holds a deactivated account signed out too: its sessions are closed already", async () => {
    serve({ "DELETE /me/sessions": { problem: { code: "ACCOUNT_DEACTIVATED", status: 401 } } });
    expect(await signOut()).toEqual({ kind: "done", data: null });
  });

  it("says the API out of reach rather than a session closed", async () => {
    server.client = createApiClient({
      address: "http://unreachable.invalid",
      fetch: () => Promise.reject(new TypeError("fetch failed")),
    });
    expect(await signOut()).toEqual({ kind: "unreachable" });
  });
});
