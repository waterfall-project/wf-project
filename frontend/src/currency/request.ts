// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The currency of the installation for the request being rendered: the `currency_code` of the
 * settings of the reference data (`getReferenceSettings`), which any open session reads
 * (WF-REF-0140), read once per request however many ask. An unreadable answer is none: the
 * amounts are shown without their currency rather than the page failing.
 */
import "server-only";

import { cache } from "react";

import { reach } from "@/api/problem";
import { serverClient } from "@/api/server";

/** The currency code of the installation, or `undefined` when the API does not give it. */
export const requestCurrency = cache(async (): Promise<string | undefined> => {
  const answer = await reach(() => serverClient().GET("/reference/settings"));
  return answer?.data?.currency_code;
});
