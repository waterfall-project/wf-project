// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The session of the request being rendered, which is the account it opens (`getMe`), read on
 * the server once per request, however many components ask: the account carries the display
 * preferences — the language and the mode of the interface — and its permissions, what the
 * navigation offers. Both are projections of the one answer: the account is never read a
 * second time.
 *
 * Without a session — none open, or an API out of reach — the session is `undefined`: the
 * page renders without preferences, and the shell offers no selectors. Its state tells the
 * two apart for the navigation: none open (a 401), it offers no function; none that can be
 * read, the status screen still (WF-ADM-0130). A session the cookie names and that lives no more
 * is neither: the read fails with `SessionLost`, which leads to the sign-in page
 * (`src/session/tokens.ts`).
 */
import "server-only";

import { cache } from "react";

import type { components } from "@/api/generated/schema";
import { reach } from "@/api/problem";
import { isDeactivation } from "@/api/problem-kind";
import { serverClient } from "@/api/server";

/** The account of the request, with its display preferences and its effective permissions. */
export type Account = components["schemas"]["UserSelf"];

/** A permission of the catalogue (WF-ADM-0100). */
export type Permission = components["schemas"]["PermissionCode"];

/**
 * What a request knows of its session: `open`, with its account and its permissions;
 * `signed_out`, the API saying there is none (401); `deactivated`, the account being so (401
 * `ACCOUNT_DEACTIVATED`: not led back to the sign-in page, which would loop, the screen says
 * it); `unreadable`, when there is none to read
 * — the API out of reach, or an answer that is neither.
 */
export type SessionState =
  | { readonly kind: "open"; readonly account: Account }
  | { readonly kind: "signed_out" | "deactivated" | "unreadable" };

/** The state of the session of the request, read once per request, however many ask. */
export const requestSessionState = cache(async (): Promise<SessionState> => {
  const answer = await reach(() => serverClient().GET("/me"));
  if (answer?.data !== undefined) {
    return { kind: "open", account: answer.data };
  }
  const status = answer?.response.status;
  if (status !== 401) {
    return { kind: "unreadable" };
  }
  // A 401 may come without the envelope (a proxy): then it is no session, not a deactivation.
  const body: unknown = answer?.error;
  const code = typeof body === "object" && body !== null && "code" in body ? body.code : undefined;
  return { kind: isDeactivation(status, code) ? "deactivated" : "signed_out" };
});

/**
 * The session of the request, its permissions evaluated by the API at every request
 * (WF-ADM-0110), or `undefined` without one.
 */
export const requestSession = cache(async (): Promise<Account | undefined> => {
  const state = await requestSessionState();
  return state.kind === "open" ? state.account : undefined;
});
