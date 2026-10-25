// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The chart of the aggregated workload (FBS-2.2, WF-PTF-0060): the load of the perimeter in a
 * stack of bars, one a month divided by role, the total of each month at the top of its bar, and
 * the capacity of the perimeter — the sum of the capacities of the roles retained, with the
 * node of organisation filtered or without it — as a dashed line across them. The capacity, the
 * total of each month and the load of each role are the server's (`capacity_monthly_hours`,
 * `monthly_totals`, `roles`): nothing is summed here (WF-ARC-0020). The table of the roles, their
 * capacity, their rate of load and their signals, is drawn under it by the view. The chart is
 * exported as a PNG image that names the perimeter, its horizon, the node and the date of
 * calculation (WF-IHM-0130, `usePortfolioExport`).
 */
"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback } from "react";

import type { components } from "@/api/generated/schema";
import {
  Chart,
  type ChartOption,
  type ChartPalette,
  planningInstant,
  timeAxis,
} from "@/components/chart/chart";
import { monthTooltip, monthTotals, stackedRoles } from "@/components/workload/stacked-load";
import { formatDecimal, formatLocale, formatMonth } from "@/i18n/format";

import { usePortfolioExport } from "./provenance";

type PortfolioWorkload = components["schemas"]["PortfolioWorkload"];

/** Render the aggregated workload: a stack of bars, the line of the capacity, the totals. */
export function PortfolioWorkloadChart({ workload }: { readonly workload: PortfolioWorkload }) {
  const t = useTranslations("portfolio.workload");
  const locale = useLocale();
  const { roles, monthly_totals: totals, capacity_monthly_hours: capacity, scope } = workload;
  const capacityLine = t("capacityLine", { hours: formatDecimal(capacity, locale) });
  const total = t("total");
  const totalSeries = t("totalSeries");

  const option = useCallback(
    (palette: ChartPalette): ChartOption => {
      const tick = new Intl.NumberFormat(formatLocale(locale));
      return {
        // Its axis of time is in UTC: its ticks too (`timeAxis`).
        useUTC: true,
        textStyle: { fontFamily: palette.font, color: palette.text },
        legend: {
          top: 0,
          textStyle: { color: palette.text },
          data: roles.map((role) => role.label),
        },
        grid: { left: 56, right: 24, top: 48, bottom: 32 },
        xAxis: timeAxis(
          palette,
          formatLocale(locale),
          totals.map((each) => planningInstant(each.month)),
          true,
        ),
        yAxis: {
          type: "value",
          // A load is never negative: its axis starts at zero. It reaches the capacity too, which
          // ECharts does not do for a marked line: it would be cut when no month gets there.
          min: 0,
          max: ({ max }: { readonly max: number }) => Math.max(max, Number(capacity)),
          axisLine: { show: true, lineStyle: { color: palette.axis } },
          axisLabel: { color: palette.text, formatter: (value: number) => tick.format(value) },
          splitLine: { lineStyle: { color: palette.grid } },
        },
        tooltip: monthTooltip(locale, (hours) => t("hours", { hours })),
        series: [
          ...stackedRoles(palette, roles),
          monthTotals(palette, totalSeries, totals, locale),
          {
            // The capacity is a series of its own, without a point and out of the legend: only its
            // marked line is drawn, dashed, across the bars.
            type: "line" as const,
            name: capacityLine,
            color: palette.mark,
            data: [],
            markLine: {
              symbol: "none",
              silent: true,
              label: { color: palette.mark, position: "insideEndTop" as const },
              data: [
                {
                  yAxis: capacity,
                  name: capacityLine,
                  label: { formatter: capacityLine },
                  lineStyle: { color: palette.mark, type: "dashed" as const },
                },
              ],
            },
          },
        ],
      };
    },
    [roles, totals, capacity, capacityLine, totalSeries, locale, t],
  );

  const exported = usePortfolioExport(scope, t("exportTitle"), t("file"), workload.months);
  return (
    <Chart
      title={t("chartTitle")}
      description={t("description")}
      note={
        <p className="text-sm text-muted-foreground">
          {t("capacityNote", { hours: formatDecimal(capacity, locale) })}
        </p>
      }
      option={option}
      exported={exported}
    >
      <table className="w-full text-left">
        <caption className="sr-only">{t("values")}</caption>
        <thead className="bg-muted text-muted-foreground">
          <tr>
            <th scope="col">{t("month")}</th>
            <th scope="col">{total}</th>
          </tr>
        </thead>
        <tbody className="tabular-nums">
          {totals.map((each) => (
            <tr key={each.month}>
              <th scope="row" className="font-normal">
                {formatMonth(each.month, locale)}
              </th>
              <td>{formatDecimal(each.hours, locale)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Chart>
  );
}
