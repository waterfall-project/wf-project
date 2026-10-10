// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { randomUUID } from "node:crypto";

import { beforeEach, describe, expect, it, vi } from "vitest";

import { updateEstimateLine } from "@/api/actions/nodes";
import type { ApiClient } from "@/api/client";
import { readOrFail } from "@/api/problem";
import { failureOf } from "@/components/system/failure";
import { fakeClient } from "@/test/fixtures";
import { TEST_SETTINGS, type TestRealm, testRealm } from "@/test/identity-provider";
import { type CookieJar, cookieJar, withTestRedis } from "@/test/session";

import { createIdentityProvider, type IdentityProvider } from "./provider";
import { type FrontSession, openSession, readSession } from "./store";
import { closeRequestSessions, REFRESH_MARGIN, requestBearer, SESSION_COOKIE } from "./tokens";

const state = vi.hoisted(() => ({
  jar: undefined as CookieJar | undefined,
  provider: undefined as IdentityProvider | undefined,
  client: undefined as ApiClient | undefined,
}));

vi.mock("next/headers", () => ({ cookies: () => Promise.resolve(state.jar) }));
vi.mock("./provider", async (original) => ({
  ...(await original<typeof import("./provider")>()),
  identityProvider: () => state.provider,
}));
vi.mock("@/api/server", () => ({ serverClient: () => state.client }));

withTestRedis();

const LINE =
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/estimate-line";
const STRUCTURE = { project_id: "p", revision_id: "r", structure_id: "s" };
const NODE = "n";

let realm: TestRealm;

beforeEach(async () => {
  realm = await testRealm();
  state.provider = createIdentityProvider(TEST_SETTINGS, realm.send);
  state.jar = cookieJar();
});

/** The session an identifier names, which the test expects to live. */
async function living(id: string): Promise<FrontSession> {
  const session = await readSession(id);
  if (session === undefined) {
    throw new Error(`no session ${id}`);
  }
  return session;
}

/** Sign a person in at the realm, open her session, and hold its cookie in the request. */
async function signedIn(subject = randomUUID(), expiresIn = 300_000): Promise<string> {
  const provider = createIdentityProvider(TEST_SETTINGS, realm.send);
  // The verifier and the challenge of RFC 7636, appendix B.
  const challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM";
  const address = provider.signInAddress("state", "nonce", challenge);
  const query = realm.signIn(address.toString(), subject);
  const { lifetime, ...tokens } = await provider.exchange(
    query,
    "state",
    "nonce",
    "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
  );
  const id = randomUUID();
  await openSession(id, { ...tokens, expiresAt: Date.now() + expiresIn }, lifetime);
  state.jar = cookieJar({ [SESSION_COOKIE]: id });
  return id;
}

describe("the token of a request", () => {
  it("is the access token of the session its cookie names, and none without a session that lives", async () => {
    expect(await requestBearer()).toBeUndefined();
    const id = await signedIn();
    const session = await readSession(id);
    expect(await requestBearer()).toBe(session?.accessToken);
    state.jar = cookieJar({ [SESSION_COOKIE]: randomUUID() });
    expect(await requestBearer()).toBeUndefined();
    expect(realm.refreshes).toEqual([]);
  });

  it("is refreshed when it expires within thirty seconds, the new tokens kept", async () => {
    const id = await signedIn(randomUUID(), REFRESH_MARGIN - 1000);
    const before = await living(id);
    const token = await requestBearer();
    const after = await living(id);
    expect(realm.refreshes).toEqual([before.refreshToken]);
    expect(token).toBe(after.accessToken);
    expect(after.accessToken).not.toBe(before.accessToken);
    expect(after.refreshToken).not.toBe(before.refreshToken);
    expect(after.expiresAt - Date.now()).toBeGreaterThan(REFRESH_MARGIN);
    expect(after.subject).toBe(before.subject);
  });

  it("is refreshed once for requests made together, which never present the same refresh token twice", async () => {
    const id = await signedIn(randomUUID(), 0);
    const tokens = await Promise.all(Array.from({ length: 5 }, () => requestBearer()));
    const session = await living(id);
    expect(realm.refreshes).toHaveLength(1);
    expect(tokens).toEqual(Array.from({ length: 5 }, () => session.accessToken));
  });

  it("interrupts a write when the session has expired: it leaves without a token, is not applied, and the screen is told to lead to the sign-in [WF-SEC-0020-A]", async () => {
    const subject = randomUUID();
    const id = await signedIn(subject, 0);
    realm.end(subject);
    const client = fakeClient(
      { [LINE]: { problem: { code: "SESSION_REQUIRED", status: 401 } } },
      {},
      requestBearer,
    );
    state.client = client;

    // A cell of the grid of the estimate entered: its hours.
    const outcome = await updateEstimateLine(STRUCTURE, NODE, { hours: "15", lock_version: 3 });

    expect(outcome).toMatchObject({ kind: "signed_out", problem: { code: "SESSION_REQUIRED" } });
    expect(client.calls.map((call) => [call.route, call.authorization])).toEqual([[LINE, null]]);
    expect(await readSession(id)).toBeUndefined();
  });
  it("leads a page left open to the sign-in at its next read once the session has expired: the read leaves without a token, and its refusal is the session lost [WF-SEC-0020-A]", async () => {
    const subject = randomUUID();
    await signedIn(subject, 0);
    realm.end(subject);
    const client = fakeClient(
      { "GET /projects": { problem: { code: "SESSION_REQUIRED", status: 401 } } },
      {},
      requestBearer,
    );

    const refusal: unknown = await readOrFail("listProjects", () => client.GET("/projects")).then(
      () => undefined,
      (error: unknown) => error,
    );

    expect(refusal).toBeInstanceOf(Error);
    expect(failureOf(refusal as Error)).toEqual({ kind: "signed_out" });
    expect(client.calls.map((call) => call.authorization)).toEqual([null]);
  });
});

describe("closing the sessions of the request", () => {
  it("closes every session of its account, on all its workstations, and forgets its cookie, another account's untouched", async () => {
    const subject = randomUUID();
    const elsewhere = await signedIn(subject);
    const other = await signedIn();
    const here = await signedIn(subject);
    await closeRequestSessions();
    expect(await readSession(here)).toBeUndefined();
    expect(await readSession(elsewhere)).toBeUndefined();
    expect(await readSession(other)).toBeDefined();
    expect(state.jar?.held.has(SESSION_COOKIE)).toBe(false);
    // Without a session, there is nothing to close.
    await expect(closeRequestSessions()).resolves.toBeUndefined();
  });
});
