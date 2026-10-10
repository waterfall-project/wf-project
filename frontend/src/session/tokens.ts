// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The token a request of the front carries to the API (US-0350, WF-ARC-0030): the browser holds
 * no token, only the opaque identifier of its session in the cookie `wf_session`; the server of
 * Next finds the tokens under it in Redis, and refreshes the access token when it expires within
 * thirty seconds — under the lock of the session, so that two requests never present the same
 * refresh token.
 *
 * When the session its cookie names lives no more — closed by the back channel, its refresh
 * refused by the realm, or over —, the request does not leave: it fails with `SessionLost`. A read
 * of a page leads to the sign-in page at once, without a click — the screen of failure does it —;
 * a write is not applied, and its screen says so before it leads there (`decode`,
 * `src/api/problem.ts`). A request without the cookie leaves without a token, and the API refuses
 * it (401) unless the operation is public: its screen offers the sign-in page, and goes nowhere by
 * itself — a sign-in the realm refused comes back without the cookie, and would loop.
 *
 * The cookies of the browser are made here too: the identifier of its session, and the cookie
 * that binds a sign-in under way to the browser that asked for it.
 */
import "server-only";

import { randomUUID } from "node:crypto";
import { setTimeout as sleep } from "node:timers/promises";

import { cookies } from "next/headers";

import { SESSION_LOST_DIGEST } from "@/components/system/failure";

import { identityProvider, REFRESH_TIMEOUT, type Tokens } from "./provider";
import { CALLBACK_PATH } from "./settings";
import {
  type FrontSession,
  forgetAccount,
  forgetSession,
  holdRefresh,
  readSession,
  releaseRefresh,
  renewSession,
  SIGN_IN_LIFETIME,
} from "./store";

/** The cookie that holds the identifier of the session of the front: nothing else. */
export const SESSION_COOKIE = "wf_session";

const SESSION_ATTRIBUTES = "Path=/; HttpOnly; Secure; SameSite=Lax";

/**
 * The cookie that opens a session: its identifier, out of reach of the scripts of the page, sent
 * over HTTPS only, and on a navigation from another site but never with its requests. No
 * expiry: Redis says how long the session lives.
 */
export function sessionCookie(id: string): string {
  return `${SESSION_COOKIE}=${id}; ${SESSION_ATTRIBUTES}`;
}

/** The cookie that forgets the identifier of a session: a sign-in refused leaves none behind. */
export function forgottenSessionCookie(): string {
  return `${SESSION_COOKIE}=; ${SESSION_ATTRIBUTES}; Max-Age=0`;
}

/**
 * The cookie that binds a sign-in under way to the browser that asked for it, one per state, so
 * that two tabs may sign in together: only the browser that went to `/login` may open the session
 * of its return — a return brought to another browser opens none (RFC 9700, §4.7). It is sent to
 * the return of the sign-in only, and lives as long as the sign-in may take.
 */
export function signInCookieName(state: string): string {
  return `wf_sign_in_${state}`;
}

const SIGN_IN_ATTRIBUTES = `Path=${CALLBACK_PATH}; HttpOnly; Secure; SameSite=Lax`;

/** The cookie `/login` gives the browser for a sign-in under way. */
export function signInCookie(state: string): string {
  return `${signInCookieName(state)}=1; ${SIGN_IN_ATTRIBUTES}; Max-Age=${String(SIGN_IN_LIFETIME)}`;
}

/** The cookie the return of a sign-in gives back, to forget the one `/login` gave. */
export function spentSignInCookie(state: string): string {
  return `${signInCookieName(state)}=; ${SIGN_IN_ATTRIBUTES}; Max-Age=0`;
}

/** Whether the request holds the cookie of the sign-in of a state: it went to `/login` for it. */
export async function holdsSignIn(state: string): Promise<boolean> {
  return (await cookies()).get(signInCookieName(state)) !== undefined;
}

/**
 * The session the cookie of the request names lives no more — closed by the back channel, its
 * refresh refused, or over —, and the request does not leave for the API. Its digest, the one
 * thing of it Next forwards, has the screen of failure lead to the sign-in page at once: it cannot
 * loop, since the session a sign-in opens lives, and one it refuses forgets the cookie. A token
 * that lives and that the API refuses is another failure, `SignedOut` (`src/api/problem.ts`),
 * whose screen leads to the sign-in page by a link only.
 */
export class SessionLost extends Error {
  readonly digest = SESSION_LOST_DIGEST;

  /** The session of the request lost: nothing more to say of it. */
  constructor() {
    super("the request holds no session that lives");
    this.name = "SessionLost";
  }
}

/** How long before its expiry an access token is refreshed, in milliseconds. */
export const REFRESH_MARGIN = 30_000;

/** How a request waits on the refresh of a session, in milliseconds. */
export interface RefreshTiming {
  /** How long the lock of a refresh is held at most, and waited for. */
  readonly lock: number;
  /** How often a request waiting for the refresh of another looks again. */
  readonly wait: number;
}

/**
 * The lock lives twice as long as a request to the realm may take: a refresh ends, answered or
 * not, before another request may take the lock and present the same refresh token.
 */
const REFRESH_TIMING: RefreshTiming = { lock: 2 * REFRESH_TIMEOUT, wait: 50 };

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
    let tokens: Tokens | undefined;
    try {
      tokens = await identityProvider().refresh(session.refreshToken);
    } catch (error) {
      // The realm out of reach closes no session: its access token serves as long as it lives.
      if (session.expiresAt > Date.now()) {
        return session.accessToken;
      }
      throw error;
    }
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
 * session does not live. A request that finds the refresh under way waits for it, as long as the
 * lock lives at most, then carries the token it has.
 */
export async function bearerOf(
  id: string,
  timing: RefreshTiming = REFRESH_TIMING,
): Promise<string | undefined> {
  const holder = randomUUID();
  const deadline = Date.now() + timing.lock;
  for (;;) {
    const session = await readSession(id);
    if (session === undefined || fresh(session)) {
      return session?.accessToken;
    }
    if (await holdRefresh(id, holder, timing.lock)) {
      return renew(id, holder);
    }
    if (Date.now() >= deadline) {
      return session.accessToken;
    }
    await sleep(timing.wait);
  }
}

/** The identifier of the session of the request, as its cookie names it. */
async function requestSessionId(): Promise<string | undefined> {
  return (await cookies()).get(SESSION_COOKIE)?.value;
}

/**
 * The access token of the session of the request; none without its cookie, and `SessionLost` when
 * the session it names lives no more.
 */
export async function requestBearer(): Promise<string | undefined> {
  const id = await requestSessionId();
  if (id === undefined) {
    return undefined;
  }
  const token = await bearerOf(id);
  if (token === undefined) {
    throw new SessionLost();
  }
  return token;
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
