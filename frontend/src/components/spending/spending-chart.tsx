// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The spending projection of a project (WF-DEV-0100, US-2050), as the API computes it: a stack of
 * bars, one a month divided by cost type, in the order of the API, in the look of the charts of
 * EP-25 (`bars`) — the cost types told apart without their colour too when the account asks for the
 * patterns —, the legend naming them, the tooltip of a month listing them with their amounts, the
 * total of each month at the top of its bar. The currency is the title of the axis (WF-REF-0140).
 * The total of a month is the server's (`monthly_totals`): nothing is summed here (WF-ARC-0020).
 * The values of the chart are read in a table (WF-IHM-0130): each month of each cost type, then the
 * total of each month.
 *
 * A month is placed at its first day at midnight in UTC on an axis written in UTC
 * (`planningInstant`); the amounts are the strings of the API, which ECharts reads a position from.
 * The chart is offered for export as a PNG image (WF-IHM-0130) that names the project, the revision
 * read, the basis, the date and the sub-project.
 */
"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback } from "react";

import {
  Chart,
  type ChartOption,
  type ChartPalette,
  type ChartProvenance,
  planningInstant,
  timeAxis,
  useProvenance,
  valueAxis,
} from "@/components/chart/chart";
import { CalculationDate } from "@/components/context/indicator";
import {
  alignedLoad,
  monthTooltip,
  monthTotals,
  stackedRoles,
} from "@/components/workload/stacked-load";
import { useCurrency } from "@/currency/context";
import { formatLocale, formatMoney, formatMonth } from "@/i18n/format";

import type { SpendingPlan } from "./spending-rows";

/** The spending projection, and where it comes from, which its exported image names. */
export interface SpendingChartProps {
  readonly spending: SpendingPlan;
  /** The project, the revision read, and the basis, the date and the sub-project (`detail`). */
  readonly provenance: ChartProvenance;
}

/** The table of the values: each month of each cost type, then the total of each month. */
function SpendingValues({ spending }: { readonly spending: SpendingPlan }) {
  const t = useTranslations("spending");
  const locale = useLocale();
  const currency = useCurrency();
  const money = (value: string) => formatMoney(value, locale, currency);
  return (
    <table className="w-full text-left">
      <thead className="bg-muted text-muted-foreground">
        <tr>
          <th scope="col">{t("costType")}</th>
          <th scope="col">{t("month")}</th>
          <th scope="col">{t("amount")}</th>
        </tr>
      </thead>
      <tbody>
        {spending.cost_types.flatMap((type) =>
          type.months.map((month) => (
            <tr key={`${type.cost_type_id}-${month.month}`}>
              <th scope="row" className="font-normal">
                {type.label}
              </th>
              <td>{formatMonth(month.month, locale)}</td>
              <td className="tabular-nums">{money(month.amount)}</td>
            </tr>
          )),
        )}
        {spending.monthly_totals.map((month) => (
          <tr key={`total-${month.month}`}>
            <th scope="row">{t("totalSeries")}</th>
            <td>{formatMonth(month.month, locale)}</td>
            <td className="tabular-nums">{money(month.amount)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Render the spending projection of a project in bars, and its values. */
export function SpendingChart({ spending, provenance }: SpendingChartProps) {
  const t = useTranslations();
  const locale = useLocale();
  const currency = useCurrency();
  const { cost_types: types, context, monthly_totals: totals } = spending;
  const totalSeries = t("spending.totalSeries");
  const exported = useProvenance(
    provenance,
    t("spending.title"),
    context.computed_at,
    t("spending.file"),
  );

  const option = useCallback(
    (palette: ChartPalette): ChartOption => {
      const money = (value: string) => formatMoney(value, locale, currency);
      const tick = new Intl.NumberFormat(formatLocale(locale));
      const months = totals.map((each) => planningInstant(each.month));
      // The series of the stack read an amount where the roles of the workload read hours: the same
      // strings of the API, only aligned.
      const stacked = alignedLoad(types, "amount");
      const monthly = totals.map(({ month, amount }) => ({ month, value: amount }));
      return {
        useUTC: true,
        textStyle: { fontFamily: palette.font, color: palette.text },
        legend: { top: 0, data: types.map((type) => type.label) },
        grid: { left: 80, right: 24, top: 48, bottom: 32 },
        xAxis: timeAxis(palette, formatLocale(locale), months, true),
        yAxis: {
          ...valueAxis(palette, (value) => tick.format(value)),
          // A spending is never negative: its axis starts at zero.
          min: 0,
          // The currency of the amounts is the title of the axis (WF-REF-0140), ticks bare.
          ...(currency === undefined
            ? {}
            : {
                name: currency,
                nameLocation: "end" as const,
                nameTextStyle: { color: palette.text },
              }),
        },
        // The tooltip and the top of the bars write an amount as the table does, in money.
        tooltip: monthTooltip(palette, locale, (shown) => shown, money),
        series: [
          ...stackedRoles(palette, stacked),
          monthTotals(palette, totalSeries, monthly, locale, money),
        ],
      };
    },
    [types, totals, totalSeries, locale, currency],
  );

  return (
    <Chart
      title={t("spending.chartTitle")}
      description={t("spending.description")}
      note={<CalculationDate context={context} />}
      option={option}
      exported={exported}
    >
      <SpendingValues spending={spending} />
    </Chart>
  );
}
