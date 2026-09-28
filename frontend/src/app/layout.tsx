// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Root layout of the application: the HTML document every page renders into, in the
 * language of the request (WF-INTF-0160), inside the shell.
 */
import type { Metadata } from "next";
import { createTranslator } from "next-intl";
import type { ReactNode } from "react";

import { Shell } from "@/components/shell/shell";
import { CATALOGUES } from "@/i18n/catalogues";
import { requestLanguage } from "@/i18n/request";

/** Title the document, in the language of the request. */
export async function generateMetadata(): Promise<Metadata> {
  const { locale } = await requestLanguage();
  const t = createTranslator({ locale, messages: CATALOGUES[locale] });
  return { title: t("app.name") };
}

/** Render the document around a page. */
export default async function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  const { locale, preference } = await requestLanguage();
  return (
    <html lang={locale}>
      <body>
        <Shell locale={locale} preference={preference}>
          {children}
        </Shell>
      </body>
    </html>
  );
}
