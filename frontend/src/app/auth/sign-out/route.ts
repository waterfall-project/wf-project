// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The way out of an account Waterfall does not admit (#664): the API refuses it whatever the
 * session, and closes none of its sessions of the realm, so that each `/login` would sign it in
 * again without asking. The screen of failure offers this route, which sends the browser to the
 * end of the session of the realm (`signOutAddress`); the realm then leads to `/login`, which
 * forgets the cookie and asks for the identifiers anew, and notifies the front by its back channel,
 * which forgets the sessions it keeps of the account.
 *
 * A link, which another site could make a browser follow: the realm, given no ID token, asks the
 * person to confirm before it ends anything.
 *
 * On the fake back (`WATERFALL_AUTH=mock`), which signs nobody in, it leads to the sign-in.
 */
import { isMockAuthentication } from "@/api/server";
import { LOGIN_ROUTE } from "@/navigation/login";
import { identityProvider } from "@/session/provider";

/** Send the browser to the end of its session of the realm. */
export function GET(): Response {
  const location = isMockAuthentication() ? LOGIN_ROUTE : identityProvider().signOutAddress().href;
  return new Response(null, {
    status: 307,
    headers: { Location: location, "Cache-Control": "no-store" },
  });
}
