// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the session (`openSession`, `closeSession`, `requestPasswordReset`,
 * `confirmPasswordReset`): the sign-in page and the menu of the account ask the server of
 * Next, which calls the API (§4.3.1), and get back the outcome the one decoder makes of its
 * answer (`src/api/problem.ts`) — never the answer itself: the session the API opens carries
 * nothing the browser needs.
 *
 * The API judges the credentials and the new password: the front checks no rule of either
 * (WF-ADM-0140), and a refusal is a code of the catalogue. The fake back grants the session the
 * whole mock-up starts from; EP-03, which opens real ones, carries the cookie of the session
 * between the browser and the API.
 */
"use server";

import type { components } from "@/api/generated/schema";
import { decode, type Settled, settled } from "@/api/problem";
import { serverClient } from "@/api/server";

type LocalCredentials = components["schemas"]["LocalCredentials"];

/**
 * Open a session with the address and the password of a local account, or of an account of the
 * directory, which the API asks (WF-ADM-0180). A 401 is the credentials refused, not a session
 * to open: the sign-in page says it as a refusal, and does not lead to itself.
 */
export async function signIn(credentials: LocalCredentials): Promise<Settled> {
  const outcome = await decode(() => serverClient().POST("/session", { body: credentials }));
  return outcome.kind === "signed_out" ? { ...outcome, kind: "refused" } : settled(outcome);
}

/**
 * Close the session (WF-SEC-0020). Without one (401), there is none to close: the user is signed
 * out all the same.
 */
export async function signOut(): Promise<Settled> {
  const outcome = settled(await decode(() => serverClient().DELETE("/session")));
  return outcome.kind === "signed_out" ? settled({ kind: "done", data: null }) : outcome;
}

/**
 * Ask for a link that sets a new password, sent to an address (WF-ADM-0140). The answer does not
 * say whether an account has that address, and neither does the screen.
 */
export async function askPasswordReset(email: string): Promise<Settled> {
  return settled(
    await decode(() => serverClient().POST("/session/password-reset", { body: { email } })),
  );
}

/** Set a new password with the token of the link the user received (WF-ADM-0140). */
export async function resetPassword(token: string, password: string): Promise<Settled> {
  return settled(
    await decode(() =>
      serverClient().POST("/session/password-reset/confirm", { body: { token, password } }),
    ),
  );
}
