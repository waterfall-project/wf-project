// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The language of a page that nothing of the request reaches — the screen of failure of the
 * root layout: the first offered language the browser asks for, else the language of the
 * reference catalogue (WF-INTF-0160). Rendered on the server, where no browser asks, it is
 * the reference one, until the browser takes over.
 */
import { useSyncExternalStore } from "react";

import { browserLocale, FALLBACK_LOCALE, type Locale } from "@/i18n/locale";

/** The languages of the browser do not change while the page is shown. */
function subscribe(): () => void {
  return () => undefined;
}

/** The offered language the browser asks for first, else the reference one. */
function browserLanguage(): Locale {
  return browserLocale(navigator.languages.join(",")) ?? FALLBACK_LOCALE;
}

/** On the server, no browser asks: the reference language. */
function serverLanguage(): Locale {
  return FALLBACK_LOCALE;
}

/** The language the browser asks for, among those offered. */
export function useBrowserLocale(): Locale {
  return useSyncExternalStore(subscribe, browserLanguage, serverLanguage);
}
