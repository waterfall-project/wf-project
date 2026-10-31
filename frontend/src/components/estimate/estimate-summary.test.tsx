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

const all = (example("me") as { permissions: Permission[] }).permissions;
const estimator = (example("me_estimator") as { permissions: Permission[] }).permissions;

/**
 * What the summary says, its tags left out: the texts a reader reads, one space apart — the
 * no-break spaces of the formats included.
 */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/Calculé le|Computed on/g, "")
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
        `^Indicateurs du devis Total du devis 68 923 691,06 ` +
          `Provisions identifiées 500 000,00 Écart avec la référence -349 860,00 ` +
          `Écart avec la révision marquée précédente -349 860,00 ` +
          `Par nature de coût Main-d'œuvre 9 528 887,59 \\(13,83 %\\) ` +
          `Débours 58 894 803,47 \\(85,44 %\\) Provision 500 000,00 \\(0,73 %\\) ` +
          `Par sous-projet Poste de commande 23 314 197,53 \\(33,83 %\\) ` +
          `Essais et mise en service 21 667 888,47 \\(31,44 %\\) ` +
          `Hors sous-projet 23 941 605,06 \\(34,73 %\\) ` +
          `Par lot Lot 1 502 434,56 \\(0,73 %\\)$`,
      ),
    );
    expect(html).toContain('<time dateTime="2026-06-03T14:05:00Z"');
  });

  it("breaks the total down by nature of cost, in amount and in share, and by sub-project, as the API gives them", () => {
    // The estimate the offer v1.0 kept at its marking, before any risk: no provision.
    const html = text(summary("estimate_indicators_breakdown", "missing_rates_none", all, "en"));
    expect(html).toContain(
      "By nature of cost Main-d'œuvre 9,343,749.58 (13.69%) Débours 58,894,953.47 (86.31%) By subproject",
    );
    expect(html).toContain("By subproject No subproject 68,238,703.05 (100%)");
    expect(html).toContain("Estimate total 68,238,703.05 Identified provisions 0.00");
  });

  it("says an amount the API could not compute for want of an hourly rate, with its reason, never a figure [WF-DEV-0010-A]", () => {
    const html = text(summary("estimate_indicators_missing_rates", "missing_rates"));
    expect(html).toContain(
      "Total du devis Non calculable — Taux horaire manquant pour l’année de référence.",
    );
    // The amounts the missing rates do not touch are computed; their share is not, said with its
    // reason rather than left out, and a share is not said twice beside an amount not computed.
    expect(html).toContain(
      "Par nature de coût Main-d'œuvre Non calculable — Taux horaire manquant pour l’année de référence. Débours 58 894 803,47 (Non calculable — Taux horaire manquant pour l’année de référence.) Provision 500 000,00 (Non calculable — Taux horaire manquant pour l’année de référence.)",
    );
    expect(html).not.toContain("Total du devis 0,00");
    expect(html).not.toContain("%");
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
    expect(html).toContain(
      "Identified provisions 500,000.00 Deviation from the reference -349,860.00 By",
    );
    expect(html).not.toContain("previous marked revision");
  });

  it("breaks the total down by work package as the API gives it, and presents a work package no task bears without a total, rather than nil [WF-DEV-0060-A]", () => {
    expect(text(summary("estimate_indicators", "missing_rates_none"))).toMatch(
      /Par sous-projet .* Par lot Lot 1 502 434,56 \(0,73 %\)$/,
    );
    // EP-14/L42s: every work package is given, its amount not computed when no task bears it.
    const byPackage = text(
      renderSummary(
        example("estimate_indicators_work_package_without_task") as EstimateIndicators,
        [] satisfies MissingRates,
      ),
    );
    expect(byPackage).toContain("Par lot");
    expect(byPackage).toMatch(/Lot 1 502 434,56 \(0,73 %\)/);
    expect(byPackage).toMatch(/Lot 2 Non calculable — Aucune tâche ne porte ce lot\./);
  });

  it("says an amount by work package the API could not compute, with its reason", () => {
    expect(text(summary("estimate_indicators_missing_rates", "missing_rates"))).toMatch(
      /Par lot Lot 1 Non calculable — Taux horaire manquant pour l’année de référence\.$/,
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
    expect(html).toContain("Par nature de coût Sans libellé 9 343 749,58 (13,69 %) Sans libellé");
    expect(html).not.toMatch(/01926f3a-/);
  });

  it("says a share not computable, and why, beside the amount of its line [WF-IND-0010-A] [WF-DEV-0060-A]", () => {
    // A variant of `estimate_indicators_breakdown`: every share of the natures of cost, not computable.
    const breakdown = example("estimate_indicators_breakdown") as EstimateIndicators;
    const share = { is_computable: false, value: null, reason: "no_total" as const };
    const html = text(
      renderSummary(
        { ...breakdown, by_cost_type: breakdown.by_cost_type.map((item) => ({ ...item, share })) },
        example("missing_rates_none") as MissingRates,
        all,
        "en",
      ),
    );
    // The section of the natures of cost alone, up to the next one.
    const from = html.indexOf("By nature of cost");
    const section = html.slice(from, html.indexOf("By subproject", from));
    expect(section).toContain("By nature of cost");
    expect(section).not.toContain("%");
    expect(section).toContain("(Not computable — The total is zero.)");
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
    const markup = renderSummary(undefined, example("missing_rates") as MissingRates);
    const html = text(markup);
    expect(html).toMatch(
      /^Taux horaires manquants .* Indicateurs du devis Les indicateurs du devis sont indisponibles\.$/,
    );
    expect(markup).not.toContain("<time");
  });

  it("says nothing of the rates when none is missing", () => {
    expect(text(summary("estimate_indicators", "missing_rates_none"))).not.toContain(
      "Taux horaires manquants",
    );
  });
});
