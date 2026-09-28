// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The shell every page renders in: the texts of the language of the request, handed to the
 * client components; the header, with the logo and the selectors of the language and the
 * mode; the navigation among the functions the session may read (WF-IHM-0010).
 *
 * Without an account there is no preference to write, and no permission to read a function:
 * the shell then offers neither selectors nor navigation — the browser and the workstation
 * decide the language and the mode.
 */
import Link from "next/link";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { TIME_ZONE } from "@/i18n/format";
import type { LanguagePreference, Locale } from "@/i18n/locale";
import type { ThemePreference } from "@/theme/theme";

import { LanguageSelector } from "./language-selector";
import { Logo } from "./logo";
import { Navigation } from "./navigation";
import { ThemeSelector } from "./theme-selector";

/**
 * The language of the request; the preferences of the account it came from and the
 * permissions of its session — `undefined` without an account —; the address of the last
 * project context the cookie keeps; and the page.
 */
export interface ShellProps {
  readonly locale: Locale;
  readonly preference: LanguagePreference | undefined;
  readonly theme: ThemePreference | undefined;
  readonly permissions: readonly components["schemas"]["PermissionCode"][] | undefined;
  readonly remembered: string | undefined;
  readonly children: ReactNode;
}

/** Render a page inside the shell, in the language of the request. */
export function Shell({
  locale,
  preference,
  theme,
  permissions,
  remembered,
  children,
}: ShellProps) {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone={TIME_ZONE}>
      <div className="min-h-screen md:grid md:grid-cols-[16rem_1fr] md:grid-rows-[auto_1fr]">
        <header className="flex flex-wrap items-center gap-4 border-b bg-card px-4 py-2 text-card-foreground md:col-span-2">
          <Link href="/" className="mr-auto rounded-md">
            <Logo theme={theme} />
          </Link>
          {preference === undefined ? null : <LanguageSelector preference={preference} />}
          {theme === undefined ? null : <ThemeSelector preference={theme} />}
        </header>
        {permissions === undefined ? null : (
          <Navigation permissions={permissions} remembered={remembered} />
        )}
        <div className="min-w-0 md:col-start-2">{children}</div>
      </div>
    </NextIntlClientProvider>
  );
}
