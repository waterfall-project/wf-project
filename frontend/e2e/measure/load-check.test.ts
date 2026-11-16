// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import {
  gesturesExpected,
  type LoadRun,
  type LoadSummary,
  loadFailures,
  volumeFailures,
} from "./load-check";

/** A load whose revision was marked at its half: frozen for the last 300 s of 600. */
const RUN: LoadRun = { users: 50, duration_s: 600, frozen_s: 300 };

/** A load that ran as asked: nearly three thousand gestures, nine readings in ten. */
const NOMINAL: LoadSummary = {
  users: 50,
  seed: 2300,
  gestures: 2900,
  reads: 2610,
  reads_refused: 0,
  writes: 290,
  writes_frozen: 0,
  writes_refused: 0,
  unauthorised: 0,
  requests: 9000,
};

describe("loadFailures", () => {
  it("accepts a load that ran as asked [WF-QUA-0060-A]", () => {
    expect(gesturesExpected(50, 600)).toBe(3000);
    expect(loadFailures(NOMINAL, RUN)).toEqual([]);
  });

  it("refuses a load whose every gesture was refused, as a whole [WF-QUA-0060-A]", () => {
    const failed = { ...NOMINAL, reads_refused: 2610, writes_refused: 290 };
    expect(loadFailures(failed, RUN)).toHaveLength(2);
  });

  it("refuses a load that wrote no summary [WF-QUA-0060-A]", () => {
    expect(loadFailures(undefined, RUN)).toEqual(["the load wrote no summary"]);
  });

  it("refuses users refused for want of a token [WF-QUA-0060-A]", () => {
    expect(loadFailures({ ...NOMINAL, unauthorised: 12 }, RUN)).toHaveLength(1);
  });

  it("tolerates the entries a marked revision refuses, and no other [WF-QUA-0060-A]", () => {
    const frozen = { ...NOMINAL, writes_frozen: 120 };
    expect(loadFailures(frozen, RUN)).toEqual([]);
    expect(loadFailures(frozen, { ...RUN, frozen_s: 0 })).toHaveLength(2);
    expect(loadFailures({ ...NOMINAL, writes_refused: 40 }, RUN)).toHaveLength(1);
  });

  it("refuses entries refused as frozen on a revision never frozen [WF-QUA-0060-A]", () => {
    const failures = loadFailures({ ...NOMINAL, writes_frozen: 3 }, { ...RUN, frozen_s: 0 });
    expect(failures).toContain("3 entries refused though the revision was never frozen");
  });

  it("tolerates every entry refused on a load frozen in whole [WF-QUA-0060-A]", () => {
    const frozen = { ...NOMINAL, writes_frozen: 290 };
    // Frozen for the whole of the load, refusing every entry is what the revision stood for.
    expect(loadFailures(frozen, { ...RUN, frozen_s: 600 })).toEqual([]);
  });

  it("bounds the entries refused as frozen by the share of the load the revision stood frozen [WF-QUA-0060-A]", () => {
    // Frozen for a tenth of the load: a tenth of the entries, and the slack, may be refused.
    const run = { ...RUN, frozen_s: 60 };
    expect(loadFailures({ ...NOMINAL, writes_frozen: 55 }, run)).toEqual([]);
    expect(loadFailures({ ...NOMINAL, writes_frozen: 90 }, run)).toHaveLength(1);
  });

  it("refuses a load that made far fewer gestures than its pauses promise [WF-QUA-0060-A]", () => {
    const few = { ...NOMINAL, gestures: 900, reads: 810, writes: 90 };
    expect(loadFailures(few, RUN)).toHaveLength(1);
  });
});

describe("volumeFailures", () => {
  it("accepts a thousand tasks of five lines each, or of the 4,999 lines the witness carries [WF-QUA-0060-A]", () => {
    expect(volumeFailures({ tasks: 1000, estimate_lines: 5000 })).toEqual([]);
    expect(volumeFailures({ tasks: 1000, estimate_lines: 4999 })).toEqual([]);
  });

  it("refuses fewer than a thousand tasks, or fewer than five lines a task [WF-QUA-0060-A]", () => {
    expect(volumeFailures({ tasks: 999, estimate_lines: 6000 })).toHaveLength(1);
    expect(volumeFailures({ tasks: 1000, estimate_lines: 4000 })).toHaveLength(1);
    expect(volumeFailures({ tasks: 40, estimate_lines: 40 })).toHaveLength(2);
  });
});
