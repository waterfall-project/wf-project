// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The arithmetic of the measure of the journey of the grids against the service (US-2210): a tool
 * of the repository, which covers no requirement of its own and cites none.
 */
import { describe, expect, it } from "vitest";

import {
  apiRequests,
  brokenSteps,
  covered,
  failedRequest,
  getMeDurations,
  getMeReport,
  type LevelReport,
  momentOf,
  partsOf,
  statisticOf,
  stepReports,
} from "./report";

/** A record of the API closing a request, as it writes it: one line of JSON. */
function record(fields: Record<string, unknown>): string {
  return JSON.stringify({ event: "request.completed", level: "info", ...fields });
}

/** The account of a user of the measure, and that of the client of `getMe`. */
const USER = "01926f3a-7c00-7000-8000-000000000901";
const PROBE = "01926f3a-7c00-7000-8000-000000000999";

/** A request the API answered for an account, from its start to its end. */
function answered(start: number, end: number, actor = USER, path = "/api/v1/projects") {
  return { start, end, actor, method: "GET", path, status: 200 };
}

describe("covered", () => {
  it("counts each instant once, overlapping spans merged, within the window alone", () => {
    const window = { start: 100, end: 200 };
    const spans = [
      { start: 50, end: 120 },
      { start: 110, end: 130 },
      { start: 150, end: 160 },
      { start: 190, end: 260 },
    ];
    expect(covered(spans, window)).toBe(30 + 10 + 10);
  });

  it("counts nothing of a span outside the window", () => {
    expect(covered([{ start: 0, end: 10 }], { start: 20, end: 30 })).toBe(0);
  });
});

describe("partsOf", () => {
  it("splits a step into the API, Next by difference and the browser, and sums the bytes of Next", () => {
    const step = { start: 1_000, end: 2_000 };
    const front = [
      { start: 1_010, end: 1_400, bytes: 30_000, prefetch: false },
      { start: 1_500, end: 1_600, bytes: 2_000, prefetch: false },
      // Outside the step: neither its time nor its bytes count.
      { start: 2_100, end: 2_200, bytes: 9_999, prefetch: false },
    ];
    const api = [answered(1_050, 1_250), answered(1_100, 1_300)];
    expect(partsOf(step, front, api, USER)).toEqual({
      usable: 1_000,
      api: 250,
      next: 390 + 100 - 250,
      browser: 1_000 - 490,
      bytes: 32_000,
      apiRequests: 2,
    });
  });

  it("counts the time and the bytes of a prefetch the step waits for, of none it started itself", () => {
    const front = [
      // Asked as a menu opened, before the gesture, and still under way: the step waits for it.
      { start: 900, end: 1_300, bytes: 8_000, prefetch: true },
      // The links of the grid hydrated, prefetching the screens they lead to: for a step to come.
      { start: 1_900, end: 2_050, bytes: 50_000, prefetch: true },
    ];
    expect(partsOf({ start: 1_000, end: 2_000 }, front, [], USER)).toMatchObject({
      next: 300,
      browser: 700,
      bytes: 8_000,
    });
  });

  it("counts a request of the API that Next made outside any answer to the browser in the server's part", () => {
    const parts = partsOf({ start: 0, end: 100 }, [], [answered(10, 40)], USER);
    expect(parts).toMatchObject({ api: 30, next: 0, browser: 70 });
  });

  it("leaves out the requests of another account, the client of getMe's among them", () => {
    const api = [answered(10, 40), answered(20, 90, PROBE, "/api/v1/me")];
    const parts = partsOf({ start: 0, end: 100 }, [], api, USER);
    expect(parts).toMatchObject({ api: 30, next: 0, browser: 70, apiRequests: 1 });
    const reports = stepReports(["open"], [{ step: "open", pass: 0, parts }], 1);
    expect(reports.open).toMatchObject({ api_ms: { median: 30 }, api_requests: { median: 1 } });
  });
});

describe("failedRequest", () => {
  it("spans a request given up after its answer began from the start its timing gives", () => {
    expect(failedRequest(1_200, 1_190, 1_500, false)).toEqual({
      start: 1_200,
      end: 1_500,
      bytes: 0,
      prefetch: false,
    });
  });

  it("spans a request that failed before any answer from the moment the page asked it, not from 0", () => {
    const failed = failedRequest(0, 1_190, 1_500, true);
    expect(failed).toEqual({ start: 1_190, end: 1_500, bytes: 0, prefetch: true });
    // Within a step after it, a prefetch given up before its headers costs that step nothing.
    expect(partsOf({ start: 1_000, end: 1_100 }, [failed], [], USER).next).toBe(0);
  });

  it("covers nothing for a request failed before any answer whose asking was not kept", () => {
    expect(failedRequest(0, undefined, 1_500, false)).toMatchObject({ start: 1_500, end: 1_500 });
  });
});

describe("momentOf", () => {
  it("reads a moment of the API to the microsecond, in UTC", () => {
    expect(momentOf("2026-11-14T20:01:17.123456Z")).toBeCloseTo(
      Date.UTC(2026, 10, 14, 20, 1, 17) + 123.456,
      6,
    );
    expect(momentOf("2026-11-14T20:01:17+00:00")).toBe(Date.UTC(2026, 10, 14, 20, 1, 17));
  });

  it("refuses a moment that is not in UTC", () => {
    expect(momentOf("2026-11-14T20:01:17+01:00")).toBeNaN();
  });
});

describe("apiRequests", () => {
  it("reads the requests the API closed, spanning their duration before their record, the clock of the API set back", () => {
    const log = [
      "starting the API",
      record({
        timestamp: "2026-11-14T20:00:00.500000Z",
        duration_ms: 120.5,
        actor: "01926f3a-7c00-7000-8000-000000000999",
        method: "GET",
        path: "/api/v1/me",
        status: 200,
      }),
      JSON.stringify({ event: "account.admitted", timestamp: "2026-11-14T20:00:00Z" }),
      `{"event": "request.completed", "broken`,
    ].join("\n");
    const end = Date.UTC(2026, 10, 14, 20, 0, 0) + 500 - 2;
    expect(apiRequests(log, 2)).toEqual([
      {
        start: end - 120.5,
        end,
        actor: "01926f3a-7c00-7000-8000-000000000999",
        method: "GET",
        path: "/api/v1/me",
        status: 200,
      },
    ]);
  });

  it("reads a record behind the prefix a log may put before it", () => {
    const line = `api-1  | ${record({ timestamp: "2026-11-14T20:00:00Z", duration_ms: 3 })}`;
    expect(apiRequests(line)).toHaveLength(1);
  });
});

describe("statisticOf", () => {
  it("gives the median and the worst of every sample, and the spread of the medians of the passes", () => {
    expect(statisticOf([[100, 300], [200], [150, 170, 400]])).toEqual({
      median: 185,
      worst: 400,
      spread: 30,
    });
  });

  it("leaves a pass without any sample out of the spread", () => {
    expect(statisticOf([[100], [], [120]])).toEqual({ median: 110, worst: 120, spread: 20 });
  });

  it("gives no spread when fewer than two passes have a sample, rather than a 0 that says stable", () => {
    expect(statisticOf([[100, 140], []])).toEqual({ median: 120, worst: 140, spread: null });
    expect(statisticOf([[], []])).toEqual({ median: 0, worst: 0, spread: null });
  });
});

describe("stepReports", () => {
  it("reports each step in the order of the journey, counting the passes it did not complete", () => {
    const parts = (usable: number) => ({
      usable,
      api: usable / 2,
      next: usable / 4,
      browser: usable / 4,
      bytes: 1_000,
      apiRequests: 3,
    });
    const reports = stepReports(
      ["open", "write"],
      [
        { step: "open", pass: 0, parts: parts(400) },
        { step: "open", pass: 1, parts: parts(600) },
        { step: "write", pass: 0, parts: parts(200) },
        { step: "write", pass: 1, parts: undefined },
      ],
      2,
    );
    expect(Object.keys(reports)).toEqual(["open", "write"]);
    expect(reports.open).toMatchObject({
      samples: 2,
      incomplete: 0,
      usable_ms: { median: 500, worst: 600, spread: 200 },
      api_ms: { median: 250, worst: 300, spread: 100 },
      bytes: { median: 1_000, worst: 1_000, spread: 0 },
    });
    expect(reports.write).toMatchObject({
      samples: 1,
      incomplete: 1,
      usable_ms: { median: 200, worst: 200, spread: null },
    });
  });
});

describe("brokenSteps", () => {
  /** A level whose users completed each step in the one pass but where `missed` says. */
  const level = (users: number, missed: readonly string[]): LevelReport => {
    const parts = { usable: 100, api: 0, next: 0, browser: 100, bytes: 0, apiRequests: 0 };
    const steps = ["open", "filter", "sort"];
    const samples = steps.map((step) => ({
      step,
      pass: 0,
      parts: missed.includes(step) ? undefined : parts,
    }));
    return {
      users,
      steps: stepReports(steps, samples, 1),
      get_me: getMeReport({ api: [], roundTrip: [], lost: 0 }),
    };
  };

  it("names the steps a user alone did not complete: a journey that no longer works", () => {
    expect(brokenSteps([level(1, ["filter", "sort"])])).toEqual(["filter", "sort"]);
  });

  it("names none that only four or eight users did not complete: the load's doing", () => {
    expect(brokenSteps([level(1, []), level(4, ["open"]), level(8, ["sort"])])).toEqual([]);
  });
});

describe("getMe", () => {
  it("reads the durations of getMe the API answered within a span, whoever asked", () => {
    const at = (start: number, path: string, method = "GET") => ({
      start,
      end: start + 20,
      actor: "anyone",
      method,
      path,
      status: 200,
    });
    const requests = [
      at(10, "/api/v1/me"),
      at(30, "/api/v1/me/preferences", "PATCH"),
      at(50, "/api/v1/me"),
      at(500, "/api/v1/me"),
    ];
    expect(getMeDurations(requests, { start: 0, end: 100 })).toEqual([20, 20]);
  });

  it("reports getMe at the API and as its client asked it, and the askings it lost", () => {
    expect(getMeReport({ api: [[10, 30], [20]], roundTrip: [[15], [25]], lost: 1 })).toEqual({
      samples: 3,
      lost: 1,
      api_ms: { median: 20, worst: 30, spread: 0 },
      round_trip_ms: { median: 20, worst: 25, spread: 10 },
    });
  });
});
