// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import { type RemainingIndicators, RemainingSummary } from "./remaining-summary";

/** What the summary says, its tags left out, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/&#x27;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/\s+/g, " ")
    .trim();
}

/** The summary of the remaining to commit on an answer of the API, in English by default. */
function renderSummary(indicators: RemainingIndicators, locale: "en" | "fr" = "en"): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <RemainingSummary indicators={indicators} />
    </NextIntlClientProvider>,
  );
}

describe("the summary of the remaining to commit", () => {
  it("leaves out the deviation from a previous review that never was, rather than nil [WF-RAE-0020-A]", () => {
    // Sur un projet sans revue précédente, l'écart correspondant est absent plutôt que nul.
    const indicators = example("remaining_indicators") as RemainingIndicators;
    const html = text(renderSummary({ ...indicators, delta_to_previous_revision: null }));
    expect(html).toContain(
      "Remaining to commit 67,293,028.72 Margin on the reference budget -3,275,301.28 By nature of cost",
    );
    expect(html).not.toContain("previous review");
  });

  it("names the gap to the reference budget a margin, negative once overrun, in French too [WF-RAE-0020-A]", () => {
    // Les écarts sont présents et signés : le reste à engager parle de marge (#466).
    const indicators = example("remaining_indicators") as RemainingIndicators;
    const html = text(renderSummary(indicators, "fr"));
    expect(html).toMatch(/Marge sur le budget de référence -3\s275\s301,28/);
    expect(html).toMatch(/Poste de commande\s: 23\s251\s897,56, marge -1\s037\s316,10/);
    expect(html).not.toContain("Écart au budget");
  });

  it("says a share too small to show below the smallest shown, in the words of each language, a nil one « 0 % » (#626)", () => {
    // A variant of `remaining_indicators`, no example of the contract bearing such a share: the
    // provision's share, 0.0074, changed to 0.00004 — the rest of the answer kept.
    const indicators = example("remaining_indicators") as RemainingIndicators;
    const tiny = {
      ...indicators,
      by_cost_type: indicators.by_cost_type.map((item) =>
        item.label === "Provision" ? { ...item, share: "0.00004" } : item,
      ),
    };
    expect(text(renderSummary(tiny))).toContain("Provision: 500,000.00 (<0.01%)");
    // The spaces of French, no-break ones, are read as plain ones.
    expect(text(renderSummary(tiny, "fr"))).toContain("Provision : 500 000,00 (< 0,01 %)");
    expect(text(renderSummary(indicators))).toContain("Provision: 500,000.00 (0.74%)");
  });
});
