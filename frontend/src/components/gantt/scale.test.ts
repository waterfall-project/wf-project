// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
// Aucune exigence : propre à l'US (US-0530, l'échelle de temps à cinq niveaux et le zoom).
import { describe, expect, it } from "vitest";

import {
  centredOffset,
  DAY,
  fittedLevel,
  levelsWith,
  revealedOffset,
  SCALE_LEVELS,
  scaleTicks,
  widthAt,
  zoomed,
} from "./scale";

const at = (date: string) => Date.parse(`${date}T00:00:00Z`);
const dates = (ticks: readonly number[]) =>
  ticks.map((tick) => new Date(tick).toISOString().slice(0, 10));

describe("the scale of the Gantt", () => {
  it("has five levels, from years and quarters down to days and worked hours", () => {
    expect(SCALE_LEVELS.map((level) => `${level.upper}/${level.lower}`)).toEqual([
      "year/quarter",
      "quarter/month",
      "month/week",
      "week/day",
      "day/hour",
    ]);
    // The hours of a day are those of the installation: without them, the scale stops at days.
    expect(levelsWith(undefined)).toBe(4);
    expect(levelsWith(8)).toBe(5);
  });

  it.each([
    ["year", ["2025-01-01", "2026-01-01", "2027-01-01"]],
    ["quarter", ["2025-10-01", "2026-01-01", "2026-04-01", "2026-07-01"]],
    ["month", ["2025-12-01", "2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01", "2026-05-01"]],
  ] as const)(
    "marks each %s from the one under way at the start to the end, in UTC",
    (unit, marked) => {
      expect(dates(scaleTicks(unit, at("2025-12-15"), at("2026-04-02")))).toEqual(marked);
    },
  );

  it("starts a week on Monday, whatever the day the span starts", () => {
    // 2026-03-01 is a Sunday: its week began on Monday 23 February.
    expect(dates(scaleTicks("week", at("2026-03-01"), at("2026-03-10")))).toEqual([
      "2026-02-23",
      "2026-03-02",
      "2026-03-09",
      "2026-03-16",
    ]);
    expect(dates(scaleTicks("day", at("2026-03-01"), at("2026-03-03")))).toEqual([
      "2026-03-01",
      "2026-03-02",
      "2026-03-03",
    ]);
  });

  it("divides each day into its worked hours, the end of the last day closing them", () => {
    const ticks = scaleTicks("hour", at("2026-03-02"), at("2026-03-04"), 8);
    expect(ticks).toHaveLength(17);
    expect(ticks[1]).toBe(at("2026-03-02") + DAY / 8);
    expect(ticks.at(-1)).toBe(at("2026-03-04"));
  });

  it("draws a span wider at each finer level, the hours by the hours of a day", () => {
    const span = 60 * DAY;
    const widths = SCALE_LEVELS.slice(0, 4).map((_, level) => widthAt(level, span));
    expect(widths).toEqual([30, 90, 360, 1440]);
    expect(widthAt(4, span, 8)).toBe(9600);
  });

  it("fits a project at the finest level its column holds, the coarsest when none does", () => {
    expect(fittedLevel(60 * DAY, 400, 4)).toBe(2);
    expect(fittedLevel(60 * DAY, 2000, 4)).toBe(3);
    expect(fittedLevel(40 * 365 * DAY, 400, 4)).toBe(0);
  });

  it("zooms a level in or out from the one shown, within those offered", () => {
    expect(zoomed("fit", 2, 1, 4)).toBe(3);
    expect(zoomed("fit", 2, -1, 4)).toBe(1);
    expect(zoomed(3, 2, 1, 4)).toBe(3);
    expect(zoomed(0, 2, -1, 4)).toBe(0);
  });

  it("keeps the date at the centre of the frame, within the bounds of the drawing", () => {
    // The middle of the axis, redrawn 1 440 wide in a frame of 400: 520 to its left.
    expect(centredOffset(0.5, 1440, 400)).toBe(520);
    expect(centredOffset(0.01, 1440, 400)).toBe(0);
    expect(centredOffset(0.99, 1440, 400)).toBe(1040);
    expect(centredOffset(0.5, 300, 400)).toBe(0);
  });

  it("scrolls the least that brings a stretch into the frame", () => {
    // A frame of 400 over 1440, scrolled by 500: it shows 500 to 900.
    expect(revealedOffset({ from: 0.4, to: 0.5 }, 1440, 400, 500)).toBe(500);
    expect(revealedOffset({ from: 0.1, to: 0.2 }, 1440, 400, 500)).toBe(144);
    expect(revealedOffset({ from: 0.7, to: 0.8 }, 1440, 400, 500)).toBe(752);
    expect(revealedOffset({ from: 0.2, to: 0.9 }, 1440, 400, 500)).toBe(288);
    expect(revealedOffset({ from: 0.95, to: 1 }, 1440, 400, 500)).toBe(1040);
    expect(revealedOffset({ from: 0, to: 0.1 }, 300, 400, 0)).toBe(0);
  });
});
