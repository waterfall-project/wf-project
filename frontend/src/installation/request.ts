// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the installation for the request being rendered: `getInstallation`, readable
 * without a session, read once per request however many ask — the language by default
 * (`i18n/request.ts`) and the time zone of the current day (WF-PLA-0130) share the one read. An
 * unreadable answer is none.
 */
import "server-only";

import { cache } from "react";

import type { components } from "@/api/generated/schema";
import { reach } from "@/api/problem";
import { serverClient } from "@/api/server";

/** The installation settings readable without a session. */
export type Installation = components["schemas"]["Installation"];

/** The installation, or `undefined` when the API does not give it. */
export const requestInstallation = cache(async (): Promise<Installation | undefined> => {
  const answer = await reach(() => serverClient({ session: "optional" }).GET("/installation"));
  return answer?.data;
});
