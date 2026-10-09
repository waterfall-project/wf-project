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
 * It presents the tree of the grid, folded as the grid is — its rows are the grid's —, and folds it
 * as the grid does (WF-PLA-0090): the bracket of a summary has the button that folds it before it,
 * and the keys of the folding act on its cells as on any cell of the grid (`fold.tsx`). Folding
 * modifies no task.
 */
"use client";

import { useLocale, useTranslations } from "next-intl";
import { createContext, type ReactNode, use, useMemo } from "react";

import { FoldToggle } from "@/components/grid/fold";
import { formatLocale, formatPlanningDate } from "@/i18n/format";
import type { Locale } from "@/i18n/locale";

import {
  type GanttBar,
  ganttLayout,
  type GanttLayout,
  type GanttLinkPart,
  type GanttRow,
} from "./layout";

/** The layout of the Gantt of the grid around, if any. */
const GanttContext = createContext<GanttLayout | undefined>(undefined);

/** A share of the axis as a length of SVG: a percentage of the width of the cell. */
function percent(share: number): string {
  return `${(share * 100).toFixed(3)}%`;
}

/**
 * Hand the cells of the Gantt the layout of the rows the grid shows — those of the answer, as
 * its writes left them —, computed again only when they change.
 */
export function GanttRows({
  rows,
  children,
}: {
  readonly rows: readonly GanttRow[];
  readonly children: ReactNode;
}) {
  const layout = useMemo(() => ganttLayout(rows), [rows]);
  return <GanttContext value={layout}>{children}</GanttContext>;
}

/** The first of each month, a vertical line across the row, under what it draws. */
function Months({ layout }: { readonly layout: GanttLayout }) {
  return layout.ticks.map((tick) => (
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
function togglePlace(bar: GanttBar | undefined): string {
  return bar === undefined ? "0px" : `max(0px, calc(${percent(bar.from)} - 1.125rem))`;
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
  const layout = use(GanttContext);
  if (layout === undefined) {
    return null;
  }
  const bar = layout.bar(row);
  const task = row.task;
  const named = bar !== undefined && task !== null && task !== undefined;
  return (
    <div className="relative">
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
      >
        <Months layout={layout} />
        {layout.links(row.node_id).map((link, at) => (
          <LinkPart key={at} link={link} />
        ))}
        {bar === undefined ? null : <Bar bar={bar} />}
      </svg>
      <FoldToggle
        rowKey={row.node_id}
        className="absolute top-1/2 -translate-y-1/2 bg-background"
        style={{ left: togglePlace(bar) }}
      />
    </div>
  );
}

/** The fewest pixels between two labels of the axis. */
const LABEL_SPACING = 64;

/**
 * Render the axis of the Gantt, in its header: the first of the months, written in the language of
 * the interface — the month and its year, the year alone when the axis steps by years —, as many
 * as its width holds. A drawing: the header is named by its heading, which a reader of the screen
 * reads.
 */
export function GanttAxis({ width }: { readonly width: number }) {
  const locale = useLocale();
  const layout = use(GanttContext);
  if (layout === undefined || layout.ticks.length < 2) {
    return null;
  }
  const marked = layout.ticks.slice(0, -1);
  const yearly = (marked[1] ?? Number.POSITIVE_INFINITY) - (marked[0] ?? 0) > 360 * 86_400_000;
  const every = Math.max(1, Math.ceil((marked.length * LABEL_SPACING) / Math.max(width, 1)));
  const format = new Intl.DateTimeFormat(formatLocale(locale), {
    ...(yearly ? {} : { month: "short" }),
    year: yearly ? "numeric" : "2-digit",
    timeZone: "UTC",
  });
  return (
    <svg aria-hidden="true" className="absolute inset-y-0 left-2 h-full w-[calc(100%-1rem)]">
      {marked.map((tick, at) =>
        at % every === 0 ? (
          <text
            key={tick}
            x={percent(layout.at(tick))}
            dx={2}
            y="62%"
            className="fill-muted-foreground text-[10px] font-normal"
          >
            {format.format(tick)}
          </text>
        ) : null,
      )}
    </svg>
  );
}
