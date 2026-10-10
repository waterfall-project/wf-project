// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { randomUUID } from "node:crypto";

import { beforeEach, describe, expect, it, vi } from "vitest";

import { type ApiClient, createApiClient } from "@/api/client";
import { openSession, readSession } from "@/session/store";
import { SESSION_COOKIE } from "@/session/tokens";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";
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

describe("the server action of the session", () => {
  it("closes the sessions of the account, and holds the user signed out when there was none left", async () => {
    const client = serve({ "DELETE /me/sessions": { status: 204 } });
    expect(await signOut()).toEqual({ kind: "done", data: null });
    expect(client.calls.map((call) => call.route)).toEqual(["DELETE /me/sessions"]);

    serve({ "DELETE /me/sessions": { problem: { code: "SESSION_EXPIRED", status: 401 } } });
    expect(await signOut()).toEqual({ kind: "done", data: null });
  });

  it("holds a deactivated account signed out too: its sessions are closed already", async () => {
    serve({ "DELETE /me/sessions": { problem: { code: "ACCOUNT_DEACTIVATED", status: 401 } } });
    expect(await signOut()).toEqual({ kind: "done", data: null });
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
    "forgets every session the front keeps of the account, and the cookie of this one, %s [WF-SEC-0020-A]",
    async (_, answer) => {
      const subject = randomUUID();
      const [elsewhere, here] = [await workstation(subject), await workstation(subject)];
      server.jar = cookieJar({ [SESSION_COOKIE]: here });
      serve({ "DELETE /me/sessions": answer });
      expect(await signOut()).toEqual({ kind: "done", data: null });
      expect(await readSession(here)).toBeUndefined();
      expect(await readSession(elsewhere)).toBeUndefined();
      expect(server.jar.held.has(SESSION_COOKIE)).toBe(false);
    },
  );

  it("touches no session of the front on the fake back, which grants its own", async () => {
    server.mock = true;
    server.jar = undefined;
    serve({ "DELETE /me/sessions": { status: 204 } });
    expect(await signOut()).toEqual({ kind: "done", data: null });
  });
});
