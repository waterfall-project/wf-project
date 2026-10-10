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
 * Nothing to return to on the fake back (`WATERFALL_AUTH=mock`), which signs nobody in.
 */
import { randomBytes } from "node:crypto";

import { isMockAuthentication } from "@/api/server";
import { HOME } from "@/navigation/home";
import { LOGIN_ROUTE } from "@/navigation/login";
import { identityProvider } from "@/session/provider";
import { openSession, takeSignIn } from "@/session/store";
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
  const spent = spentSignInCookie(state);
  const signIn = await takeSignIn(state);
  if (signIn === undefined) {
    return redirect(LOGIN_ROUTE, spent);
  }
  const signedIn = await identityProvider().exchange(search, state, signIn.nonce, signIn.verifier);
  if (signedIn === undefined) {
    return redirect(HOME, forgottenSessionCookie(), spent);
  }
  const { lifetime, ...session } = signedIn;
  const id = randomBytes(32).toString("base64url");
  await openSession(id, session, lifetime);
  // Relative, as the target is: behind a proxy, the address of the request is not the browser's.
  return redirect(signIn.target, sessionCookie(id), spent);
}
