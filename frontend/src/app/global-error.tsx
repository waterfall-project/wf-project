// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The boundary of the root layout: when the shell itself fails, this document replaces it,
 * with its own `<html>`, the stylesheet of the charter and its font, so that the screen of
 * failure still shows rather than a blank page.
 *
 * Nothing of the request reaches it — neither the session nor the language the server chose:
 * the language is the first offered one the browser asks for, else the language of the
 * reference catalogue (WF-INTF-0160); the mode follows the workstation.
 */
"use client";

import "@/theme/globals.css";

import { GeistSans } from "geist/font/sans";
import { NextIntlClientProvider } from "next-intl";

import { useBrowserLocale } from "@/components/system/browser-locale";
import type { BoundaryError } from "@/components/system/failure";
import { SystemFailure } from "@/components/system/system-failure";
import { CATALOGUES } from "@/i18n/catalogues";
import { TIME_ZONE } from "@/i18n/format";

/** Render the screen of failure in a document of its own. */
export default function GlobalError({
  error,
  retry,
}: {
  readonly error: BoundaryError;
  readonly retry: () => void;
}) {
  const locale = useBrowserLocale();
  return (
    <html lang={locale} className={GeistSans.variable}>
      <head>
        <title>{CATALOGUES[locale].app.name}</title>
      </head>
      <body>
        <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone={TIME_ZONE}>
          <SystemFailure error={error} retry={retry} />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
