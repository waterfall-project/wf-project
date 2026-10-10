// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The back-channel logout of the realm (US-0350, WF-SEC-0020): when the sessions of an account
 * close in Keycloak — the API closing them at a sign-out (`closeMySessions`), a deactivation or
 * the withdrawal of every role —, Keycloak posts a logout token here, and the front closes every
 * session of that account it keeps in Redis: the next request of each of its workstations leaves
 * without a token. A route of the front, not an operation of the API: the API never sees it.
 *
 * The token is checked by the keys of the realm — its issuer, its audience, its event, no nonce —;
 * one that is not valid is refused (400), and closes nothing.
 */
import { isMockAuthentication } from "@/api/server";
import { identityProvider } from "@/session/provider";
import { forgetAccount } from "@/session/store";

const NO_STORE = { "Cache-Control": "no-store" };

/** Close the sessions of the account a logout token of the realm names. */
export async function POST(request: Request): Promise<Response> {
  if (isMockAuthentication()) {
    return new Response(null, { status: 404 });
  }
  const form = await request.formData().catch(() => undefined);
  const token = form?.get("logout_token");
  const subject = typeof token === "string" ? await identityProvider().loggedOut(token) : undefined;
  if (subject === undefined) {
    return new Response(null, { status: 400, headers: NO_STORE });
  }
  await forgetAccount(subject);
  return new Response(null, { status: 200, headers: NO_STORE });
}
