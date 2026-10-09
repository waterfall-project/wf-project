// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The session of the request being rendered, read on the server once per request
 * (`getCurrentSession`), however many components ask: its account carries the display
 * preferences — the language and the mode of the interface —, its permissions what the
 * navigation offers. Both are projections of the one answer: the account is never read
 * a second time.
 *
 * Without a session — none open, or an API out of reach — the session is `undefined`: the
 * page renders without preferences, and the shell offers no selectors. Its state tells the
 * two apart for the navigation: none open, it offers no function; none that can be read, the
 * status screen still (WF-ADM-0130).
 */
import "server-only";

import { cache } from "react";

import type { components } from "@/api/generated/schema";
import { reach } from "@/api/problem";
import { serverClient } from "@/api/server";

/** The session of a request: its account, and its effective permissions. */
export type Session = components["schemas"]["Session"];

/** The account of the request, with its display preferences. */
export type Account = Session["user"];

/** A permission of the catalogue (WF-ADM-0100). */
export type Permission = components["schemas"]["PermissionCode"];

/**
 * What a request knows of its session: `open`, with its account and its permissions;
 * `signed_out`, the API saying there is none (401); `unreadable`, when there is none to read
 * — the API out of reach, or an answer that is neither.
 */
export type SessionState =
  | { readonly kind: "open"; readonly session: Session }
  | { readonly kind: "signed_out" | "unreadable" };

/** The state of the session of the request, read once per request, however many ask. */
export const requestSessionState = cache(async (): Promise<SessionState> => {
  const answer = await reach(() => serverClient().GET("/session"));
  if (answer?.data !== undefined) {
    return { kind: "open", session: answer.data };
  }
  return { kind: answer?.response.status === 401 ? "signed_out" : "unreadable" };
});

/**
 * The session of the request, its permissions evaluated by the API at every request
 * (WF-ADM-0110), or `undefined` without one.
 */
export const requestSession = cache(async (): Promise<Session | undefined> => {
  const state = await requestSessionState();
  return state.kind === "open" ? state.session : undefined;
});
