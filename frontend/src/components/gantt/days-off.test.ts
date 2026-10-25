// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { DAY_OFF_HATCH, dayOffBands, hasDaysOff } from "./days-off";

/** The tokens of the charter, which the classes of the hatching paint with. */
const CSS = readFileSync(join(import.meta.dirname, "../../theme/globals.css"), "utf-8");

const WEEK = {
  monday: "8",
  tuesday: "8",
  wednesday: "8",
  thursday: "8",
  friday: "8",
  saturday: "0",
  sunday: "0.00",
};

/** The midnight that starts a day, in UTC. */
function day(date: string): number {
  return Date.parse(`${date}T00:00:00Z`);
}

describe("the days off of a task in the Gantt", () => {
  // WF-PLA-0090 : les jours à 0 heure du calendrier de la tâche sont ses jours chômés.
  it("are the days at 0 hours of its calendar, a weekend one band [WF-PLA-0090-A]", () => {
    // From Monday 2 March to Monday 16 March 2026: two weekends.
    const bands = dayOffBands(WEEK, { from: day("2026-03-02"), to: day("2026-03-16") }, 6);
    expect(bands).toEqual([
      { from: day("2026-03-07"), to: day("2026-03-09") },
      { from: day("2026-03-14"), to: day("2026-03-16") },
    ]);
  });

  it("follow the calendar of each task: a Wednesday off is a band of its own [WF-PLA-0090-A]", () => {
    const bands = dayOffBands(
      { ...WEEK, wednesday: "0", saturday: "4", sunday: "4" },
      { from: day("2026-03-02"), to: day("2026-03-09") },
      6,
    );
    expect(bands).toEqual([{ from: day("2026-03-04"), to: day("2026-03-05") }]);
  });

  it("are none for a calendar worked every day, without calendar, or where a day takes under a pixel [WF-PLA-0090-A]", () => {
    const extent = { from: day("2026-03-02"), to: day("2026-04-02") };
    const worked = { ...WEEK, saturday: "8", sunday: "8" };
    expect(hasDaysOff(worked)).toBe(false);
    expect(dayOffBands(worked, extent, 24)).toEqual([]);
    expect(dayOffBands(undefined, extent, 24)).toEqual([]);
    expect(hasDaysOff(WEEK)).toBe(true);
    expect(dayOffBands(WEEK, extent, 0.5)).toEqual([]);
    expect(dayOffBands(WEEK, extent, 1.5)).not.toEqual([]);
  });
});

// aucune exigence : propre à l'US (US-0530, la teinte que l'écran et l'image reprennent, #1420).
describe("the hatching of the days off", () => {
  it("is painted by tokens of the charter, light and dark, that its classes read on the screen and in the image", () => {
    const { fillToken, markToken, fillClass, markClass } = DAY_OFF_HATCH;
    for (const token of [fillToken, markToken]) {
      expect(CSS).toMatch(new RegExp(`\\s${token}: light-dark\\(#[0-9a-f]{6}, #[0-9a-f]{6}\\);`));
    }
    // `fill-day-off` and `stroke-day-off-mark` are the colours of Tailwind on the tokens.
    expect(CSS).toContain(`--color-${fillClass.replace(/^fill-/, "")}: var(${fillToken});`);
    expect(CSS).toContain(`--color-${markClass.replace(/^stroke-/, "")}: var(${markToken});`);
  });
});
