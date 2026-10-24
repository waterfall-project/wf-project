// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The Gantt exported as a PNG image (WF-IHM-0130, US-0530): its whole extent at the level shown —
 * the width of its drawing zoomed, that of its column fitted to the project —, drawn anew on a
 * canvas as its cells draw it in SVG — the axis of two rows, the days off hatched (`DAY_OFF_HATCH`,
 * `dayOffBands`), the months, the links, the bars —, a row for each task the grid shows, folded as
 * it is. Its title and its provenance at its head, as every exported chart has them
 * (`useProvenance`), the legend of the days off under it when the Gantt tints them, on the
 * background of the charter, in the colours the document shows.
 *
 * A canvas has bounds that browsers do not pass (`CANVAS_LIMITS`): the image is drawn twice as
 * dense as the screen when it holds in them, as dense as the screen otherwise, and not at all when
 * even that does not hold — the command then says why (`ganttOverflow`).
 */
"use client";

import {
  type ChartExport,
  type ChartPalette,
  EXPORT_MARGINS,
  EXPORT_SUBTITLE,
  EXPORT_TITLE,
  readPalette,
  wrapLines,
} from "@/components/chart/chart";

import { DAY_OFF_HATCH, type DayOffBand, dayOffBands } from "./days-off";
import type { GanttBar, GanttLayout, GanttLinkPart, GanttRow } from "./layout";

/** The height of a row and of the axis, as the grid draws them, in pixels. */
const ROW = 28;
const AXIS = 36;

/** The margin around the drawing, the height of the legend, and the narrowest image. */
const MARGIN = 16;
const LEGEND = 24;
const NARROWEST = 640;

/** The room the head of an image takes at most, when it is judged before it is written. */
const HEAD_ROOM = 120;

/**
 * The largest canvas Chromium, Firefox and Safari draw: 32 767 pixels a side, 16 384 squared in
 * all. Beyond, the canvas stays blank, and the image would be empty.
 */
const CANVAS_LIMITS = { side: 32_767, area: 268_435_456 } as const;

/** The names of the probes of the colours of the Gantt that a chart has not. */
export const GANTT_PROBES = {
  critical: "gantt-critical",
  primary: "gantt-primary",
  dayOff: "day-off",
  dayOffMark: "day-off-mark",
} as const;

/** The colours of the Gantt: those of a chart, the critical path, the bars, the days off. */
export interface GanttColours extends ChartPalette {
  readonly critical: string;
  readonly primary: string;
  readonly dayOff: string;
  readonly dayOffMark: string;
}

/**
 * Read the colours of the Gantt from its probes, as the document shows them now: the hatching of
 * the days off from the classes of its tokens (`DAY_OFF_HATCH`), its fill and its stroke.
 */
export function readGanttColours(probes: HTMLElement): GanttColours {
  const probe = (name: string) => {
    const found = probes.querySelector(`[data-probe="${name}"]`);
    return found === null ? undefined : getComputedStyle(found);
  };
  return {
    ...readPalette(probes),
    critical: probe(GANTT_PROBES.critical)?.color ?? "",
    primary: probe(GANTT_PROBES.primary)?.color ?? "",
    dayOff: probe(GANTT_PROBES.dayOff)?.fill ?? "",
    dayOffMark: probe(GANTT_PROBES.dayOffMark)?.stroke ?? "",
  };
}

/** A label of a row of the axis: where it stands on the drawing, and what it writes. */
export type AxisLabel = readonly [x: number, text: string];

/** What the image of the Gantt draws, as the Gantt shows it. */
export interface GanttDrawing {
  /** The rows of the tasks the grid shows, in its order: a row without task draws nothing. */
  readonly rows: readonly GanttRow[];
  readonly layout: GanttLayout;
  /** The width of the drawing at the level shown, in pixels. */
  readonly width: number;
  /** The boundaries of the lower and the upper row of the axis, in milliseconds. */
  readonly lower: readonly number[];
  readonly upper: readonly number[];
  readonly labels: { readonly upper: readonly AxisLabel[]; readonly lower: readonly AxisLabel[] };
  /** The width of a day, which says whether its days off are tinted. */
  readonly dayWidth: number;
  /** What the legend names the hatching; none, no day off is tinted. */
  readonly legend: string | undefined;
}

/** The size of the image over a drawing and a head of some height. */
function sizeOf(width: number, rows: number, legend: boolean, head: number) {
  return {
    width: Math.max(width + 2 * MARGIN, NARROWEST),
    height: head + AXIS + rows * ROW + (legend ? LEGEND : 0) + MARGIN,
  };
}

/** The bound of a canvas an image passes: its width, its height, or the area of both. */
export type GanttOverflow = "width" | "height" | "area";

/** The bound a canvas of a size, as dense as a ratio, passes in the browsers, if any. */
function overflowOf(
  size: { readonly width: number; readonly height: number },
  ratio: number,
): GanttOverflow | undefined {
  const [width, height] = [Math.ceil(size.width * ratio), Math.ceil(size.height * ratio)];
  if (width > CANVAS_LIMITS.side) {
    return "width";
  }
  if (height > CANVAS_LIMITS.side) {
    return "height";
  }
  return width * height > CANVAS_LIMITS.area ? "area" : undefined;
}

/**
 * The bound the image of a drawing so wide, of so many rows, passes at the density of the screen,
 * if any: the command says which, for the remedy differs — zoom out for the width, fold summaries
 * for the height. The head is judged at its usual height (`HEAD_ROOM`); the export measures it.
 */
export function ganttOverflow(
  width: number,
  rows: number,
  legend: boolean,
): GanttOverflow | undefined {
  return overflowOf(sizeOf(width, rows, legend, HEAD_ROOM), 1);
}

/** The hatching of the days off as a pattern of the canvas: the tile, its stroke, turned. */
function hatching(context: CanvasRenderingContext2D, colours: GanttColours) {
  const { size, stroke, rotation } = DAY_OFF_HATCH;
  const tile = document.createElement("canvas");
  tile.width = size;
  tile.height = size;
  const drawn = tile.getContext("2d");
  if (drawn === null) {
    return colours.dayOff;
  }
  drawn.fillStyle = colours.dayOff;
  drawn.fillRect(0, 0, size, size);
  drawn.strokeStyle = colours.dayOffMark;
  drawn.lineWidth = stroke;
  drawn.beginPath();
  drawn.moveTo(0, 0);
  drawn.lineTo(0, size);
  drawn.stroke();
  const pattern = context.createPattern(tile, "repeat");
  pattern?.setTransform(new DOMMatrix().rotateSelf(rotation));
  return pattern ?? colours.dayOff;
}

/** A straight line of the drawing. */
function line(context: CanvasRenderingContext2D, from: [number, number], to: [number, number]) {
  context.beginPath();
  context.moveTo(...from);
  context.lineTo(...to);
  context.stroke();
}

/** A closed shape of the drawing, filled. */
function polygon(context: CanvasRenderingContext2D, points: readonly (readonly number[])[]) {
  context.beginPath();
  for (const [x = 0, y = 0] of points) {
    context.lineTo(x, y);
  }
  context.closePath();
  context.fill();
}

/** The part of a link a row draws, as `LinkPart` draws it. */
function linkPart(
  context: CanvasRenderingContext2D,
  link: GanttLinkPart,
  x: (share: number) => number,
  top: number,
) {
  const out = x(link.out);
  const [from, to] = {
    leaves: link.down ? [0.5, 1] : [0, 0.5],
    passes: [0, 1],
    arrives: link.down ? [0, 0.5] : [0.5, 1],
  }[link.part];
  line(context, [out, top + (from ?? 0) * ROW], [out, top + (to ?? 1) * ROW]);
  if (link.part === "arrives") {
    const [end, middle] = [x(link.in), top + ROW / 2];
    line(context, [out, middle], [end, middle]);
    const back = link.in >= link.out ? -5 : 5;
    polygon(context, [
      [end + back, middle - 3],
      [end, middle],
      [end + back, middle + 3],
    ]);
  }
}

/** The bar of a task, as `Bar` draws it: a bracket, a diamond, a bar. */
function bar(
  context: CanvasRenderingContext2D,
  drawn: GanttBar,
  x: (share: number) => number,
  top: number,
  colours: GanttColours,
) {
  const [from, to] = [x(drawn.from), x(drawn.to)];
  if (drawn.nature === "summary") {
    context.fillStyle = colours.mark;
    context.fillRect(from, top + 0.3 * ROW, Math.max(to - from, 0), 0.2 * ROW);
    context.fillRect(from, top + 0.3 * ROW, 3, 0.45 * ROW);
    context.fillRect(to - 3, top + 0.3 * ROW, 3, 0.45 * ROW);
    return;
  }
  context.fillStyle = drawn.critical ? colours.critical : colours.background;
  context.strokeStyle = drawn.critical ? colours.critical : colours.primary;
  context.lineWidth = 1.5;
  const middle = top + ROW / 2;
  if (drawn.nature === "milestone") {
    polygon(context, [
      [to, middle - 6],
      [to + 6, middle],
      [to, middle + 6],
      [to - 6, middle],
    ]);
    context.stroke();
    return;
  }
  context.fillRect(from, top + 0.25 * ROW, Math.max(to - from, 0), 0.5 * ROW);
  context.strokeRect(from, top + 0.25 * ROW, Math.max(to - from, 0), 0.5 * ROW);
}

/** The axis of two rows, as `GanttAxis` draws it, its boundaries and its labels. */
function axis(
  context: CanvasRenderingContext2D,
  drawing: GanttDrawing,
  top: number,
  colours: GanttColours,
) {
  const x = (share: number) => MARGIN + share * drawing.width;
  context.strokeStyle = colours.grid;
  context.lineWidth = 1;
  for (const tick of drawing.upper.slice(1, -1)) {
    line(context, [x(drawing.layout.at(tick)), top], [x(drawing.layout.at(tick)), top + AXIS / 2]);
  }
  line(context, [MARGIN, top + AXIS / 2], [MARGIN + drawing.width, top + AXIS / 2]);
  line(context, [MARGIN, top + AXIS], [MARGIN + drawing.width, top + AXIS]);
  context.fillStyle = colours.text;
  context.font = `10px ${colours.font}`;
  for (const [row, y] of [
    [drawing.labels.upper, 0.4],
    [drawing.labels.lower, 0.88],
  ] as const) {
    for (const [at, text] of row) {
      context.fillText(text, MARGIN + at + 2, top + y * AXIS);
    }
  }
}

/** The rows of the tasks: their days off, the months across, the links, the bars. */
function tasks(
  context: CanvasRenderingContext2D,
  drawing: GanttDrawing,
  top: number,
  colours: GanttColours,
) {
  const { layout, rows } = drawing;
  const x = (share: number) => MARGIN + share * drawing.width;
  const extent = { from: layout.ticks[0] ?? 0, to: layout.ticks.at(-1) ?? 0 };
  const bottom = top + rows.length * ROW;
  if (drawing.legend !== undefined) {
    context.fillStyle = hatching(context, colours);
    // The same hours of a week give the same bands: walked once for each calendar of the export.
    const known = new Map<string, DayOffBand[]>();
    const bandsOf = (calendar: Parameters<typeof dayOffBands>[0]) => {
      const key = JSON.stringify(calendar ?? null);
      const found = known.get(key) ?? dayOffBands(calendar, extent, drawing.dayWidth);
      known.set(key, found);
      return found;
    };
    rows.forEach((row, index) => {
      for (const band of bandsOf(row.task?.calendar_hours)) {
        const from = x(layout.at(band.from));
        context.fillRect(from, top + index * ROW, x(layout.at(band.to)) - from, ROW);
      }
    });
  }
  context.strokeStyle = colours.grid;
  context.lineWidth = 1;
  for (const tick of drawing.lower) {
    line(context, [x(layout.at(tick)), top], [x(layout.at(tick)), bottom]);
  }
  rows.forEach((row, index) => {
    context.strokeStyle = colours.text;
    context.fillStyle = colours.text;
    context.lineWidth = 1;
    for (const part of layout.links(row.node_id)) {
      linkPart(context, part, x, top + index * ROW);
    }
    const drawn = layout.bar(row);
    if (drawn !== undefined) {
      bar(context, drawn, x, top + index * ROW, colours);
    }
  });
}

/** The legend of the days off, under the rows: the hatched tint, named. */
function legend(
  context: CanvasRenderingContext2D,
  text: string,
  top: number,
  colours: GanttColours,
) {
  context.fillStyle = hatching(context, colours);
  context.fillRect(MARGIN, top + 6, 20, 12);
  context.strokeStyle = colours.dayOffMark;
  context.lineWidth = 1;
  context.strokeRect(MARGIN, top + 6, 20, 12);
  context.fillStyle = colours.text;
  context.font = `${String(EXPORT_SUBTITLE.size)}px ${colours.font}`;
  context.fillText(text, MARGIN + 28, top + 16);
}

/** The head of the image: its title and its provenance in lines within its width, their height. */
function head(context: CanvasRenderingContext2D, image: ChartExport, width: number, font: string) {
  const within = (text: string, size: number) => {
    context.font = `${String(size)}px ${font}`;
    return wrapLines(text, width - 2 * MARGIN, (part) => context.measureText(part).width);
  };
  const title = within(image.title, EXPORT_TITLE.size);
  const subtitle = within(image.subtitle, EXPORT_SUBTITLE.size);
  const height =
    EXPORT_MARGINS.top +
    title.length * EXPORT_TITLE.line +
    EXPORT_MARGINS.gap +
    subtitle.length * EXPORT_SUBTITLE.line +
    EXPORT_MARGINS.bottom;
  return { title, subtitle, height };
}

/** Write the lines of a text from a height down, in a size and a colour. */
function lines(
  context: CanvasRenderingContext2D,
  written: readonly string[],
  top: number,
  size: { readonly size: number; readonly line: number },
  colour: string,
  font: string,
) {
  context.fillStyle = colour;
  context.font = `${String(size.size)}px ${font}`;
  written.forEach((text, index) => {
    context.fillText(text, MARGIN, top + (index + 1) * size.line - (size.line - size.size) / 2);
  });
}

/**
 * Export the Gantt as a PNG image, whose file the browser saves: drawn on a canvas out of the
 * document, as dense as its size allows, then released. Nothing is saved when the head
 * measured makes an image no canvas holds even as dense as the screen: the bound it passes is
 * returned, for the command to tell; "unsupported" when the document gives no canvas context.
 */
export function exportGanttPng(
  drawing: GanttDrawing,
  colours: GanttColours,
  image: ChartExport,
): GanttOverflow | "unsupported" | undefined {
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d");
  if (context === null) {
    return "unsupported";
  }
  const legendShown = drawing.legend !== undefined;
  const width = sizeOf(drawing.width, drawing.rows.length, legendShown, 0).width;
  const written = head(context, image, width, colours.font);
  const size = sizeOf(drawing.width, drawing.rows.length, legendShown, written.height);
  const passed = overflowOf(size, 1);
  if (passed !== undefined) {
    return passed;
  }
  const ratio = overflowOf(size, 2) === undefined ? 2 : 1;
  canvas.width = Math.ceil(size.width * ratio);
  canvas.height = Math.ceil(size.height * ratio);
  context.scale(ratio, ratio);
  context.fillStyle = colours.background;
  context.fillRect(0, 0, size.width, size.height);
  lines(context, written.title, EXPORT_MARGINS.top, EXPORT_TITLE, colours.mark, colours.font);
  lines(
    context,
    written.subtitle,
    EXPORT_MARGINS.top + written.title.length * EXPORT_TITLE.line + EXPORT_MARGINS.gap,
    EXPORT_SUBTITLE,
    colours.text,
    colours.font,
  );
  axis(context, drawing, written.height, colours);
  tasks(context, drawing, written.height + AXIS, colours);
  if (drawing.legend !== undefined) {
    legend(context, drawing.legend, written.height + AXIS + drawing.rows.length * ROW, colours);
  }
  canvas.toBlob((blob) => {
    if (blob !== null) {
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = image.fileName;
      link.click();
      // Some browsers start the download after the task: the address lives until then.
      setTimeout(() => {
        URL.revokeObjectURL(url);
      }, 0);
    }
    canvas.width = 0;
    canvas.height = 0;
  }, "image/png");
  return undefined;
}
