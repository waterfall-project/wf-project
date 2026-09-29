// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { UNREACHABLE_DIGEST } from "@/components/system/failure";
import { CATALOGUES } from "@/i18n/catalogues";

import GlobalError from "./global-error";
import NotFound from "./not-found";

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

describe("the screen not found", () => {
  it("says the address leads to nothing the user may consult, whether it exists or not, and leads home", () => {
    const html = renderToStaticMarkup(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <NotFound />
      </NextIntlClientProvider>,
    );
    expect(text(html)).toBe(
      "Introuvable Cette adresse ne mène à rien que vous puissiez consulter. Retour à l’accueil",
    );
    expect(html).toMatch(/^<main[^>]*><h1[^>]*>Introuvable<\/h1>/);
    expect(html).toContain('<a class="font-medium underline" href="/">');
  });
});

describe("the screen of failure of the root layout", () => {
  it("is a document of its own, in the reference language on the server, never a blank page", () => {
    const error = Object.assign(new Error("An error occurred."), { digest: UNREACHABLE_DIGEST });
    const html = renderToStaticMarkup(<GlobalError error={error} retry={vi.fn()} />);
    expect(html).toMatch(
      /^<html lang="fr" class="font-geist-sans"><head><title>Waterfall<\/title>/,
    );
    expect(text(html)).toBe(
      "Waterfall Service injoignable " +
        "Le service ne répond pas : l’écran n’a pas pu lire ses données. " +
        "Réessayez dans un instant. Réessayer",
    );
  });
});
