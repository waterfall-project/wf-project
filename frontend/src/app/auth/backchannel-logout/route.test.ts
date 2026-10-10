// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { randomUUID } from "node:crypto";

import { beforeEach, describe, expect, it, vi } from "vitest";

import { createIdentityProvider, type IdentityProvider } from "@/session/provider";
import { openSession, readSession } from "@/session/store";
import { TEST_SETTINGS, type TestRealm, testRealm } from "@/test/identity-provider";
import { withTestRedis } from "@/test/session";

import { POST } from "./route";

const state = vi.hoisted(() => ({ provider: undefined as IdentityProvider | undefined }));

vi.mock("@/session/provider", async (original) => ({
  ...(await original<typeof import("@/session/provider")>()),
  identityProvider: () => state.provider,
}));

withTestRedis();

let realm: TestRealm;

beforeEach(async () => {
  vi.stubEnv("WATERFALL_AUTH", undefined);
  realm = await testRealm();
  state.provider = createIdentityProvider(TEST_SETTINGS, realm.send);
});

/** Open a session of an account on a workstation: its identifier. */
async function workstation(subject: string): Promise<string> {
  const id = randomUUID();
  const session = { accessToken: "a", refreshToken: "r", expiresAt: Date.now() + 300_000, subject };
  await openSession(id, session, 7200);
  return id;
}

/** Post a logout token as Keycloak does: a form of one field. */
function logout(token: string | undefined): Promise<Response> {
  const body = new URLSearchParams(token === undefined ? {} : { logout_token: token });
  return POST(new Request("https://front.test/auth/backchannel-logout", { method: "POST", body }));
}

describe("the back-channel logout", () => {
  it("closes every session of the account the realm names, on each of its workstations, and no other [WF-SEC-0020-A]", async () => {
    const subject = randomUUID();
    const [first, second, other] = [
      await workstation(subject),
      await workstation(subject),
      await workstation(randomUUID()),
    ];
    const response = await logout(await realm.logoutToken(subject));
    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(await readSession(first)).toBeUndefined();
    expect(await readSession(second)).toBeUndefined();
    expect(await readSession(other)).toBeDefined();
  });

  const refusals: [string, { claims?: Record<string, unknown>; foreign?: boolean }][] = [
    ["signed by another key", { foreign: true }],
    ["for another client", { claims: { aud: "waterfall-api" } }],
    ["without its event", { claims: { events: {} } }],
    ["with a nonce", { claims: { nonce: "n" } }],
  ];

  it.each(refusals)("refuses a token %s, and closes nothing", async (_, { claims, foreign }) => {
    const subject = randomUUID();
    const id = await workstation(subject);
    const response = await logout(await realm.logoutToken(subject, claims, foreign));
    expect(response.status).toBe(400);
    expect(await readSession(id)).toBeDefined();
  });

  it("refuses a request without a token, or not even a form", async () => {
    expect((await logout(undefined)).status).toBe(400);
    const text = new Request("https://front.test/auth/backchannel-logout", {
      method: "POST",
      body: "{}",
      headers: { "Content-Type": "application/json" },
    });
    expect((await POST(text)).status).toBe(400);
  });

  it("answers nothing on the fake back", async () => {
    vi.stubEnv("WATERFALL_AUTH", "mock");
    expect((await logout("t")).status).toBe(404);
  });
});
