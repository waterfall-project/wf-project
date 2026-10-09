// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The way in: `/login?next=<the screen aimed at>`, where a refusal for want of a session (401)
 * leads (`loginHref`). A route handler, not a page: Waterfall shows no sign-in screen and asks
 * for no password, the identity provider does (WF-ADM-0140).
 *
 * On the fake back (`WATERFALL_AUTH=mock`), which grants the session the whole mock-up starts
 * from, there is nothing to sign in to: the route leads straight to the screen `next` names —
 * a path of this front, the home page otherwise (`returnTarget`). It answers nothing else yet:
 * US-0350/L4 makes it the start of the authorization code flow of the identity provider.
 */
import { isMockAuthentication } from "@/api/server";
import { NEXT_PARAMETER, returnTarget } from "@/navigation/login";

/** Lead to the screen aimed at, once the session is open. */
export function GET(request: Request): Response {
  if (!isMockAuthentication()) {
    // For the operator, not the user: no catalogue of translation speaks to it.
    return new Response("Sign-in is not available yet: it comes with US-0350/L4.\n", {
      status: 501,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }
  const next = new URL(request.url).searchParams.get(NEXT_PARAMETER);
  // A relative address: behind a proxy, the address the request carries is not the browser's.
  return new Response(null, { status: 307, headers: { Location: returnTarget(next) } });
}
