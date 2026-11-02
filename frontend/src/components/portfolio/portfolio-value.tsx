// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The value of the portfolio (WF-PTF-0050) as the server computes it on the perimeter retained —
 * the order book, the pipeline raw and weighted, the delivered, the conversion rate —, and the
 * pieces every view of the portfolio is written with: a section named by its title, a figure of a
 * list of terms. Nothing is summed, averaged nor divided here
 * (WF-ARC-0020): a sum is marked computed, Σ (WF-IHM-0030), and a value the server could not
 * compute is said so with its reason, never zero. Every figure carries the date of calculation of
 * its view, under its title (`PortfolioHeader`). The value lies in a card of figures (US-0550).
 */
import type { ReactNode } from "react";
import { useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { ComputableValue } from "@/components/computable-value";
import { ComputedTotal } from "@/components/computed-amount";
import { FigureTerm, FiguresCard, FiguresGrid, FiguresList } from "@/components/figures-card";
import { formatPlanningDate, formatShare } from "@/i18n/format";

type Schemas = components["schemas"];

/** A part of a view: its title, which names it, and what it shows. */
export function ViewSection({
  title,
  children,
}: {
  readonly title: string;
  readonly children: ReactNode;
}) {
  return (
    <section aria-label={title} className="space-y-3">
      <h2 className="text-base font-semibold">{title}</h2>
      {children}
    </section>
  );
}

/** A figure of a list of terms: its name, and its value. */
export function Figure({
  name,
  children,
}: {
  readonly name: string;
  readonly children: ReactNode;
}) {
  return <FigureTerm name={name}>{children}</FigureTerm>;
}

/** The period the statistics of the value are computed on, as the server retained it. */
function ValuePeriod({ scope }: { readonly scope: Schemas["PortfolioScope"] }) {
  const t = useTranslations("portfolio.value");
  const locale = useLocale();
  const from = scope.from ?? null;
  const to = scope.to ?? null;
  const date = (value: string) => formatPlanningDate(value, locale);
  const sentence =
    from !== null && to !== null
      ? t("period", { from: date(from), to: date(to) })
      : from !== null
        ? t("since", { from: date(from) })
        : to !== null
          ? t("until", { to: date(to) })
          : t("noPeriod");
  return <p className="text-sm text-muted-foreground">{sentence}</p>;
}

/**
 * Render the value of the portfolio: order book, pipeline raw and weighted, delivered, conversion;
 * and the period its statistics — the delivered, the conversion — are computed on (WF-IHM-0020).
 */
export function PortfolioValueView({ value }: { readonly value: Schemas["PortfolioValue"] }) {
  const t = useTranslations("portfolio.value");
  const bounds = useTranslations("share");
  const locale = useLocale();
  const amounts = [
    ["orderBook", value.order_book],
    ["pipelineGross", value.pipeline_gross],
    ["pipelineWeighted", value.pipeline_weighted],
    ["delivered", value.delivered],
  ] as const;
  return (
    <FiguresGrid>
      <FiguresCard title={t("title")}>
        <ValuePeriod scope={value.scope} />
        <FiguresList>
          {amounts.map(([name, amount]) => (
            <ComputedTotal key={name} name={t(name)} amount={amount} />
          ))}
          <Figure name={t("conversionRate")}>
            <ComputableValue
              value={value.conversion_rate}
              format={(rate) => formatShare(rate, locale, bounds)}
            />
          </Figure>
        </FiguresList>
      </FiguresCard>
    </FiguresGrid>
  );
}
