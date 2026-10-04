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
 * The curves are told apart without their colour too: each is named at its end (`curve`).
 *
 * A chart may be exported as a PNG image (WF-IHM-0130): drawn anew by an instance out of the
 * screen, on a canvas — an SVG is no PNG —, at a size of its own, with its title and the
 * provenance its caller names, on the background of the charter.
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
  TitleComponent,
  type TitleComponentOption,
} from "echarts/components";
import { type ComposeOption, init, use as register } from "echarts/core";
import { LabelLayout } from "echarts/features";
import { CanvasRenderer, SVGRenderer } from "echarts/renderers";
import { ImageDown } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { type ReactNode, useEffect, useId, useRef } from "react";

import { Button } from "@/components/ui/button";
import { formatTimestamp } from "@/i18n/format";

register([
  LabelLayout,
  LineChart,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TitleComponent,
  AriaComponent,
  SVGRenderer,
  CanvasRenderer,
]);

/** What a chart of the application may draw: lines on a grid, a legend, marked lines, a title. */
export type ChartOption = ComposeOption<
  | LineSeriesOption
  | GridComponentOption
  | LegendComponentOption
  | MarkLineComponentOption
  | TitleComponentOption
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
  /** The background of the page, which an exported image is drawn on: `--background`. */
  readonly background: string;
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
  background: "text-background",
} as const;

/** The symbols of the series, in their order: a series is told apart without its colour. */
const SERIES_SYMBOLS = ["circle", "triangle", "rect", "diamond"] as const;

/** The strokes of the series, once their symbols have all been taken, for the same reason. */
const SERIES_STROKES = ["solid", "dashed", "dotted"] as const;

/** The width the name at the end of a curve takes at most, beyond which it is cut short. */
export const END_LABEL_WIDTH = 128;

/** A point a curve leaves out: a value the API could not compute is a gap, never a zero. */
export const GAP = "-";

/** The points of a curve: the instant or the category, and the value as the API wrote it. */
export type CurvePoints = readonly (readonly [string, string])[];

/**
 * A curve of a rank, its points and how it is drawn: named at the end of its curve — its last drawn
 * point —, by its own name, which tells any number of series apart where a legend of one entry per
 * series or a palette of four colours could not, the names of curves that end close moved apart;
 * then its colour, its symbol and its stroke, in turn, which help the eye from one point to the
 * next. A curve without a drawn point bears no name — ECharts would place it nowhere, and stop
 * moving the others apart —: its table of values still lists it.
 */
export function curve(palette: ChartPalette, rank: number, points: CurvePoints) {
  const symbols = SERIES_SYMBOLS.length;
  const drawn = points.some(([, value]) => value !== GAP);
  return {
    type: "line" as const,
    data: points.map((point) => [...point]),
    color: palette.series[rank % palette.series.length] ?? palette.mark,
    symbol: SERIES_SYMBOLS[rank % symbols] ?? "circle",
    symbolSize: 8,
    lineStyle: {
      type: SERIES_STROKES[Math.floor(rank / symbols) % SERIES_STROKES.length] ?? "solid",
    },
    endLabel: {
      show: drawn,
      formatter: "{a}",
      width: END_LABEL_WIDTH,
      overflow: "truncate" as const,
      // The height of a line of the page's font, which ECharts would measure shorter: two names
      // moved apart would still touch.
      lineHeight: 16,
    },
    labelLayout: { moveOverlap: "shiftY" as const },
  };
}

/**
 * A date of planning (`2026-04-24`) or a month (`2026-04`) as an instant of an axis of time: its
 * midnight in UTC, so that no time zone moves it a day — its axis is written in UTC (`timeAxis`).
 */
export function planningInstant(date: string): string {
  return date.length === 7 ? `${date}-01T00:00:00Z` : `${date}T00:00:00Z`;
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
    background: colour("background"),
    font: getComputedStyle(probes).fontFamily,
  };
}

/** How the ticks of an axis of time are written: the month and the year, in the language given. */
const MONTH: Intl.DateTimeFormatOptions = { month: "short", year: "numeric" };

/**
 * The shortest span between two ticks of an axis of time, in milliseconds: four weeks, so that two
 * ticks never fall in the same month, which their labels would write alike.
 */
const MONTH_SPAN = 28 * 24 * 60 * 60 * 1000;

/**
 * An axis of time, its ticks written in the language of the interface by month — in UTC for an
 * axis of dates of planning, which have no time zone (`utc`), in the local time of the
 * workstation otherwise —, a tick that would overlap another left out. ECharts places the ticks
 * at the first of each month in the local time of the workstation, unless the option of the chart
 * says `useUTC`: a chart with an axis in UTC says it, or its ticks, written in UTC, would name the
 * month before east of Greenwich.
 */
export function timeAxis(palette: ChartPalette, locale: string, utc = false) {
  const format = new Intl.DateTimeFormat(locale, utc ? { ...MONTH, timeZone: "UTC" } : MONTH);
  return {
    type: "time" as const,
    minInterval: MONTH_SPAN,
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
  const singles = (["text", "mark", "axis", "grid", "background"] as const).map((name) => (
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

/** What an exported image says of itself, and the name of its file. */
export interface ChartExport {
  /** The title drawn at the head of the image. */
  readonly title: string;
  /** What the image says under its title: where it comes from, the date it is computed at. */
  readonly subtitle: string;
  /** The name of the file, its extension `.png` included. */
  readonly fileName: string;
}

/** Where a chart comes from, which its exported image names (WF-IHM-0130). */
export interface ChartProvenance {
  /** The name of the project. */
  readonly project: string;
  /** The code of the project, which names the file; its identifier when it has none. */
  readonly code: string;
  /** The name of the revision the chart is computed on. */
  readonly revision: string;
}

/**
 * What the exported image of a chart says of itself: its title and the project, then the
 * revision and the date of calculation — written in the local time of the workstation, at the
 * moment of the export —, and the name of its file, `file` followed by the code of the project.
 */
export function useProvenance(
  provenance: ChartProvenance,
  title: string,
  computedAt: string,
  file: string,
): () => ChartExport {
  const t = useTranslations("chart");
  const locale = useLocale();
  return () => ({
    title: t("exportTitle", { title, project: provenance.project }),
    subtitle: t("exportSubtitle", {
      revision: provenance.revision,
      date: formatTimestamp(computedAt, locale),
    }),
    fileName: t("fileName", { file, code: provenance.code }),
  });
}

/** The size of an exported image, whatever the size of the screen. */
const EXPORT_SIZE = { width: 1280, height: 720 } as const;

/** The height the title of an exported image takes above the chart, in pixels. */
const EXPORT_HEADER = 64;

/** A component of an option moved down by the height of the title, if it says where its top is. */
function below<T>(component: T): T {
  if (typeof component !== "object" || component === null || Array.isArray(component)) {
    return component;
  }
  const top = "top" in component && typeof component.top === "number" ? component.top : 0;
  return { ...component, top: top + EXPORT_HEADER };
}

/**
 * Export a chart as a PNG image, whose file the browser saves: drawn by an instance out of the
 * screen, on a canvas, at the size of an image rather than of the screen, its title and its
 * provenance at its head, its legend and its series as on the screen, on the background of the
 * charter; the instance is released once the image is taken.
 */
export function exportPng(option: ChartOption, palette: ChartPalette, image: ChartExport) {
  const host = document.createElement("div");
  host.style.position = "fixed";
  host.style.left = `-${String(EXPORT_SIZE.width * 2)}px`;
  host.style.top = "0";
  host.style.width = `${String(EXPORT_SIZE.width)}px`;
  host.style.height = `${String(EXPORT_SIZE.height)}px`;
  document.body.append(host);
  const chart = init(host, null, { renderer: "canvas", ...EXPORT_SIZE });
  try {
    chart.setOption({
      ...option,
      ...inertLegend(option.legend === undefined ? undefined : below(option.legend)),
      grid: below(option.grid),
      title: {
        text: image.title,
        subtext: image.subtitle,
        left: 16,
        top: 12,
        textStyle: { color: palette.mark, fontFamily: palette.font, fontSize: 18 },
        subtextStyle: { color: palette.text, fontFamily: palette.font },
      },
      backgroundColor: palette.background,
      animation: false,
    });
    const link = document.createElement("a");
    link.href = chart.getDataURL({
      type: "png",
      pixelRatio: 2,
      backgroundColor: palette.background,
    });
    link.download = image.fileName;
    link.click();
  } finally {
    chart.dispose();
    host.remove();
  }
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
  /**
   * What the image of the chart says of itself, read when it is exported — in the browser, so
   * that a date is written in the local time of the workstation —; without it, the chart is not
   * offered for export.
   */
  readonly exported?: () => ChartExport;
}

/** Render a chart: a figure, its caption, its drawing named by a sentence, its values. */
export function Chart({ title, description, note, option, children, exported }: ChartProps) {
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
          // The charter has no animation: a chart is drawn at once, in its final state.
          animation: false,
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

  const exportImage = () => {
    const tokens = probes.current;
    if (exported !== undefined && tokens !== null) {
      const palette = readPalette(tokens);
      exportPng(option(palette), palette, exported());
    }
  };

  return (
    <figure aria-labelledby={caption} className="space-y-2">
      {/* The figure is named by its title alone, not by the command beside it. */}
      <figcaption className="flex flex-wrap items-start justify-between gap-2">
        <span id={caption} className="font-medium">
          {title}
        </span>
        {exported === undefined ? null : (
          <Button type="button" variant="outline" size="sm" onClick={exportImage}>
            <ImageDown aria-hidden="true" />
            {t("exportPng")}
          </Button>
        )}
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
