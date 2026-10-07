// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The indicators of the remaining to commit (WF-RAE-0020), above its grid: its total — the lines
 * of provision of the risks identified included (WF-RAE-0010) —, its margin on the reference
 * budget — the budget less the actual cost and the remaining, in the one sense of the balances of
 * the sub-projects (#466) —, its deviation from the previous marked revision, its totals by nature of cost and, for
 * each sub-project — the whole « out of any sub-project » among them —, its remaining to commit and
 * the margin between its budget and its actual cost plus its remaining to commit, with the
 * signal of an overrun in the zone the server classes it in, never one deduced here (`Signal`,
 * WF-IHM-0070); and the coverage of the
 * risks (`RiskCoverageSummary`, WF-RIS-0050). All with the date they are computed at
 * (WF-IHM-0020), or said unavailable when the API did not give them.
 *
 * Every figure is the API's, formatted from its exact string: nothing is summed nor subtracted
 * here (WF-ARC-0020). A deviation the API does not give — no previous review — is left out,
 * absent rather than nil.
 */
import { useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { ComputedTotal } from "@/components/computed-amount";
import { CalculationDate } from "@/components/context/indicator";
import { RiskCoverageSummary } from "@/components/risks/risk-coverage";
import { Signal } from "@/components/signal/signal";
import { formatMoney, formatPercent } from "@/i18n/format";
import { UNASSIGNED } from "@/navigation/context";

/** The indicators of the remaining to commit, as the API computes them. */
export type RemainingIndicators = components["schemas"]["RemainingIndicators"];

/** The name of a key of a breakdown: the label the server gives, « out of any sub-project ». */
function useKeyName() {
  const t = useTranslations();
  return (item: { readonly key: string; readonly label?: string }) =>
    item.label ??
    (item.key === UNASSIGNED ? t("enums.Scope.unassigned") : t("remainingSummary.unnamed"));
}

/** The figures of the indicators: the total, the deviations, the breakdowns. */
function Figures({ indicators }: { readonly indicators: RemainingIndicators }) {
  const t = useTranslations("remainingSummary");
  const locale = useLocale();
  const name = useKeyName();
  const reference = indicators.delta_to_reference;
  const previous = indicators.delta_to_previous_revision;
  const money = (amount: string) => formatMoney(amount, locale);
  return (
    <dl className="flex flex-wrap gap-x-8 gap-y-2">
      <ComputedTotal name={t("total")} amount={indicators.total} />
      {reference === null || reference === undefined ? null : (
        <ComputedTotal name={t("deltaToReference")} amount={reference} />
      )}
      {previous === null || previous === undefined ? null : (
        <ComputedTotal name={t("deltaToPrevious")} amount={previous} />
      )}
      <div className="space-y-0.5">
        <dt className="text-xs text-muted-foreground">{t("byCostType")}</dt>
        <dd>
          <ul className="flex flex-wrap gap-x-4 gap-y-0.5">
            {indicators.by_cost_type.map((item) => (
              <li key={item.key} className="tabular-nums">
                {item.share === undefined
                  ? t("amount", { name: name(item), amount: money(item.amount) })
                  : t("amountShare", {
                      name: name(item),
                      amount: money(item.amount),
                      share: formatPercent(item.share, locale),
                    })}
              </li>
            ))}
          </ul>
        </dd>
      </div>
      <div className="space-y-0.5">
        <dt className="text-xs text-muted-foreground">{t("bySubproject")}</dt>
        <dd>
          <ul className="flex flex-wrap gap-x-4 gap-y-0.5">
            {indicators.by_subproject.map((item) => (
              <li key={item.key} className="flex flex-wrap items-center gap-x-2 tabular-nums">
                <span>
                  {t("balance", {
                    name: name(item),
                    remaining: money(item.remaining),
                    variance: money(item.variance),
                  })}
                </span>
                <Signal zone={item.zone} variant="icon" />
              </li>
            ))}
          </ul>
        </dd>
      </div>
    </dl>
  );
}

/** Render the indicators of the remaining to commit, or say them unavailable. */
export function RemainingSummary({
  indicators,
}: {
  readonly indicators: RemainingIndicators | undefined;
}) {
  const t = useTranslations("remainingSummary");
  return (
    <section aria-label={t("title")} className="space-y-1.5 text-sm">
      <div className="flex flex-wrap items-baseline gap-x-3">
        <h2 className="text-sm font-semibold">{t("title")}</h2>
        {indicators === undefined ? null : <CalculationDate context={indicators.context} />}
      </div>
      {indicators === undefined ? (
        <p className="text-muted-foreground">{t("unavailable")}</p>
      ) : (
        <div className="flex flex-wrap gap-x-8 gap-y-2">
          <Figures indicators={indicators} />
          <RiskCoverageSummary coverage={indicators.coverage} />
        </div>
      )}
    </section>
  );
}
