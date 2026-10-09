// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cumulative curves of a project, as the API computes them (`CurveSeries`): the S-curve of
 * the costs (FBS-4.8.7, WF-IND-0100) — the reference budget, the actual cost to the date of
 * calculation, then the project manager's projection —, shifted by the payment delays when the
 * API says so, and the curves of earned value (FBS-4.8.8, WF-IND-0110) — planned value, earned
 * value, actual cost. One curve per series, in the order of the API, named at its end by the
 * catalogue; the changes of the reference budget are marks across the chart at their date,
 * named by their cause; the cash out by month, when the API gives it, is a table.
 *
 * Each point is a date of planning and an amount, the strings of the API: the date at midnight in
 * UTC on an axis written in UTC (`planningInstant`), the amount as written, which ECharts reads a
 * position from — nothing is summed, shifted nor ordered here: the payment delays are shifted by
 * the server. The chart carries its date of calculation, and its tables are its text alternative;
 * it is offered for export as a PNG image that names its project, its revision and its date
 * (WF-IHM-0130).
 */
"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback } from "react";

import type { components } from "@/api/generated/schema";
import {
  Chart,
  type ChartOption,
  type ChartPalette,
  type ChartProvenance,
  curve,
  END_LABEL_WIDTH,
  planningInstant,
  timeAxis,
  useProvenance,
} from "@/components/chart/chart";
import { CalculationDate } from "@/components/context/indicator";
import { formatLocale, formatMoney, formatMonth, formatPlanningDate } from "@/i18n/format";

/** Cumulative curves, as the API computes them. */
export type CurveSeries = components["schemas"]["CurveSeries"];

/** The series that cumulate dated events, drawn by steps: the earned value, the actual cost. */
const STEPPED: ReadonlySet<CurveSeries["series"][number]["name"]> = new Set([
  "earned_value",
  "actual_cost",
]);

/**
 * What a chart of cumulative curves is named — its caption, the sentence of its image, the name
 * of the file of its exported image before the code of the project —, and where it comes from.
 */
export interface CurveSeriesChartProps {
  readonly curves: CurveSeries;
  readonly title: string;
  readonly description: string;
  readonly file: string;
  readonly provenance: ChartProvenance;
}

/** The tables of the values of the curves: each point, each step, each month of cash out. */
function CurveValues({ curves }: { readonly curves: CurveSeries }) {
  const t = useTranslations();
  const locale = useLocale();
  /**
   * The heading of the row of a point: the name of its series, said before or after the step when
   * the point shares its date with the one after or before it.
   */
  const stepSide = (
    points: CurveSeries["series"][number]["points"],
    index: number,
    name: string,
  ): string => {
    const date = points[index]?.date;
    if (points[index - 1]?.date === date) {
      return t("projectIndicators.curves.afterStep", { series: name });
    }
    return points[index + 1]?.date === date
      ? t("projectIndicators.curves.beforeStep", { series: name })
      : name;
  };
  const steps = curves.steps ?? [];
  const months = curves.cash_out_by_month ?? [];
  const caption = "text-left font-medium";
  return (
    <div className="space-y-4">
      <table className="w-full text-left">
        <thead className="bg-muted text-muted-foreground">
          <tr>
            <th scope="col">{t("projectIndicators.curves.series")}</th>
            <th scope="col">{t("projectIndicators.curves.date")}</th>
            <th scope="col">{t("projectIndicators.curves.amount")}</th>
          </tr>
        </thead>
        <tbody>
          {curves.series.flatMap((series) =>
            // A date may come twice in a series: the two sides of a step of the budget, whose
            // rows a reader of the screen tells apart by their heading, before and after (#290).
            series.points.map((point, index) => (
              <tr key={`${series.name}-${point.date}-${String(index)}`}>
                <th scope="row" className="font-normal">
                  {stepSide(
                    series.points,
                    index,
                    t(`enums.CurveSeries.series.name.${series.name}`),
                  )}
                </th>
                <td>{formatPlanningDate(point.date, locale)}</td>
                <td className="tabular-nums">{formatMoney(point.amount, locale)}</td>
              </tr>
            )),
          )}
        </tbody>
      </table>
      {steps.length === 0 ? null : (
        <table className="w-full text-left">
          <caption className={caption}>{t("projectIndicators.curves.steps")}</caption>
          <thead className="bg-muted text-muted-foreground">
            <tr>
              <th scope="col">{t("projectIndicators.curves.date")}</th>
              <th scope="col">{t("projectIndicators.curves.cause")}</th>
              {/* The amount of the step, signed: what the budget changes by, not the budget after. */}
              <th scope="col">{t("projectIndicators.curves.stepAmount")}</th>
            </tr>
          </thead>
          <tbody>
            {steps.map((step) => (
              <tr key={`${step.date}-${step.cause}`}>
                <th scope="row" className="font-normal">
                  {formatPlanningDate(step.date, locale)}
                </th>
                <td>{t(`enums.CurveSeries.steps.cause.${step.cause}`)}</td>
                <td className="tabular-nums">{formatMoney(step.amount, locale)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {months.length === 0 ? null : (
        <table className="w-full text-left">
          <caption className={caption}>{t("projectIndicators.curves.cashOut")}</caption>
          <thead className="bg-muted text-muted-foreground">
            <tr>
              <th scope="col">{t("projectIndicators.curves.month")}</th>
              <th scope="col">{t("projectIndicators.curves.past")}</th>
              <th scope="col">{t("projectIndicators.curves.forecast")}</th>
            </tr>
          </thead>
          <tbody>
            {months.map((month) => (
              <tr key={month.month}>
                <th scope="row" className="font-normal">
                  {formatMonth(month.month, locale)}
                </th>
                <td className="tabular-nums">{formatMoney(month.past, locale)}</td>
                <td className="tabular-nums">{formatMoney(month.forecast, locale)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

/** Render cumulative curves, their steps, and the tables of their values. */
export function CurveSeriesChart({
  curves,
  title,
  description,
  file,
  provenance,
}: CurveSeriesChartProps) {
  const t = useTranslations();
  const locale = useLocale();
  const exported = useProvenance(provenance, title, curves.context.computed_at, file);

  const option = useCallback(
    (palette: ChartPalette): ChartOption => {
      const tick = new Intl.NumberFormat(formatLocale(locale));
      const steps = curves.steps ?? [];
      const lines = curves.series.map((series, index) => ({
        name: t(`enums.CurveSeries.series.name.${series.name}`),
        ...curve(
          palette,
          index,
          series.points.map((point) => [planningInstant(point.date), point.amount] as const),
        ),
        // A cumulation of dated events — the earned value at the completion of each task, the
        // actual cost at the date of each document — climbs by steps at their dates, never by a
        // slope between them (WF-IND-0110); a cumulation spread over durations is a line.
        ...(STEPPED.has(series.name) ? { step: "end" as const } : {}),
      }));
      return {
        // Its axis of time is in UTC: its ticks too (`timeAxis`).
        useUTC: true,
        textStyle: { fontFamily: palette.font, color: palette.text },
        // No legend: each curve is named at its end (`curve`).
        grid: { left: 80, right: END_LABEL_WIDTH + 16, top: 24, bottom: 32 },
        xAxis: timeAxis(
          palette,
          formatLocale(locale),
          [
            ...curves.series.flatMap((series) =>
              series.points.map((point) => planningInstant(point.date)),
            ),
            ...steps.map((step) => planningInstant(step.date)),
          ],
          true,
        ),
        yAxis: {
          type: "value",
          axisLine: { show: true, lineStyle: { color: palette.axis } },
          axisLabel: { color: palette.text, formatter: (value: number) => tick.format(value) },
          splitLine: { lineStyle: { color: palette.grid } },
        },
        series: [
          ...lines,
          // The steps of the reference budget are a series of their own, without a point: a mark
          // across the chart at the date of each, named by its cause.
          ...(steps.length === 0
            ? []
            : [
                {
                  type: "line" as const,
                  name: t("projectIndicators.curves.steps"),
                  color: palette.mark,
                  data: [],
                  markLine: {
                    symbol: "none",
                    silent: true,
                    label: { color: palette.mark, position: "insideEndTop" as const },
                    data: steps.map((step) => {
                      const cause = t(`enums.CurveSeries.steps.cause.${step.cause}`);
                      return {
                        xAxis: planningInstant(step.date),
                        name: cause,
                        label: { formatter: cause },
                        lineStyle: { color: palette.mark, type: "dashed" as const },
                      };
                    }),
                  },
                },
              ]),
        ],
      };
    },
    [curves, locale, t],
  );

  return (
    <Chart
      title={title}
      description={description}
      note={<CalculationDate context={curves.context} />}
      option={option}
      exported={exported}
    >
      <CurveValues curves={curves} />
    </Chart>
  );
}
