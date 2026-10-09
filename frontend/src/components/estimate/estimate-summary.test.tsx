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

/** The summary of the estimate on answers of the API, in a language. */
function renderSummary(
  indicators: EstimateIndicators | undefined,
  rates: MissingRates,
  permissions: readonly Permission[] = all,
  locale: Locale = "fr",
): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <EstimateSummary indicators={indicators} missingRates={rates} permissions={permissions} />
    </NextIntlClientProvider>,
  );
}

/** The summary of the estimate on examples of the contract, named, in a language. */
function summary(
  indicators: string,
  rates: string,
  permissions: readonly Permission[] = all,
  locale: Locale = "fr",
): string {
  return renderSummary(
    example(indicators) as EstimateIndicators,
    example(rates) as MissingRates,
    permissions,
    locale,
  );
}

describe("the summary of the estimate", () => {
  it("shows the total, the provisions and the deviations the API gives, with the date they are computed at", () => {
    const html = summary("estimate_indicators", "missing_rates_none");
    expect(text(html)).toMatch(
      new RegExp(
        `^Indicateurs du devis Calculé le .*Total du devis 65 605 723,89 ` +
          `Provisions identifiées 500,00 Écart avec la référence -210,00 ` +
          `Écart avec la révision marquée précédente -210,00 ` +
          `Par nature de coût Main-d'œuvre 9 131 215,00 \\(13,92 %\\) ` +
          `Débours 56 474 008,89 \\(86,08 %\\) Provision 500,00 \\(0 %\\) ` +
          `Par sous-projet Poste de commande 22 276 516,46 \\(33,96 %\\) ` +
          `Essais et mise en service 20 807 656,85 \\(31,72 %\\) ` +
          `Hors sous-projet 22 521 550,58 \\(34,32 %\\) ` +
          `Par poste Fourniture et montage des armoires 2 934,56 \\(0 %\\)$`,
      ),
    );
    expect(html).toContain('<time dateTime="2026-06-03T14:05:00Z"');
  });

  it("breaks the total down by nature of cost, in amount and in share, and by sub-project, as the API gives them", () => {
    // The estimate the offer v1.0 kept at its marking, before any risk: no provision.
    const html = text(summary("estimate_indicators_breakdown", "missing_rates_none", all, "en"));
    expect(html).toContain(
      "By nature of cost Main-d'œuvre 8,953,673.75 (13.68%) Débours 56,474,158.89 (86.32%) By subproject",
    );
    expect(html).toContain("By subproject No subproject 65,427,832.64 (100%)");
    expect(html).toContain("Estimate total 65,427,832.64 Identified provisions 0.00");
  });

  it("says an amount the API could not compute for want of an hourly rate, with its reason, never a figure [WF-DEV-0010-A]", () => {
    const html = text(summary("estimate_indicators_missing_rates", "missing_rates"));
    expect(html).toContain(
      "Total du devis Non calculable — Taux horaire manquant pour l’année de référence.",
    );
    // The amounts the missing rates do not touch are computed; no share without the total.
    expect(html).toContain(
      "Par nature de coût Main-d'œuvre Non calculable — Taux horaire manquant pour l’année de référence. Débours 56 474 008,89 Provision 500,00",
    );
    expect(html).not.toContain("%");
    expect(html).not.toContain("Total du devis 0,00");
  });

  it("leaves out a deviation the API does not give, rather than showing it as zero", () => {
    const html = text(summary("estimate_indicators_breakdown", "missing_rates_none"));
    expect(html).not.toContain("Écart");
  });

  it("names the deviation from the reference apart from that from the previous marked revision [WF-DEV-0060-A]", () => {
    const indicators = example("estimate_indicators") as EstimateIndicators;
    const html = text(
      renderSummary(
        { ...indicators, delta_to_previous_revision: null },
        [] satisfies MissingRates,
        all,
        "en",
      ),
    );
    expect(html).toContain("Identified provisions 500.00 Deviation from the reference -210.00 By");
    expect(html).not.toContain("previous marked revision");
  });

  it("breaks the total down by order item as the API gives it, and leaves the order items out of a planning not structured in them, rather than nil [WF-DEV-0060-A]", () => {
    expect(text(summary("estimate_indicators", "missing_rates_none"))).toMatch(
      /Par sous-projet .* Par poste Fourniture et montage des armoires 2 934,56 \(0 %\)$/,
    );
    const indicators = example("estimate_indicators") as EstimateIndicators;
    expect(
      text(renderSummary({ ...indicators, by_order_item: null }, [] satisfies MissingRates)),
    ).not.toContain("Par poste");
  });

  it("says an amount by order item the API could not compute, with its reason", () => {
    expect(text(summary("estimate_indicators_missing_rates", "missing_rates"))).toMatch(
      /Par poste Fourniture et montage des armoires Non calculable — Taux horaire manquant pour l’année de référence\.$/,
    );
  });

  it("names each category whose hourly rate the calculation lacks, with its year, and leads to the reference", () => {
    const html = summary("estimate_indicators", "missing_rates");
    expect(text(html)).toMatch(
      /^Taux horaires manquants Le devis ne peut pas être calculé tant que ces catégories de coût n’ont pas de taux horaire pour son année de référence : Ingénierie électrique — 2026 Renseigner les taux horaires Indicateurs du devis/,
    );
    expect(html).toMatch(/<a [^>]*href="\/reference\/costs"/);
  });

  it("leads a session that may read the reference but not write it to see the rates, by a link bearing the icon of the function", () => {
    const html = summary("estimate_indicators", "missing_rates", estimator);
    expect(text(html)).toContain("Ingénierie électrique — 2026 Voir les taux horaires Indicateurs");
    expect(html).toMatch(
      /<a [^>]*href="\/reference\/costs"[^>]*><svg[^>]*aria-hidden="true"[^>]*>.*?<\/svg>Voir les taux horaires<\/a>/,
    );
  });

  it("names the missing rates without a way to a reference the session may not read", () => {
    // No session: no permission at all.
    const html = summary("estimate_indicators", "missing_rates", []);
    expect(text(html)).toContain("Ingénierie électrique — 2026 Indicateurs");
    expect(html).not.toContain("<a ");
  });

  it("never names a category or a nature by its identifier when the API gives no label", () => {
    const unlabelled = <T extends { label?: string }>(items: readonly T[]) =>
      items.map((item) => ({ ...item, label: undefined }));
    const breakdown = example("estimate_indicators_breakdown") as EstimateIndicators;
    const html = text(
      renderSummary(
        { ...breakdown, by_cost_type: unlabelled(breakdown.by_cost_type) },
        unlabelled(example("missing_rates") as MissingRates),
      ),
    );
    expect(html).toContain("Sans libellé — 2026");
    expect(html).toContain("Par nature de coût Sans libellé 8 953 673,75 (13,68 %) Sans libellé");
    expect(html).not.toMatch(/01926f3a-/);
  });

  it("leaves out a breakdown the API gives empty", () => {
    const indicators = example("estimate_indicators") as EstimateIndicators;
    const html = text(
      renderSummary({ ...indicators, by_subproject: [] }, [] satisfies MissingRates),
    );
    expect(html).toContain("Par nature de coût Main-d'œuvre");
    expect(html).not.toContain("Par sous-projet");
  });

  it("says the indicators are unavailable when the API did not give them, the missing rates still named", () => {
    const html = text(renderSummary(undefined, example("missing_rates") as MissingRates));
    expect(html).toMatch(
      /^Taux horaires manquants .* Indicateurs du devis Les indicateurs du devis sont indisponibles\.$/,
    );
    expect(html).not.toContain("Calculé le");
  });

  it("says nothing of the rates when none is missing", () => {
    expect(text(summary("estimate_indicators", "missing_rates_none"))).not.toContain(
      "Taux horaires manquants",
    );
  });
});
