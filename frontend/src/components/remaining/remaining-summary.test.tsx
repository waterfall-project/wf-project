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
    .replace(/\s+/g, " ")
    .trim();
}

/** The summary of the remaining to commit on an answer of the API, in English. */
function renderSummary(indicators: RemainingIndicators): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
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
      "Remaining to commit 21,534.56 Deviation from the reference budget -93,900.00 By nature of cost",
    );
    expect(html).not.toContain("previous review");
  });
});
