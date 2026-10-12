// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server action of the session (`closeMySessions`): the menu of the account asks the
 * server of Next, which calls the API (§4.3.1), and gets back the outcome the one decoder
 * makes of its answer (`src/api/problem.ts`).
 *
 * Waterfall asks for no password: the identity provider authenticates (WF-ADM-0140), and the
 * fake back grants the session the whole mock-up starts from.
 */
"use server";

import { decodeOrLost, type Settled, settled } from "@/api/problem";
import { isMockAuthentication, serverClient } from "@/api/server";
import { HOME } from "@/navigation/home";
import { asksIdentifiers, LOGIN_ROUTE, loginHref, signOutHref } from "@/navigation/login";
import { identityProvider } from "@/session/provider";
import { StoreUnreachable } from "@/session/store";
import { armRequestSignOut, closeRequestSessions } from "@/session/tokens";

/** A sign-out done: the browser loads the document at the address it gives. */
export interface SignedOff {
  readonly kind: "left";
  readonly address: string;
}

/**
 * The silent sign-in that closes every workstation, armed for the cookie of this browser; the
 * service out of reach without Redis.
 */
async function armedSignOut(): Promise<Settled | SignedOff> {
  try {
    const ticket = await armRequestSignOut();
    return { kind: "left", address: ticket === undefined ? LOGIN_ROUTE : signOutHref(ticket) };
  } catch (error) {
    if (!(error instanceof StoreUnreachable)) {
      throw error;
    }
    return { kind: "unreachable" };
  }
}

/**
 * Close the sessions of the account, on all its workstations (WF-SEC-0020): the API has Keycloak
 * close them, and the front forgets those it keeps, without waiting for the back channel; the
 * browser then loads the sign-in, which forgets the cookie (#724). Without one (401), or the
 * account deactivated (401 `ACCOUNT_DEACTIVATED`), whose sessions are closed already, there is none
 * to close: the user is signed out all the same. A token of a sign-in that precedes the closing
 * of the sessions (401 `SESSION_REVOKED`) leads to a sign-in that asks for the identifiers again:
 * the session of the realm, whose closing was missed, would sign the user in again without them,
 * to the same refusal (#855). An account Waterfall does not admit (401
 * `ACCOUNT_NOT_ADMITTED`) holds a session of the realm the API does not close: the browser ends it
 * at the realm. The API out of reach, nothing is closed, and the screen says so.
 *
 * When the session of the front the cookie names lives no more, the request does not leave, and
 * Keycloak may still hold the session of this browser, which would sign the user in again
 * without asking: the browser goes through a silent sign-in, whose token closes the sessions of
 * the account on all its workstations (#689). Only this action arms it, under a ticket of one use
 * bound to the cookie of the request (`armRequestSignOut`), that `/login` takes only from the
 * browser holding that same cookie (`signOutHref`). The identifier of the action is public, and
 * anyone may call it from a server of their own, with a cookie of their own: the ticket they get
 * is bound to that cookie, and a victim led to it signs in like any other, nothing closed. Redis
 * out of reach, nothing is armed, and the screen says the service out of reach.
 */
export async function signOut(): Promise<Settled | SignedOff> {
  const outcome = await decodeOrLost(() => serverClient().DELETE("/me/sessions"));
  if (outcome.kind === "lost") {
    return armedSignOut();
  }
  const refused = outcome.kind === "refused" ? outcome.problem.code : undefined;
  const closed =
    outcome.kind === "done" ||
    outcome.kind === "signed_out" ||
    refused === "ACCOUNT_DEACTIVATED" ||
    refused === "ACCOUNT_NOT_ADMITTED";
  if (!closed) {
    return settled(outcome);
  }
  if (isMockAuthentication()) {
    return { kind: "left", address: LOGIN_ROUTE };
  }
  await closeRequestSessions();
  if (refused === "ACCOUNT_NOT_ADMITTED") {
    return { kind: "left", address: identityProvider().signOutAddress().href };
  }
  const revoked = outcome.kind === "signed_out" && asksIdentifiers(outcome.problem.code);
  return { kind: "left", address: revoked ? loginHref(HOME, true) : LOGIN_ROUTE };
}
