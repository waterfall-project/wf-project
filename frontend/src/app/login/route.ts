// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The way in: `/login?next=<the screen aimed at>`, where a refusal for want of a session (401)
 * leads (`loginHref`). A route handler, not a page: Waterfall shows no sign-in screen and asks
 * for no password, the identity provider does (WF-ADM-0140).
 *
 * It starts the authorization code flow of the realm (US-0350): a state, a nonce and a PKCE
 * verifier, kept in Redis with the screen aimed at for fifteen minutes at most, the browser given
 * a cookie bound to the state — only it may open the session of the return (`signInCookie`) —,
 * and sent to the sign-in page of Keycloak. The screen is kept on the server, bound to the state
 * of the request, and only a path of this front is kept — another site leads home
 * (`returnTarget`); the return, `/auth/callback`, leads there.
 *
 * It forgets the cookie of the session the browser held, if any: the sign-out leads here once the
 * sessions are closed, without touching the cookie itself (#724), and a session lost or refused
 * has nothing more to give. With `sign_out` (`SIGN_OUT_HREF`), the sign-in is the sign-out of a
 * session the front lost (#689): silent (`prompt=none`), its return closes the sessions of the
 * account rather than open one. Redis out of reach, the browser is told the sign-in could not be
 * made, never a bare error (#687).
 *
 * On the fake back (`WATERFALL_AUTH=mock`), which grants the session the whole mock-up starts
 * from, there is nothing to sign in to: the route leads straight to the screen `next` names.
 */
import { isMockAuthentication } from "@/api/server";
import {
  NEXT_PARAMETER,
  returnTarget,
  SIGN_OUT_PARAMETER,
  signInUnavailableHref,
} from "@/navigation/login";
import { identityProvider, signInChecks } from "@/session/provider";
import { rememberSignIn, StoreUnreachable } from "@/session/store";
import { forgottenSessionCookie, signInCookie } from "@/session/tokens";

/** A redirect of the sign-in, never kept by a cache. */
function redirect(location: string, ...cookies: string[]): Response {
  const headers = new Headers({ Location: location, "Cache-Control": "no-store" });
  for (const cookie of cookies) {
    headers.append("Set-Cookie", cookie);
  }
  return new Response(null, { status: 307, headers });
}

/** Start the sign-in, which comes back to the screen aimed at — or the sign-out of a lost session. */
export async function GET(request: Request): Promise<Response> {
  const { searchParams } = new URL(request.url);
  const target = returnTarget(searchParams.get(NEXT_PARAMETER));
  if (isMockAuthentication()) {
    // A relative address: behind a proxy, the address the request carries is not the browser's.
    return new Response(null, { status: 307, headers: { Location: target } });
  }
  const signOut = searchParams.has(SIGN_OUT_PARAMETER);
  const { state, nonce, verifier, challenge } = await signInChecks();
  try {
    await rememberSignIn(state, { verifier, nonce, target, signOut });
  } catch (error) {
    if (!(error instanceof StoreUnreachable)) {
      throw error;
    }
    console.error("A sign-in could not be started", error);
    return redirect(signInUnavailableHref(target));
  }
  const address = identityProvider().signInAddress(state, nonce, challenge, signOut);
  return redirect(address.toString(), signInCookie(state), forgottenSessionCookie());
}
