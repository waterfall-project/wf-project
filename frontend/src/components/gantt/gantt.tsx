// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The Gantt of the planning (FBS-4.3.3, WF-PLA-0090, US-0220): a column of the grid of the
 * planning, to the right of the others, whose cells each draw the row of their task in SVG — its
 * bar, the parts of the links that leave it, pass it by or reach it, the months of the axis —, so
 * that the drawing is aligned row for row on the grid and rendered with its rows alone, as they
 * come into view (EP-02, « Gantt »). Its header draws the axis.
 *
 * It is read, never entered: no bar moves, nothing in it takes the pointer, and its cells take no
 * entry — every entry is made in the grid. The critical path is told by the drawing as by the name
 * of the bar, never by its colour alone (WF-PLA-0100): a task on it is a filled bar, the others an
 * outline; a summary is a bracket, a milestone a diamond, so that the three sorts of task read
 * apart (WF-PLA-0080). Each bar is an image named by its dates, as the API gives them.
 *
 * The days off of a task — the days at 0 hours of its calendar (`days-off.ts`) — are tinted across its
 * row, in a hatching as well as a colour, so that the colour does not carry them alone (WCAG 1.4.1);
 * a legend under the grid names the tint. Not where a day takes under a pixel.
 *
 * It presents the tree of the grid, folded as the grid is — its rows are the grid's —, and folds it
 * as the grid does (WF-PLA-0090): the bracket of a summary has the button that folds it before it,
 * and the keys of the folding act on its cells as on any cell of the grid (`fold.tsx`). Folding
 * modifies no task.
 *
 * Its axis has two rows, in the language of the interface, at one of the levels of its scale
 * (`scale.ts`, US-0530). It opens fitted to the project, and zooms in and out by the commands in the
 * corner of its header (`GanttZoom`) and in the menu of a cell (`GanttZoomItems`), by Ctrl and plus or minus in the grid, and by Ctrl and the wheel on
 * the Gantt; zoomed, its drawing scrolls in its own frame — the axis with the bars, by the scroll bar
 * of its header or the wheel —, the date at its centre kept. Neither zooming nor scrolling modifies a
 * task (WF-PLA-0090). Its finest level, the worked hours, divides each day into the hours of a day
 * of work of the installation, numbered from the first.
 *
 * Where its grid names where it comes from, it is exported as a PNG image (`gantt-image.ts`) by a
 * command beside the zoom and in the menu of a cell: its whole extent at the level shown, its days
 * off and its legend, its title and its provenance (WF-IHM-0130).
 */
"use client";

import { Expand, ZoomIn, ZoomOut } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import {
  createContext,
  type KeyboardEvent,
  type ReactNode,
  type RefObject,
  use,
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import type { ChartProvenance } from "@/components/chart/chart";
import { CommandTooltip } from "@/components/commands/command-tooltip";
import { MenuCommand } from "@/components/commands/menu-command";
import { UNAVAILABLE } from "@/components/commands/offer";
import { FoldToggle } from "@/components/grid/fold";
import { Button } from "@/components/ui/button";
import { ContextMenuItem, ContextMenuSeparator } from "@/components/ui/context-menu";
import { formatPlanningDate } from "@/i18n/format";
import type { Locale } from "@/i18n/locale";

import { axisWriter, labelsOf } from "./axis-labels";
import { DAY_OFF_HATCH, dayOffBands, hasDaysOff, MIN_DAY_WIDTH } from "./days-off";
import { GanttExportButton, GanttExportItem, GanttProbes } from "./gantt-export";
import { ganttFits } from "./gantt-image";
import {
  type GanttBar,
  ganttLayout,
  type GanttLayout,
  type GanttLinkPart,
  type GanttRow,
  type GanttTask,
} from "./layout";
import {
  centredOffset,
  DAY,
  fittedLevel,
  levelsWith,
  revealedOffset,
  SCALE_LEVELS,
  scaleTicks,
  widthAt,
  type Zoom,
  zoomed,
} from "./scale";
import { useKeptZoom } from "./zoom";

/** The Gantt of the grid around: its layout, the level of its scale, where its drawing scrolls. */
export interface GanttView {
  readonly layout: GanttLayout;
  /** The level of the scale shown, and whether it is the whole project fitted to the column. */
  readonly level: number;
  readonly zoom: Zoom;
  /** The width of the drawing in pixels, zoomed; none, fitted to its column. */
  readonly width: number | undefined;
  /** How far the drawing has scrolled, in pixels. */
  readonly offset: number;
  /** The boundaries of the lower and the upper row of the axis, in milliseconds. */
  readonly lower: readonly number[];
  readonly upper: readonly number[];
  /** The frame that scrolls, in the header, and what tells the view where it is and how wide. */
  readonly scroller: (element: HTMLDivElement | null) => void;
  readonly scrolled: (offset: number) => void;
  readonly framed: (width: number) => void;
  /** Zoom in or out a level, or fit the project; whether each goes anywhere. */
  readonly zoomTo: (step: 1 | -1 | "fit") => void;
  /** Scroll the drawing to bring a stretch of the axis, two shares of its width, into view. */
  readonly reveal: (from: number, to: number) => void;
  readonly can: { readonly in: boolean; readonly out: boolean };
  /** The width of a day, in pixels, at the level shown. */
  readonly dayWidth: number;
  /** Whether the days off of some task are tinted: a legend names the tint then. */
  readonly tinted: boolean;
  /** The graduations of hours of a day at the finest level; none, the scale stops at days. */
  readonly hoursPerDay: number | undefined;
  /** What the export of the Gantt as an image needs; none where its grid names no provenance. */
  readonly exporting: GanttExporting | undefined;
}

/** Where the image of a Gantt comes from, which it names (WF-IHM-0130). */
export interface GanttExported {
  /** The project and the revision. */
  readonly provenance: ChartProvenance;
  /** The instant the dates were last calculated at (`meta.scheduled_at`). */
  readonly scheduledAt: string;
}

/** What the export of a Gantt draws, and whether it can. */
export interface GanttExporting {
  readonly exported: GanttExported;
  /** The rows of the tasks the grid shows, folded as it is. */
  readonly rows: readonly GanttRow[];
  /** The width of the drawing at the level shown: zoomed, or that of its column. */
  readonly width: number;
  /** Whether a canvas holds its image: too wide or too long, it is not drawn. */
  readonly fits: boolean;
  /** The probes of its colours, in the document. */
  readonly probes: RefObject<HTMLSpanElement | null>;
}

/** The Gantt of the grid around, if any. */
const GanttContext = createContext<GanttView | undefined>(undefined);

/** The Gantt around — its layout, its level, its scroll —, for a drawing on its axis: the timeline. */
export function useGanttView(): GanttView | undefined {
  return use(GanttContext);
}

/** A share of the axis as a length of SVG: a percentage of the width of the cell. */
export function percent(share: number): string {
  return `${(share * 100).toFixed(3)}%`;
}

/** The zoom a key asks for in the grid: Ctrl — or Cmd — and plus or minus, the keypad's too. */
function keyZoom(event: KeyboardEvent): 1 | -1 | undefined {
  if (!(event.ctrlKey || event.metaKey) || event.altKey) {
    return undefined;
  }
  if (["+", "="].includes(event.key) || event.code === "NumpadAdd") {
    return 1;
  }
  return event.key === "-" || event.code === "NumpadSubtract" ? -1 : undefined;
}

/**
 * What the export of a Gantt needs, given where it comes from: the rows of its tasks, the width of
 * its drawing, whether its image holds in a canvas, and the probes of its colours.
 */
function useExporting(
  exported: GanttExported | undefined,
  rows: readonly GanttRow[],
  width: number,
  tinted: boolean,
): readonly [GanttExporting | undefined, ReactNode] {
  const tasks = useMemo(
    () => rows.filter(({ task }) => task !== null && task !== undefined),
    [rows],
  );
  const probes = useRef<HTMLSpanElement>(null);
  return exported === undefined
    ? [undefined, null]
    : [
        { exported, rows: tasks, width, fits: ganttFits(width, tasks.length, tinted), probes },
        <GanttProbes key="probes" probes={probes} />,
      ];
}

/** Zoom by Ctrl and plus or minus pressed in the grid or the frieze. */
function zoomByKey(event: KeyboardEvent, zoomTo: (step: 1 | -1) => void) {
  const step = keyZoom(event);
  const target = event.target instanceof Element ? event.target : undefined;
  if (step !== undefined && target?.closest('[role="treegrid"], [data-timeline]') != null) {
    event.preventDefault();
    zoomTo(step);
  }
}

/**
 * Hand the cells of the Gantt the layout of the rows the grid shows — those of the answer, as
 * its writes left them —, computed again only when they change, and the level of its scale, kept
 * under a scope — the grid and the revision — for the session; without a scope, fitted to the
 * project, and nothing zooms. Given the hours of a day, its finest level is the worked hours; given
 * where it comes from, it is exported as an image.
 */
export function GanttRows({
  rows,
  scope,
  hoursPerDay,
  exported,
  children,
}: {
  readonly rows: readonly GanttRow[];
  readonly scope?: string | undefined;
  /** The graduations of hours of a day (`hoursOfDay`); none, the scale stops at days. */
  readonly hoursPerDay?: number | undefined;
  readonly exported?: GanttExported | undefined;
  readonly children: ReactNode;
}) {
  const layout = useMemo(() => ganttLayout(rows), [rows]);
  const levels = levelsWith(hoursPerDay);
  const [zoom, setZoom] = useKeptZoom(scope, levels);
  const [frame, setFrame] = useState(0);
  // False until a tick after the mount: the time the axis, if drawn, has to measure its frame.
  const [settled, setSettled] = useState(false);
  useEffect(() => {
    const tick = setTimeout(() => {
      setSettled(true);
    }, 0);
    return () => {
      clearTimeout(tick);
    };
  }, []);
  const [offset, setOffset] = useState(0);
  const scroller = useRef<HTMLDivElement>(null);
  const attach = useCallback((element: HTMLDivElement | null) => {
    scroller.current = element;
  }, []);
  const held = useRef<HTMLDivElement>(null);
  // The date at the centre when a zoom was asked, a share of the axis, until the drawing is redrawn.
  const centre = useRef<number | undefined>(undefined);
  const first = layout.ticks[0] ?? 0;
  const last = layout.ticks.at(-1) ?? first;
  const fitted = fittedLevel(last - first, frame, levels, hoursPerDay);
  const level = zoom === "fit" ? fitted : zoom;
  const width = zoom === "fit" ? undefined : widthAt(level, last - first, hoursPerDay);
  const scale = SCALE_LEVELS[level];
  const lower = useMemo(
    () => (scale === undefined ? [] : scaleTicks(scale.lower, first, last, hoursPerDay)),
    [scale, first, last, hoursPerDay],
  );
  const upper = useMemo(
    () => (scale === undefined ? [] : scaleTicks(scale.upper, first, last)),
    [scale, first, last],
  );
  // The width of the drawing: zoomed, or that of its column.
  const drawn = width ?? frame;
  const dayWidth = drawn / Math.max((last - first) / DAY, 1);
  const anyDayOff = useMemo(
    () => rows.some(({ task }) => hasDaysOff(task?.calendar_hours)),
    [rows],
  );
  // The width of the frame that scrolls, as the header shows it; that of the column before it is drawn.
  const seen = () => scroller.current?.clientWidth ?? frame;
  const zoomTo = (step: 1 | -1 | "fit") => {
    // The scroll of the frame itself, which a scroll not yet told to the view may have moved, and
    // its width within the header, inset from the edges of the column.
    const scrolled = width === undefined ? 0 : (scroller.current?.scrollLeft ?? offset);
    centre.current = (scrolled + seen() / 2) / Math.max(drawn, 1);
    setZoom(step === "fit" ? "fit" : zoomed(zoom, fitted, step, levels));
  };
  const reveal = (from: number, to: number) => {
    if (width === undefined || scroller.current === null) {
      return;
    }
    const kept = revealedOffset({ from, to }, width, frame, scroller.current.scrollLeft);
    scroller.current.scrollLeft = kept;
    setOffset(kept);
  };
  useLayoutEffect(() => {
    if (centre.current === undefined) {
      return;
    }
    const kept = centredOffset(
      centre.current,
      width ?? frame,
      scroller.current?.clientWidth ?? frame,
    );
    centre.current = undefined;
    if (scroller.current !== null) {
      scroller.current.scrollLeft = kept;
    }
    setOffset(kept);
  }, [width, frame]);
  // Ctrl and the wheel zoom on the Gantt, the wheel across scrolls it: the page neither zooms nor
  // scrolls aside, which a passive listener — React's — could not prevent. A gesture mostly
  // downward passes, though it drifts aside on a touchpad: the grid scrolls down.
  const wheel = useRef<(event: WheelEvent) => void>(() => undefined);
  useEffect(() => {
    wheel.current = (event) => {
      if (!(event.target instanceof Element) || event.target.closest("[data-gantt]") === null) {
        return;
      }
      if (event.ctrlKey && event.deltaY !== 0) {
        event.preventDefault();
        zoomTo(event.deltaY < 0 ? 1 : -1);
      } else if (
        width !== undefined &&
        (event.shiftKey || Math.abs(event.deltaX) > Math.abs(event.deltaY))
      ) {
        event.preventDefault();
        scroller.current?.scrollBy({ left: event.deltaX === 0 ? event.deltaY : event.deltaX });
      }
    };
  });
  useEffect(() => {
    const element = held.current;
    if (scope === undefined || element === null) {
      return undefined;
    }
    const listener = (event: WheelEvent) => {
      wheel.current(event);
    };
    element.addEventListener("wheel", listener, { passive: false });
    return () => {
      element.removeEventListener("wheel", listener);
    };
  }, [scope]);
  const tinted =
    anyDayOff && (dayWidth >= MIN_DAY_WIDTH || (width === undefined && frame === 0 && !settled));
  const [exporting, probed] = useExporting(exported, rows, drawn, tinted);
  const view: GanttView = {
    layout,
    level,
    zoom,
    width,
    offset: width === undefined ? 0 : offset,
    lower,
    upper,
    scroller: attach,
    scrolled: setOffset,
    framed: setFrame,
    zoomTo,
    reveal,
    can: { in: level < levels - 1 || zoom === "fit", out: level > 0 || zoom === "fit" },
    dayWidth,
    // Fitted and not yet measured, for a tick at most, the legend is held: it keeps its place, and
    // the bands, which wait for the width of a day, come after the measure. The layout moves once
    // only if the measure shows days under a pixel (the legend then goes), or if no axis is drawn.
    tinted,
    hoursPerDay,
    exporting,
  };
  return (
    <GanttContext value={view}>
      {scope === undefined ? (
        <>
          {children}
          {probed}
        </>
      ) : (
        <div
          ref={held}
          className="contents"
          onKeyDown={(event) => {
            zoomByKey(event, zoomTo);
          }}
        >
          {children}
          {probed}
        </div>
      )}
    </GanttContext>
  );
}

/** The keys that zoom in the grid or the frieze, as `aria-keyshortcuts` names them (`keyZoom`). */
const ZOOM_KEYS = {
  zoomIn: "Control+Plus Meta+Plus",
  zoomOut: "Control+- Meta+-",
} as const;

/**
 * The commands of the zoom of the Gantt, their icon, their step, whether each goes anywhere, and the
 * keys that ask it.
 */
export function zoomCommands(view: GanttView) {
  return [
    {
      key: "zoomIn",
      icon: <ZoomIn aria-hidden="true" />,
      step: 1,
      offered: view.can.in,
      keys: ZOOM_KEYS.zoomIn,
    },
    {
      key: "zoomOut",
      icon: <ZoomOut aria-hidden="true" />,
      step: -1,
      offered: view.can.out,
      keys: ZOOM_KEYS.zoomOut,
    },
    {
      key: "fit",
      icon: <Expand aria-hidden="true" />,
      step: "fit",
      offered: view.zoom !== "fit",
      keys: undefined,
    },
  ] as const;
}

/**
 * The commands of the zoom of the Gantt, icons in the upper right corner of its header, over the
 * end of the axis and away from the handle on its left edge: seen at every width, the column being
 * pinned at the end. Out of the order of tabulation, as the button and the handle of a header — the
 * grid is one stop (WF-IHM-0100) —, the keyboard zooming by Ctrl and plus or minus in the grid, or by
 * the menu of a cell (`GanttZoomItems`). After them, its export, where it is offered.
 */
export function GanttZoom() {
  const t = useTranslations("gantt");
  const said = useTranslations("commands");
  const view = use(GanttContext);
  if (view === undefined) {
    return null;
  }
  return (
    <div className="absolute top-0.5 right-1 z-10 flex gap-0.5 rounded-sm bg-background/90">
      <div role="group" aria-label={t("zoom")} className="flex gap-0.5">
        {zoomCommands(view).map((command) => (
          <CommandTooltip
            key={command.key}
            label={t(command.key)}
            help={said(`${command.key}.help`)}
            keys={command.keys}
            unavailable={command.offered ? undefined : said(`${command.key}.unavailable`)}
          >
            <Button
              type="button"
              variant="ghost"
              size="icon"
              tabIndex={-1}
              className={`size-5 [&_svg]:size-3.5 ${UNAVAILABLE}`}
              aria-label={t(command.key)}
              onClick={() => {
                if (command.offered) {
                  view.zoomTo(command.step);
                }
              }}
            >
              {command.icon}
            </Button>
          </CommandTooltip>
        ))}
      </div>
      {view.exporting === undefined ? null : (
        <GanttExportButton view={view} exporting={view.exporting} />
      )}
    </div>
  );
}

/**
 * The commands of the zoom of the Gantt, in the menu of a cell of its grid: after a separator when
 * other commands come before them.
 */
export function GanttZoomItems({ separated }: { readonly separated: boolean }) {
  const t = useTranslations("gantt");
  const said = useTranslations("commands");
  const view = use(GanttContext);
  if (view === undefined) {
    return null;
  }
  return (
    <>
      {separated ? <ContextMenuSeparator /> : null}
      {zoomCommands(view).map((command) => (
        <MenuCommand
          key={command.key}
          item={ContextMenuItem}
          label={t(command.key)}
          help={said(`${command.key}.help`)}
          keys={command.keys}
          unavailable={command.offered ? undefined : said(`${command.key}.unavailable`)}
          icon={command.icon}
          className={UNAVAILABLE}
          onSelect={(event) => {
            // Pressed where it goes nowhere, it does nothing, and the menu stays open on why.
            if (!command.offered) {
              event.preventDefault();
              return;
            }
            view.zoomTo(command.step);
          }}
        />
      ))}
      {view.exporting === undefined ? null : (
        <GanttExportItem view={view} exporting={view.exporting} />
      )}
    </>
  );
}

/** The boundaries of the lower row of the axis, vertical lines across the row, under its drawing. */
function Months({
  layout,
  ticks,
}: {
  readonly layout: GanttLayout;
  readonly ticks: readonly number[];
}) {
  return ticks.map((tick) => (
    <line
      key={tick}
      x1={percent(layout.at(tick))}
      x2={percent(layout.at(tick))}
      y1="0"
      y2="100%"
      className="stroke-border"
    />
  ));
}

/** The hatching of the days off, a tint with diagonal strokes on it, as a pattern of an SVG. */
function DayOffPattern({ id }: { readonly id: string }) {
  const { size, stroke, rotation, fillClass, markClass } = DAY_OFF_HATCH;
  return (
    <defs>
      <pattern
        id={id}
        width={size}
        height={size}
        patternUnits="userSpaceOnUse"
        patternTransform={`rotate(${rotation.toString()})`}
      >
        <rect width={size} height={size} className={fillClass} />
        <line x1={0} x2={0} y1={0} y2={size} strokeWidth={stroke} className={markClass} />
      </pattern>
    </defs>
  );
}

/** The days off of a task, bands across its row under the months, the width of a day told by the view. */
function DaysOff({
  view,
  calendar,
  pattern,
}: {
  readonly view: GanttView;
  readonly calendar: GanttTask["calendar_hours"];
  readonly pattern: string;
}) {
  const { layout, dayWidth } = view;
  const first = layout.ticks[0] ?? 0;
  const last = layout.ticks.at(-1) ?? first;
  const bands = useMemo(
    () => dayOffBands(calendar, { from: first, to: last }, dayWidth),
    [calendar, first, last, dayWidth],
  );
  return bands.map((band) => (
    <rect
      key={band.from}
      data-day-off=""
      x={percent(layout.at(band.from))}
      width={percent(layout.at(band.to) - layout.at(band.from))}
      y={0}
      height="100%"
      fill={`url(#${pattern})`}
    />
  ));
}

/**
 * The legend of the Gantt, under the grid: the hatched tint of the days off, named. Nothing where
 * no day off is tinted.
 */
export function GanttLegend() {
  const t = useTranslations("gantt");
  const view = use(GanttContext);
  const pattern = useId();
  if (view?.tinted !== true) {
    return null;
  }
  return (
    <div
      role="group"
      aria-label={t("legend")}
      className="flex items-center gap-2 px-2 py-1 text-xs text-muted-foreground"
    >
      <svg
        aria-hidden="true"
        width={20}
        height={12}
        className="shrink-0 border border-day-off-mark"
      >
        <DayOffPattern id={pattern} />
        <rect width={20} height={12} fill={`url(#${pattern})`} />
      </svg>
      <span>{t("dayOff")}</span>
    </div>
  );
}

/** The part of a link a row draws: its vertical stretch, and where it arrives its arrow. */
function LinkPart({ link }: { readonly link: GanttLinkPart }) {
  const out = percent(link.out);
  const span = {
    leaves: link.down ? ["50%", "100%"] : ["0", "50%"],
    passes: ["0", "100%"],
    arrives: link.down ? ["0", "50%"] : ["50%", "100%"],
  }[link.part];
  const rightward = link.in >= link.out;
  return (
    <g className="fill-muted-foreground stroke-muted-foreground">
      <line x1={out} x2={out} y1={span[0]} y2={span[1]} />
      {link.part === "arrives" ? (
        <>
          <line x1={out} x2={percent(link.in)} y1="50%" y2="50%" />
          <svg x={percent(link.in)} y="50%" overflow="visible" aria-hidden="true">
            <polygon points={rightward ? "-5,-3 0,0 -5,3" : "5,-3 0,0 5,3"} strokeWidth={0} />
          </svg>
        </>
      ) : null}
    </g>
  );
}

/** The bar of a task: a bracket for a summary, a diamond for a milestone, a bar for a task. */
function Bar({ bar }: { readonly bar: GanttBar }) {
  const shape = bar.critical
    ? "fill-destructive stroke-destructive"
    : "fill-background stroke-primary";
  if (bar.nature === "milestone") {
    return (
      <svg x={percent(bar.to)} y="50%" overflow="visible" aria-hidden="true">
        <polygon points="0,-6 6,0 0,6 -6,0" className={shape} strokeWidth={1.5} />
      </svg>
    );
  }
  const x = percent(bar.from);
  const width = percent(Math.max(bar.to - bar.from, 0));
  if (bar.nature === "summary") {
    return (
      <g className="fill-foreground">
        <rect x={x} y="30%" width={width} height="20%" />
        <rect x={x} y="30%" width={3} height="45%" />
        <svg x={percent(bar.to)} y="30%" overflow="visible" aria-hidden="true">
          <rect x={-3} width={3} height="45%" />
        </svg>
      </g>
    );
  }
  return (
    <rect x={x} y="25%" width={width} height="50%" rx={2} className={shape} strokeWidth={1.5} />
  );
}

/** The name of a bar: its dates, as the API gives them, and whether it is on the critical path. */
function barName(
  task: NonNullable<GanttRow["task"]>,
  locale: Locale,
  name: (start: string, finish: string) => string,
): string {
  const date = (instant: { readonly date: string } | null | undefined) =>
    instant === null || instant === undefined
      ? ""
      : formatPlanningDate(instant.date, locale, "short");
  return name(date(task.start), date(task.finish));
}

/** Where the button that folds a summary stands: just before its bracket, within the cell. */
function togglePlace(bar: GanttBar | undefined, view: GanttView): string {
  if (bar === undefined) {
    return "0px";
  }
  const place =
    view.width === undefined
      ? percent(bar.from)
      : `${String(bar.from * view.width - view.offset)}px`;
  return `max(0px, calc(${place} - 1.125rem))`;
}

/**
 * Render the row of a task in the Gantt: the months, the links, its bar — named by its dates —, the
 * months and the links alone for a row without dates, hidden from the readers of the screen; before
 * the bracket of a summary, the button that folds it; nothing outside the rows a Gantt lays out
 * (`GanttRows`).
 */
export function GanttCell({ row }: { readonly row: GanttRow }) {
  const t = useTranslations("gantt");
  const locale = useLocale();
  const view = use(GanttContext);
  const pattern = useId();
  if (view === undefined) {
    return null;
  }
  const layout = view.layout;
  const bar = layout.bar(row);
  const task = row.task;
  const named = bar !== undefined && task !== null && task !== undefined;
  return (
    <div className="relative overflow-hidden" data-gantt="">
      <svg
        role={named ? "img" : undefined}
        aria-hidden={named ? undefined : true}
        aria-label={
          named
            ? barName(task, locale, (start, finish) =>
                t("bar", { nature: bar.nature, start, finish, critical: String(bar.critical) }),
              )
            : undefined
        }
        className="pointer-events-none block h-7 w-full overflow-visible"
        style={
          view.width === undefined
            ? undefined
            : { width: view.width, transform: `translateX(-${String(view.offset)}px)` }
        }
      >
        {view.tinted ? (
          <>
            <DayOffPattern id={pattern} />
            <DaysOff view={view} calendar={task?.calendar_hours} pattern={pattern} />
          </>
        ) : null}
        <Months layout={layout} ticks={view.lower} />
        {layout.links(row.node_id).map((link, at) => (
          <LinkPart key={at} link={link} />
        ))}
        {bar === undefined ? null : <Bar bar={bar} />}
      </svg>
      <FoldToggle
        rowKey={row.node_id}
        className="absolute top-1/2 -translate-y-1/2 bg-background"
        style={{ left: togglePlace(bar, view) }}
      />
    </div>
  );
}

/**
 * Render the axis of the Gantt, in its header: two rows — the upper unit of its level over the
 * lower, written in the language of the interface, in UTC —, as many labels as its width holds;
 * zoomed, the frame that scrolls the drawing, its scroll bar under the labels. A drawing: the header
 * is named by its heading, which a reader of the screen reads.
 */
export function GanttAxis({ width }: { readonly width: number }) {
  const t = useTranslations("gantt");
  const locale = useLocale();
  const view = use(GanttContext);
  const framed = view?.framed;
  useEffect(() => {
    framed?.(width);
  }, [framed, width]);
  if (view === undefined || view.layout.ticks.length < 2) {
    return null;
  }
  const { scroller, scrolled } = view;
  const drawn = view.width ?? width;
  const write = axisWriter(t, locale, view);
  const row = (which: "lower" | "upper", y: string) =>
    labelsOf(which === "lower" ? view.lower : view.upper, drawn, which, view.layout.at).map(
      ([tick, x]) => (
        <text
          key={tick}
          x={x}
          dx={2}
          y={y}
          className="fill-muted-foreground text-[10px] font-normal"
        >
          {write(which, tick)}
        </text>
      ),
    );
  return (
    <div
      ref={scroller}
      className={`absolute inset-y-0 left-2 w-[calc(100%-1rem)] ${
        view.width === undefined ? "overflow-hidden" : "overflow-x-auto [scrollbar-width:thin]"
      }`}
      onScroll={(event) => {
        scrolled(event.currentTarget.scrollLeft);
      }}
    >
      <svg aria-hidden="true" className="h-full" style={{ width: view.width ?? "100%" }}>
        {view.upper.slice(1, -1).map((tick) => (
          <line
            key={tick}
            x1={view.layout.at(tick) * drawn}
            x2={view.layout.at(tick) * drawn}
            y1="0"
            y2="50%"
            className="stroke-border"
          />
        ))}
        <line x1="0" x2="100%" y1="50%" y2="50%" className="stroke-border" />
        {row("upper", "40%")}
        {row("lower", "88%")}
      </svg>
    </div>
  );
}
