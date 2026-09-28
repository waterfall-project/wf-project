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
 * page renders without preferences, and the shell offers neither selectors nor functions.
 */
import "server-only";

import { unstable_rethrow } from "next/navigation";
import { cache } from "react";

import type { components } from "@/api/generated/schema";
import { serverClient } from "@/api/server";

/** The session of a request: its account, and its effective permissions. */
export type Session = components["schemas"]["Session"];

/** The account of the request, with its display preferences. */
export type Account = Session["user"];

/** A permission of the catalogue (WF-ADM-0100). */
export type Permission = components["schemas"]["PermissionCode"];

/**
 * Call the API, or `undefined` when it cannot be reached — `fetch` failing, a `TypeError`: a
 * page never waits on it, and the page itself says the API is out of reach (US-0170). Any
 * other error is a defect, and goes on: an error of Next first, which it must handle itself,
 * then the rest — a fake client's call without an answer among them.
 */
export async function reach<T>(call: () => Promise<T>): Promise<T | undefined> {
  try {
    return await call();
  } catch (error) {
    unstable_rethrow(error);
    if (error instanceof TypeError) {
      return undefined;
    }
    throw error;
  }
}

/**
 * The session of the request, its permissions evaluated by the API at every request
 * (WF-ADM-0110), or `undefined` without one.
 */
export const requestSession = cache(async (): Promise<Session | undefined> => {
  const answer = await reach(() => serverClient().GET("/session"));
  return answer?.data;
});
