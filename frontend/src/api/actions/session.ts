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
import { LOGIN_ROUTE, SIGN_OUT_HREF } from "@/navigation/login";
import { identityProvider } from "@/session/provider";
import { closeRequestSessions } from "@/session/tokens";

/** A sign-out done: the browser loads the document at the address it gives. */
export interface SignedOff {
  readonly kind: "left";
  readonly address: string;
}

/**
 * Close the sessions of the account, on all its workstations (WF-SEC-0020): the API has Keycloak
 * close them, and the front forgets those it keeps, without waiting for the back channel; the
 * browser then loads the sign-in, which forgets the cookie (#724). Without one (401), or the
 * account deactivated (401 `ACCOUNT_DEACTIVATED`), whose sessions are closed already, there is none
 * to close: the user is signed out all the same. An account Waterfall does not admit (401
 * `ACCOUNT_NOT_ADMITTED`) holds a session of the realm the API does not close: the browser ends it
 * at the realm. The API out of reach, nothing is closed, and the screen says so.
 *
 * When the session of the front the cookie names lives no more, the request does not leave, and
 * Keycloak may still hold the session of this browser, which would sign the user in again
 * without asking: the browser goes through a silent sign-in, whose token closes the sessions of
 * the account on all its workstations (`SIGN_OUT_HREF`, #689).
 */
export async function signOut(): Promise<Settled | SignedOff> {
  const outcome = await decodeOrLost(() => serverClient().DELETE("/me/sessions"));
  if (outcome.kind === "lost") {
    return { kind: "left", address: SIGN_OUT_HREF };
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
  return {
    kind: "left",
    address:
      refused === "ACCOUNT_NOT_ADMITTED" ? identityProvider().signOutAddress().href : LOGIN_ROUTE,
  };
}
