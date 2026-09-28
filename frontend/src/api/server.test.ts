// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { afterEach, describe, expect, it, vi } from "vitest";

import { serverClient } from "./server";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("serverClient", () => {
  it("makes a client whether the address is configured or not", () => {
    expect(typeof serverClient().GET).toBe("function");
    vi.stubEnv("WATERFALL_API_ADDRESS", "http://mock:4010");
    expect(typeof serverClient().GET).toBe("function");
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
