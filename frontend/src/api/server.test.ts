// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { API_PREFIX } from "./client";
import { DEFAULT_ADDRESS, isMockAuthentication, MOCK_TOKEN, serverClient } from "./server";

/** Stub the platform's fetch, which the server client uses: the addresses it is asked for. */
function stubFetch(authorizations: (string | null)[] = []): string[] {
  const urls: string[] = [];
  vi.stubGlobal("fetch", (request: Request) => {
    urls.push(request.url);
    authorizations.push(request.headers.get("Authorization"));
    return Promise.resolve(Response.json({ status: "ok" }));
  });
  return urls;
}

beforeEach(() => {
  vi.stubEnv("WATERFALL_AUTH", undefined);
  vi.stubEnv("WATERFALL_E2E", undefined);
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("serverClient", () => {
  it("calls the fake back of make mock when no address is configured", async () => {
    vi.stubEnv("WATERFALL_API_ADDRESS", undefined);
    const urls = stubFetch();
    const { data } = await serverClient().GET("/health");
    expect(DEFAULT_ADDRESS).toBe("http://localhost:4010");
    expect(urls).toEqual([`http://localhost:4010${API_PREFIX}/health`]);
    expect(data).toEqual({ status: "ok" });
  });

  it("calls the API at the configured address, read each time a client is made", async () => {
    const urls = stubFetch();
    vi.stubEnv("WATERFALL_API_ADDRESS", "http://mock:4010");
    await serverClient().GET("/health");
    vi.stubEnv("WATERFALL_API_ADDRESS", "https://api.example");
    await serverClient().GET("/health");
    expect(urls).toEqual([
      `http://mock:4010${API_PREFIX}/health`,
      `https://api.example${API_PREFIX}/health`,
    ]);
  });
});

describe("the mock authentication", () => {
  it("sends the fixed token of the fake back, and nothing without the mode", async () => {
    const sent: (string | null)[] = [];
    stubFetch(sent);
    vi.stubEnv("WATERFALL_AUTH", undefined);
    await serverClient().GET("/health");
    vi.stubEnv("WATERFALL_AUTH", "mock");
    await serverClient().GET("/health");
    expect(sent).toEqual([null, `Bearer ${MOCK_TOKEN}`]);
  });

  it("is refused in production, except for the end-to-end harness", () => {
    vi.stubEnv("WATERFALL_AUTH", "mock");
    vi.stubEnv("NODE_ENV", "production");
    expect(() => isMockAuthentication()).toThrow("refused in production");
    vi.stubEnv("WATERFALL_E2E", "1");
    expect(isMockAuthentication()).toBe(true);
  });

  it("refuses a mode that is not mock", () => {
    vi.stubEnv("WATERFALL_AUTH", "oidc");
    expect(() => isMockAuthentication()).toThrow('must be "mock"');
  });
});

describe("the module of the server client", () => {
  afterEach(() => {
    vi.doMock("server-only", () => ({}));
    vi.resetModules();
  });

  it("refuses to load outside the server of Next", async () => {
    vi.doUnmock("server-only");
    vi.resetModules();
    await expect(import("./server")).rejects.toThrow("Client Component");
  });
});
