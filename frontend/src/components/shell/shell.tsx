// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The shell every page renders in: the texts of the language of the request, handed to the
 * client components, and the header with the language selector.
 */
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";

import { CATALOGUES } from "@/i18n/catalogues";
import { TIME_ZONE } from "@/i18n/format";
import type { LanguagePreference, Locale } from "@/i18n/locale";

import { LanguageSelector } from "./language-selector";

/**
 * The language of the request, the preference of the account it came from — `undefined`
 * without an account —, and the page.
 */
export interface ShellProps {
  readonly locale: Locale;
  readonly preference: LanguagePreference | undefined;
  readonly children: ReactNode;
}

/** Render a page inside the shell, in the language of the request. */
export function Shell({ locale, preference, children }: ShellProps) {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone={TIME_ZONE}>
      <header>
        {/* Without an account there is no preference to write: the browser decides. */}
        {preference === undefined ? null : <LanguageSelector preference={preference} />}
      </header>
      {children}
    </NextIntlClientProvider>
  );
}
