// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { randomUUID } from "node:crypto";

import { createClient } from "@redis/client";
import { describe, expect, it, vi } from "vitest";

import { withTestRedis } from "@/test/session";

import {
  closeStore,
  type FrontSession,
  forgetAccount,
  holdRefresh,
  openSession,
  readSession,
  releaseRefresh,
  renewSession,
  rememberSignIn,
  SIGN_IN_LIFETIME,
  takeSignIn,
} from "./store";

withTestRedis();

/** The time to live Redis gives a key, in seconds. */
async function ttl(key: string): Promise<number> {
  const client = await createClient({ url: process.env.WATERFALL_TEST_REDIS_URL ?? "" }).connect();
  try {
    return await client.ttl(key);
  } finally {
    await client.close();
  }
}

/** A session of an account, its access token good for five minutes. */
function sessionOf(subject: string): FrontSession {
  const id = randomUUID();
  return {
    accessToken: `a-${id}`,
    refreshToken: `r-${id}`,
    expiresAt: Date.now() + 300_000,
    subject,
  };
}

describe("the store of the sessions of the front", () => {
  it("keeps a sign-in under way fifteen minutes at most, and gives it once", async () => {
    const state = randomUUID();
    const signIn = { verifier: "v", nonce: "n", target: "/projects?sort_by=code" };
    await rememberSignIn(state, signIn);
    const left = await ttl(`wf:sign-in:${state}`);
    expect(left).toBeGreaterThan(SIGN_IN_LIFETIME - 5);
    expect(left).toBeLessThanOrEqual(15 * 60);
    expect(await takeSignIn(state)).toEqual(signIn);
    expect(await takeSignIn(state)).toBeUndefined();
  });

  it("keeps a session as long as Keycloak does, and closes every session of an account, not another's", async () => {
    const [first, second, other] = [randomUUID(), randomUUID(), randomUUID()];
    const subject = randomUUID();
    const session = sessionOf(subject);
    await openSession(first, session, 7200);
    await openSession(second, sessionOf(subject), 600);
    await openSession(other, sessionOf(randomUUID()), 600);
    expect(await readSession(first)).toEqual(session);
    expect(await ttl(`wf:session:${first}`)).toBeGreaterThan(7190);
    // The index of the account lives as long as the longest of its sessions.
    expect(await ttl(`wf:account:${subject}`)).toBeGreaterThan(7190);

    await forgetAccount(subject);
    expect(await readSession(first)).toBeUndefined();
    expect(await readSession(second)).toBeUndefined();
    expect(await readSession(other)).toBeDefined();
  });

  it("renews a session that lives, and never brings back one closed meanwhile", async () => {
    const [living, closed] = [randomUUID(), randomUUID()];
    const subject = randomUUID();
    await openSession(living, sessionOf(subject), 60);
    const renewed = sessionOf(subject);
    await renewSession(living, renewed, 7200);
    expect(await readSession(living)).toEqual(renewed);
    expect(await ttl(`wf:session:${living}`)).toBeGreaterThan(7190);
    expect(await ttl(`wf:account:${subject}`)).toBeGreaterThan(7190);

    await renewSession(closed, sessionOf(subject), 7200);
    expect(await readSession(closed)).toBeUndefined();
  });

  it("lends the lock of a refresh to one holder at a time, given back by that holder only", async () => {
    const id = randomUUID();
    expect(await holdRefresh(id, "first", 10_000)).toBe(true);
    expect(await holdRefresh(id, "second", 10_000)).toBe(false);
    await releaseRefresh(id, "second");
    expect(await holdRefresh(id, "second", 10_000)).toBe(false);
    await releaseRefresh(id, "first");
    expect(await holdRefresh(id, "second", 10_000)).toBe(true);
  });

  it("fails at once while Redis is out of reach, rather than keep the request waiting, and connects once it is back", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const address = process.env.WATERFALL_REDIS_URL;
    await closeStore();
    // A port nobody listens on.
    process.env.WATERFALL_REDIS_URL = "redis://127.0.0.1:1/0";
    const started = Date.now();
    await expect(readSession(randomUUID())).rejects.toThrow();
    expect(Date.now() - started).toBeLessThan(3000);
    expect(error).toHaveBeenCalledWith(
      "The sessions of the front cannot reach Redis",
      expect.anything(),
    );
    process.env.WATERFALL_REDIS_URL = address;
    expect(await readSession(randomUUID())).toBeUndefined();
    error.mockRestore();
  });
});
