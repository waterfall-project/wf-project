// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { Caller } from "./background";
import {
  compareScale,
  GAP_FINDING,
  portfolioReading,
  type ScalePlatform,
  summary,
  timeReads,
} from "./scale";

/** A platform that read the revisions named by the keys of `medians`, in those seconds. */
function platform(projects: number, medians: Record<string, number>): ScalePlatform {
  return {
    projects,
    reads: Object.entries(medians).map(([name, median]) =>
      summary(name, median * 2, [median, median]),
    ),
  };
}

describe("compareScale", () => {
  it("finds the same duration on one project and on six hundred when no read is a quarter apart [WF-DAT-0050-A]", () => {
    const comparison = compareScale(
      platform(1, { a: 0.1, b: 0.2 }),
      platform(600, { a: 0.11, b: 0.2 }),
    );
    expect(comparison.finding).toBe(false);
    expect(comparison.gap).toBeCloseTo(0.033, 3);
    expect(comparison.reads.map(({ gap }) => gap)).toEqual([0.1, 0]);
    expect(comparison.note).toContain("No gap of more than a quarter.");
  });

  it("makes a finding of a read more than a quarter apart, and names it [WF-DAT-0050-A]", () => {
    const comparison = compareScale(
      platform(1, { a: 0.1, b: 1 }),
      platform(600, { a: 0.14, b: 1 }),
    );
    expect(GAP_FINDING).toBe(0.25);
    expect(comparison.finding).toBe(true);
    expect(comparison.note).toContain("A finding");
    expect(comparison.note).toContain("a (+40 %)");
  });

  it("makes a finding of the sum when it is a quarter apart, a faster platform included [WF-DAT-0050-A]", () => {
    const comparison = compareScale(platform(1, { a: 1 }), platform(600, { a: 0.5 }));
    expect(comparison.finding).toBe(true);
    expect(comparison.gap).toBe(-0.5);
  });

  it("refuses to compare platforms that did not read the same revisions [WF-DAT-0050-A]", () => {
    expect(() => compareScale(platform(1, { a: 1 }), platform(600, { b: 1 }))).toThrow(
      "the same revisions",
    );
    expect(() => compareScale(platform(1, {}), platform(600, {}))).toThrow("the same revisions");
  });

  it("calls the gap infinite against a read that took no time [WF-DAT-0050-A]", () => {
    const comparison = compareScale(platform(1, { a: 0 }), platform(600, { a: 0.1 }));
    expect(comparison.gap).toBe(Infinity);
    expect(comparison.finding).toBe(true);
  });
});

describe("timeReads", () => {
  it("keeps the first read apart and takes the median and the worst of the passes after it [WF-DAT-0050-A]", async () => {
    const durations = [0.9, 0.3, 0.1, 0.2];
    const api = {
      timed: () => Promise.resolve({ seconds: durations.shift() ?? 0, status: 200 }),
    } as unknown as Caller;
    expect(await timeReads(api, "read", "/path", 3)).toEqual({
      name: "read",
      first_s: 0.9,
      median_s: 0.2,
      worst_s: 0.3,
      passes: 3,
    });
  });

  it("refuses a read that does not answer 200 [WF-DAT-0050-A]", async () => {
    const api = { timed: () => Promise.resolve({ seconds: 0, status: 409 }) } as unknown as Caller;
    await expect(timeReads(api, "read", "/path", 2)).rejects.toThrow("answered 409, not 200");
  });

  it("leaves a read out when its first answer is the status it was told to leave [WF-DAT-0040]", async () => {
    const api = { timed: () => Promise.resolve({ seconds: 0, status: 409 }) } as unknown as Caller;
    expect(await timeReads(api, "read", "/path", 2, 409)).toBeUndefined();
  });

  it("refuses a summary of no pass [WF-DAT-0050-A]", () => {
    expect(() => summary("read", 1, [])).toThrow("no pass after the first");
  });
});

describe("portfolioReading", () => {
  it("does not warm a cache when the first reading is within the objective [US-2970]", () => {
    const reading = portfolioReading(300, 2, 1.5, [0.4, 0.5, 0.6]);
    expect(reading).toMatchObject({ warming: "not retained", cold_s: 1.5, hot_median_s: 0.5 });
    expect(reading.decision).toContain("first reading is within the objective");
  });

  it("warms the cache when the first reading is over the objective and the cache brings it back [US-2970]", () => {
    const reading = portfolioReading(300, 2, 9, [0.4, 0.5, 1.8]);
    expect(reading.warming).toBe("retained");
    expect(reading.decision).toContain("cold 9 s, hot 0.5 s, objective 2 s");
    expect(reading.hot_worst_s).toBe(1.8);
    expect(reading.hot_passes).toBe(3);
  });

  it("does not warm a cache that is not what costs: hot, the portfolio is over its objective too [US-2970]", () => {
    const reading = portfolioReading(300, 2, 9, [3, 4]);
    expect(reading.warming).toBe("not retained");
    expect(reading.decision).toContain("hot, the portfolio is over its objective too");
  });
});
