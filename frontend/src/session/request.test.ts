// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
import { fakeClient } from "@/test/fixtures";

import { requestSession, requestSessionState } from "./request";

const server = vi.hoisted(() => ({ client: undefined as ApiClient | undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));

const UNAUTHORIZED = { problem: { code: "SESSION_REQUIRED", status: 401 } } as const;

describe("the session of a request", () => {
  it("holds the account, its preferences, and the permissions the API evaluated", async () => {
    server.client = fakeClient({ "GET /me": "me_dark" });
    const session = await requestSession();
    expect(session?.display_preferences?.theme).toBe("dark");
    expect(session?.permissions).toContain("system_status.read");
  });

  it("is none without a session", async () => {
    server.client = fakeClient({ "GET /me": UNAUTHORIZED });
    expect(await requestSession()).toBeUndefined();
  });

  it("is none when the API cannot be reached", async () => {
    server.client = createApiClient({
      address: "http://unreachable.invalid",
      fetch: () => Promise.reject(new TypeError("fetch failed")),
    });
    expect(await requestSession()).toBeUndefined();
  });

  it("tells a session the API says is none from one that cannot be read", async () => {
    server.client = fakeClient({ "GET /me": UNAUTHORIZED });
    expect(await requestSessionState()).toEqual({ kind: "signed_out" });
    server.client = createApiClient({
      address: "http://unreachable.invalid",
      fetch: () => Promise.reject(new TypeError("fetch failed")),
    });
    expect(await requestSessionState()).toEqual({ kind: "unreadable" });
    server.client = createApiClient({
      address: "http://gateway.invalid",
      fetch: () => Promise.resolve(new Response("<html>Bad gateway</html>", { status: 502 })),
    });
    expect(await requestSessionState()).toEqual({ kind: "unreadable" });
    server.client = fakeClient({ "GET /me": "me" });
    expect(await requestSessionState()).toMatchObject({ kind: "open" });
  });

  it("tells a deactivated account from a session that is none: the screen says it, no sign-in leads back", async () => {
    server.client = fakeClient({
      "GET /me": { problem: { code: "ACCOUNT_DEACTIVATED", status: 401 } },
    });
    expect(await requestSessionState()).toEqual({ kind: "deactivated" });
    expect(await requestSession()).toBeUndefined();
    server.client = createApiClient({
      address: "http://proxy.invalid",
      fetch: () => Promise.resolve(new Response("<html>Unauthorized</html>", { status: 401 })),
    });
    expect(await requestSessionState()).toEqual({ kind: "signed_out" });
  });

  it("lets a defect through rather than take it for an API out of reach", async () => {
    server.client = fakeClient({});
    await expect(requestSession()).rejects.toThrow("fakeClient: no answer for GET /me");
  });
});
