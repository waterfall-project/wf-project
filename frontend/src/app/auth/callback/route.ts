// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The return of the sign-in (US-0350): Keycloak sends the browser back here with the code of the
 * authorization and the state of the request `/login` made. The state is taken once from Redis —
 * unknown, already used or older than fifteen minutes, the sign-in starts again —, the code is
 * exchanged with its PKCE verifier, the ID token checked against its nonce, and the session of the
 * front opened: its tokens in Redis, its opaque identifier alone in the cookie `wf_session` —
 * `HttpOnly`, `Secure`, `SameSite=Lax` —, so that the browser holds no token (WF-ARC-0030). The
 * browser goes on to the screen the request aimed at, its address whole, query included.
 *
 * Nothing to return to on the fake back (`WATERFALL_AUTH=mock`), which signs nobody in.
 */
import { randomBytes } from "node:crypto";

import { isMockAuthentication } from "@/api/server";
import { LOGIN_ROUTE } from "@/navigation/login";
import { identityProvider } from "@/session/provider";
import { openSession, takeSignIn } from "@/session/store";
import { sessionCookie } from "@/session/tokens";

// A redirect of the return is never kept by a cache: it carries the cookie of one session.
const NO_STORE = { "Cache-Control": "no-store" };

/** Open the session of a sign-in that comes back, and lead to the screen it aimed at. */
export async function GET(request: Request): Promise<Response> {
  if (isMockAuthentication()) {
    return new Response(null, { status: 404 });
  }
  const { search, searchParams } = new URL(request.url);
  const state = searchParams.get("state");
  const signIn = state === null ? undefined : await takeSignIn(state);
  if (state === null || signIn === undefined) {
    return new Response(null, { status: 303, headers: { Location: LOGIN_ROUTE, ...NO_STORE } });
  }
  const { lifetime, ...session } = await identityProvider().exchange(
    search,
    state,
    signIn.nonce,
    signIn.verifier,
  );
  const id = randomBytes(32).toString("base64url");
  await openSession(id, session, lifetime);
  return new Response(null, {
    status: 303,
    // Relative, as the target is: behind a proxy, the address of the request is not the browser's.
    headers: { Location: signIn.target, "Set-Cookie": sessionCookie(id), ...NO_STORE },
  });
}
