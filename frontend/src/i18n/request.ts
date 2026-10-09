// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The language of the request being rendered, read on the server at every request
 * (WF-INTF-0160), and the configuration next-intl takes from it — the plugin of
 * `next.config.ts` finds this module by its path.
 *
 * The sources are read lazily: the account of the session first (`getMe`, read
 * once for the request, see `@/session/request`), whose preference prevails when it names a
 * language; the browser next (`Accept-Language`); the installation last
 * (`getInstallation`, readable without a session), only when neither decided. A change of
 * preference is therefore seen by the next render — a refresh, not a new session.
 */
import "server-only";

import { headers } from "next/headers";
import { getRequestConfig } from "next-intl/server";
import { cache } from "react";

import { reach } from "@/api/problem";
import { serverClient } from "@/api/server";
import { type Account, requestSession } from "@/session/request";

import { CATALOGUES, type Catalogue } from "./catalogues";
import { TIME_ZONE } from "./format";
import { FALLBACK_LOCALE, type LanguagePreference, type Locale, resolveLocale } from "./locale";

/**
 * The language a request renders in, and the preference of the account it came from —
 * `undefined` without an account: no session, or an API out of reach.
 */
export interface RequestLanguage {
  readonly locale: Locale;
  readonly preference: LanguagePreference | undefined;
}

/**
 * Decide the language of the request for the account of its session — `undefined` without
 * one —, reading the browser and the installation only when the account does not decide.
 */
async function languageOf(account: Account | undefined): Promise<RequestLanguage> {
  // An account without the field follows the browser; no account — the sign-in page, an API
  // out of reach — has no preference at all.
  const preference =
    account === undefined ? undefined : (account.display_preferences?.language ?? "default");
  const decided = resolveLocale(preference, (await headers()).get("accept-language"));
  if (decided !== undefined) {
    return { locale: decided, preference };
  }
  const installation = await reach(() => serverClient().GET("/installation"));
  return { locale: installation?.data?.default_language ?? FALLBACK_LOCALE, preference };
}

/** The language of the request: read once per request, however many components ask. */
export const requestLanguage = cache(async (): Promise<RequestLanguage> =>
  languageOf(await requestSession()),
);

/** The configuration of next-intl for the request: its language, its texts, and its zone. */
export async function requestConfig(): Promise<{
  locale: Locale;
  messages: Catalogue;
  timeZone: string;
}> {
  const { locale } = await requestLanguage();
  return { locale, messages: CATALOGUES[locale], timeZone: TIME_ZONE };
}

export default getRequestConfig(requestConfig);
