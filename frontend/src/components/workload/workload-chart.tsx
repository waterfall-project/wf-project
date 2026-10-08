// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The workload of a project (FBS-4.4.4, WF-DEV-0070), as the API computes it on the basis it
 * names: for each role of resource, in the order of the API, its load by month in bars, told apart
 * without their colour too (`bars`), the legend naming them; and, in the table of the values, the
 * monthly capacity of each role in regard of its load, a role without load included. The plan of a
 * project presents no ratio of its load to the capacity, which is that of the whole installation:
 * the capacity is not drawn either, a line that would crush the bars (decision of the author on
 * #375, option b) — the ratio stays the aggregated workload's (WF-PTF-0060).
 *
 * A month is placed at its first day at midnight in UTC on an axis written in UTC
 * (`planningInstant`); the hours are the strings of the API, which ECharts reads a position from;
 * the zone of a month is the API's, said by `Signal` (WF-IHM-0070) — nothing is summed, divided
 * nor ordered here.
 *
 * The chart is offered for export as a PNG image (WF-IHM-0130): its title names the project, and
 * its provenance the revision read, the basis, the node of organisation the server filtered on and
 * the date of calculation, written in the local time of the workstation at the moment of the export
 * (`useProvenance`).
 */
"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback } from "react";

import type { components } from "@/api/generated/schema";
import {
  bars,
  Chart,
  type ChartOption,
  type ChartPalette,
  type ChartProvenance,
  planningInstant,
  timeAxis,
  useProvenance,
} from "@/components/chart/chart";
import { CalculationDate } from "@/components/context/indicator";
import { Signal } from "@/components/signal/signal";
import { formatDecimal, formatLocale, formatMonth } from "@/i18n/format";

/** The workload of a project, as the API computes it. */
export type WorkloadPlan = components["schemas"]["WorkloadPlan"];

/** The workload, and where it comes from, which its exported image names. */
export interface WorkloadChartProps {
  readonly workload: WorkloadPlan;
  /** The project, the revision read, and the basis and the node of organisation (`detail`). */
  readonly provenance: ChartProvenance;
}

/** The table of the values: each month of each role, a role without load said so. */
function WorkloadValues({ workload }: { readonly workload: WorkloadPlan }) {
  const t = useTranslations("workload");
  const locale = useLocale();
  const hours = (value: string | undefined) =>
    value === undefined ? null : formatDecimal(value, locale);
  return (
    <table className="w-full text-left">
      <thead className="bg-muted text-muted-foreground">
        <tr>
          <th scope="col">{t("role")}</th>
          <th scope="col">{t("month")}</th>
          <th scope="col">{t("hours")}</th>
          <th scope="col">{t("capacity")}</th>
          <th scope="col">{t("zone")}</th>
        </tr>
      </thead>
      <tbody>
        {workload.roles.flatMap((role) =>
          role.months.length === 0
            ? [
                <tr key={role.resource_role_id}>
                  <th scope="row" className="font-normal">
                    {role.label}
                  </th>
                  <td colSpan={2}>{t("noLoad")}</td>
                  <td className="tabular-nums">{hours(role.capacity_monthly_hours)}</td>
                  <td />
                </tr>,
              ]
            : role.months.map((month) => (
                <tr key={`${role.resource_role_id}-${month.month}`}>
                  <th scope="row" className="font-normal">
                    {role.label}
                  </th>
                  <td>{formatMonth(month.month, locale)}</td>
                  <td className="tabular-nums">{hours(month.hours)}</td>
                  <td className="tabular-nums">{hours(role.capacity_monthly_hours)}</td>
                  <td>{month.zone === undefined ? null : <Signal zone={month.zone} />}</td>
                </tr>
              )),
        )}
      </tbody>
    </table>
  );
}

/** Render the workload of a project in bars, and its values, the capacity of each role among them. */
export function WorkloadChart({ workload, provenance }: WorkloadChartProps) {
  const t = useTranslations();
  const locale = useLocale();
  const { roles, context } = workload;
  const exported = useProvenance(
    provenance,
    t("workload.title"),
    context.computed_at,
    t("workload.file"),
  );

  const option = useCallback(
    (palette: ChartPalette): ChartOption => {
      const tick = new Intl.NumberFormat(formatLocale(locale));
      const months = roles.flatMap((role) =>
        role.months.map((month) => planningInstant(month.month)),
      );
      return {
        // Its axis of time is in UTC: its ticks too (`timeAxis`).
        useUTC: true,
        textStyle: { fontFamily: palette.font, color: palette.text },
        // The legend names the roles.
        legend: {
          top: 0,
          textStyle: { color: palette.text },
          data: roles.map((role) => role.label),
        },
        // No name at the end of a series: the bars need no room on their right.
        grid: { left: 56, right: 24, top: 48, bottom: 32 },
        xAxis: timeAxis(palette, formatLocale(locale), months, true),
        yAxis: {
          type: "value",
          // A load is never negative: its axis starts at zero.
          min: 0,
          axisLine: { show: true, lineStyle: { color: palette.axis } },
          axisLabel: { color: palette.text, formatter: (value: number) => tick.format(value) },
          splitLine: { lineStyle: { color: palette.grid } },
        },
        series: roles.map((role, rank) => ({
          ...bars(palette, rank),
          name: role.label,
          data: role.months.map((month) => [planningInstant(month.month), month.hours]),
        })),
      };
    },
    [roles, locale],
  );

  return (
    <Chart
      title={t("workload.chartTitle")}
      description={t("workload.description")}
      note={<CalculationDate context={context} />}
      option={option}
      exported={exported}
    >
      <WorkloadValues workload={workload} />
    </Chart>
  );
}
