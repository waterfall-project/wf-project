// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  addressOf,
  fieldOf,
  isInstant,
  localDay,
  periodHref,
  readPeriod,
  refusedPeriod,
} from "./period";

describe("a period in the address", () => {
  it("reads two days of planning, a day that is none not asked", () => {
    expect(readPeriod(new URLSearchParams("from=2026-03-01&to=2026-03-16"), "date")).toEqual({
      from: "2026-03-01",
      to: "2026-03-16",
    });
    expect(readPeriod(new URLSearchParams("from=2026-02-30&to=16/03/2026"), "date")).toEqual({
      from: undefined,
      to: undefined,
    });
  });

  it("reads two instants, an instant that is none — or a day alone — not asked", () => {
    const search = new URLSearchParams("from=2026-02-28T23:00:00.000Z&to=2026-03-01");
    expect(readPeriod(search, "day")).toEqual({ from: "2026-02-28T23:00:00.000Z", to: undefined });
    expect(isInstant("2026-02-30T00:00:00Z")).toBe(false);
    expect(isInstant("2026-03-01T24:00:00Z")).toBe(false);
    expect(isInstant("2026-03-01T10:00:00+01:00")).toBe(true);
  });

  it("writes the period, a side left empty lifted, back to the first page of a paged list, the rest kept", () => {
    const query = new URLSearchParams("sort_by=code&offset=50&to=2026-04-30");
    expect(periodHref("/", query, { from: "2026-03-01", to: undefined }, { page: "offset" })).toBe(
      "/?sort_by=code&from=2026-03-01",
    );
    expect(
      periodHref("/", new URLSearchParams("from=2026-03-01"), { from: "", to: undefined }),
    ).toBe("/");
  });

  it("reads the sides the API refused, by the start it names or a bound it does not take", () => {
    expect(
      refusedPeriod([
        { pointer: "/query/to", code: "VALUE_OUT_OF_RANGE", params: { minimum: "2026-03-31" } },
        { pointer: "/query/from", code: "DATE_INVALID" },
      ]),
    ).toEqual({
      to: { code: "VALUE_OUT_OF_RANGE", minimum: "2026-03-31" },
      from: { code: "DATE_INVALID" },
    });
    // Another field, another code, or a start not named, name no side.
    expect(
      refusedPeriod([
        { pointer: "/query/states", code: "VALUE_OUT_OF_RANGE", params: { minimum: "2026-03-31" } },
        { pointer: "/query/to", code: "VALUE_REQUIRED" },
        { pointer: "/query/to", code: "VALUE_OUT_OF_RANGE" },
      ]),
    ).toBeUndefined();
  });
});

describe("the fields of a period, in the local time of the workstation", () => {
  const original = process.env.TZ;

  beforeEach(() => {
    process.env.TZ = "Europe/Paris";
  });

  afterEach(() => {
    process.env.TZ = original;
  });

  it("draws the instants of local days: the start of the first, the start of the day after the last", () => {
    expect(addressOf("day", "from", "2026-03-01")).toBe("2026-02-28T23:00:00.000Z");
    expect(addressOf("day", "to", "2026-03-31")).toBe("2026-03-31T22:00:00.000Z");
    expect(addressOf("day", "from", "")).toBeUndefined();
    expect(addressOf("day", "from", "2026-02-30")).toBeUndefined();
  });

  it("draws and shows the days the clocks change, which last 23 and 25 hours, by their local starts, never 24 hours apart", () => {
    // The clocks go forward on 29 March: that day starts at 23:00 in universal time, the next one
    // at 22:00, 23 hours later.
    expect(addressOf("day", "to", "2026-03-29")).toBe("2026-03-29T22:00:00.000Z");
    expect(fieldOf("day", "to", "2026-03-29T22:00:00.000Z")).toBe("2026-03-29");
    // They go back on 25 October: that day starts at 22:00 in universal time, the next one at
    // 23:00, 25 hours later.
    expect(addressOf("day", "to", "2026-10-25")).toBe("2026-10-25T23:00:00.000Z");
    expect(fieldOf("day", "to", "2026-10-25T23:00:00.000Z")).toBe("2026-10-25");
  });

  it("shows the local days of the instants, the end excluded shown by the last day it keeps", () => {
    expect(fieldOf("day", "from", "2026-02-28T23:00:00.000Z")).toBe("2026-03-01");
    expect(fieldOf("day", "to", "2026-03-31T22:00:00.000Z")).toBe("2026-03-31");
    // A modification at 23:30 in universal time on 28 February is of 1 March in Paris.
    expect(localDay("2026-02-28T23:30:00Z")).toBe("2026-03-01");
  });

  it("writes and shows the instants entered to the minute, the days of planning as they are", () => {
    expect(addressOf("instant", "to", "2026-05-01T08:00")).toBe("2026-05-01T06:00:00.000Z");
    expect(fieldOf("instant", "from", "2026-05-01T06:00:00Z")).toBe("2026-05-01T08:00");
    expect(addressOf("date", "to", "2026-04-30")).toBe("2026-04-30");
    expect(fieldOf("date", "to", "2026-04-30")).toBe("2026-04-30");
  });
});

describe("the fields of a period, west of Greenwich", () => {
  const original = process.env.TZ;

  beforeEach(() => {
    process.env.TZ = "America/New_York";
  });

  afterEach(() => {
    process.env.TZ = original;
  });

  it("draws and shows the local days of New York, five hours behind universal time in winter", () => {
    // 03:00 in universal time on 1 March is still 28 February in New York.
    expect(localDay("2026-03-01T03:00:00Z")).toBe("2026-02-28");
    expect(fieldOf("day", "from", "2026-03-01T03:00:00Z")).toBe("2026-02-28");
    expect(addressOf("day", "from", "2026-03-01")).toBe("2026-03-01T05:00:00.000Z");
    expect(fieldOf("day", "from", "2026-03-01T05:00:00.000Z")).toBe("2026-03-01");
  });
});
