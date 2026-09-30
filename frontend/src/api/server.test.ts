// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { afterEach, describe, expect, it, vi } from "vitest";

import { API_PREFIX } from "./client";
import { DEFAULT_ADDRESS, serverClient } from "./server";

/** Stub the platform's fetch, which the server client uses: the addresses it is asked for. */
function stubFetch(): string[] {
  const urls: string[] = [];
  vi.stubGlobal("fetch", (request: Request) => {
    urls.push(request.url);
    return Promise.resolve(Response.json({ status: "ok" }));
  });
  return urls;
}

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
