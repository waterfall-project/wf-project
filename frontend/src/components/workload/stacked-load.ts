// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the two workload charts share (WF-DEV-0070, WF-PTF-0060): the load of each role in a stack
 * of bars, one bar per month divided by role, in the look of the charts (`bars`) — told apart
 * without its colour when the account asks for the patterns —, the tooltip of a month that names
 * the roles and their values — hours, or amounts —, and the total of a month that labels the top
 * of its bar. The values are the strings of the API, which ECharts reads a position from, and the
 * total of a month is the server's (`monthly_totals`): nothing is summed here (WF-ARC-0020).
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
  readonly months: readonly { readonly month: string; readonly value: string }[];
}

/**
 * A load of the API aligned for the stack: the contract names its values `hours`, or `amount`, where
 * the stack reads a `value` — the same strings, only renamed (WF-ARC-0020).
 */
export function alignedLoad<K extends string>(
  series: readonly {
    readonly label: string;
    readonly months: readonly ({ readonly month: string } & Readonly<Record<K, string>>)[];
  }[],
  key: K,
): LoadRole[] {
  return series.map(({ label, months }) => ({
    label,
    months: months.map((each) => ({ month: each.month, value: each[key] })),
  }));
}

/** The name of the stack all the roles share. */
const STACK = "load";

/** What ECharts reads as no value at a point: a month a role carries no load on. */
const EMPTY = "-";

/**
 * The series of the roles, stacked: a bar a month, divided by role, in the order of the API.
 * ECharts stacks the bars of a time axis by the rank of their points, not by their instant
 * (WF-DEV-0070-A): the service gives a role only the months it is loaded on, so each role is given
 * the months at least one role carries, in order, and a month without load is left empty. Nothing
 * is summed (WF-ARC-0020): the points are only aligned.
 */
export function stackedRoles(palette: ChartPalette, roles: readonly LoadRole[]) {
  const months = [
    ...new Set(roles.flatMap((role) => role.months.map((each) => each.month))),
  ].sort();
  return roles.map((role, rank) => {
    const values = new Map(role.months.map((each) => [each.month, each.value]));
    return {
      ...bars(palette, rank),
      name: role.label,
      stack: STACK,
      data: months.map((month) => [planningInstant(month), values.get(month) ?? EMPTY]),
    };
  });
}

/**
 * The total of each month, as the server gives it, at the top of its bar: a series of its own,
 * without a line nor a symbol, whose only mark is the label of its points — out of the legend,
 * which names the roles alone —, and listed last by the tooltip of the month.
 */
export function monthTotals(
  palette: ChartPalette,
  name: string,
  totals: readonly { readonly month: string; readonly value: string }[],
  locale: Locale,
  amount: (value: string) => string = (value) => formatDecimal(value, locale),
): LineSeriesOption {
  return {
    type: "line",
    name,
    color: palette.text,
    symbol: "none",
    lineStyle: { opacity: 0 },
    silent: true,
    // It stays as it is while a role under the pointer fades the others.
    blur: { label: { opacity: 1 } },
    data: totals.map((total) => [planningInstant(total.month), total.value]),
    label: {
      show: true,
      position: "top",
      color: palette.text,
      formatter: (point) => {
        const [, value] = pointOf(point.value);
        return typeof value === "string" ? amount(value) : "";
      },
    },
  };
}

/** The `[instant, value]` a point of a series holds, as ECharts hands it back; nothing otherwise. */
function pointOf(value: unknown): readonly unknown[] {
  return Array.isArray(value) ? value : [];
}

/**
 * The tooltip of a month: the month, then each role and its hours, in the language of the
 * interface. It lists the roles loaded that month only — each named, the dot of its colour beside
 * it: the tooltip tells the roles apart without the patterns.
 * The total of the month comes under them when the chart draws it. The month under the pointer
 * is shaded in the tone of the grid.
 */
export function monthTooltip(
  palette: ChartPalette,
  locale: Locale,
  unit: (value: string) => string,
  amount: (value: string) => string = (value) => formatDecimal(value, locale),
): TooltipComponentOption {
  return {
    trigger: "axis",
    axisPointer: { type: "shadow", shadowStyle: { color: palette.grid, opacity: 0.5 } },
    formatter: (params) => {
      const rows = Array.isArray(params) ? params : [params];
      // The month is the instant the first point holds, `2026-06-01T00:00:00Z`.
      const [instant] = pointOf(rows[0]?.value);
      const month = typeof instant === "string" ? formatMonth(instant.slice(0, 7), locale) : "";
      // A role without load that month holds an empty point: it is not listed.
      const loaded = rows.filter((row) => pointOf(row.value)[1] !== EMPTY);
      const lines = loaded.map((row) => {
        const [, value] = pointOf(row.value);
        const marker = typeof row.marker === "string" ? row.marker : "";
        const shown = typeof value === "string" ? amount(value) : "";
        return `${marker}${escapeHtml(row.seriesName ?? "")} <b>${escapeHtml(unit(shown))}</b>`;
      });
      return [`<b>${escapeHtml(month)}</b>`, ...lines].join("<br/>");
    },
  };
}
