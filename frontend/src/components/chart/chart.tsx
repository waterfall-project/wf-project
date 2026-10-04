// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The one envelope of the charts of the application (PBS-1.3, EP-02 « Courbes »): Apache
 * ECharts, imported piece by piece and drawn in SVG, its option `aria` on. A chart is a
 * figure: its caption names it; the drawing is an image whose name says what it shows, in a
 * sentence of the catalogue; and its values are a table under it — the text alternative a
 * reader of the screen, a keyboard, a printed page can read (§3.6). Whatever a chart shows is
 * the API's: the series it is handed are drawn as they come, nothing summed, averaged nor
 * ordered here (WF-ARC-0020).
 *
 * ECharts writes its colours into the attributes of its SVG, where a variable of CSS does not
 * reach: the colours of a chart are those of the tokens of the charter (`--chart-1`…), read
 * from the document as it shows them — each token is the colour of a hidden probe, which the
 * browser resolves in the mode the page is in. A change of mode — the workstation's, or the
 * one the account forces (`data-theme`) — draws the chart again in the colours of the new one.
 * The series are told apart without their colour too, by their symbol and their stroke.
 */
"use client";

import { LineChart, type LineSeriesOption } from "echarts/charts";
import {
  AriaComponent,
  type AriaComponentOption,
  GridComponent,
  type GridComponentOption,
  LegendComponent,
  type LegendComponentOption,
  MarkLineComponent,
  type MarkLineComponentOption,
} from "echarts/components";
import { type ComposeOption, init, use as register } from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import { useTranslations } from "next-intl";
import { type ReactNode, useEffect, useId, useRef } from "react";

register([
  LineChart,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  AriaComponent,
  SVGRenderer,
]);

/** What a chart of the application may draw: lines on a grid, a legend, marked lines. */
export type ChartOption = ComposeOption<
  | LineSeriesOption
  | GridComponentOption
  | LegendComponentOption
  | MarkLineComponentOption
  | AriaComponentOption
>;

/** The colours and the font of a chart, as the document shows the tokens of the charter. */
export interface ChartPalette {
  /** The colours of the series, in their order: `--chart-1` to `--chart-4`. */
  readonly series: readonly string[];
  /** The text of the axes and of the legend: `--muted-foreground`. */
  readonly text: string;
  /** What a chart marks: a threshold, a diagonal — `--foreground`. */
  readonly mark: string;
  /** The lines of the axes, which show where a value is read: `--input`, at 3:1. */
  readonly axis: string;
  /** The lines that only separate: `--border`. */
  readonly grid: string;
  /** The font of the page. */
  readonly font: string;
}

/** The token of each colour of the palette, as the class that paints a probe with it. */
const PROBES = {
  series: ["text-chart-1", "text-chart-2", "text-chart-3", "text-chart-4"],
  text: "text-muted-foreground",
  mark: "text-foreground",
  axis: "text-input",
  grid: "text-border",
} as const;

/** The symbols of the series, in their order: a series is told apart without its colour. */
const SERIES_SYMBOLS = ["circle", "triangle", "rect", "diamond"] as const;

/** The strokes of the series, once their symbols have all been taken, for the same reason. */
const SERIES_STROKES = ["solid", "dashed", "dotted"] as const;

/**
 * How the series of a rank is drawn: its colour, its symbol and its stroke — the colours and the
 * symbols in turn, the stroke changing each time the symbols come round again, so that twelve
 * series are told apart without their colour.
 */
export function seriesLook(palette: ChartPalette, rank: number) {
  const symbols = SERIES_SYMBOLS.length;
  return {
    color: palette.series[rank % palette.series.length] ?? palette.mark,
    symbol: SERIES_SYMBOLS[rank % symbols] ?? "circle",
    symbolSize: 8,
    lineStyle: {
      type: SERIES_STROKES[Math.floor(rank / symbols) % SERIES_STROKES.length] ?? "solid",
    },
  };
}

/** Read the palette from the probes, as the document shows them now. */
function readPalette(probes: HTMLElement): ChartPalette {
  const colour = (name: string) => {
    const probe = probes.querySelector(`[data-probe="${name}"]`);
    return probe === null ? "" : getComputedStyle(probe).color;
  };
  return {
    series: PROBES.series.map((_, index) => colour(`series-${index.toString()}`)),
    text: colour("text"),
    mark: colour("mark"),
    axis: colour("axis"),
    grid: colour("grid"),
    font: getComputedStyle(probes).fontFamily,
  };
}

/** How the ticks of an axis of time are written: the month and the year, in the language given. */
const MONTH: Intl.DateTimeFormatOptions = { month: "short", year: "numeric" };

/**
 * An axis of time, its ticks written in the language of the interface by month, in the local time
 * of the workstation, a tick that would overlap another left out.
 */
export function timeAxis(palette: ChartPalette, locale: string) {
  const format = new Intl.DateTimeFormat(locale, MONTH);
  return {
    type: "time" as const,
    axisLine: { show: true, lineStyle: { color: palette.axis } },
    axisLabel: {
      color: palette.text,
      hideOverlap: true,
      formatter: (value: number) => format.format(value),
    },
    splitLine: { lineStyle: { color: palette.grid } },
  };
}

/** The probes of the tokens, hidden: each takes the colour of one. */
function Probes() {
  const singles = (["text", "mark", "axis", "grid"] as const).map((name) => (
    <span key={name} data-probe={name} className={PROBES[name]} />
  ));
  return (
    <>
      {PROBES.series.map((tone, index) => (
        <span key={tone} data-probe={`series-${index.toString()}`} className={tone} />
      ))}
      {singles}
    </>
  );
}

/**
 * The legend of an option, its entries made inert: a click on one would hide its series with the
 * pointer alone, out of reach of the keyboard (WF-IHM-0100), and a reader would no longer see
 * what the API gave.
 */
function inertLegend(legend: ChartOption["legend"]): Pick<ChartOption, "legend"> {
  if (legend === undefined) {
    return {};
  }
  const inert = (each: LegendComponentOption) => ({ ...each, selectedMode: false });
  return { legend: Array.isArray(legend) ? legend.map(inert) : inert(legend) };
}

/** A chart: its name, what it shows in a sentence, how it is drawn, and its values. */
export interface ChartProps {
  /** The name of the chart, the caption of its figure. */
  readonly title: string;
  /** What the chart shows, in a sentence: the name of its image (text alternative). */
  readonly description: string;
  /** What the figure says under its caption: the date its values are computed at. */
  readonly note?: ReactNode;
  /**
   * The option of the chart in a palette — memoised by the caller: a new function draws the
   * chart anew.
   */
  readonly option: (palette: ChartPalette) => ChartOption;
  /** The values of the chart, as a table: shown on demand under the drawing. */
  readonly children: ReactNode;
}

/** Render a chart: a figure, its caption, its drawing named by a sentence, its values. */
export function Chart({ title, description, note, option, children }: ChartProps) {
  const t = useTranslations("chart");
  const drawing = useRef<HTMLDivElement>(null);
  const probes = useRef<HTMLSpanElement>(null);
  const caption = useId();

  useEffect(() => {
    const element = drawing.current;
    const tokens = probes.current;
    if (element === null || tokens === null) {
      return undefined;
    }
    const chart = init(element, null, { renderer: "svg" });
    const draw = () => {
      const chosen = option(readPalette(tokens));
      chart.setOption(
        {
          ...chosen,
          ...inertLegend(chosen.legend),
          aria: { enabled: true, label: { description } },
        },
        true,
      );
    };
    draw();
    const scheme = window.matchMedia("(prefers-color-scheme: dark)");
    scheme.addEventListener("change", draw);
    const theme = new MutationObserver(draw);
    theme.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    const size = new ResizeObserver(() => {
      chart.resize();
    });
    size.observe(element);
    return () => {
      size.disconnect();
      theme.disconnect();
      scheme.removeEventListener("change", draw);
      chart.dispose();
    };
  }, [option, description]);

  return (
    <figure aria-labelledby={caption} className="space-y-2">
      <figcaption id={caption} className="font-medium">
        {title}
      </figcaption>
      {note}
      <span ref={probes} hidden>
        <Probes />
      </span>
      <div ref={drawing} role="img" aria-label={description} className="h-72 w-full" />
      <details className="text-sm">
        <summary className="cursor-pointer text-muted-foreground">{t("values")}</summary>
        <div className="mt-2 overflow-x-auto">{children}</div>
      </details>
    </figure>
  );
}
