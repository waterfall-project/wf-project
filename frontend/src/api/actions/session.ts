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
import { identityProvider } from "@/session/provider";
import { closeRequestSessions } from "@/session/tokens";

/** A sign-out the identity provider is to end in the browser, at the address it gives. */
export interface SignOutAtProvider {
  readonly kind: "provider";
  readonly address: string;
}

/**
 * Close the sessions of the account, on all its workstations (WF-SEC-0020): the API has Keycloak
 * close them, and the front forgets those it keeps, and the cookie of this one, without waiting
 * for the back channel. Without one (401), or the account deactivated (401
 * `ACCOUNT_DEACTIVATED`), whose sessions are closed already, there is none to close: the user is
 * signed out all the same. The API out of reach, nothing is closed, and the screen says so.
 *
 * When the session of the front the cookie names lives no more, the request does not leave, and
 * Keycloak may still hold the session of this browser, which would sign the user in again
 * without asking: the cookie is forgotten, and the browser is to end that session at the realm.
 * The other workstations of the account are not closed, there being no token to ask for it (#689).
 */
export async function signOut(): Promise<Settled | SignOutAtProvider> {
  const outcome = await decodeOrLost(() => serverClient().DELETE("/me/sessions"));
  if (outcome.kind === "lost") {
    await closeRequestSessions();
    return { kind: "provider", address: identityProvider().signOutAddress().href };
  }
  const deactivated = outcome.kind === "refused" && outcome.problem.code === "ACCOUNT_DEACTIVATED";
  const closed = outcome.kind === "done" || outcome.kind === "signed_out" || deactivated;
  if (closed && !isMockAuthentication()) {
    await closeRequestSessions();
  }
  return closed ? settled({ kind: "done", data: null }) : settled(outcome);
}
