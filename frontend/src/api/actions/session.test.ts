// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { randomUUID } from "node:crypto";

import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
import { createIdentityProvider } from "@/session/provider";
import { FRONT_CLIENT } from "@/session/settings";
import { openSession, readSession, takeSignOut } from "@/session/store";
import { requestBearer, SESSION_COOKIE, SessionLost } from "@/session/tokens";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";
import { TEST_SETTINGS } from "@/test/identity-provider";
import { type CookieJar, cookieJar, withTestRedis } from "@/test/session";

import { signOut } from "./session";

const server = vi.hoisted(() => ({
  client: undefined as ApiClient | undefined,
  mock: false,
  jar: undefined as CookieJar | undefined,
}));

vi.mock("@/api/server", () => ({
  serverClient: () => server.client,
  isMockAuthentication: () => server.mock,
}));
vi.mock("next/headers", () => ({ cookies: () => Promise.resolve(server.jar) }));
vi.mock("@/session/provider", async (original) => ({
  ...(await original<typeof import("@/session/provider")>()),
  identityProvider: () => createIdentityProvider(TEST_SETTINGS),
}));

withTestRedis();

/** Open a session of an account on a workstation: its identifier. */
async function workstation(subject: string): Promise<string> {
  const id = randomUUID();
  const session = { accessToken: "a", refreshToken: "r", expiresAt: Date.now() + 300_000, subject };
  await openSession(id, session, 7200);
  return id;
}

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers): FakeClient {
  const client = fakeClient(answers);
  server.client = client;
  return client;
}

beforeEach(() => {
  server.client = undefined;
  server.mock = false;
  server.jar = cookieJar();
});

// The sign-out done, the browser loads the sign-in.
const TO_SIGN_IN = { kind: "left", address: "/login" } as const;

describe("the server action of the session", () => {
  it("closes the sessions of the account, and holds the user signed out when there was none left", async () => {
    const client = serve({ "DELETE /me/sessions": { status: 204 } });
    expect(await signOut()).toEqual(TO_SIGN_IN);
    expect(client.calls.map((call) => call.route)).toEqual(["DELETE /me/sessions"]);

    serve({ "DELETE /me/sessions": { problem: { code: "SESSION_EXPIRED", status: 401 } } });
    expect(await signOut()).toEqual(TO_SIGN_IN);
  });

  it("holds a deactivated account signed out too: its sessions are closed already", async () => {
    serve({ "DELETE /me/sessions": { problem: { code: "ACCOUNT_DEACTIVATED", status: 401 } } });
    expect(await signOut()).toEqual(TO_SIGN_IN);
  });

  it("ends at the realm the session of an account Waterfall does not admit, which the API does not close (#664)", async () => {
    const subject = randomUUID();
    const here = await workstation(subject);
    server.jar = cookieJar({ [SESSION_COOKIE]: here });
    serve({ "DELETE /me/sessions": { problem: { code: "ACCOUNT_NOT_ADMITTED", status: 401 } } });
    const outcome = await signOut();
    expect(outcome.kind).toBe("left");
    const address = new URL(outcome.kind === "left" ? outcome.address : "");
    expect(`${address.origin}${address.pathname}`).toBe(
      `${TEST_SETTINGS.realmAddress}/protocol/openid-connect/logout`,
    );
    expect(Object.fromEntries(address.searchParams)).toEqual({
      client_id: FRONT_CLIENT,
      post_logout_redirect_uri: "https://front.test/login",
    });
    expect(await readSession(here)).toBeUndefined();
  });

  it("says the API out of reach rather than a session closed, and keeps the session", async () => {
    const id = await workstation(randomUUID());
    server.jar = cookieJar({ [SESSION_COOKIE]: id });
    server.client = createApiClient({
      address: "http://unreachable.invalid",
      fetch: () => Promise.reject(new TypeError("fetch failed")),
    });
    expect(await signOut()).toEqual({ kind: "unreachable" });
    expect(await readSession(id)).toBeDefined();
    expect(server.jar.held.has(SESSION_COOKIE)).toBe(true);
  });

  it.each([
    ["once the API has closed them", { status: 204 }],
    ["when the API finds none left", { problem: { code: "SESSION_EXPIRED", status: 401 } }],
  ] as const)(
    "forgets every session the front keeps of the account, %s, and leaves the cookie to the sign-in, lest Next render the page anew without a session (#724) [WF-SEC-0020-A]",
    async (_, answer) => {
      const subject = randomUUID();
      const [elsewhere, here] = [await workstation(subject), await workstation(subject)];
      server.jar = cookieJar({ [SESSION_COOKIE]: here });
      serve({ "DELETE /me/sessions": answer });
      expect(await signOut()).toEqual(TO_SIGN_IN);
      expect(await readSession(here)).toBeUndefined();
      expect(await readSession(elsewhere)).toBeUndefined();
      expect(server.jar.held.get(SESSION_COOKIE)).toBe(here);
    },
  );

  it("sends the browser to the silent sign-in that closes every workstation when the session of the front is lost, the request not leaving (#689) [WF-SEC-0020-A]", async () => {
    const lost = randomUUID();
    server.jar = cookieJar({ [SESSION_COOKIE]: lost });
    const sent: Request[] = [];
    server.client = createApiClient({
      address: "http://api.test",
      bearer: requestBearer,
      fetch: (request) => {
        sent.push(request);
        return Promise.resolve(new Response(null, { status: 204 }));
      },
    });

    const left = await signOut();
    expect(left.kind).toBe("left");
    const address = new URL(left.kind === "left" ? left.address : "", "https://front.test");
    expect(address.pathname).toBe("/login");
    // The ticket only this action arms, bound to the cookie of the request, which the sign-in
    // takes once, and only for that cookie: one a third party arms for a cookie of its own signs
    // no victim out.
    const ticket = address.searchParams.get("sign_out") ?? "";
    expect(ticket).toMatch(/^[A-Za-z0-9_-]{43}$/);
    expect(await takeSignOut(ticket, randomUUID())).toBe(false);
    expect(await takeSignOut(ticket, lost)).toBe(true);
    expect(await takeSignOut(ticket, lost)).toBe(false);
    expect(sent).toEqual([]);
    expect(server.jar.held.get(SESSION_COOKIE)).toBe(lost);
  });

  it("leads to the sign-in, nothing armed, when a request without the cookie finds its session lost: no browser to bind a ticket to", async () => {
    server.client = createApiClient({
      address: "http://api.test",
      bearer: () => Promise.reject(new SessionLost()),
      fetch: () => Promise.resolve(new Response(null, { status: 204 })),
    });
    expect(await signOut()).toEqual(TO_SIGN_IN);
  });

  it("touches no session of the front on the fake back, which grants its own", async () => {
    server.mock = true;
    server.jar = undefined;
    serve({ "DELETE /me/sessions": { status: 204 } });
    expect(await signOut()).toEqual(TO_SIGN_IN);
  });
});
