// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The scale of time of the Gantt (US-0530): its levels, each a pair of units — the upper row of the
 * axis and the lower one —, and the width a day takes at each, as in Microsoft Project. Neither
 * server nor client: the Gantt reads it in the browser, its tests in the project `node`.
 *
 * Each boundary is a midnight in UTC, as the dates of planning are placed (`layout.ts`), which no
 * time zone moves; a week starts on Monday (ISO 8601), whatever the language. The Gantt opens
 * « fitted to the project »: its drawing takes the width of its column, graduated at the finest
 * level whose own width the column holds (`fittedLevel`). Zoomed, the drawing takes the width of
 * its level, and scrolls in its own frame, the date at its centre kept (`centredOffset`).
 *
 * The finest level, days and worked hours, divides each day into the hours of work of the
 * installation (`DurationUnits.hours_per_day`): the planning does not read them yet, and a Gantt
 * that is not given them stops at weeks and days (`levelsWith`).
 */

/** A unit of the axis, by the boundaries it marks. */
export type ScaleUnit = "year" | "quarter" | "month" | "week" | "day" | "hour";

/** A level of the scale: the unit of its upper row, that of its lower row, a day's width. */
export interface ScaleLevel {
  readonly upper: ScaleUnit;
  readonly lower: ScaleUnit;
  /** The width of a day, in pixels; the hours level multiplies it by the hours of a day. */
  readonly day: number;
}

/** The five levels, from the coarsest — years and quarters — to the finest. */
export const SCALE_LEVELS: readonly ScaleLevel[] = [
  { upper: "year", lower: "quarter", day: 0.5 },
  { upper: "quarter", lower: "month", day: 1.5 },
  { upper: "month", lower: "week", day: 6 },
  { upper: "week", lower: "day", day: 24 },
  { upper: "day", lower: "hour", day: 20 },
];

/** The level the Gantt shows: one of the scale, by its index, or the whole project fitted. */
export type Zoom = number | "fit";

/** A day, in milliseconds. */
export const DAY = 86_400_000;

/** The levels a Gantt offers: the hours level only when it knows the hours of a day. */
export function levelsWith(hoursPerDay: number | undefined): number {
  return hoursPerDay === undefined ? SCALE_LEVELS.length - 1 : SCALE_LEVELS.length;
}

/** The width of the drawing of a span of time at a level, in pixels. */
export function widthAt(level: number, span: number, hoursPerDay = 1): number {
  const scale = SCALE_LEVELS[level];
  const day = (scale?.day ?? 1) * (scale?.lower === "hour" ? hoursPerDay : 1);
  return Math.ceil((span / DAY) * day);
}

/** The finest level whose drawing of a span the width of a column holds; the coarsest otherwise. */
export function fittedLevel(span: number, width: number, levels: number): number {
  let fitted = 0;
  for (let level = 0; level < levels; level += 1) {
    if (widthAt(level, span) <= width) {
      fitted = level;
    }
  }
  return fitted;
}

/** The first boundary of a unit at or before an instant, in UTC. */
function floor(time: number, unit: Exclude<ScaleUnit, "hour">): number {
  const date = new Date(time);
  const year = date.getUTCFullYear();
  const month = date.getUTCMonth();
  const day = Date.UTC(year, month, date.getUTCDate());
  switch (unit) {
    case "year":
      return Date.UTC(year, 0, 1);
    case "quarter":
      return Date.UTC(year, month - (month % 3), 1);
    case "month":
      return Date.UTC(year, month, 1);
    case "week":
      // Sunday is 0: a Monday is 1, and Sunday comes six days after it.
      return day - ((date.getUTCDay() + 6) % 7) * DAY;
    case "day":
      return day;
  }
}

/** The boundary of a unit after another. */
function next(time: number, unit: Exclude<ScaleUnit, "hour">): number {
  const date = new Date(time);
  const steps = { year: 12, quarter: 3, month: 1 } as const;
  if (unit === "week" || unit === "day") {
    return time + (unit === "week" ? 7 : 1) * DAY;
  }
  return Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + steps[unit], 1);
}

/**
 * The boundaries of a unit over a span, in milliseconds: the first at or before its start, the
 * last at or after its end — each hour of work an equal part of its day.
 */
export function scaleTicks(unit: ScaleUnit, from: number, to: number, hoursPerDay = 1): number[] {
  const ticks: number[] = [];
  if (unit === "hour") {
    for (const day of scaleTicks("day", from, to).slice(0, -1)) {
      for (let hour = 0; hour < hoursPerDay; hour += 1) {
        ticks.push(day + Math.round((hour * DAY) / hoursPerDay));
      }
    }
    return [...ticks, Math.max(...scaleTicks("day", from, to))];
  }
  let tick = floor(from, unit);
  ticks.push(tick);
  while (tick < to) {
    tick = next(tick, unit);
    ticks.push(tick);
  }
  return ticks;
}

/**
 * Where the drawing scrolls to keep the date at the centre of its frame, as a share of the axis,
 * once it is redrawn at a new width: within its bounds, at the start when it is narrower than its
 * frame.
 */
export function centredOffset(centre: number, width: number, frame: number): number {
  return Math.round(Math.min(Math.max(centre * width - frame / 2, 0), Math.max(width - frame, 0)));
}

/**
 * The offset that brings a stretch of the axis — two shares of its width — into the frame, moving
 * the least: unchanged when it is wholly in view, its start at the edge when it is cut on that side
 * or wider than the frame, its end at the edge when it is cut on the other.
 */
export function revealedOffset(
  span: { readonly from: number; readonly to: number },
  width: number,
  frame: number,
  offset: number,
): number {
  const from = span.from * width;
  const to = span.to * width;
  let target = offset;
  if (from < offset || to - from > frame) {
    target = from;
  } else if (to > offset + frame) {
    target = to - frame;
  }
  return Math.round(Math.min(Math.max(target, 0), Math.max(width - frame, 0)));
}

/** The level a zoom in or out reaches from the one shown, within those offered. */
export function zoomed(zoom: Zoom, fitted: number, step: 1 | -1, levels: number): number {
  const from = zoom === "fit" ? fitted : zoom;
  return Math.min(Math.max(from + step, 0), levels - 1);
}
