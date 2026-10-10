// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { createClient } from "@redis/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createIdentityProvider } from "@/session/provider";
import { FRONT_CLIENT } from "@/session/settings";
import { TEST_SETTINGS } from "@/test/identity-provider";
import { withTestRedis } from "@/test/session";

import { GET } from "./route";

vi.mock("@/session/provider", async (original) => ({
  ...(await original<typeof import("@/session/provider")>()),
  identityProvider: () => createIdentityProvider(TEST_SETTINGS),
}));

withTestRedis();

/** Ask for the sign-in route, with the query a refusal for want of a session writes. */
function login(query = ""): Promise<Response> {
  return GET(new Request(`http://front.example/login${query}`));
}

/** What Redis keeps of a sign-in under way, and for how long. */
async function kept(state: string): Promise<{ value: unknown; ttl: number }> {
  const client = await createClient({ url: process.env.WATERFALL_TEST_REDIS_URL ?? "" }).connect();
  try {
    const key = `wf:sign-in:${state}`;
    return { value: JSON.parse((await client.get(key)) ?? "null"), ttl: await client.ttl(key) };
  } finally {
    await client.close();
  }
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("the sign-in route on the fake back", () => {
  beforeEach(() => {
    vi.stubEnv("WATERFALL_AUTH", "mock");
  });

  it("leads to the screen the 401 was aimed at", async () => {
    const response = await login(`?next=${encodeURIComponent("/projects/p1/lifecycle?tab=2")}`);
    expect(response.status).toBe(307);
    expect(response.headers.get("Location")).toBe("/projects/p1/lifecycle?tab=2");
  });

  it.each(["", "?next=https://elsewhere.example/", "?next=//elsewhere.example/"])(
    "leads to the home page when the query names no screen of this front: %j",
    async (query) => {
      expect((await login(query)).headers.get("Location")).toBe("/");
    },
  );
});

describe("the sign-in route on the identity provider", () => {
  beforeEach(() => {
    vi.stubEnv("WATERFALL_AUTH", undefined);
  });

  it("sends the browser to the sign-in page of the realm, by the code flow with PKCE, the screen aimed at kept on the server under the state for fifteen minutes at most [WF-SEC-0020-A]", async () => {
    const screen = "/projects/p1/revisions/r1/estimate?subproject_id=s1&as_of=2026-06-03";
    const response = await login(`?next=${encodeURIComponent(screen)}`);
    expect(response.status).toBe(307);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    const address = new URL(response.headers.get("Location") ?? "");
    expect(`${address.origin}${address.pathname}`).toBe(
      `${TEST_SETTINGS.realmAddress}/protocol/openid-connect/auth`,
    );
    const query = address.searchParams;
    expect(Object.fromEntries(query)).toMatchObject({
      client_id: FRONT_CLIENT,
      response_type: "code",
      scope: "openid",
      redirect_uri: TEST_SETTINGS.callback,
      code_challenge_method: "S256",
    });
    // The screen aimed at never travels to the realm: it is kept here, bound to the state.
    expect(address.toString()).not.toContain("subproject_id");
    const signIn = await kept(query.get("state") ?? "");
    expect(signIn.value).toMatchObject({ target: screen, nonce: query.get("nonce") });
    expect(signIn.ttl).toBeGreaterThan(0);
    expect(signIn.ttl).toBeLessThanOrEqual(15 * 60);
  });

  it("keeps the home page in place of another site [WF-SEC-0020-A]", async () => {
    const response = await login(`?next=${encodeURIComponent("https://elsewhere.example/a?b=c")}`);
    const state = new URL(response.headers.get("Location") ?? "").searchParams.get("state");
    expect((await kept(state ?? "")).value).toMatchObject({ target: "/" });
  });
});
