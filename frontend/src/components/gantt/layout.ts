// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Where the Gantt draws (FBS-4.3.3, WF-PLA-0090): the axis of time over the tasks of the answer,
 * and the links between them. Neither server nor client: the cells of the Gantt read it in the
 * browser, its tests in the project `node`.
 *
 * Nothing is scheduled here. The dates are those the API gives (`TaskFacet.start`, `finish`), and
 * the Gantt only places them on its axis, as a chart places the points it is given: at the scale of
 * the day, a task running from the start of its first day to the end of its last — a finish at
 * hour 0 of a day being its very start —, a milestone standing at its finish. The axis runs from
 * the first of the month of the earliest start to the first of the month after the latest finish
 * (`monthTicks`), and a place on it is a share of its width: the drawing follows the width of its
 * column, whatever the user sets it to.
 *
 * A link joins the place its type names on the predecessor — its finish, or its start for a link
 * from start — to the place it names on the task — its start, or its finish for a link to finish
 * (WF-PLA-0030); a lag is already in the dates. A predecessor the answer does not hold — out of
 * what a search retained — draws no link: its row is not there.
 */
import type { components } from "@/api/generated/schema";
import { monthTicks } from "@/components/chart/ticks";

/** A start or a finish of a task: a date, and the hours of work elapsed that day. */
type WorkInstant = components["schemas"]["WorkInstant"];

/** A link of a task to one of its predecessors. */
type Predecessor = components["schemas"]["Predecessor"];

/** What the Gantt reads of a task: its dates, its nature, the critical path. */
export interface GanttTask {
  readonly start?: WorkInstant | null;
  readonly finish?: WorkInstant | null;
  readonly is_summary: boolean;
  readonly is_milestone: boolean;
  readonly is_critical?: boolean;
}

/** What the Gantt reads of a row: its identity, its task, its links. */
export interface GanttRow {
  readonly node_id: string;
  readonly task?: GanttTask | null;
  readonly predecessors?: readonly Predecessor[];
}

/** A day, in milliseconds. */
const DAY = 86_400_000;

/** An exact decimal of the contract that reads as zero: `0`, `0.00`. */
const ZERO = /^-?0+(\.0+)?$/;

/** The midnight that starts a date of planning, in UTC, which no time zone moves. */
function midnight(date: string): number {
  return Date.parse(`${date}T00:00:00Z`);
}

/** Where a task starts on the axis: the start of its first day. */
export function startTime(instant: WorkInstant): number {
  return midnight(instant.date);
}

/** Where a task finishes on the axis: the end of its last day, or its start at hour 0. */
export function finishTime(instant: WorkInstant): number {
  return midnight(instant.date) + (ZERO.test(instant.hours) ? 0 : DAY);
}

/** A task as the Gantt draws it: where it starts and finishes, a share of the axis each. */
export interface GanttBar {
  readonly from: number;
  readonly to: number;
  readonly nature: "summary" | "milestone" | "task";
  readonly critical: boolean;
}

/** The part of a link a row draws, its places shares of the axis. */
export interface GanttLinkPart {
  /** Where the link leaves the predecessor, and runs along the rows between. */
  readonly out: number;
  /** Where it reaches the task. */
  readonly in: number;
  /** What the row draws of it: its start, a stretch passing by, or its end and its arrow. */
  readonly part: "leaves" | "passes" | "arrives";
  /** Whether the link runs down the grid, the task below its predecessor. */
  readonly down: boolean;
}

/** The axis of the Gantt over an answer, and what each of its rows draws. */
export interface GanttLayout {
  /** The first of each month the axis marks, in milliseconds; the first and last bound it. */
  readonly ticks: readonly number[];
  /** The place of an instant on the axis, a share of its width from 0 to 1. */
  readonly at: (time: number) => number;
  /** The bar of a task, none without dates. */
  readonly bar: (row: GanttRow) => GanttBar | undefined;
  /** The parts of the links a row draws, by the identity of its node. */
  readonly links: (nodeId: string) => readonly GanttLinkPart[];
}

/** A link between two rows of the answer, its places shares of the axis. */
interface Link {
  readonly from: number;
  readonly to: number;
  readonly out: number;
  readonly in: number;
}

/**
 * The place a link names on a task: its finish or its start — a milestone's is always where it
 * stands, at its finish.
 */
function anchor(task: GanttTask | null | undefined, finish: boolean): number | undefined {
  if (finish || task?.is_milestone === true) {
    return task?.finish === null || task?.finish === undefined
      ? undefined
      : finishTime(task.finish);
  }
  return task?.start === null || task?.start === undefined ? undefined : startTime(task.start);
}

/** The links between the rows of an answer whose ends both have dates, as times. */
function linksOf(rows: readonly GanttRow[], index: ReadonlyMap<string, number>): Link[] {
  return rows.flatMap((row, to) =>
    (row.predecessors ?? []).flatMap((link) => {
      const from = index.get(link.predecessor_node_id);
      const predecessor = from === undefined ? undefined : rows[from]?.task;
      const out = anchor(predecessor, link.link_type.startsWith("finish"));
      const reached = anchor(row.task, link.link_type.endsWith("finish"));
      return from === undefined || out === undefined || reached === undefined
        ? []
        : [{ from, to, out, in: reached }];
    }),
  );
}

/** The part of a link a row between its ends draws. */
function partAt(link: Link, index: number, at: (time: number) => number): GanttLinkPart {
  let part: GanttLinkPart["part"] = "passes";
  if (index === link.from) {
    part = "leaves";
  } else if (index === link.to) {
    part = "arrives";
  }
  return { out: at(link.out), in: at(link.in), part, down: link.to > link.from };
}

/**
 * The parts of the links each row draws, by its index, laid out once: a row reads its own, never
 * every link of the answer.
 */
function partsByRow(
  links: readonly Link[],
  at: (time: number) => number,
): ReadonlyMap<number, readonly GanttLinkPart[]> {
  const parts = new Map<number, GanttLinkPart[]>();
  for (const link of links) {
    for (let row = Math.min(link.from, link.to); row <= Math.max(link.from, link.to); row += 1) {
      const drawn = parts.get(row) ?? [];
      drawn.push(partAt(link, row, at));
      parts.set(row, drawn);
    }
  }
  return parts;
}

/** The nature of a task as its bar shows it. */
function natureOf(task: GanttTask): GanttBar["nature"] {
  if (task.is_summary) {
    return "summary";
  }
  return task.is_milestone ? "milestone" : "task";
}

/**
 * The layout of the Gantt over the rows of an answer, in its order: the axis over their dates, the
 * bar of each task, the links between the rows. An answer without a date has an axis without ticks,
 * and no bar.
 */
export function ganttLayout(rows: readonly GanttRow[]): GanttLayout {
  const times = rows
    .flatMap(({ task }) => [anchor(task, false) ?? [], anchor(task, true) ?? []])
    .flat();
  const ticks = monthTicks(
    times.map((time) => new Date(time).toISOString()),
    true,
  );
  const first = ticks[0] ?? 0;
  const span = (ticks.at(-1) ?? first + DAY) - first;
  const at = (time: number) => (time - first) / span;
  const index = new Map(rows.map((row, at) => [row.node_id, at]));
  const parts = partsByRow(linksOf(rows, index), at);
  return {
    ticks,
    at,
    bar: ({ task }) => {
      const [start, finish] = [anchor(task, false), anchor(task, true)];
      if (task === null || task === undefined || start === undefined || finish === undefined) {
        return undefined;
      }
      return {
        from: at(start),
        to: at(finish),
        nature: natureOf(task),
        critical: task.is_critical === true,
      };
    },
    links: (nodeId) => {
      const row = index.get(nodeId);
      return (row === undefined ? undefined : parts.get(row)) ?? [];
    },
  };
}
