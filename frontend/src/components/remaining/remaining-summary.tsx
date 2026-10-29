// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The indicators of the remaining to commit (WF-RAE-0020), above its grid: its total — the lines
 * of provision of the risks identified included (WF-RAE-0010) —, its margin on the reference
 * budget — the budget less the actual cost and the remaining, in the one sense of the balances of
 * the sub-projects (#466) —, its deviation from the previous review — what the review changed,
 * which is no margin —, its totals by nature of cost and, for each sub-project — the whole « out
 * of any sub-project » among them —, its remaining to commit and its margin, its budget less its
 * actual cost and its remaining to commit, with the signal of an overrun in the zone the server
 * classes it in, never one deduced here (`Signal`, WF-IHM-0070); and the coverage of the risks
 * (`RiskCoverageSummary`, WF-RIS-0050). All with the date they are computed at
 * (WF-IHM-0020), or said unavailable when the API did not give them.
 *
 * The figures lie in cards (`FiguresCard`, US-0550), one for each block above.
 *
 * Every figure is the API's, formatted from its exact string: nothing is summed nor subtracted
 * here (WF-ARC-0020). A deviation the API does not give — no previous review — is left out,
 * absent rather than nil.
 */
import { useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { ComputedTotal } from "@/components/computed-amount";
import { FiguresCard, FiguresGrid, FiguresList } from "@/components/figures-card";
import { ComputableValue } from "@/components/portfolio/portfolio-value";
import { RiskCoverageSummary } from "@/components/risks/risk-coverage";
import { Signal } from "@/components/signal/signal";
import { formatMoney, formatShare } from "@/i18n/format";
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

/** The cards of the indicators: the total and the deviations, the breakdowns, the coverage. */
function Figures({ indicators }: { readonly indicators: RemainingIndicators }) {
  const t = useTranslations("remainingSummary");
  const bounds = useTranslations("share");
  const locale = useLocale();
  const name = useKeyName();
  const reference = indicators.delta_to_reference;
  const previous = indicators.delta_to_previous_revision;
  const { context } = indicators;
  const money = (amount: string) => formatMoney(amount, locale);
  return (
    <FiguresGrid>
      <FiguresCard title={t("title")} context={context}>
        <FiguresList>
          <ComputedTotal name={t("total")} amount={indicators.total} />
          {reference === null || reference === undefined ? null : (
            <ComputedTotal name={t("deltaToReference")} amount={reference} />
          )}
          {previous === null || previous === undefined ? null : (
            <ComputedTotal name={t("deltaToPrevious")} amount={previous} />
          )}
        </FiguresList>
      </FiguresCard>
      {indicators.by_cost_type.length === 0 ? null : (
        <FiguresCard title={t("byCostType")} context={context}>
          <ul className="space-y-1 text-xs leading-snug">
            {indicators.by_cost_type.map((item) => (
              <li key={item.key} className="tabular-nums">
                {t.rich("amountShare", {
                  name: name(item),
                  amount: money(item.amount),
                  share: () => (
                    <ComputableValue
                      value={item.share}
                      format={(share) => formatShare(share, locale, bounds)}
                    />
                  ),
                })}
              </li>
            ))}
          </ul>
        </FiguresCard>
      )}
      {indicators.by_subproject.length === 0 ? null : (
        <FiguresCard title={t("bySubproject")} context={context}>
          <ul className="space-y-1 text-xs leading-snug">
            {indicators.by_subproject.map((item) => (
              <li key={item.key} className="flex items-center gap-x-2 leading-snug tabular-nums">
                <span className="min-w-0 grow">
                  {t("balance", {
                    name: name(item),
                    remaining: money(item.remaining),
                    variance: money(item.variance),
                  })}
                </span>
                <span className="shrink-0">
                  <Signal zone={item.zone} variant="icon" />
                </span>
              </li>
            ))}
          </ul>
        </FiguresCard>
      )}
      <RiskCoverageSummary coverage={indicators.coverage} context={context} />
    </FiguresGrid>
  );
}

/** Render the indicators of the remaining to commit, or say them unavailable. */
export function RemainingSummary({
  indicators,
}: {
  readonly indicators: RemainingIndicators | undefined;
}) {
  const t = useTranslations("remainingSummary");
  return indicators === undefined ? (
    <FiguresGrid>
      <FiguresCard title={t("title")}>
        <p className="text-muted-foreground">{t("unavailable")}</p>
      </FiguresCard>
    </FiguresGrid>
  ) : (
    <Figures indicators={indicators} />
  );
}
