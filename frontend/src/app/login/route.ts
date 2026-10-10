// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The way in: `/login?next=<the screen aimed at>`, where a refusal for want of a session (401)
 * leads (`loginHref`). A route handler, not a page: Waterfall shows no sign-in screen and asks
 * for no password, the identity provider does (WF-ADM-0140).
 *
 * It starts the authorization code flow of the realm (US-0350): a state, a nonce and a PKCE
 * verifier, kept in Redis with the screen aimed at for fifteen minutes at most, and the browser
 * sent to the sign-in page of Keycloak. The screen is kept on the server, bound to the state of
 * the request, and only a path of this front is kept — another site leads home (`returnTarget`);
 * the return, `/auth/callback`, leads there.
 *
 * On the fake back (`WATERFALL_AUTH=mock`), which grants the session the whole mock-up starts
 * from, there is nothing to sign in to: the route leads straight to the screen `next` names.
 */
import { isMockAuthentication } from "@/api/server";
import { NEXT_PARAMETER, returnTarget } from "@/navigation/login";
import { identityProvider, signInChecks } from "@/session/provider";
import { rememberSignIn } from "@/session/store";

/** Start the sign-in, which comes back to the screen aimed at. */
export async function GET(request: Request): Promise<Response> {
  const target = returnTarget(new URL(request.url).searchParams.get(NEXT_PARAMETER));
  if (isMockAuthentication()) {
    // A relative address: behind a proxy, the address the request carries is not the browser's.
    return new Response(null, { status: 307, headers: { Location: target } });
  }
  const { state, nonce, verifier, challenge } = await signInChecks();
  await rememberSignIn(state, { verifier, nonce, target });
  const address = identityProvider().signInAddress(state, nonce, challenge);
  return new Response(null, {
    status: 307,
    headers: { Location: address.toString(), "Cache-Control": "no-store" },
  });
}
