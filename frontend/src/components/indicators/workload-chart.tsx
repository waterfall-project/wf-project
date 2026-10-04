// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The workload of a project (FBS-4.4.4, WF-DEV-0070), as the API computes it on the basis it
 * names: for each role of resource, in the order of the API, its load by month in bars, and its
 * monthly capacity in regard, a dashed line over the months of its load, named at its end
 * (`curve`) — a role without load has its capacity in the table. The bars of a role are told
 * apart without their colour too (`bars`), and the legend names them.
 *
 * A month is placed at its first day at midnight in UTC on an axis written in UTC
 * (`planningInstant`); the hours are the strings of the API, which ECharts reads a position from;
 * the ratio of the load to the capacity and its zone are the API's, said by `Signal`
 * (WF-IHM-0070) — nothing is summed, divided nor ordered here.
 *
 * The chart is offered for export as a PNG image (WF-IHM-0130): its title names the project, and
 * its subtitle the revision read, the basis and the date of calculation, written in the local time
 * of the workstation at the moment of the export.
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
  curve,
  END_LABEL_WIDTH,
  planningInstant,
  timeAxis,
} from "@/components/chart/chart";
import { CalculationDate } from "@/components/context/indicator";
import { Signal } from "@/components/signal/signal";
import {
  formatDecimal,
  formatLocale,
  formatMonth,
  formatPercent,
  formatTimestamp,
} from "@/i18n/format";

/** The workload of a project, as the API computes it. */
export type WorkloadPlan = components["schemas"]["WorkloadPlan"];

/** A month of the load of a role. */
type WorkloadMonth = WorkloadPlan["roles"][number]["months"][number];

/** The workload, and what its exported image says of where it comes from. */
export interface WorkloadChartProps {
  readonly workload: WorkloadPlan;
  /** The name of the project. */
  readonly project: string;
  /** The name of the revision the workload is computed on. */
  readonly revision: string;
  /** The name of the file of the exported image. */
  readonly fileName: string;
}

/** The ratio of a month's load to the capacity: written, or said not computable with its reason. */
function LoadRatio({ month }: { readonly month: WorkloadMonth }) {
  const t = useTranslations();
  const locale = useLocale();
  const ratio = month.load_ratio;
  if (ratio === undefined) {
    return null;
  }
  const value = ratio.is_computable ? (ratio.value ?? null) : null;
  if (value !== null) {
    return formatPercent(value, locale);
  }
  const reason = ratio.reason ?? null;
  return reason === null
    ? t("indicator.notComputable")
    : t("projectIndicators.notComputable", { reason: t(`enums.NotComputableReason.${reason}`) });
}

/** The table of the values: each month of each role, a role without load said so. */
function WorkloadValues({ workload }: { readonly workload: WorkloadPlan }) {
  const t = useTranslations("workload");
  const locale = useLocale();
  const hours = (value: string | undefined) =>
    value === undefined ? null : formatDecimal(value, locale);
  return (
    <table className="w-full text-left">
      <thead className="text-muted-foreground">
        <tr>
          <th scope="col">{t("role")}</th>
          <th scope="col">{t("month")}</th>
          <th scope="col">{t("hours")}</th>
          <th scope="col">{t("capacity")}</th>
          <th scope="col">{t("loadRatio")}</th>
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
                  <td className="tabular-nums">
                    <LoadRatio month={month} />
                  </td>
                  <td>{month.zone === undefined ? null : <Signal zone={month.zone} />}</td>
                </tr>
              )),
        )}
      </tbody>
    </table>
  );
}

/** Render the workload of a project in bars, the capacity of each role across, and its values. */
export function WorkloadChart({ workload, project, revision, fileName }: WorkloadChartProps) {
  const t = useTranslations();
  const locale = useLocale();
  const basis = t(`enums.WorkloadPlan.basis.${workload.basis}`);

  const option = useCallback(
    (palette: ChartPalette): ChartOption => {
      const tick = new Intl.NumberFormat(formatLocale(locale));
      return {
        // Its axis of time is in UTC: its ticks too (`timeAxis`).
        useUTC: true,
        textStyle: { fontFamily: palette.font, color: palette.text },
        // The legend names the roles; each capacity is named at its end.
        legend: {
          top: 0,
          textStyle: { color: palette.text },
          data: workload.roles.map((role) => role.label),
        },
        grid: { left: 56, right: END_LABEL_WIDTH + 16, top: 48, bottom: 32 },
        xAxis: timeAxis(palette, formatLocale(locale), true),
        yAxis: {
          type: "value",
          // A load is never negative: its axis starts at zero.
          min: 0,
          axisLine: { show: true, lineStyle: { color: palette.axis } },
          axisLabel: { color: palette.text, formatter: (value: number) => tick.format(value) },
          splitLine: { lineStyle: { color: palette.grid } },
        },
        series: [
          ...workload.roles.map((role, rank) => ({
            ...bars(palette, rank),
            name: role.label,
            data: role.months.map((month) => [planningInstant(month.month), month.hours]),
          })),
          // The capacity of each role over the months of its load: a line, so that the axis
          // reaches it, in the colour of its bars, dashed, named at its end.
          ...workload.roles.flatMap((role, rank) => {
            const capacity = role.capacity_monthly_hours;
            return capacity === undefined || role.months.length === 0
              ? []
              : [
                  {
                    ...curve(
                      palette,
                      rank,
                      role.months.map((month) => [planningInstant(month.month), capacity] as const),
                    ),
                    name: t("workload.capacityOf", { role: role.label }),
                    lineStyle: { type: "dashed" as const },
                  },
                ];
          }),
        ],
      };
    },
    [workload.roles, locale, t],
  );

  const exported = useCallback(
    () => ({
      title: t("workload.exportTitle", { project }),
      subtitle: t("workload.exportSubtitle", {
        revision,
        basis,
        date: formatTimestamp(workload.context.computed_at, locale),
      }),
      fileName,
    }),
    [t, project, revision, basis, workload.context.computed_at, locale, fileName],
  );

  return (
    <Chart
      title={t("workload.chartTitle")}
      description={t("workload.description")}
      note={<CalculationDate context={workload.context} />}
      option={option}
      exported={exported}
    >
      <WorkloadValues workload={workload} />
    </Chart>
  );
}
