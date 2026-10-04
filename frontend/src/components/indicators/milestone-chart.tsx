// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The tracking of the milestones, the time/time diagram (WF-IND-0090): for each milestone entered
 * in the tracking, the date each marked revision forecast for it, as a function of the date of its
 * marking, and the last point at the current day for the revision under way — a milestone that
 * holds draws a horizontal line, one that slips climbs. The diagonal of equal dates is drawn
 * from the first marking the API gives to the date of calculation; the curve of a milestone stops
 * where the API stops it, at its completion.
 *
 * The forecast is a date of planning, without a time zone: it is placed at midnight in UTC and
 * its axis written in UTC, so that no zone moves it a day (`planningInstant`). ECharts places the
 * ticks of both axes of a chart in one time zone (`useUTC`): the axis of the markings, by month,
 * is written in UTC too, and each marking, an instant, in the local time of the workstation in
 * the table. The chart carries its date of calculation, and the table is its text alternative.
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
  planningInstant,
  timeAxis,
} from "@/components/chart/chart";
import { CalculationDate } from "@/components/context/indicator";
import { LocalTime } from "@/components/local-time";
import { formatLocale, formatPlanningDate } from "@/i18n/format";

/** The tracking of the milestones, as the API reads it. */
export type MilestoneTracking = components["schemas"]["MilestoneTracking"];

/** The tracking of the milestones of a project. */
export interface MilestoneChartProps {
  readonly tracking: MilestoneTracking;
}

/** Render the time/time diagram of the milestones, and the table of its values. */
export function MilestoneChart({ tracking }: MilestoneChartProps) {
  const t = useTranslations("projectIndicators.milestones");
  const locale = useLocale();
  const { milestones, context } = tracking;
  const first = milestones[0]?.points[0]?.marked_at;

  const option = useCallback(
    (palette: ChartPalette): ChartOption => {
      const diagonal =
        first === undefined
          ? []
          : [
              {
                type: "line" as const,
                name: t("diagonal"),
                color: palette.mark,
                symbol: "none",
                silent: true,
                lineStyle: { type: "dotted" as const },
                endLabel: { show: true, formatter: "{a}", color: palette.mark },
                data: [
                  [first, first],
                  [context.computed_at, context.computed_at],
                ],
              },
            ];
      return {
        // Its axes of time are in UTC: their ticks too (`timeAxis`).
        useUTC: true,
        textStyle: { fontFamily: palette.font, color: palette.text },
        // No legend: each curve is named at its end (`curve`), the diagonal too.
        grid: { left: 96, right: END_LABEL_WIDTH + 16, top: 24, bottom: 32 },
        xAxis: timeAxis(palette, formatLocale(locale), true),
        yAxis: timeAxis(palette, formatLocale(locale), true),
        series: [
          ...milestones.map((milestone, index) => ({
            name: milestone.label,
            ...curve(
              palette,
              index,
              milestone.points.map(
                (point) => [point.marked_at, planningInstant(point.forecast_date)] as const,
              ),
            ),
          })),
          ...diagonal,
        ],
      };
    },
    [milestones, context.computed_at, first, locale, t],
  );

  return (
    <Chart
      title={t("chartTitle")}
      description={t("description")}
      note={<CalculationDate context={context} />}
      option={option}
    >
      <table className="w-full text-left">
        <thead className="text-muted-foreground">
          <tr>
            <th scope="col">{t("milestone")}</th>
            <th scope="col">{t("markedAt")}</th>
            <th scope="col">{t("forecast")}</th>
            <th scope="col">{t("completedOn")}</th>
          </tr>
        </thead>
        <tbody>
          {milestones.flatMap((milestone) =>
            milestone.points.map((point) => (
              <tr key={`${milestone.lineage_id}-${point.marked_at}`}>
                <th scope="row" className="font-normal">
                  {milestone.label}
                </th>
                <td>
                  <LocalTime value={point.marked_at} />
                </td>
                <td>{formatPlanningDate(point.forecast_date, locale)}</td>
                <td>
                  {milestone.completed_on === null || milestone.completed_on === undefined
                    ? t("notCompleted")
                    : formatPlanningDate(milestone.completed_on, locale)}
                </td>
              </tr>
            )),
          )}
        </tbody>
      </table>
    </Chart>
  );
}
