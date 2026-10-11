// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The return of the sign-in (US-0350): Keycloak sends the browser back here with the code of the
 * authorization and the state of the request `/login` made. Only the browser that asked for it may
 * come back: it holds the cookie `/login` bound to the state (`signInCookie`), or the sign-in starts
 * again, the request untouched (RFC 9700, §4.7) — a return brought to another browser, the
 * attacker's own, opens no session there. The state is then taken once from Redis — unknown,
 * already used or older than fifteen minutes, the sign-in starts again —, the code is exchanged
 * with its PKCE verifier, the ID token checked against its nonce, and the session of the front
 * opened: its tokens in Redis, its opaque identifier alone in the cookie `wf_session` —
 * `HttpOnly`, `Secure`, `SameSite=Lax` —, so that the browser holds no token (WF-ARC-0030). The
 * browser goes on to the screen the request aimed at, its address whole, query included.
 *
 * A sign-in the realm refused — an error in the return, a code refused, a wrong nonce — opens no
 * session, forgets the cookie of the one it replaced, and leads home: not to `/login`, which the
 * session of Keycloak would answer at once with the same refusal, again and again. Home, without
 * the cookie, offers the sign-in page and goes nowhere by itself (`requestBearer`).
 *
 * The sign-out of a session the front lost (`signOut`, #689) comes back here from its silent
 * sign-in: its token closes the sessions of the account on all its workstations
 * (`closeMySessions`, WF-SEC-0020), the front forgets those it keeps, and the browser goes on to
 * the sign-in, which the realm asks for anew. Refused, the realm holding no session for the
 * browser, there is no workstation left to close: the browser goes on to the sign-in all the same.
 * Should the API not close them, the browser ends at least its own session at the realm.
 *
 * The realm or Redis out of reach, or the realm silent past its time, the browser is told the
 * sign-in could not be made, never a bare error (#687).
 *
 * Nothing to return to on the fake back (`WATERFALL_AUTH=mock`), which signs nobody in.
 */
import { randomBytes } from "node:crypto";

import { reach } from "@/api/problem";
import { isMockAuthentication, tokenClient } from "@/api/server";
import { HOME } from "@/navigation/home";
import { LOGIN_ROUTE, signInUnavailableHref } from "@/navigation/login";
import { identityProvider, RealmUnreachable, type SignedIn } from "@/session/provider";
import {
  forgetAccount,
  openSession,
  type SignIn,
  StoreUnreachable,
  takeSignIn,
} from "@/session/store";
import {
  forgottenSessionCookie,
  holdsSignIn,
  sessionCookie,
  spentSignInCookie,
} from "@/session/tokens";

/** A redirect of the return, never kept by a cache: it carries the cookie of one session. */
function redirect(location: string, ...cookies: string[]): Response {
  const headers = new Headers({ Location: location, "Cache-Control": "no-store" });
  for (const cookie of cookies) {
    headers.append("Set-Cookie", cookie);
  }
  return new Response(null, { status: 303, headers });
}

/**
 * Close the sessions of the account a silent sign-in found, on all its workstations, and lead to
 * the sign-in — or, the API not closing them, end at least the session of this browser at the realm.
 */
async function closeEverywhere(signedIn: SignedIn, spent: string): Promise<Response> {
  const answer = await reach(() => tokenClient(signedIn.accessToken).DELETE("/me/sessions"));
  await forgetAccount(signedIn.subject);
  if (answer?.response.ok !== true) {
    console.error("The sign-out of a lost session did not close it", answer?.response.status);
    return redirect(identityProvider().signOutAddress().href, spent);
  }
  return redirect(LOGIN_ROUTE, spent);
}

/** Exchange the code of a return; the browser leads where the sign-in ends. */
async function returned(search: string, state: string, signIn: SignIn): Promise<Response> {
  const spent = spentSignInCookie(state);
  const signedIn = await identityProvider().exchange(search, state, signIn.nonce, signIn.verifier);
  if (signedIn === undefined) {
    // Refused: home, which offers the sign-in — or, signing out, the sign-in, nothing left to close.
    return redirect(signIn.signOut ? LOGIN_ROUTE : HOME, forgottenSessionCookie(), spent);
  }
  if (signIn.signOut) {
    return closeEverywhere(signedIn, spent);
  }
  const { lifetime, ...session } = signedIn;
  const id = randomBytes(32).toString("base64url");
  await openSession(id, session, lifetime);
  // Relative, as the target is: behind a proxy, the address of the request is not the browser's.
  return redirect(signIn.target, sessionCookie(id), spent);
}

/** Whether a failure is the realm or Redis out of reach: the sign-in could not be made. */
function isUnavailable(error: unknown): boolean {
  return error instanceof RealmUnreachable || error instanceof StoreUnreachable;
}

/** Open the session of a sign-in that comes back, and lead to the screen it aimed at. */
export async function GET(request: Request): Promise<Response> {
  if (isMockAuthentication()) {
    return new Response(null, { status: 404 });
  }
  const { search, searchParams } = new URL(request.url);
  const state = searchParams.get("state");
  if (state === null || !(await holdsSignIn(state))) {
    return redirect(LOGIN_ROUTE);
  }
  let target = HOME;
  try {
    const signIn = await takeSignIn(state);
    if (signIn === undefined) {
      return redirect(LOGIN_ROUTE, spentSignInCookie(state));
    }
    target = signIn.target;
    return await returned(search, state, signIn);
  } catch (error) {
    if (!isUnavailable(error)) {
      throw error;
    }
    console.error("A sign-in could not be made", error);
    return redirect(signInUnavailableHref(target), spentSignInCookie(state));
  }
}
