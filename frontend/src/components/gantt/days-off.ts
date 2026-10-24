// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The days off of a task in the Gantt (US-0530/L5, WF-PLA-0090): the days at 0 hours of the calendar
 * that applies to it, as the planning gives it (`TaskFacet.calendar_hours`) — the contract knows no
 * public holiday. Neither server nor client, and no DOM: the cells of the Gantt draw its bands in
 * SVG, and the export of the Gantt as an image draws the same ones on a canvas (`dayOffBands`).
 */
import type { components } from "@/api/generated/schema";

import { ZERO } from "./layout";
import { DAY } from "./scale";

/** The hours of each day of the week of a calendar. */
type WeeklyHours = components["schemas"]["WeeklyHours"];

/** A stretch of consecutive days off, in milliseconds: from its first midnight to the one after its last. */
export interface DayOffBand {
  readonly from: number;
  readonly to: number;
}

/** The fewest pixels a day takes for its tint to be drawn: under it, a day is no more than a hair. */
export const MIN_DAY_WIDTH = 1;

/** The days of the week by `Date.getUTCDay`, Sunday first. */
const WEEKDAYS = [
  "sunday",
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
] as const;

/** Whether a calendar has a day off at all. */
export function hasDaysOff(calendar: WeeklyHours | undefined): boolean {
  return calendar !== undefined && WEEKDAYS.some((day) => ZERO.test(calendar[day]));
}

/**
 * The bands of days off of a calendar over the extent of an axis, each stretch of consecutive days
 * one band — a weekend, not two days. The extent is the axis as the layout bounds it: whole days,
 * UTC midnights. None for a calendar without day off, or when a day takes fewer than
 * `MIN_DAY_WIDTH` pixels at the scale (`pixelsPerDay`): the tint would be lost in the rule of the
 * axis, and the bands too many to draw for nothing.
 */
export function dayOffBands(
  calendar: WeeklyHours | undefined,
  extent: { readonly from: number; readonly to: number },
  pixelsPerDay: number,
): DayOffBand[] {
  if (calendar === undefined || pixelsPerDay < MIN_DAY_WIDTH || !hasDaysOff(calendar)) {
    return [];
  }
  const bands: DayOffBand[] = [];
  for (let day = extent.from; day < extent.to; day += DAY) {
    const weekday = WEEKDAYS[new Date(day).getUTCDay()];
    if (weekday === undefined || !ZERO.test(calendar[weekday])) {
      continue;
    }
    const last = bands.at(-1);
    if (last?.to === day) {
      bands[bands.length - 1] = { from: last.from, to: day + DAY };
    } else {
      bands.push({ from: day, to: day + DAY });
    }
  }
  return bands;
}
