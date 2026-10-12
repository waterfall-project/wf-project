// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GET as login } from "@/app/login/route";
import { createIdentityProvider, type IdentityProvider } from "@/session/provider";
import { armSignOut, openSession, readSession } from "@/session/store";
import { requestBearer, SESSION_COOKIE } from "@/session/tokens";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";
import { TEST_SETTINGS, type TestRealm, testRealm } from "@/test/identity-provider";
import { type CookieJar, cookieJar, withTestRedis } from "@/test/session";

import { GET as callback } from "./route";

const state = vi.hoisted(() => ({
  provider: undefined as IdentityProvider | undefined,
  jar: undefined as CookieJar | undefined,
  api: undefined as FakeAnswers | undefined,
  clients: [] as FakeClient[],
}));

// The API a sign-out of a lost session reaches with the token its silent sign-in obtained.
vi.mock("@/api/server", async (original) => ({
  ...(await original<typeof import("@/api/server")>()),
  tokenClient: (token: string) => {
    const client = fakeClient(state.api ?? {}, {}, () => token);
    state.clients.push(client);
    return client;
  },
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

/**
 * Start a sign-in from a screen aimed at — or a sign-out, in a browser holding the cookie of the
 * session it lost: the answer of `/login`, and its cookie.
 */
async function start(next: string, query = `?next=${encodeURIComponent(next)}`, held = "") {
  const headers: HeadersInit = held === "" ? {} : { Cookie: `${SESSION_COOKIE}=${held}` };
  const started = await login(new Request(`https://front.test/login${query}`, { headers }));
  const address = started.headers.get("Location") ?? "";
  const [pair = ""] = (started.headers.getSetCookie()[0] ?? "").split(";");
  const [name = "", value = ""] = pair.split("=");
  return { started, address, cookie: { [name]: value } };
}

/** Come back from the sign-in page with a query, in a browser that holds these cookies. */
function back(query: string, held: Record<string, string>): Promise<Response> {
  state.jar = cookieJar(held);
  return callback(new Request(`http://front:3000/auth/callback${query}`));
}

/** Sign in from a screen aimed at: the answer of `/login`, then that of the return. */
async function signIn(next: string, subject = "camille") {
  const { started, address, cookie } = await start(next);
  const query = realm.signIn(address, subject);
  const returned = await back(query, cookie);
  return { started, returned, query, cookie };
}

/** The cookie of the session a response gives, if it gives one. */
function sessionCookieOf(response: Response): string | undefined {
  return response.headers
    .getSetCookie()
    .find((cookie) => cookie.startsWith(`${SESSION_COOKIE}=`) && !cookie.includes("Max-Age=0"));
}

/** The identifier of the session a response opens, as its cookie holds it. */
function sessionIdOf(response: Response): string {
  const cookie = sessionCookieOf(response) ?? "";
  return cookie.slice(`${SESSION_COOKIE}=`.length).split(";")[0] ?? "";
}

describe("the return of the sign-in", () => {
  it("comes back to the screen aimed at, its address whole, query included, and forgets the cookie of its sign-in", async () => {
    const screen = "/projects/p1/revisions/r1/estimate?subproject_id=s1&as_of=2026-06-03#ligne";
    const { returned, cookie } = await signIn(screen);
    expect(returned.status).toBe(303);
    expect(returned.headers.get("Location")).toBe(screen);
    expect(returned.headers.get("Cache-Control")).toBe("no-store");
    expect(await readSession(sessionIdOf(returned))).toMatchObject({ subject: "camille" });
    const [name = ""] = Object.keys(cookie);
    expect(returned.headers.getSetCookie()).toContainEqual(
      expect.stringMatching(new RegExp(`^${name}=;.*Max-Age=0`)),
    );
  });

  it.each(["https://elsewhere.example/projects", "//elsewhere.example/", "/\\elsewhere.example"])(
    "refuses a return to another site, %j, and leads home",
    async (next) => {
      const { returned } = await signIn(next);
      expect(returned.headers.get("Location")).toBe("/");
    },
  );

  it("opens no session for a return brought to another browser, without the cookie of its sign-in or with that of another, and leaves it to its own browser", async () => {
    const { address, cookie } = await start("/projects");
    // Someone signs in, stops before the return, and has it opened in another browser.
    const query = realm.signIn(address, "intruder");
    const another = await start("/projects");
    for (const held of [{}, another.cookie]) {
      const response = await back(query, held);
      expect(response.status).toBe(303);
      expect(response.headers.get("Location")).toBe("/login");
      expect(response.headers.getSetCookie()).toEqual([]);
    }
    expect(realm.codes).toEqual([]);
    // The request and its code were left untouched: the browser that asked opens its session.
    const own = await back(query, cookie);
    expect(await readSession(sessionIdOf(own))).toMatchObject({ subject: "intruder" });
  });

  it("opens no session for a state it does not know, or knows no more, and starts the sign-in again", async () => {
    const { query, cookie } = await signIn("/projects");
    const replayed = await back(query, cookie);
    expect(replayed.status).toBe(303);
    expect(replayed.headers.get("Location")).toBe("/login");
    expect(sessionCookieOf(replayed)).toBeUndefined();
    const without = await back("?code=c", cookie);
    expect(without.headers.get("Location")).toBe("/login");
  });

  const refused: [string, (address: string, query: string) => string][] = [
    [
      "an error in the return",
      (address) => {
        const state = new URL(address).searchParams.get("state") ?? "";
        return `?${new URLSearchParams({ error: "access_denied", state }).toString()}`;
      },
    ],
    ["a code the realm refuses", (_, query) => query.replace(/code=[^&]+/, "code=unknown")],
    [
      "an ID token without the nonce of the request",
      (address) => {
        const another = new URL(address);
        another.searchParams.set("nonce", "another");
        return realm.signIn(another.toString(), "camille");
      },
    ],
  ];

  it.each(refused)(
    "leads home without a session, forgetting the cookie of the one before, for %s",
    async (_, returning) => {
      const { address, cookie } = await start("/projects");
      const query = realm.signIn(address, "camille");
      const response = await back(returning(address, query), cookie);
      expect(response.status).toBe(303);
      expect(response.headers.get("Location")).toBe("/");
      expect(sessionCookieOf(response)).toBeUndefined();
      expect(response.headers.getSetCookie()).toContainEqual(
        expect.stringMatching(new RegExp(`^${SESSION_COOKIE}=;.*Max-Age=0`)),
      );
    },
  );

  it("asks nothing of the realm for an error in the return", async () => {
    const { address, cookie } = await start("/projects");
    const state = new URL(address).searchParams.get("state") ?? "";
    await back(`?error=access_denied&state=${state}`, cookie);
    expect(realm.codes).toEqual([]);
  });

  it("leaves the browser no token: an opaque identifier in a cookie scripts cannot read, the tokens on the server, carried to the API by the server alone [WF-ARC-0030-A]", async () => {
    const { started, returned } = await signIn("/projects");
    const browser = `${await received(started)}\n${await received(returned)}`;
    expect(realm.issued).toHaveLength(3);
    for (const token of realm.issued) {
      expect(browser).not.toContain(token);
    }
    const cookie = sessionCookieOf(returned) ?? "";
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

  it("says the sign-in could not be made when the realm cannot be reached, offering it again for the screen aimed at, the cookie of the session held forgotten (#687)", async () => {
    const { address, cookie } = await start("/account?tab=1");
    const query = realm.signIn(address, "camille");
    state.provider = createIdentityProvider(TEST_SETTINGS, () =>
      Promise.reject(new TypeError("fetch failed")),
    );
    const response = await back(query, { ...cookie, [SESSION_COOKIE]: "held" });
    expect(response.status).toBe(303);
    expect(response.headers.get("Location")).toBe(
      `/login/unavailable?next=${encodeURIComponent("/account?tab=1")}`,
    );
    expect(sessionCookieOf(response)).toBeUndefined();
    expect(response.headers.getSetCookie()).toContain(
      `${SESSION_COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`,
    );
  });

  it("answers nothing on the fake back, which signs nobody in", async () => {
    vi.stubEnv("WATERFALL_AUTH", "mock");
    const response = await callback(new Request("https://front.test/auth/callback?state=s"));
    expect(response.status).toBe(404);
  });
});

describe("the return of the sign-out of a session the front lost (#689)", () => {
  beforeEach(() => {
    state.clients = [];
    state.api = { "DELETE /me/sessions": { status: 204 } };
  });

  /** A session of the account the front still keeps on another workstation: its identifier. */
  async function elsewhere(subject: string): Promise<string> {
    const id = crypto.randomUUID();
    const session = {
      accessToken: "a",
      refreshToken: "r",
      expiresAt: Date.now() + 300_000,
      subject,
    };
    await openSession(id, session, 7200);
    return id;
  }

  /** Start the sign-out of a session this browser lost, the ticket armed for its cookie. */
  async function lostSignOut() {
    const lost = crypto.randomUUID();
    return start("", `?sign_out=${await armSignOut(lost)}`, lost);
  }

  it("closes the sessions of the account on all its workstations by the token of its silent sign-in, opens none, and leads to the sign-in [WF-SEC-0020-A]", async () => {
    const subject = crypto.randomUUID();
    const other = await elsewhere(subject);
    const { address, cookie } = await lostSignOut();
    const response = await back(realm.signIn(address, subject), cookie);
    expect(response.status).toBe(303);
    expect(response.headers.get("Location")).toBe("/login");
    expect(sessionCookieOf(response)).toBeUndefined();
    const calls = state.clients.flatMap((client) => client.calls);
    expect(calls.map((call) => call.route)).toEqual(["DELETE /me/sessions"]);
    expect(realm.issued).toContain(calls[0]?.authorization?.replace("Bearer ", ""));
    expect(await readSession(other)).toBeUndefined();
  });

  it("leads to the sign-in when the realm holds no session for the browser: no workstation left to close", async () => {
    const { address, cookie } = await lostSignOut();
    const signIn = new URL(address).searchParams.get("state") ?? "";
    const query = `?${new URLSearchParams({ error: "login_required", state: signIn }).toString()}`;
    const response = await back(query, cookie);
    expect(response.headers.get("Location")).toBe("/login");
    expect(state.clients).toEqual([]);
  });

  it("leads to a sign-in that asks for the identifiers again when the API refuses the token of its silent sign-in as of a session closed already, which the realm outlived: the browser reaches the sign-in page, nothing loops (#855) [WF-SEC-0020-A]", async () => {
    state.api = {
      "DELETE /me/sessions": { problem: example("session_revoked") as Problem & { status: 401 } },
    };
    const subject = crypto.randomUUID();
    const other = await elsewhere(subject);
    const { address, cookie } = await lostSignOut();
    const response = await back(realm.signIn(address, subject), cookie);
    expect(response.status).toBe(303);
    const location = response.headers.get("Location") ?? "";
    expect(location).toBe("/login?next=%2F&reauthenticate=1");
    expect(sessionCookieOf(response)).toBeUndefined();
    expect(await readSession(other)).toBeUndefined();
    // Followed, it is no silent sign-in again, but the page of the realm that asks for them.
    const { address: page } = await start("", location.slice("/login".length));
    expect(new URL(page).searchParams.get("prompt")).toBe("login");
  });

  it("ends at least the session of the browser at the realm when the API does not close them", async () => {
    state.api = {
      "DELETE /me/sessions": { problem: { code: "COMPONENT_UNAVAILABLE", status: 503 } },
    };
    const { address, cookie } = await lostSignOut();
    const response = await back(realm.signIn(address, crypto.randomUUID()), cookie);
    const location = new URL(response.headers.get("Location") ?? "");
    expect(`${location.origin}${location.pathname}`).toBe(
      `${TEST_SETTINGS.realmAddress}/protocol/openid-connect/logout`,
    );
  });
});
