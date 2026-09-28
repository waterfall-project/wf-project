// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Root layout of the application: the HTML document every page renders into, in the
 * language of the request (WF-INTF-0160) and in the mode the account asks for — none forced
 * when it follows the workstation —, inside the shell.
 */
import "@/theme/globals.css";

import { GeistSans } from "geist/font/sans";
import type { Metadata } from "next";
import { cookies } from "next/headers";
import { createTranslator } from "next-intl";
import type { ReactNode } from "react";

import { Shell } from "@/components/shell/shell";
import { CATALOGUES } from "@/i18n/catalogues";
import { requestLanguage } from "@/i18n/request";
import { LAST_CONTEXT_COOKIE, rememberedAddress } from "@/navigation/context";
import { requestSession } from "@/session/request";
import { forcedTheme, themePreference } from "@/theme/theme";

/** Title the document, in the language of the request; a page names its screen. */
export async function generateMetadata(): Promise<Metadata> {
  const { locale } = await requestLanguage();
  const t = createTranslator({ locale, messages: CATALOGUES[locale] });
  return { title: t("app.name") };
}

/** Render the document around a page. */
export default async function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  // One read of the session for the request, whose account decides the language and the
  // mode, and whose permissions the navigation offers; the language is the request's, read
  // once, whatever else asks for it.
  const [session, { locale, preference }, jar] = await Promise.all([
    requestSession(),
    requestLanguage(),
    cookies(),
  ]);
  const theme = themePreference(session?.user);
  return (
    <html lang={locale} data-theme={forcedTheme(theme)} className={GeistSans.variable}>
      <body>
        <Shell
          locale={locale}
          preference={preference}
          theme={theme}
          permissions={session?.permissions}
          remembered={rememberedAddress(jar.get(LAST_CONTEXT_COOKIE)?.value)}
        >
          {children}
        </Shell>
      </body>
    </html>
  );
}
