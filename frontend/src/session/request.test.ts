// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
import { fakeClient } from "@/test/fixtures";

import { requestAccount, requestPermissions } from "./request";

const server = vi.hoisted(() => ({ client: undefined as ApiClient | undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));

const UNAUTHORIZED = { problem: { code: "SESSION_REQUIRED", status: 401 } } as const;

describe("the session of a request", () => {
  it("reads the permissions the API evaluated for the session", async () => {
    server.client = fakeClient({ "GET /session": "session_project_manager" });
    const permissions = await requestPermissions();
    expect(permissions).toContain("portfolio_projects.read");
    expect(permissions).not.toContain("system_status.read");
  });

  it("reads the account and its preferences", async () => {
    server.client = fakeClient({ "GET /me": "me_dark" });
    expect((await requestAccount())?.display_preferences?.theme).toBe("dark");
  });

  it("has neither account nor permissions without a session", async () => {
    server.client = fakeClient({ "GET /me": UNAUTHORIZED, "GET /session": UNAUTHORIZED });
    expect(await requestAccount()).toBeUndefined();
    expect(await requestPermissions()).toBeUndefined();
  });

  it("has neither when the API cannot be reached", async () => {
    server.client = createApiClient({
      address: "http://unreachable.invalid",
      fetch: () => Promise.reject(new TypeError("fetch failed")),
    });
    expect(await requestAccount()).toBeUndefined();
    expect(await requestPermissions()).toBeUndefined();
  });
});
