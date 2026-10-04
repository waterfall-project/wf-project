// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The two charts of the portfolio: the evolution of its two indices quarter by quarter, computed
 * at past dates by the server (WF-PTF-0070), and its cash-out month by month, the past and the
 * forecast (WF-PTF-0100). Each is a figure of `Chart`, named by a sentence, its values in a table
 * under it — the text alternative (WF-IHM-0100) —, drawn from the strings of the API as they are:
 * a value the server could not compute is a gap in its curve, and a row of the table that says
 * why. The date of calculation is the view's, under its title (`PortfolioHeader`).
 */
"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback } from "react";

import type { components } from "@/api/generated/schema";
import {
  Chart,
  type ChartOption,
  type ChartPalette,
  curve,
  END_LABEL_WIDTH,
  GAP,
  planningInstant,
  timeAxis,
} from "@/components/chart/chart";
import { formatDecimal, formatLocale, formatMoney, formatMonth } from "@/i18n/format";

import { ComputableValue } from "./portfolio-value";

type Quarter = components["schemas"]["PortfolioPerformance"]["quarterly"][number];
type CashOutMonth = components["schemas"]["CashOutMonth"];
type Computable = components["schemas"]["Computable"];

/** The two indices a quarter gives, as the contract names them. */
const INDICES = ["cost_index", "schedule_index"] as const;

/** The parts of a quarter of the contract, `2026-Q1`: its year and its number. */
const QUARTER = /^(\d{4})-Q([1-4])$/;

/** The name of a quarter in the language of the interface: « T1 2026 », « Q1 2026 ». */
function useQuarterName() {
  const t = useTranslations("portfolio.performance");
  return useCallback(
    (quarter: string) => {
      const [, year = "", number = ""] = QUARTER.exec(quarter) ?? [];
      return t("quarter", { year, number });
    },
    [t],
  );
}

/** A value of a curve: as the API wrote it, or a gap. */
function point(value: Computable): string {
  return value.is_computable ? (value.value ?? GAP) : GAP;
}

/**
 * The axis of the values of a chart — from zero for an index, from the lowest value drawn for a
 * signed amount —, its ticks in the language of the interface.
 */
function valueAxis(palette: ChartPalette, locale: string, fromZero: boolean) {
  const tick = new Intl.NumberFormat(locale);
  return {
    type: "value" as const,
    // An index is never negative, its axis starts at zero; an amount is signed, its axis reaches
    // down to the lowest value drawn.
    ...(fromZero ? { min: 0 } : {}),
    axisLine: { show: true, lineStyle: { color: palette.axis } },
    axisLabel: { color: palette.text, formatter: (value: number) => tick.format(value) },
    splitLine: { lineStyle: { color: palette.grid } },
  };
}

/** Render the evolution of the two indices of the portfolio, quarter by quarter, and its table. */
export function QuarterlyChart({ quarters }: { readonly quarters: readonly Quarter[] }) {
  const t = useTranslations();
  const locale = useLocale();
  const name = useQuarterName();
  const option = useCallback(
    (palette: ChartPalette): ChartOption => ({
      textStyle: { fontFamily: palette.font, color: palette.text },
      grid: { left: 48, right: END_LABEL_WIDTH + 16, top: 24, bottom: 32 },
      xAxis: {
        type: "category",
        data: quarters.map((quarter) => name(quarter.quarter)),
        axisLine: { show: true, lineStyle: { color: palette.axis } },
        axisLabel: { color: palette.text },
      },
      yAxis: valueAxis(palette, formatLocale(locale), true),
      series: INDICES.map((index, rank) => ({
        name: t(`portfolio.performance.${index}`),
        ...curve(
          palette,
          rank,
          quarters.map((quarter) => [name(quarter.quarter), point(quarter[index])] as const),
        ),
      })),
    }),
    [quarters, locale, t, name],
  );
  const value = (computable: Computable) => (
    <ComputableValue value={computable} format={(index) => formatDecimal(index, locale)} />
  );
  return (
    <Chart
      title={t("portfolio.performance.quarterly")}
      description={t("portfolio.performance.quarterlyDescription")}
      option={option}
    >
      <table className="w-full text-left">
        <thead className="text-muted-foreground">
          <tr>
            <th scope="col">{t("portfolio.performance.quarterColumn")}</th>
            <th scope="col">{t("portfolio.performance.cost_index")}</th>
            <th scope="col">{t("portfolio.performance.schedule_index")}</th>
          </tr>
        </thead>
        <tbody className="tabular-nums">
          {quarters.map((quarter) => (
            <tr key={quarter.quarter}>
              <th scope="row" className="font-normal">
                {name(quarter.quarter)}
              </th>
              <td>{value(quarter.cost_index)}</td>
              <td>{value(quarter.schedule_index)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Chart>
  );
}

/** The two parts of a month of cash-out, as the contract names them. */
const PARTS = ["past", "forecast"] as const;

/**
 * The month after a month of the contract (`2026-09` → `2026-10`): where the last month of a
 * cash-out ends on its axis. A position of the drawing, never a figure the screen shows.
 */
export function monthAfter(month: string): string {
  const [year = 0, number = 0] = month.split("-").map(Number);
  return number === 12
    ? `${String(year + 1)}-01`
    : `${String(year)}-${String(number + 1).padStart(2, "0")}`;
}

/**
 * Render the cash-out of the portfolio month by month, the past and the forecast, and its table.
 */
export function CashOutChart({ months }: { readonly months: readonly CashOutMonth[] }) {
  const t = useTranslations("portfolio.cashOut");
  const locale = useLocale();
  const last = months.at(-1);
  // The last month holds until the first of the next, as every other: its step ends there.
  const end = last === undefined ? undefined : planningInstant(monthAfter(last.month));
  const option = useCallback(
    (palette: ChartPalette): ChartOption => ({
      // Its axis of time is in UTC, a month having no time zone: its ticks too (`timeAxis`).
      useUTC: true,
      textStyle: { fontFamily: palette.font, color: palette.text },
      grid: { left: 96, right: END_LABEL_WIDTH + 16, top: 24, bottom: 32 },
      // The axis runs to the first of the month after the latest already (`monthTicks`).
      xAxis: timeAxis(
        palette,
        formatLocale(locale),
        months.map((month) => planningInstant(month.month)),
        true,
      ),
      yAxis: valueAxis(palette, formatLocale(locale), false),
      series: PARTS.map((part, rank) => {
        const drawn = curve(
          palette,
          rank,
          months.map((month) => [planningInstant(month.month), month[part]] as const),
        );
        return {
          name: t(part),
          // An amount of a month holds over the month, from its first day: a step at the next,
          // never a slope between them — the last one too, to the end of its month, unmarked.
          step: "end" as const,
          ...drawn,
          data:
            last === undefined || end === undefined
              ? drawn.data
              : [...drawn.data, { value: [end, last[part]], symbol: "none" }],
        };
      }),
    }),
    [months, last, end, locale, t],
  );
  return (
    <Chart title={t("chartTitle")} description={t("description")} option={option}>
      <table className="w-full text-left">
        <thead className="text-muted-foreground">
          <tr>
            <th scope="col">{t("month")}</th>
            <th scope="col">{t("past")}</th>
            <th scope="col">{t("forecast")}</th>
          </tr>
        </thead>
        <tbody className="tabular-nums">
          {months.map((month) => (
            <tr key={month.month}>
              <th scope="row" className="font-normal">
                {formatMonth(month.month, locale)}
              </th>
              <td>{formatMoney(month.past, locale)}</td>
              <td>{formatMoney(month.forecast, locale)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Chart>
  );
}
