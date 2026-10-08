// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The indicators of a project (FBS-4.8.1 to FBS-4.8.5), one card each, as the API computes them
 * (WF-IND-0040 to WF-IND-0080): the financial progress with the consumption of the budget; the
 * three projections at completion, named by their hypothesis, together with their variance from
 * the budget; the physical progress; the index of cost and the index of schedule, each with its
 * zone by `Signal` (WF-IHM-0070), its variance and the evolution of the index (WF-IND-0130).
 *
 * Every indicator carries the date it is computed at (WF-IHM-0020): a value under `Computable`
 * through `ComputedIndicator`, the figures of a card under the date of its card. Nothing is
 * summed, divided nor compared here (WF-ARC-0020): an amount is the API's string, formatted; a
 * value the API could not compute is said so with its reason; a zone is the API's, and a zone
 * the API leaves out shows no signal.
 */
import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import {
  CalculationDate,
  type CalculationContext,
  ComputedIndicator,
} from "@/components/context/indicator";
import { Signal } from "@/components/signal/signal";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatMoney } from "@/i18n/format";

import { type IndexHistory, IndexChart } from "./index-chart";

/** The indicators of a project, as the API computes them. */
export type ProjectIndicators = components["schemas"]["ProjectIndicators"];

/** An amount of the contract, always computed. */
type Money = components["schemas"]["Money"];

/**
 * A progress the API leaves out — the contract does not require it —: said missing, as a value
 * that is not computable without a reason, never made up.
 */
const NOT_GIVEN = { is_computable: false } as const;

/** The name of a figure in the catalogues. */
type FigureName =
  | "referenceBudget"
  | "plannedValue"
  | "earnedValue"
  | "actualCost"
  | "remaining"
  | "costVariance"
  | "scheduleVariance";

/** The figures of a card, each named, its amount the API's; one the API leaves out, not shown. */
function Figures({ figures }: { readonly figures: readonly [FigureName, Money | undefined][] }) {
  const t = useTranslations("projectIndicators.figures");
  const locale = useLocale();
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
      {figures.map(([name, amount]) =>
        amount === undefined ? null : (
          <div key={name} className="space-y-0.5">
            <dt className="text-xs text-muted-foreground">{t(name)}</dt>
            <dd className="font-semibold tabular-nums">{formatMoney(amount, locale)}</dd>
          </div>
        ),
      )}
    </dl>
  );
}

/** A card of the screen: its title, the date its figures are computed at, its content. */
function IndicatorCard({
  title,
  context,
  children,
}: {
  readonly title: string;
  readonly context: CalculationContext;
  readonly children: ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>
          <CalculationDate context={context} />
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">{children}</CardContent>
    </Card>
  );
}

/** The projections at completion, by hypothesis, with their variance from the budget. */
function Projections({ indicators }: { readonly indicators: ProjectIndicators }) {
  const t = useTranslations("projectIndicators.projections");
  const locale = useLocale();
  const { projections, context } = indicators;
  const money = (amount: Money | null | undefined) =>
    amount === null || amount === undefined ? null : formatMoney(amount, locale);
  return (
    <>
      <table className="w-full text-left text-sm">
        <thead className="bg-muted text-muted-foreground">
          <tr>
            <th scope="col">{t("hypothesis")}</th>
            <th scope="col" className="text-right">
              {t("amount")}
            </th>
            <th scope="col" className="text-right">
              {t("variance")}
            </th>
          </tr>
        </thead>
        <tbody className="tabular-nums">
          <tr>
            <th scope="row" className="font-normal">
              {t("atBudget")}
            </th>
            <td className="text-right">{money(projections.at_budget)}</td>
            <td className="text-right">{money(projections.variance_at_budget)}</td>
          </tr>
          <tr>
            <th scope="row" className="font-normal">
              {t("projectManager")}
            </th>
            <td className="text-right">{money(projections.project_manager)}</td>
            <td className="text-right">{money(projections.variance_project_manager)}</td>
          </tr>
        </tbody>
      </table>
      <ComputedIndicator
        indicator="indicator.names.projectionAtObservedRate"
        value={projections.at_observed_rate}
        context={context}
        date="held"
      />
      {projections.variance_at_observed_rate === null ||
      projections.variance_at_observed_rate === undefined ? null : (
        <p className="text-sm">
          {t("varianceAtObservedRate", {
            variance: formatMoney(projections.variance_at_observed_rate, locale),
          })}
        </p>
      )}
    </>
  );
}

/** An index, its zone when the API gives one, and the evolution of the index. */
function IndexCard({
  kind,
  indicators,
  history,
}: {
  readonly kind: "cost" | "schedule";
  readonly indicators: ProjectIndicators;
  readonly history: IndexHistory;
}) {
  const t = useTranslations("projectIndicators");
  const index = kind === "cost" ? indicators.cost_index : indicators.schedule_index;
  const figures: readonly [FigureName, Money | undefined][] =
    kind === "cost"
      ? [
          ["costVariance", indicators.cost_variance],
          ["earnedValue", indicators.earned_value],
          ["actualCost", indicators.actual_cost],
        ]
      : [
          ["scheduleVariance", indicators.schedule_variance],
          ["earnedValue", indicators.earned_value],
          ["plannedValue", indicators.planned_value],
        ];
  return (
    <IndicatorCard title={t(`${kind}.title`)} context={indicators.context}>
      <div className="flex flex-wrap items-start gap-4">
        <ComputedIndicator
          indicator={
            kind === "cost" ? "indicator.names.costIndex" : "indicator.names.scheduleIndex"
          }
          value={index.value}
          context={indicators.context}
          date="held"
        />
        {index.zone === null ? null : <Signal zone={index.zone} />}
      </div>
      <Figures figures={figures} />
      <IndexChart kind={kind} history={history} />
    </IndicatorCard>
  );
}

/** The indicators of a project and the evolution of its indices. */
export interface ProjectIndicatorCardsProps {
  readonly indicators: ProjectIndicators;
  readonly history: IndexHistory;
}

/** Render the indicators of a project, one card for each function FBS-4.8.1 to FBS-4.8.5. */
export function ProjectIndicatorCards({ indicators, history }: ProjectIndicatorCardsProps) {
  const t = useTranslations("projectIndicators");
  const { context } = indicators;
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <IndicatorCard title={t("financial.title")} context={context}>
        <div className="flex flex-wrap gap-8">
          <ComputedIndicator
            indicator="indicator.names.financialProgress"
            value={indicators.financial_progress ?? NOT_GIVEN}
            context={context}
            date="held"
          />
          <ComputedIndicator
            indicator="indicator.names.budgetConsumption"
            value={indicators.budget_consumption ?? NOT_GIVEN}
            context={context}
            date="held"
          />
        </div>
        <Figures
          figures={[
            ["actualCost", indicators.actual_cost],
            ["remaining", indicators.remaining],
            ["referenceBudget", indicators.reference_budget],
          ]}
        />
      </IndicatorCard>
      <IndicatorCard title={t("projections.title")} context={context}>
        <Projections indicators={indicators} />
      </IndicatorCard>
      <IndicatorCard title={t("physical.title")} context={context}>
        <ComputedIndicator
          indicator="indicator.names.physicalProgress"
          value={indicators.physical_progress ?? NOT_GIVEN}
          context={context}
          date="held"
        />
        <Figures
          figures={[
            ["earnedValue", indicators.earned_value],
            ["referenceBudget", indicators.reference_budget],
          ]}
        />
      </IndicatorCard>
      <div className="grid gap-6 lg:col-span-2 lg:grid-cols-2">
        <IndexCard kind="cost" indicators={indicators} history={history} />
        <IndexCard kind="schedule" indicators={indicators} history={history} />
      </div>
    </div>
  );
}
