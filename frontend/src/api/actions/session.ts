// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server action of the session (`closeMySessions`): the menu of the account asks the
 * server of Next, which calls the API (§4.3.1), and gets back the outcome the one decoder
 * makes of its answer (`src/api/problem.ts`).
 *
 * Waterfall opens no session and asks for no password: the identity provider authenticates
 * (WF-ADM-0140), and the fake back grants the session the whole mock-up starts from.
 */
"use server";

import { decode, type Settled, settled } from "@/api/problem";
import { serverClient } from "@/api/server";

/**
 * Close the sessions of the account, on all its workstations (WF-SEC-0020). Without one (401),
 * or the account deactivated (401 `ACCOUNT_DEACTIVATED`), whose sessions are closed already,
 * there is none to close: the user is signed out all the same.
 */
export async function signOut(): Promise<Settled> {
  const outcome = settled(await decode(() => serverClient().DELETE("/me/sessions")));
  const deactivated = outcome.kind === "refused" && outcome.problem.code === "ACCOUNT_DEACTIVATED";
  return outcome.kind === "signed_out" || deactivated
    ? settled({ kind: "done", data: null })
    : outcome;
}
