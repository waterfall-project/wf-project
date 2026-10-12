// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { randomUUID } from "node:crypto";

import { createClient } from "@redis/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createIdentityProvider } from "@/session/provider";
import { armSignOut, closeStore } from "@/session/store";
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
function login(query = "", headers: HeadersInit = {}): Promise<Response> {
  return GET(new Request(`http://front.example/login${query}`, { headers }));
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

  it("sends the browser to the sign-in page of the realm, by the code flow with PKCE, the screen aimed at kept on the server under the state for fifteen minutes at most, the browser bound to the state", async () => {
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
    expect(query.has("prompt")).toBe(false);
    expect(signIn.value).toMatchObject({ signOut: false });
    // The cookie of the session the browser held is forgotten here, where the sign-out leads (#724).
    expect(response.headers.getSetCookie()).toEqual([
      `wf_sign_in_${query.get("state") ?? ""}=1; Path=/auth/callback; HttpOnly; Secure; SameSite=Lax; Max-Age=900`,
      "__Host-wf_session=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0",
    ]);
  });

  it("signs in silently for the sign-out of a session the front lost, its return to close the sessions of the account, the ticket the sign-out armed taken once, by the browser whose cookie it is bound to only (#689)", async () => {
    const [mine, theirs] = [randomUUID(), randomUUID()];
    const ticket = await armSignOut(mine);
    // Another browser, or one without the cookie — a victim led to the ticket a third party armed
    // for a cookie of its own —, signs in like any other, and leaves the ticket in place.
    for (const headers of [{ Cookie: `__Host-wf_session=${theirs}` }, {}]) {
      const query = new URL(
        (await login(`?sign_out=${ticket}`, headers)).headers.get("Location") ?? "",
      ).searchParams;
      expect(query.has("prompt")).toBe(false);
      expect((await kept(query.get("state") ?? "")).value).toMatchObject({ signOut: false });
    }
    const response = await login(`?sign_out=${ticket}`, { Cookie: `__Host-wf_session=${mine}` });
    const query = new URL(response.headers.get("Location") ?? "").searchParams;
    expect(query.get("prompt")).toBe("none");
    expect((await kept(query.get("state") ?? "")).value).toMatchObject({
      signOut: true,
      target: "/",
    });
    // Spent: the same address again is a sign-in like any other.
    const again = new URL(
      (await login(`?sign_out=${ticket}`, { Cookie: `__Host-wf_session=${mine}` })).headers.get(
        "Location",
      ) ?? "",
    );
    expect(again.searchParams.has("prompt")).toBe(false);
  });

  it("asks the realm for the identifiers again where a session closed leads, the screen aimed at kept: its session may live, and would bring a token of the same sign-in again (#855)", async () => {
    const response = await login(`?next=${encodeURIComponent("/account?tab=1")}&reauthenticate=1`, {
      Cookie: "__Host-wf_session=held",
    });
    const query = new URL(response.headers.get("Location") ?? "").searchParams;
    expect(query.get("prompt")).toBe("login");
    expect((await kept(query.get("state") ?? "")).value).toMatchObject({
      target: "/account?tab=1",
      signOut: false,
    });
  });

  it.each(["1", "unknown-ticket", ""])(
    "takes a sign-out no server action armed — a link of another site — for an ordinary sign-in: no silent sign-in, nothing closed at its return: %j",
    async (ticket) => {
      const response = await login(`?sign_out=${ticket}`, { Cookie: "__Host-wf_session=held" });
      const query = new URL(response.headers.get("Location") ?? "").searchParams;
      expect(query.has("prompt")).toBe(false);
      expect((await kept(query.get("state") ?? "")).value).toMatchObject({ signOut: false });
    },
  );

  it("says the sign-in could not be made when Redis is out of reach, rather than fail bare, and forgets the cookie of the session, which the page would read Redis for (#687)", async () => {
    // A Redis nobody serves: the connection is refused.
    await closeStore();
    vi.stubEnv("WATERFALL_REDIS_URL", "redis://127.0.0.1:1/0");
    try {
      const response = await login(`?next=${encodeURIComponent("/account?tab=1")}`, {
        Cookie: "__Host-wf_session=held",
      });
      expect(response.status).toBe(307);
      expect(response.headers.get("Location")).toBe(
        `/login/unavailable?next=${encodeURIComponent("/account?tab=1")}`,
      );
      expect(response.headers.getSetCookie()).toEqual([
        "__Host-wf_session=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0",
      ]);
    } finally {
      await closeStore();
    }
  });

  it("offers again, when Redis is out of reach, a sign-in that asks for the identifiers, as the one asked did (#855)", async () => {
    await closeStore();
    vi.stubEnv("WATERFALL_REDIS_URL", "redis://127.0.0.1:1/0");
    try {
      const response = await login(
        `?next=${encodeURIComponent("/account?tab=1")}&reauthenticate=1`,
      );
      expect(response.headers.get("Location")).toBe(
        `/login/unavailable?next=${encodeURIComponent("/account?tab=1")}&reauthenticate=1`,
      );
    } finally {
      await closeStore();
    }
  });

  it("keeps the home page in place of another site", async () => {
    const response = await login(`?next=${encodeURIComponent("https://elsewhere.example/a?b=c")}`);
    const state = new URL(response.headers.get("Location") ?? "").searchParams.get("state");
    expect((await kept(state ?? "")).value).toMatchObject({ target: "/" });
  });
});
