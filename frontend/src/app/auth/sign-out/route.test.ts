// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { afterEach, describe, expect, it, vi } from "vitest";

import { createIdentityProvider } from "@/session/provider";
import { FRONT_CLIENT } from "@/session/settings";
import { TEST_SETTINGS } from "@/test/identity-provider";

import { GET } from "./route";

vi.mock("@/session/provider", async (original) => ({
  ...(await original<typeof import("@/session/provider")>()),
  identityProvider: () => createIdentityProvider(TEST_SETTINGS),
}));

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("the way out of an account Waterfall does not admit (#664)", () => {
  it("sends the browser to the end of its session of the realm, which leads back to the sign-in", () => {
    vi.stubEnv("WATERFALL_AUTH", undefined);
    const response = GET();
    expect(response.status).toBe(307);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    const address = new URL(response.headers.get("Location") ?? "");
    expect(`${address.origin}${address.pathname}`).toBe(
      `${TEST_SETTINGS.realmAddress}/protocol/openid-connect/logout`,
    );
    expect(Object.fromEntries(address.searchParams)).toEqual({
      client_id: FRONT_CLIENT,
      post_logout_redirect_uri: "https://front.test/login",
    });
  });

  it("leads to the sign-in on the fake back, which signs nobody in", () => {
    vi.stubEnv("WATERFALL_AUTH", "mock");
    expect(GET().headers.get("Location")).toBe("/login");
  });
});
