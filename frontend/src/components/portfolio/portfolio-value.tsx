// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The value of the portfolio (WF-PTF-0050) as the server computes it on the perimeter retained —
 * the order book, the pipeline raw and weighted, the delivered, the conversion rate —, and the
 * pieces every view of the portfolio is written with: a section named by its title, a figure of a
 * list of terms, a value that may not be computable. Nothing is summed, averaged nor divided here
 * (WF-ARC-0020): a sum is marked computed, Σ (WF-IHM-0030), and a value the server could not
 * compute is said so with its reason, never zero. Every figure carries the date of calculation of
 * its view, under its title (`PortfolioHeader`).
 */
import type { ReactNode } from "react";
import { useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { ComputedTotal } from "@/components/computed-amount";
import { formatPercent } from "@/i18n/format";

type Schemas = components["schemas"];
type Computable = Schemas["Computable"];

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

/** A value that may not be computable: shown by `format`, or said not computable and why. */
export function ComputableValue({
  value,
  format,
}: {
  readonly value: Computable;
  readonly format: (value: string) => ReactNode;
}) {
  const t = useTranslations();
  const computed = value.is_computable ? (value.value ?? null) : null;
  if (computed !== null) {
    return format(computed);
  }
  const reason = value.reason ?? null;
  return reason === null
    ? t("indicator.notComputable")
    : t("projectIndicators.notComputable", { reason: t(`enums.NotComputableReason.${reason}`) });
}

/** A figure of a list of terms: its name, and its value. */
export function Figure({
  name,
  children,
}: {
  readonly name: string;
  readonly children: ReactNode;
}) {
  return (
    <div className="space-y-0.5">
      <dt className="text-xs text-muted-foreground">{name}</dt>
      <dd className="font-semibold tabular-nums">{children}</dd>
    </div>
  );
}

/**
 * Render the value of the portfolio: order book, pipeline raw and weighted, delivered, conversion.
 */
export function PortfolioValueView({ value }: { readonly value: Schemas["PortfolioValue"] }) {
  const t = useTranslations("portfolio.value");
  const locale = useLocale();
  const amounts = [
    ["orderBook", value.order_book],
    ["pipelineGross", value.pipeline_gross],
    ["pipelineWeighted", value.pipeline_weighted],
    ["delivered", value.delivered],
  ] as const;
  return (
    <ViewSection title={t("title")}>
      <dl className="flex flex-wrap gap-x-8 gap-y-2">
        {amounts.map(([name, amount]) => (
          <ComputedTotal key={name} name={t(name)} amount={amount} />
        ))}
        <Figure name={t("conversionRate")}>
          <ComputableValue
            value={value.conversion_rate}
            format={(rate) => formatPercent(rate, locale)}
          />
        </Figure>
      </dl>
    </ViewSection>
  );
}
