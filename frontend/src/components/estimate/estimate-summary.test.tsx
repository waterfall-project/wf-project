// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { example } from "@/test/fixtures";

import { type EstimateIndicators, EstimateSummary, type MissingRates } from "./estimate-summary";

type Permission = Parameters<typeof EstimateSummary>[0]["permissions"][number];

const all = (example("session") as { permissions: Permission[] }).permissions;
const estimator = (example("session_estimator") as { permissions: Permission[] }).permissions;

/**
 * What the summary says, its tags left out: the texts a reader reads, one space apart — the
 * no-break spaces of the formats included.
 */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/&#x27;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

/** The summary of the estimate on examples of the contract, in a language. */
function summary(
  indicators: string,
  rates: string,
  permissions: readonly Permission[] = all,
  locale: Locale = "fr",
): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <EstimateSummary
        indicators={example(indicators) as EstimateIndicators}
        missingRates={example(rates) as MissingRates}
        permissions={permissions}
      />
    </NextIntlClientProvider>,
  );
}

describe("the summary of the estimate", () => {
  it("shows the total, the provisions and the deviation the API gives, with the date they are computed at", () => {
    const html = summary("estimate_indicators", "missing_rates_none");
    expect(text(html)).toMatch(
      new RegExp(
        `^Indicateurs du devis Calculé le .*Total du devis 100 000,00 ` +
          `Provisions identifiées 0,00 Écart avec la révision marquée précédente 0,00 ` +
          `Par nature de coût Débours 100 000,00 \\(100 %\\) ` +
          `Par sous-projet Hors sous-projet 100 000,00 \\(100 %\\)$`,
      ),
    );
    expect(html).toContain('<time dateTime="2026-03-16T14:05:00Z"');
  });

  it("breaks the total down by nature of cost, in amount and in share, and by sub-project, as the API gives them", () => {
    const html = text(summary("estimate_indicators_breakdown", "missing_rates_none", all, "en"));
    expect(html).toContain(
      "By nature of cost Main-d'œuvre 1,000.00 (36.57%) Débours 1,234.56 (45.15%) Provision 500.00 (18.28%)",
    );
    expect(html).toContain(
      "By subproject Poste de commande 2,234.56 (81.72%) No subproject 500.00 (18.28%)",
    );
    expect(html).toContain("Estimate total 2,734.56 Identified provisions 500.00");
  });

  it("leaves out a deviation the API does not give, rather than showing it as zero", () => {
    const html = text(summary("estimate_indicators_breakdown", "missing_rates_none"));
    expect(html).not.toContain("Écart");
  });

  it("names each category whose hourly rate the calculation lacks, with its year, and leads to the reference", () => {
    const html = summary("estimate_indicators", "missing_rates");
    expect(text(html)).toMatch(
      /^Taux horaires manquants Le devis ne peut pas être calculé tant que ces catégories de coût n’ont pas de taux horaire pour son année de référence : Ingénierie électrique — 2026 Mise en service — 2026 Renseigner les taux horaires Indicateurs du devis/,
    );
    expect(html).toMatch(/<a [^>]*href="\/reference\/costs"/);
  });

  it("names the missing rates without a way to a reference the session may not read", () => {
    const html = summary("estimate_indicators", "missing_rates", estimator);
    expect(text(html)).toContain("Ingénierie électrique — 2026 Mise en service — 2026");
    expect(html).not.toContain("<a ");
  });

  it("says nothing of the rates when none is missing", () => {
    expect(text(summary("estimate_indicators", "missing_rates_none"))).not.toContain(
      "Taux horaires manquants",
    );
  });
});
