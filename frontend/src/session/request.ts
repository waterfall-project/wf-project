// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The account and the session of the request being rendered, read on the server once per
 * request, however many components ask: the language and the mode of the interface come
 * from the preferences of the account (`getMe`), what the navigation offers from the
 * permissions of the session (`getCurrentSession`).
 *
 * Without an account — no session, or an API out of reach — both are `undefined`: the page
 * renders without preferences, and the shell offers neither selectors nor functions.
 */
import "server-only";

import { unstable_rethrow } from "next/navigation";
import { cache } from "react";

import type { components } from "@/api/generated/schema";
import { serverClient } from "@/api/server";

/** The account of the request, with its display preferences. */
export type Account = components["schemas"]["UserSelf"];

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

/** The account of the request, or `undefined` without one. */
export const requestAccount = cache(async (): Promise<Account | undefined> => {
  const answer = await reach(() => serverClient().GET("/me"));
  return answer?.data;
});

/**
 * The effective permissions of the session of the request, evaluated by the API at every
 * request (WF-ADM-0110), or `undefined` without a session.
 */
export const requestPermissions = cache(async (): Promise<readonly Permission[] | undefined> => {
  const answer = await reach(() => serverClient().GET("/session"));
  return answer?.data?.permissions;
});
