// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";

import SignInUnavailablePage from "./page";

/** The page rendered in French, for a query. */
async function rendered(query: Record<string, string | string[]>): Promise<string> {
  const page: ReactNode = await SignInUnavailablePage({ searchParams: Promise.resolve(query) });
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
      {page}
    </NextIntlClientProvider>,
  );
}

describe("the sign-in that could not be made (#687)", () => {
  it("says the service out of reach, never a bare error, and offers the sign-in again for the screen aimed at", async () => {
    const html = await rendered({ next: "/account?tab=1" });
    expect(html).toContain("Service injoignable");
    expect(html).toContain(
      "Le service ne répond pas : la connexion n’a pas pu se faire. Réessayez dans un instant.",
    );
    expect(html).toMatch(/<a [^>]*href="\/login\?next=%2Faccount%3Ftab%3D1"[^>]*>.*Se connecter/);
  });

  it("offers the sign-in for the home page when the screen aimed at is another site, or none", async () => {
    for (const next of ["https://elsewhere.example/", ["/a", "/b"]]) {
      expect(await rendered({ next })).toMatch(/href="\/login\?next=%2F"/);
    }
  });
});
