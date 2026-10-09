// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The account a screen of the account shows (`getMe`): read by the server for the page, which
 * cannot do without it — without a session (401), the screen of failure leads to the sign-in
 * page, which comes back to it.
 */
import "server-only";

import type { components } from "@/api/generated/schema";
import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";

/** The account of the user, with its display preferences. */
export type Me = components["schemas"]["UserSelf"];

/** Read the account of the user, or throw for the screen of failure. */
export async function readMe(): Promise<Me> {
  return readOrFail("getMe", () => serverClient().GET("/me"));
}
