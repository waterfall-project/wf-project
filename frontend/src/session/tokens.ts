// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The token a request of the front carries to the API (US-0350, WF-ARC-0030): the browser holds
 * no token, only the opaque identifier of its session in the cookie `wf_session`; the server of
 * Next finds the tokens under it in Redis, and refreshes the access token when it expires within
 * thirty seconds — under the lock of the session, so that two requests never present the same
 * refresh token.
 *
 * Without a session that lives — none opened, closed by the back channel, or its refresh refused
 * by the realm —, the request leaves without a token, and the API refuses it for want of a
 * session (401): a read leads to the sign-in page, a write is not applied and its screen says so
 * (`src/api/problem.ts`).
 */
import "server-only";

import { randomUUID } from "node:crypto";
import { setTimeout as sleep } from "node:timers/promises";

import { cookies } from "next/headers";

import { identityProvider } from "./provider";
import {
  type FrontSession,
  forgetAccount,
  forgetSession,
  holdRefresh,
  readSession,
  releaseRefresh,
  renewSession,
} from "./store";

/** The cookie that holds the identifier of the session of the front: nothing else. */
export const SESSION_COOKIE = "wf_session";

/**
 * The cookie that opens a session: its identifier, out of reach of the scripts of the page, sent
 * over HTTPS only, and on a navigation from another site but never with its requests. No
 * expiry: Redis says how long the session lives.
 */
export function sessionCookie(id: string): string {
  return `${SESSION_COOKIE}=${id}; Path=/; HttpOnly; Secure; SameSite=Lax`;
}

/** How long before its expiry an access token is refreshed, in milliseconds. */
export const REFRESH_MARGIN = 30_000;

/** How long the lock of a refresh is held at most, and waited for, in milliseconds. */
const REFRESH_LOCK = 10_000;

/** How often a request waiting for the refresh of another looks again, in milliseconds. */
const REFRESH_WAIT = 50;

/** Whether the access token of a session is good for thirty seconds more. */
function fresh(session: FrontSession): boolean {
  return session.expiresAt - Date.now() > REFRESH_MARGIN;
}

/** Refresh a session under its lock, held by `holder`: the session as it is then, its access token. */
async function renew(id: string, holder: string): Promise<string | undefined> {
  try {
    // Read again under the lock: the refresh of another may have ended just before.
    const session = await readSession(id);
    if (session === undefined || fresh(session)) {
      return session?.accessToken;
    }
    const tokens = await identityProvider().refresh(session.refreshToken);
    if (tokens === undefined) {
      await forgetSession(id);
      return undefined;
    }
    const { lifetime, ...renewed } = tokens;
    await renewSession(id, { ...renewed, subject: session.subject }, lifetime);
    return tokens.accessToken;
  } finally {
    await releaseRefresh(id, holder);
  }
}

/**
 * The access token of a session, refreshed when it expires within thirty seconds; none when the
 * session does not live. A request that finds the refresh under way waits for it, ten seconds at
 * most, then carries the token it has.
 */
export async function bearerOf(id: string): Promise<string | undefined> {
  const holder = randomUUID();
  const deadline = Date.now() + REFRESH_LOCK;
  for (;;) {
    const session = await readSession(id);
    if (session === undefined || fresh(session)) {
      return session?.accessToken;
    }
    if (await holdRefresh(id, holder, REFRESH_LOCK)) {
      return renew(id, holder);
    }
    if (Date.now() >= deadline) {
      return session.accessToken;
    }
    await sleep(REFRESH_WAIT);
  }
}

/** The identifier of the session of the request, as its cookie names it. */
async function requestSessionId(): Promise<string | undefined> {
  return (await cookies()).get(SESSION_COOKIE)?.value;
}

/** The access token of the session of the request; none without a session that lives. */
export async function requestBearer(): Promise<string | undefined> {
  const id = await requestSessionId();
  return id === undefined ? undefined : bearerOf(id);
}

/**
 * Close the sessions of the account of the request on all its workstations, and forget its
 * cookie: the sign-out (WF-SEC-0020), whatever the back channel of Keycloak says after.
 */
export async function closeRequestSessions(): Promise<void> {
  const id = await requestSessionId();
  if (id === undefined) {
    return;
  }
  const session = await readSession(id);
  if (session !== undefined) {
    await forgetAccount(session.subject);
  }
  (await cookies()).delete(SESSION_COOKIE);
}
