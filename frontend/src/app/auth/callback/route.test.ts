// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GET as login } from "@/app/login/route";
import { createIdentityProvider, type IdentityProvider } from "@/session/provider";
import { readSession } from "@/session/store";
import { requestBearer, SESSION_COOKIE } from "@/session/tokens";
import { fakeClient } from "@/test/fixtures";
import { TEST_SETTINGS, type TestRealm, testRealm } from "@/test/identity-provider";
import { type CookieJar, cookieJar, withTestRedis } from "@/test/session";

import { GET as callback } from "./route";

const state = vi.hoisted(() => ({
  provider: undefined as IdentityProvider | undefined,
  jar: undefined as CookieJar | undefined,
}));

vi.mock("@/session/provider", async (original) => ({
  ...(await original<typeof import("@/session/provider")>()),
  identityProvider: () => state.provider,
}));
vi.mock("next/headers", () => ({ cookies: () => Promise.resolve(state.jar) }));

withTestRedis();

let realm: TestRealm;

beforeEach(async () => {
  vi.stubEnv("WATERFALL_AUTH", undefined);
  realm = await testRealm();
  state.provider = createIdentityProvider(TEST_SETTINGS, realm.send);
});

/** Everything the browser receives of a response: its status, its headers, its body. */
async function received(response: Response): Promise<string> {
  return [String(response.status), ...response.headers.entries(), await response.text()].join("\n");
}

/** Sign in from a screen aimed at: the answer of `/login`, then that of the return. */
async function signIn(next: string, subject = "camille") {
  const started = await login(
    new Request(`https://front.test/login?next=${encodeURIComponent(next)}`),
  );
  const address = started.headers.get("Location") ?? "";
  const query = realm.signIn(address, subject);
  const returned = await callback(new Request(`http://front:3000/auth/callback${query}`));
  return { started, returned, query };
}

/** The identifier of the session a response opens, as its cookie holds it. */
function sessionIdOf(response: Response): string {
  const cookie = response.headers.get("Set-Cookie") ?? "";
  return cookie.slice(`${SESSION_COOKIE}=`.length).split(";")[0] ?? "";
}

describe("the return of the sign-in", () => {
  it("comes back to the screen aimed at, its address whole, query included [WF-SEC-0020-A]", async () => {
    const screen = "/projects/p1/revisions/r1/estimate?subproject_id=s1&as_of=2026-06-03#ligne";
    const { returned } = await signIn(screen);
    expect(returned.status).toBe(303);
    expect(returned.headers.get("Location")).toBe(screen);
    expect(returned.headers.get("Cache-Control")).toBe("no-store");
    expect(await readSession(sessionIdOf(returned))).toMatchObject({ subject: "camille" });
  });

  it.each(["https://elsewhere.example/projects", "//elsewhere.example/", "/\\elsewhere.example"])(
    "refuses a return to another site, %j, and leads home [WF-SEC-0020-A]",
    async (next) => {
      const { returned } = await signIn(next);
      expect(returned.headers.get("Location")).toBe("/");
    },
  );

  it("opens no session for a state it does not know, or knows no more, and starts the sign-in again", async () => {
    const { query } = await signIn("/projects");
    const replayed = await callback(new Request(`https://front.test/auth/callback${query}`));
    expect(replayed.status).toBe(303);
    expect(replayed.headers.get("Location")).toBe("/login");
    expect(replayed.headers.get("Set-Cookie")).toBeNull();
    const without = await callback(new Request("https://front.test/auth/callback?code=c"));
    expect(without.headers.get("Location")).toBe("/login");
  });

  it("leaves the browser no token: an opaque identifier in a cookie scripts cannot read, the tokens on the server, carried to the API by the server alone [WF-ARC-0030-A]", async () => {
    const { started, returned } = await signIn("/projects");
    const browser = `${await received(started)}\n${await received(returned)}`;
    expect(realm.issued).toHaveLength(3);
    for (const token of realm.issued) {
      expect(browser).not.toContain(token);
    }
    const cookie = returned.headers.get("Set-Cookie") ?? "";
    expect(cookie.split("; ").slice(1)).toEqual(["Path=/", "HttpOnly", "Secure", "SameSite=Lax"]);
    const id = sessionIdOf(returned);
    expect(id).toMatch(/^[A-Za-z0-9_-]{43}$/);

    // The tokens live in Redis under that identifier, and the server of Next carries them.
    const session = await readSession(id);
    expect(realm.issued).toContain(session?.accessToken);
    expect(realm.issued).toContain(session?.refreshToken);
    state.jar = cookieJar({ [SESSION_COOKIE]: id });
    const api = fakeClient({ "GET /me": "me" }, {}, requestBearer);
    await api.GET("/me");
    expect(api.calls.map((call) => call.authorization)).toEqual([
      `Bearer ${session?.accessToken ?? ""}`,
    ]);
  });

  it("answers nothing on the fake back, which signs nobody in", async () => {
    vi.stubEnv("WATERFALL_AUTH", "mock");
    const response = await callback(new Request("https://front.test/auth/callback?state=s"));
    expect(response.status).toBe(404);
  });
});
