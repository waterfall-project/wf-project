// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { randomUUID } from "node:crypto";
import { setTimeout as sleep } from "node:timers/promises";

import { beforeEach, describe, expect, it, vi } from "vitest";

import { updateEstimateLine } from "@/api/actions/nodes";
import type { ApiClient } from "@/api/client";
import { readOrFail } from "@/api/problem";
import { SESSION_LOST_DIGEST, SESSION_REQUIRED_DIGEST } from "@/components/system/failure";
import { fakeClient } from "@/test/fixtures";
import { TEST_SETTINGS, type TestRealm, testRealm } from "@/test/identity-provider";
import { type CookieJar, cookieJar, withTestRedis } from "@/test/session";

import { createIdentityProvider, type IdentityProvider, type Send } from "./provider";
import { type FrontSession, openSession, readSession } from "./store";
import {
  bearerOf,
  closeRequestSessions,
  REFRESH_MARGIN,
  requestBearer,
  SESSION_COOKIE,
} from "./tokens";

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

/** The realm, answering a refresh it took only once released, or once its time is up. */
function late(send: Send, released: Promise<unknown>): Send {
  return async (url, init) => {
    const answer = await send(url, init);
    await new Promise((resolve, reject) => {
      void released.then(resolve);
      init.signal?.addEventListener("abort", () => {
        reject(init.signal?.reason as Error);
      });
    });
    return answer;
  };
}

/** The realm out of reach for its tokens: the request to its token endpoint rejected. */
function down(send: Send): Send {
  return (url, init) =>
    url.endsWith("/token") ? Promise.reject(new TypeError("fetch failed")) : send(url, init);
}

/** What a read of a page throws, or nothing when it reads. */
async function failureOfRead(client: ApiClient): Promise<unknown> {
  return readOrFail("listProjects", () => client.GET("/projects")).then(
    () => undefined,
    (error: unknown) => error,
  );
}

const SESSION_REQUIRED = { problem: { code: "SESSION_REQUIRED", status: 401 } } as const;

/** Sign a person in at the realm, open her session, and hold its cookie in the request. */
async function signedIn(subject = randomUUID(), expiresIn = 300_000): Promise<string> {
  const provider = createIdentityProvider(TEST_SETTINGS, realm.send);
  // The verifier and the challenge of RFC 7636, appendix B.
  const challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM";
  const address = provider.signInAddress("state", "nonce", challenge);
  const query = realm.signIn(address.toString(), subject);
  const verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk";
  const opened = await provider.exchange(query, "state", "nonce", verifier);
  if (opened === undefined) {
    throw new Error("the realm refused the sign-in");
  }
  const { lifetime, ...tokens } = opened;
  const id = randomUUID();
  await openSession(id, { ...tokens, expiresAt: Date.now() + expiresIn }, lifetime);
  state.jar = cookieJar({ [SESSION_COOKIE]: id });
  return id;
}

describe("the token of a request", () => {
  it("is the access token of the session its cookie names, none without the cookie, and the session lost once the session lives no more", async () => {
    expect(await requestBearer()).toBeUndefined();
    const id = await signedIn();
    const session = await readSession(id);
    expect(await requestBearer()).toBe(session?.accessToken);
    state.jar = cookieJar({ [SESSION_COOKIE]: randomUUID() });
    await expect(requestBearer()).rejects.toMatchObject({ digest: SESSION_LOST_DIGEST });
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

  it("never presents a refresh token twice when the realm answers after its time: the refresh ends before its lock, and the session is lost", async () => {
    const id = await signedIn(randomUUID(), 0);
    let release: (value?: unknown) => void = () => undefined;
    const released = new Promise((resolve) => {
      release = resolve;
    });
    state.provider = createIdentityProvider(TEST_SETTINGS, late(realm.send, released), 50);
    const timing = { lock: 200, wait: 10 };
    const first = bearerOf(id, timing);
    await sleep(timing.lock + 50);
    const second = bearerOf(id, timing);
    const tokens = await Promise.all([first, second]);
    release();
    expect(tokens).toEqual([undefined, undefined]);
    expect(realm.refreshes).toHaveLength(1);
    expect(await readSession(id)).toBeUndefined();
  });

  it("serves the access token while it lives when the realm cannot be reached, and fails once it has expired", async () => {
    state.provider = createIdentityProvider(TEST_SETTINGS, down(realm.send));
    const id = await signedIn(randomUUID(), 20_000);
    expect(await requestBearer()).toBe((await living(id)).accessToken);
    const expired = await signedIn(randomUUID(), -1000);
    await expect(requestBearer()).rejects.toThrow("fetch failed");
    expect(await readSession(expired)).toBeDefined();
  });

  it("interrupts a write when the session has expired: it does not leave, is not applied, and the screen is told to lead to the sign-in [WF-SEC-0020-A]", async () => {
    const subject = randomUUID();
    const id = await signedIn(subject, 0);
    realm.end(subject);
    const client = fakeClient({ [LINE]: SESSION_REQUIRED }, {}, requestBearer);
    state.client = client;

    // A cell of the grid of the estimate entered: its hours.
    const outcome = await updateEstimateLine(STRUCTURE, NODE, { hours: "15", lock_version: 3 });

    // An outcome the screen says, and never a failure: the screen of failure would lead away at once.
    expect(outcome).toMatchObject({ kind: "signed_out", problem: { code: "SESSION_REQUIRED" } });
    expect(client.calls).toEqual([]);
    expect(await readSession(id)).toBeUndefined();
  });

  it("leads a page to the sign-in at once when its session has expired: the read does not leave, and fails as the session lost [WF-SEC-0020-A]", async () => {
    const subject = randomUUID();
    await signedIn(subject, 0);
    realm.end(subject);
    const client = fakeClient({ "GET /projects": SESSION_REQUIRED }, {}, requestBearer);
    expect(await failureOfRead(client)).toMatchObject({ digest: SESSION_LOST_DIGEST });
    expect(client.calls).toEqual([]);
  });

  it("leaves a page on its screen when the API refuses the token of a session that lives: the read fails as refused, and leads nowhere by itself", async () => {
    const id = await signedIn();
    const client = fakeClient({ "GET /projects": SESSION_REQUIRED }, {}, requestBearer);
    expect(await failureOfRead(client)).toMatchObject({ digest: SESSION_REQUIRED_DIGEST });
    const { accessToken } = await living(id);
    expect(client.calls.map((call) => call.authorization)).toEqual([`Bearer ${accessToken}`]);
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
