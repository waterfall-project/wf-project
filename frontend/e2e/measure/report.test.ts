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
  screenOf,
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

/** The paths of three screens of the journey. */
const PLANNING = "/projects/p/revisions/r/planning";
const ESTIMATE = "/projects/p/revisions/r/estimate";
const REMAINING = "/projects/p/revisions/r/remaining";

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
      { start: 1_010, end: 1_400, bytes: 30_000, path: PLANNING, prefetch: false },
      { start: 1_500, end: 1_600, bytes: 2_000, path: PLANNING, prefetch: false },
      // Outside the step: neither its time nor its bytes count.
      { start: 2_100, end: 2_200, bytes: 9_999, path: PLANNING, prefetch: false },
    ];
    const api = [answered(1_050, 1_250), answered(1_100, 1_300)];
    expect(partsOf(step, front, api, USER)).toEqual({
      usable: 1_000,
      api: 250,
      next: 390 + 100 - 250,
      browser: 1_000 - 490,
      bytes: 32_000,
      unweighed: 0,
      apiRequests: 2,
    });
  });

  it("counts the requests whose bytes are unknown, which a step waits for [WF-QUA-0060-A]", () => {
    const known = { start: 1_000, end: 1_200, bytes: 700, path: PLANNING, prefetch: false };
    const cut = failedRequest(0, 1_100, 1_500, true, PLANNING);
    const parts = partsOf(
      { start: 1_200, end: 2_000 },
      [known, cut],
      [answered(1_300, 1_400)],
      USER,
    );
    expect(parts).toMatchObject({ bytes: 0, unweighed: 1, apiRequests: 1 });
  });

  it("leaves the weight of a step that waited for a request of unknown bytes out of the statistic [WF-QUA-0060-A]", () => {
    // An API that answered during the step says Next rendered it: a weight of 0 is no download
    // that never was, but a request whose bytes the router cut short.
    const whole = { start: 1_000, end: 1_400, bytes: 49_855, path: PLANNING, prefetch: false };
    const cut = failedRequest(0, 900, 1_300, true, PLANNING);
    const step = { start: 1_000, end: 2_000 };
    const api = [answered(1_050, 1_250)];
    const weighed = partsOf(step, [whole], api, USER);
    const unknown = partsOf(step, [cut], api, USER);
    const samples = [
      { step: "open", pass: 0, parts: weighed },
      { step: "open", pass: 0, parts: unknown },
      { step: "open", pass: 0, parts: unknown },
    ];
    const reports = stepReports(["open"], samples, 1);
    expect(reports.open?.bytes).toMatchObject({ median: 49_855, worst: 49_855 });
    // Time stays: the step did wait for the cut request.
    expect(reports.open?.api_ms.median).toBe(200);
    expect(reports.open?.samples).toBe(3);
  });

  it("counts the time and the bytes of a prefetch the step waits for, of none it started itself", () => {
    const front = [
      // Asked as a menu opened, before the gesture, and still under way: the step waits for it.
      { start: 900, end: 1_300, bytes: 8_000, path: ESTIMATE, prefetch: true },
      // The links of the grid hydrated, prefetching the screens they lead to: for a step to come.
      { start: 1_900, end: 2_050, bytes: 50_000, path: REMAINING, prefetch: true },
    ];
    expect(partsOf({ start: 1_000, end: 2_000 }, front, [], USER)).toMatchObject({
      next: 300,
      browser: 700,
      bytes: 8_000,
    });
  });

  it("counts the time and the bytes of a prefetch the step started for the screen it ends on", () => {
    // The entry of the prefetch cache gone stale, the router asks the screen again, as a
    // prefetch, and the click waits for it: its bytes (none, once) and its time are the step's.
    const asked = { start: 1_050, end: 1_900, bytes: 49_795, path: PLANNING, prefetch: true };
    const links = { start: 1_100, end: 1_950, bytes: 50_000, path: ESTIMATE, prefetch: true };
    const parts = partsOf({ start: 1_000, end: 2_000 }, [asked, links], [], USER, PLANNING);
    expect(parts).toMatchObject({ next: 850, browser: 150, bytes: 49_795 });
    expect(partsOf({ start: 1_000, end: 2_000 }, [asked], [], USER).bytes).toBe(0);
  });

  it("counts a prefetch of the destination, query included, and not one of the same path for a step to come", () => {
    // Filter, sort and search stay on one path: the links of the grid prefetch it with the query
    // of a step to come, which this step does not wait for.
    const destination = screenOf(`http://x${ESTIMATE}?sort_by=x&_rsc=a1`);
    const asked = {
      start: 1_050,
      end: 1_900,
      bytes: 700,
      path: screenOf(`${ESTIMATE}?_rsc=b2&sort_by=x`),
      prefetch: true,
    };
    const later = {
      start: 1_100,
      end: 1_950,
      bytes: 50_000,
      path: screenOf(`${ESTIMATE}?search=y`),
      prefetch: true,
    };
    const api = [answered(1_100, 1_800), answered(1_910, 1_950)];
    const parts = partsOf({ start: 1_000, end: 2_000 }, [asked, later], api, USER, destination);
    expect(destination).toBe(`${ESTIMATE}?sort_by=x`);
    expect(parts).toMatchObject({ bytes: 700, api: 700, next: 150, browser: 150, apiRequests: 1 });
  });

  it("counts a request of the API only while a request of Next the step waits for is under way", () => {
    // The links of the grid prefetch the screens to come: under the load of several users their
    // requests of the API, queued, ran to the end of the step, and left it no browser at all.
    const document = { start: 0, end: 800, bytes: 100, path: PLANNING, prefetch: false };
    const links = { start: 300, end: 1_000, bytes: 9, path: ESTIMATE, prefetch: true };
    const api = [answered(100, 600), answered(350, 1_000), answered(900, 1_000)];
    const parts = partsOf({ start: 0, end: 1_000 }, [document, links], api, USER, PLANNING);
    expect(parts).toMatchObject({ usable: 1_000, api: 700, next: 100, browser: 200 });
    expect(parts.apiRequests).toBe(2);
  });

  it("leaves a request of the API under way while no request of Next is awaited to the browser", () => {
    const parts = partsOf({ start: 0, end: 100 }, [], [answered(10, 40)], USER);
    expect(parts).toMatchObject({ api: 0, next: 0, browser: 100, apiRequests: 0 });
  });

  it("leaves out the requests of another account, the client of getMe's among them", () => {
    const api = [answered(10, 40), answered(20, 90, PROBE, "/api/v1/me")];
    const document = { start: 0, end: 90, bytes: 1, path: PLANNING, prefetch: false };
    const parts = partsOf({ start: 0, end: 100 }, [document], api, USER);
    expect(parts).toMatchObject({ api: 30, next: 60, browser: 10, apiRequests: 1 });
    const reports = stepReports(["open"], [{ step: "open", pass: 0, parts }], 1);
    expect(reports.open).toMatchObject({ api_ms: { median: 30 }, api_requests: { median: 1 } });
  });
});

describe("failedRequest", () => {
  it("spans a request given up after its answer began from the start its timing gives", () => {
    expect(failedRequest(1_200, 1_190, 1_500, false, PLANNING)).toEqual({
      start: 1_200,
      end: 1_500,
      bytes: 0,
      path: PLANNING,
      prefetch: false,
      weighed: false,
    });
  });

  it("spans a request that failed before any answer from the moment the page asked it, not from 0", () => {
    const failed = failedRequest(0, 1_190, 1_500, true, ESTIMATE);
    expect(failed).toEqual({
      start: 1_190,
      end: 1_500,
      bytes: 0,
      path: ESTIMATE,
      prefetch: true,
      weighed: false,
    });
    // Within a step after it, a prefetch given up before its headers costs that step nothing.
    expect(partsOf({ start: 1_000, end: 1_100 }, [failed], [], USER).next).toBe(0);
  });

  it("covers nothing for a request failed before any answer whose asking was not kept", () => {
    expect(failedRequest(0, undefined, 1_500, false, PLANNING)).toMatchObject({
      start: 1_500,
      end: 1_500,
    });
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
      unweighed: 0,
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

describe("stepReports, bytes unknown", () => {
  const parts = (unweighed: number, bytes: number) => ({
    usable: 100,
    api: 50,
    next: 25,
    browser: 25,
    bytes,
    unweighed,
    apiRequests: 1,
  });

  it("gives no weight, neither 0 nor silence, when every sample waited for unknown bytes", () => {
    const { open } = stepReports(
      ["open"],
      [
        { step: "open", pass: 0, parts: parts(1, 0) },
        { step: "open", pass: 1, parts: parts(2, 300) },
      ],
      2,
    );
    expect(open).toMatchObject({ samples: 2, unweighed: 2, bytes: null });
    expect(open?.usable_ms.median).toBe(100);
  });

  it("counts the samples left out of the weight of the others", () => {
    const { open } = stepReports(
      ["open"],
      [
        { step: "open", pass: 0, parts: parts(0, 1_000) },
        { step: "open", pass: 1, parts: parts(1, 0) },
      ],
      2,
    );
    expect(open).toMatchObject({ samples: 2, unweighed: 1, bytes: { median: 1_000 } });
  });
});

describe("brokenSteps", () => {
  /** A level whose users completed each step in the one pass but where `missed` says. */
  const level = (users: number, missed: readonly string[]): LevelReport => {
    const parts = {
      usable: 100,
      api: 0,
      next: 0,
      browser: 100,
      bytes: 0,
      unweighed: 0,
      apiRequests: 0,
    };
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
