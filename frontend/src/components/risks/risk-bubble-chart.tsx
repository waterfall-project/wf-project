// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The risk matrix as a bubble chart (WF-RIS-0040, US-0550), shared by the screen of the risks of a
 * project and by the risks of the portfolio: the probability across, the severity — in percent of
 * the assessed base of the project — up, each risk a bubble at its exact values, as large as its
 * severity in amount (bounded), on the sixteen zones of the matrix. Every number is the server's:
 * the position of a bubble is the probability and the severity ratio of its point, its zone the one
 * the server classes (`zone`), the count of the cells the server's (`cells`, the table under the
 * chart); the front only lays out, it computes and classes nothing (WF-ARC-0020). A zone is told
 * apart without its colour (WF-IHM-0100, WF-IHM-0070): it is named in its area, and its sides have
 * a stroke of its own; a state of a risk, by the shape of its bubble. A tooltip tells a bubble in
 * words; a click leads to the risk, or to its project in the portfolio. The chart is exported as a
 * PNG image with its provenance (WF-IHM-0130). No bubble is reached from the keyboard: the grid of
 * the risks, on the same screen, gives the keyboard the same data, and the axes stay linear, at
 * the exact values (#1253). A project's chart starts folded, to keep its grid in the window (#1252).
 */
"use client";

import type { MarkAreaComponentOption, MarkLineComponentOption } from "echarts/components";
import { usePathname, useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useCallback, useMemo } from "react";

import type { components } from "@/api/generated/schema";
import {
  Chart,
  type ChartExport,
  type ChartOption,
  type ChartPalette,
  type ChartProvenance,
  dataId,
  escapeHtml,
  useProvenance,
} from "@/components/chart/chart";
import { usePendingAddress } from "@/components/grid/pending-address";
import { formatMoney, formatPercent, formatLocale } from "@/i18n/format";
import type { PortfolioScope } from "@/components/portfolio/address";
import { usePortfolioExport } from "@/components/portfolio/provenance";

import { riskHref, type RiskState } from "./address";
import { type RiskMatrix, RiskCountsTable } from "./risk-matrix";

type Point = components["schemas"]["RiskMatrixPoint"];
type Level = components["schemas"]["RiskMatrixLevel"];
type AlertZone = components["schemas"]["AlertZone"];

/** A zone of the matrix: the corner it starts at, with its look, and the corner it ends at. */
type Area = Extract<NonNullable<MarkAreaComponentOption["data"]>[number], readonly unknown[]>;

/** A side of a zone: the corner it starts at, with its stroke, and the corner it ends at. */
type Edge = Extract<NonNullable<MarkLineComponentOption["data"]>[number], readonly unknown[]>;

/** The rank of the colour and the shape of the bubbles of each state of a risk. */
const STATE_STYLE: Readonly<
  Record<RiskState, { readonly rank: number; readonly symbol: "circle" | "diamond" | "triangle" }>
> = {
  identified: { rank: 0, symbol: "circle" },
  occurred: { rank: 1, symbol: "diamond" },
  dismissed: { rank: 2, symbol: "triangle" },
};

/** The stroke of the sides of each zone, a second mark of the zone beside its name. */
const ZONE_STROKE: Readonly<Record<AlertZone, "solid" | "dashed" | "dotted">> = {
  nominal: "solid",
  watch: "dashed",
  alert: "dotted",
};

/** The smallest and the largest bubble, in pixels: a severity in amount sets the size within. */
const BUBBLE = { smallest: 12, largest: 40 } as const;

/** How much of the area of a zone its colour fills: the bubbles stay legible over it. */
const ZONE_OPACITY = 0.18;

/**
 * The least share of the height of the chart a zone takes to be named in its area: a thinner band
 * has no room for a line of text, and its stroke and its signal in the table still tell it.
 */
const LABELLED = 0.08;

/** Whether a number laid out is one that can be read (neither `NaN` nor infinite). */
function isReadable(value: number): boolean {
  return Number.isFinite(value);
}

/** The size of the bubble of a severity in amount, the largest shown being the largest bubble. */
function bubbleSize(amount: string, largest: number): number {
  if (largest <= 0) {
    return BUBBLE.smallest;
  }
  // Layout: a size in pixels, not a figure; an amount that cannot be read draws the smallest.
  const ratio = Number(amount) / largest;
  const share = Number.isFinite(ratio) ? Math.min(1, Math.max(0, ratio)) : 0;
  return BUBBLE.smallest + (BUBBLE.largest - BUBBLE.smallest) * Math.sqrt(share);
}

/** The bounds of a level on an axis that ends at `top`: its lower bound, its upper one or `top`. */
function span({ lower, upper }: Level, top: number): readonly [number, number] {
  return [Number(lower), upper === null ? top : Number(upper)];
}

/** The ticks of an axis: the lower bound of each level. */
function ticks(levels: readonly Level[]): number[] {
  return levels.map(({ lower }) => Number(lower));
}

/** The risks the chart draws: those in the states asked, every one when none is. */
function shownPoints(points: readonly Point[], states: readonly RiskState[]): readonly Point[] {
  return states.length === 0 ? points : points.filter(({ state }) => states.includes(state));
}

/** The states of the portfolio matrix: the server filters it, so that none is asked here. */
const EVERY_STATE: readonly RiskState[] = [];

/** What the bubble chart draws, and what a click on a bubble does. */
export interface RiskBubbleChartProps {
  /** The matrix, as the contract gives it: its levels, its cells and its points. */
  readonly matrix: RiskMatrix;
  /** The states of the risks drawn; every state when empty. */
  readonly states: readonly RiskState[];
  /** What the exported image says of itself. */
  readonly exported: () => ChartExport;
  /** Called with the point of the bubble clicked. */
  readonly onOpen: (point: Point) => void;
  /** Whether the drawing starts folded, to keep the grid of the screen in its window. */
  readonly folded?: boolean;
}

/** Render the bubble chart of the matrix, and under it the count of its cells. */
export function RiskBubbleChart({
  matrix,
  states,
  exported,
  onOpen,
  folded = false,
}: RiskBubbleChartProps) {
  const t = useTranslations();
  const locale = useLocale();
  const points = useMemo(() => shownPoints(matrix.points, states), [matrix.points, states]);
  const open = useCallback(
    (id: string) => {
      const point = points.find((each) => each.risk_id === id);
      if (point !== undefined) {
        onOpen(point);
      }
    },
    [points, onOpen],
  );

  const option = useCallback(
    (palette: ChartPalette): ChartOption => {
      const percent = new Intl.NumberFormat(formatLocale(locale), {
        style: "percent",
        maximumFractionDigits: 2,
      });
      const lastSeverity = matrix.severity_levels.at(-1);
      // The axes reach the end of the last level, which ECharts does not do for an area: the last
      // level is unbounded, and is drawn up to a bit above the highest bubble of the matrix — all
      // the states, so that the zones and their names stay where they are whatever the filter.
      // `Number` is for this layout alone, never for a value drawn; a ratio that cannot be read
      // leaves the axis alone.
      const top = Math.max(
        Number(lastSeverity?.lower ?? 0) * 1.5,
        ...matrix.points.map((point) => Number(point.severity_ratio) * 1.15).filter(isReadable),
      );
      const right = 1;
      const zones = matrix.cells.flatMap((cell) => {
        const across = matrix.probability_levels.find(
          ({ level }) => level === cell.probability_level,
        );
        const up = matrix.severity_levels.find(({ level }) => level === cell.severity_level);
        if (across === undefined || up === undefined) {
          return [];
        }
        const [left, over] = span(across, right);
        const [bottom, high] = span(up, top);
        const colour = palette.zones[cell.zone];
        const name = t(`enums.AlertZone.${cell.zone}`);
        const area: Area = [
          {
            name,
            xAxis: left,
            yAxis: bottom,
            itemStyle: {
              color: colour,
              opacity: ZONE_OPACITY,
            },
            label: {
              show: (high - bottom) / top >= LABELLED,
              color: palette.text,
              fontFamily: palette.font,
              fontSize: 11,
              position: "insideTopLeft" as const,
            },
          },
          { xAxis: over, yAxis: high },
        ];
        // The stroke of a zone is drawn on its left side and its lower side: a side shared by two
        // zones is drawn once, by the zone it is the left or the lower side of, and never as the
        // superposition of two strokes. The zones of the last column and of the last row also draw
        // their right side and their upper side, which are the outer ones of the matrix.
        const style = { color: colour, width: 1, type: ZONE_STROKE[cell.zone] };
        const edges: Edge[] = [
          [{ name, coord: [left, bottom], lineStyle: style }, { coord: [left, high] }],
          [{ name, coord: [left, bottom], lineStyle: style }, { coord: [over, bottom] }],
          ...(over === right
            ? [[{ name, coord: [over, bottom], lineStyle: style }, { coord: [over, high] }] as Edge]
            : []),
          ...(high === top
            ? [[{ name, coord: [left, high], lineStyle: style }, { coord: [over, high] }] as Edge]
            : []),
        ];
        return [{ area, edges }];
      });
      const areas = zones.map(({ area }) => area);
      const edges = zones.flatMap((zone) => zone.edges);
      // Layout again: the size of the bubbles, from the severities in amount that can be read.
      const largest = Math.max(
        0,
        ...points.map((point) => Number(point.severity_amount)).filter(isReadable),
      );
      const present = (Object.keys(STATE_STYLE) as RiskState[]).filter((state) =>
        points.some((point) => point.state === state),
      );
      const stateName = (state: RiskState) => t(`enums.RiskState.${state}`);
      return {
        textStyle: { fontFamily: palette.font, color: palette.text },
        legend: { top: 0, textStyle: { color: palette.text }, data: present.map(stateName) },
        grid: { left: 76, right: 24, top: 36, bottom: 44 },
        xAxis: {
          type: "value",
          min: 0,
          max: right,
          name: t("risks.matrix.probability"),
          nameLocation: "middle",
          nameGap: 28,
          nameTextStyle: { color: palette.text },
          axisLine: { show: true, lineStyle: { color: palette.axis } },
          axisTick: { customValues: ticks(matrix.probability_levels) },
          axisLabel: {
            color: palette.text,
            hideOverlap: true,
            customValues: ticks(matrix.probability_levels),
            formatter: (value: number) => percent.format(value),
          },
          splitLine: { show: false },
        },
        yAxis: {
          type: "value",
          min: 0,
          max: top,
          name: t("risks.matrix.axisSeverity"),
          nameLocation: "middle",
          nameGap: 54,
          nameTextStyle: { color: palette.text },
          axisLine: { show: true, lineStyle: { color: palette.axis } },
          axisTick: { customValues: ticks(matrix.severity_levels) },
          axisLabel: {
            color: palette.text,
            hideOverlap: true,
            customValues: ticks(matrix.severity_levels),
            formatter: (value: number) => percent.format(value),
          },
          splitLine: { show: false },
        },
        tooltip: {
          trigger: "item",
          confine: true,
          formatter: (params) => {
            const each = Array.isArray(params) ? params[0] : params;
            const point = points.find(({ risk_id: id }) => id === dataId(each?.data));
            if (point === undefined) {
              return "";
            }
            const line = (name: string, value: string) =>
              `${escapeHtml(name)} : ${escapeHtml(value)}`;
            return [
              `<b>${escapeHtml(point.label)}</b>`,
              ...(point.project_label === undefined
                ? []
                : [line(t("risks.matrix.tooltip.project"), point.project_label)]),
              line(t("risks.matrix.tooltip.probability"), formatPercent(point.probability, locale)),
              line(
                t("risks.matrix.tooltip.severity"),
                `${formatMoney(point.severity_amount, locale)} (${formatPercent(point.severity_ratio, locale)})`,
              ),
              line(
                t("risks.matrix.tooltip.provision"),
                formatMoney(point.provision_amount, locale),
              ),
              line(t("risks.matrix.tooltip.state"), stateName(point.state)),
              line(t("risks.matrix.tooltip.zone"), t(`enums.AlertZone.${point.zone}`)),
              ...(point.can_open === false ? [escapeHtml(t("risks.matrix.tooltip.closed"))] : []),
            ].join("<br/>");
          },
        },
        series: [
          {
            // The sixteen zones are the marked areas of a series of their own, without a point and
            // out of the legend: only its areas are drawn, under the bubbles.
            type: "scatter" as const,
            silent: true,
            data: [],
            markArea: { silent: true, data: areas },
            markLine: { silent: true, symbol: "none", label: { show: false }, data: edges },
          },
          ...present.map((state) => ({
            type: "scatter" as const,
            name: stateName(state),
            color: palette.series[STATE_STYLE[state].rank] ?? palette.mark,
            symbol: STATE_STYLE[state].symbol,
            itemStyle: { borderColor: palette.mark, borderWidth: 1, opacity: 0.85 },
            z: 3,
            data: points
              .filter((point) => point.state === state)
              .map((point) => ({
                id: point.risk_id,
                name: point.label,
                // The strings of the API as they are: ECharts reads the position from them.
                value: [point.probability, point.severity_ratio],
                symbolSize: bubbleSize(point.severity_amount, largest),
              })),
          })),
        ],
      };
    },
    [matrix, points, locale, t],
  );

  return (
    <Chart
      title={t("risks.matrix.title")}
      description={t("risks.matrix.description")}
      note={
        points.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("risks.matrix.none")}</p>
        ) : undefined
      }
      option={option}
      exported={exported}
      onPoint={open}
      folded={folded}
    >
      <RiskCountsTable matrix={matrix} />
    </Chart>
  );
}

/** What the matrix of a project draws and says of itself. */
export interface ProjectRiskMatrixProps {
  readonly matrix: RiskMatrix;
  /** The states of the risks drawn, as the address filters them; every state when empty. */
  readonly states: readonly RiskState[];
  /** The project and the revision the matrix is computed on, which the exported image names. */
  readonly provenance: ChartProvenance;
  /** The instant the revision is computed at (`context.computed_at`). */
  readonly computedAt: string;
}

/** Render the matrix of the risks of a project: a bubble opens the detail of its risk. */
export function ProjectRiskMatrix({
  matrix,
  states,
  provenance,
  computedAt,
}: ProjectRiskMatrixProps) {
  const t = useTranslations("risks.matrix");
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const exported = useProvenance(provenance, t("title"), computedAt, t("file"));
  return (
    <RiskBubbleChart
      matrix={matrix}
      states={states}
      exported={exported}
      folded
      onOpen={(point) => {
        request((query) => riskHref(pathname, query, point.risk_id));
      }}
    />
  );
}

/** Render the matrix of the risks of the portfolio: a bubble opens the project of its risk. */
export function PortfolioRiskMatrix({
  matrix,
  scope,
}: {
  readonly matrix: RiskMatrix;
  readonly scope: PortfolioScope;
}) {
  const t = useTranslations("risks.matrix");
  const router = useRouter();
  const exported = usePortfolioExport(scope, t("title"), t("file"));
  return (
    <RiskBubbleChart
      matrix={matrix}
      states={EVERY_STATE}
      exported={exported}
      onOpen={(point) => {
        // A project the caller cannot open is named by the bubble, and not opened (WF-PTF-0030).
        if (point.can_open === true && point.project_id !== undefined) {
          router.push(`/projects/${point.project_id}`);
        }
      }}
    />
  );
}
