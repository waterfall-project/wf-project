// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { afterEach, describe, expect, it, vi } from "vitest";

import { API_PREFIX, createApiClient } from "./client";

/** A fetch that records the requests it receives, and answers an empty object. */
function recorder(): { fetch: (request: Request) => Promise<Response>; urls: string[] } {
  const urls: string[] = [];
  const record = (request: Request): Promise<Response> => {
    urls.push(request.url);
    return Promise.resolve(Response.json({}));
  };
  return { fetch: record, urls };
}

describe("createApiClient", () => {
  it("calls an operation of the contract under the prefix of the contract", async () => {
    const { fetch, urls } = recorder();
    const client = createApiClient({ address: "http://localhost:4010", fetch });
    await client.GET("/health");
    expect(urls).toEqual([`http://localhost:4010${API_PREFIX}/health`]);
  });

  it("keeps the prefix when the address ends with a slash", async () => {
    const { fetch, urls } = recorder();
    const client = createApiClient({ address: "http://api.example/", fetch });
    await client.GET("/health");
    expect(urls).toEqual([`http://api.example${API_PREFIX}/health`]);
  });

  it("uses the platform's fetch when none is given", () => {
    const client = createApiClient({ address: "http://localhost:4010" });
    expect(typeof client.GET).toBe("function");
  });
});

describe("the module of the client", () => {
  afterEach(() => {
    vi.doMock("server-only", () => ({}));
    vi.resetModules();
  });

  it("refuses to load outside the server of Next", async () => {
    vi.doUnmock("server-only");
    vi.resetModules();
    await expect(import("./client")).rejects.toThrow("Client Component");
  });
});
