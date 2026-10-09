// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The ticks of an axis of time, on the first of the months it shows: those of a chart
 * (`timeAxis`), and those of the Gantt, which draws its own axis and does not load ECharts.
 */

/**
 * The steps between two ticks of an axis of time, in months: one month, then longer ones for a
 * long range, so that an axis writes `MAX_TICKS` ticks at most.
 */
const MONTH_STEPS = [1, 2, 3, 6, 12, 24, 60, 120] as const;

/** The most ticks an axis of time writes before its step lengthens. */
const MAX_TICKS = 13;

/**
 * The ticks of an axis of time over the instants it shows: the first of each month — in UTC, or in
 * the local time of the workstation —, from the month of the earliest instant to the first of the
 * month after the latest; every second, third, sixth month, every year or more over a long range,
 * a step falling on the first of a month that is a multiple of it counted from January of year 0 —
 * a month from January of each year under a year, a year that is a multiple of the step in years
 * beyond (#415) —, the shortest step whose ticks, so aligned, are `MAX_TICKS` at most (#290).
 * None without an instant. They are positions of the axis, never figures the screen shows.
 */
export function monthTicks(instants: readonly string[], utc: boolean): number[] {
  const times = instants.map((instant) => Date.parse(instant)).filter(Number.isFinite);
  if (times.length === 0) {
    return [];
  }
  const parts = (time: number) => {
    const date = new Date(time);
    return utc
      ? { year: date.getUTCFullYear(), month: date.getUTCMonth() }
      : { year: date.getFullYear(), month: date.getMonth() };
  };
  const first = (year: number, month: number) =>
    utc ? Date.UTC(year, month, 1) : new Date(year, month, 1).getTime();
  const earliest = Math.min(...times);
  const latest = Math.max(...times);
  const start = parts(earliest);
  // Months counted from January of year 0: a step of years falls on a year that is a multiple of
  // it, and a step under a year, which divides twelve, on the same months every year.
  const startMonth = start.year * 12 + start.month;
  /** The ticks at a step, from the first of the aligned month at or before the earliest. */
  const ticksAt = (step: number): number[] => {
    const from = startMonth - (startMonth % step);
    const ticks: number[] = [];
    for (let index = 0; ticks.length === 0 || (ticks.at(-1) ?? latest) <= latest; index += 1) {
      const month = from + index * step;
      ticks.push(first(Math.floor(month / 12), month % 12));
    }
    return ticks;
  };
  let ticks: number[] = [];
  for (const step of MONTH_STEPS) {
    ticks = ticksAt(step);
    if (ticks.length <= MAX_TICKS) {
      break;
    }
  }
  return ticks;
}
