// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The evolution of an index — the index of cost (FBS-4.8.4) or of schedule (FBS-4.8.5) — for the
 * project and for each of its sub-projects, the whole outside any sub-project included
 * (WF-IND-0130, WF-IND-0020): one curve per scope, in the order the API gives them, one point per
 * marked revision at its marking and the last at the current day, with the thresholds of watch and
 * alert of the reference drawn across (WF-REF-0170). A point the API could not compute is a gap
 * in its curve, and a row of the table that says why — never a zero.
 *
 * The table of the values is the text alternative of the chart: each point, its revision, its
 * date in local time, its value or why it has none, and its zone by `Signal` (WF-IHM-0070). The
 * chart draws the values as the API wrote them, the strings themselves: ECharts reads a position
 * from them, and the figures shown are formatted from the same strings (`formatDecimal`).
 */
"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback } from "react";

import type { components } from "@/api/generated/schema";
import {
  Chart,
  type ChartOption,
  type ChartPalette,
  seriesLook,
  timeAxis,
} from "@/components/chart/chart";
import { LocalTime } from "@/components/local-time";
import { Signal } from "@/components/signal/signal";
import { formatDecimal, formatLocale } from "@/i18n/format";

/** The evolution of the indices, as the API reads it. */
export type IndexHistory = components["schemas"]["IndexHistory"];

/** The curves of one scope of calculation. */
type IndexHistoryScope = components["schemas"]["IndexHistoryScope"];

/** An index and its zone (WF-IND-0070, WF-IND-0080). */
type IndexValue = components["schemas"]["IndexValue"];

/** Which index a chart follows. */
export type IndexKind = "cost" | "schedule";

/** The field of a point and the thresholds of each index, as the contract names them. */
const FIELDS = {
  cost: { point: "cost_index", watch: "cost_watch", alert: "cost_alert" },
  schedule: { point: "schedule_index", watch: "schedule_watch", alert: "schedule_alert" },
} as const;

/** The name of a scope: the project and « unassigned » by the catalogue, a sub-project by its label. */
function useScopeName() {
  const t = useTranslations();
  return useCallback(
    (scope: IndexHistoryScope) => {
      if (scope.scope === "project" || scope.scope === "unassigned") {
        return t(`enums.Scope.${scope.scope}`);
      }
      return scope.label ?? t("projectIndicators.unnamedSubproject");
    },
    [t],
  );
}

/** The value of an index in a cell: written, or said not computable with its reason. */
function IndexFigure({ index }: { readonly index: IndexValue }) {
  const t = useTranslations();
  const locale = useLocale();
  const { value } = index;
  const computed = value.is_computable ? (value.value ?? null) : null;
  if (computed !== null) {
    return formatDecimal(computed, locale);
  }
  const reason = value.reason ?? null;
  return reason === null
    ? t("indicator.notComputable")
    : t("projectIndicators.notComputable", { reason: t(`enums.NotComputableReason.${reason}`) });
}

/** The evolution of one index, its thresholds, for every scope. */
export interface IndexChartProps {
  readonly kind: IndexKind;
  readonly history: IndexHistory;
}

/** Render the chart of the evolution of one index, and the table of its values. */
export function IndexChart({ kind, history }: IndexChartProps) {
  const t = useTranslations("projectIndicators.history");
  const locale = useLocale();
  const scopeName = useScopeName();
  const fields = FIELDS[kind];
  const watch = history.thresholds[fields.watch];
  const alert = history.thresholds[fields.alert];

  const option = useCallback(
    (palette: ChartPalette): ChartOption => {
      const tick = new Intl.NumberFormat(formatLocale(locale));
      const thresholds = [
        { name: t("watch"), value: watch, type: "dashed" as const },
        { name: t("alert"), value: alert, type: "dotted" as const },
      ];
      return {
        textStyle: { fontFamily: palette.font, color: palette.text },
        legend: { top: 0, textStyle: { color: palette.text } },
        grid: { left: 48, right: 24, top: 40, bottom: 32 },
        xAxis: timeAxis(palette, formatLocale(locale)),
        yAxis: {
          type: "value",
          // An index is never negative: its axis starts at zero, drawn even when no point is.
          min: 0,
          axisLine: { show: true, lineStyle: { color: palette.axis } },
          axisLabel: { color: palette.text, formatter: (value: number) => tick.format(value) },
          splitLine: { lineStyle: { color: palette.grid } },
        },
        series: history.scopes.map((scope, index) => ({
          type: "line" as const,
          name: scopeName(scope),
          ...seriesLook(palette, index),
          data: scope.points.map((point) => {
            const { value } = point[fields.point];
            return [point.at, value.is_computable ? (value.value ?? "-") : "-"];
          }),
          ...(index === 0
            ? {
                markLine: {
                  symbol: "none",
                  silent: true,
                  label: { color: palette.mark, position: "insideEndTop" as const },
                  data: thresholds.map((threshold) => ({
                    yAxis: threshold.value,
                    name: threshold.name,
                    label: { formatter: threshold.name },
                    lineStyle: { color: palette.mark, type: threshold.type },
                  })),
                },
              }
            : {}),
        })),
      };
    },
    [history.scopes, fields.point, watch, alert, locale, t, scopeName],
  );

  const values = { watch: formatDecimal(watch, locale), alert: formatDecimal(alert, locale) };
  return (
    <Chart title={t(`${kind}Title`)} description={t(`${kind}Description`, values)} option={option}>
      <table className="w-full text-left">
        <thead className="text-muted-foreground">
          <tr>
            <th scope="col">{t("scope")}</th>
            <th scope="col">{t("revision")}</th>
            <th scope="col">{t("date")}</th>
            <th scope="col">{t("value")}</th>
            <th scope="col">{t("zone")}</th>
          </tr>
        </thead>
        <tbody>
          {history.scopes.flatMap((scope) =>
            scope.points.map((point) => {
              const index = point[fields.point];
              return (
                <tr key={`${scope.scope}-${point.revision_id}`}>
                  <th scope="row" className="font-normal">
                    {scopeName(scope)}
                  </th>
                  <td>{point.version_name ?? t("currentRevision")}</td>
                  <td>
                    <LocalTime value={point.at} />
                  </td>
                  <td className="tabular-nums">
                    <IndexFigure index={index} />
                  </td>
                  <td>{index.zone === null ? null : <Signal zone={index.zone} />}</td>
                </tr>
              );
            }),
          )}
        </tbody>
      </table>
    </Chart>
  );
}
