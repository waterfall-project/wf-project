// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the two workload charts share (WF-DEV-0070, WF-PTF-0060): the load of each role in a stack
 * of bars, one bar per month divided by role, each role told apart without its colour too (`bars`),
 * the tooltip of a month that lists the roles and their hours, and the total of a month that
 * labels the top of its bar. The hours are the strings of the API, which ECharts reads a position
 * from, and the total of a month is the server's (`monthly_totals`): nothing is summed here
 * (WF-ARC-0020).
 */
"use client";

import type { LineSeriesOption } from "echarts/charts";
import type { TooltipComponentOption } from "echarts/components";

import { bars, type ChartPalette, escapeHtml, planningInstant } from "@/components/chart/chart";
import { formatDecimal, formatMonth } from "@/i18n/format";
import type { Locale } from "@/i18n/locale";

/** A role and its load by month, as the contract names them. */
export interface LoadRole {
  readonly label: string;
  readonly months: readonly { readonly month: string; readonly hours: string }[];
}

/** The name of the stack all the roles share. */
const STACK = "load";

/** The series of the roles, stacked: a bar a month, divided by role, in the order of the API. */
export function stackedRoles(palette: ChartPalette, roles: readonly LoadRole[]) {
  return roles.map((role, rank) => ({
    ...bars(palette, rank),
    name: role.label,
    stack: STACK,
    data: role.months.map((month) => [planningInstant(month.month), month.hours]),
  }));
}

/**
 * The total of each month, as the server gives it, at the top of its bar: a series of its own,
 * without a line nor a symbol, whose only mark is the label of its points — out of the legend,
 * which names the roles alone —, and listed last by the tooltip of the month.
 */
export function monthTotals(
  palette: ChartPalette,
  name: string,
  totals: readonly { readonly month: string; readonly hours: string }[],
  locale: Locale,
): LineSeriesOption {
  return {
    type: "line",
    name,
    color: palette.text,
    symbol: "none",
    lineStyle: { opacity: 0 },
    silent: true,
    data: totals.map((total) => [planningInstant(total.month), total.hours]),
    label: {
      show: true,
      position: "top",
      color: palette.text,
      formatter: (point) => {
        const [, hours] = pointOf(point.value);
        return typeof hours === "string" ? formatDecimal(hours, locale) : "";
      },
    },
  };
}

/** The `[instant, hours]` a point of a series holds, as ECharts hands it back; nothing otherwise. */
function pointOf(value: unknown): readonly unknown[] {
  return Array.isArray(value) ? value : [];
}

/**
 * The tooltip of a month: the month, then each role and its hours, in the language of the
 * interface — and the total of the month under them when the chart draws it.
 */
export function monthTooltip(
  locale: Locale,
  unit: (hours: string) => string,
): TooltipComponentOption {
  return {
    trigger: "axis",
    axisPointer: { type: "shadow" },
    formatter: (params) => {
      const rows = Array.isArray(params) ? params : [params];
      // The month is the instant the first point holds, `2026-06-01T00:00:00Z`.
      const [instant] = pointOf(rows[0]?.value);
      const month = typeof instant === "string" ? formatMonth(instant.slice(0, 7), locale) : "";
      const lines = rows.map((row) => {
        const [, hours] = pointOf(row.value);
        const marker = typeof row.marker === "string" ? row.marker : "";
        const shown = typeof hours === "string" ? formatDecimal(hours, locale) : "";
        return `${marker}${escapeHtml(row.seriesName ?? "")} <b>${escapeHtml(unit(shown))}</b>`;
      });
      return [`<b>${escapeHtml(month)}</b>`, ...lines].join("<br/>");
    },
  };
}
