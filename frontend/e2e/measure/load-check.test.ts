// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import {
  gesturesExpected,
  type LoadRun,
  type LoadSummary,
  type Refusal,
  loadFailures,
  logText,
  refusalsOf,
  refusedTolerated,
  volumeFailures,
} from "./load-check";

/** The refusals a log names, as many as the summary counts. */
function named(count: number): Refusal[] {
  return Array.from({ length: count }, () => ({
    kind: "write",
    name: "estimate-line",
    status: 500,
  }));
}

/** No refusal named: what a load that refused nothing has. */
const NAMED: Refusal[] = [];

/** A load whose revision was marked at its half: frozen for the last 300 s of 600. */
const RUN: LoadRun = { users: 50, duration_s: 600, frozen_s: 300 };

/** A load that ran as asked: nearly three thousand gestures, nine readings in ten. */
const NOMINAL: LoadSummary = {
  users: 50,
  seed: 2300,
  gestures: 2900,
  reads: 2610,
  reads_frozen: 0,
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
    expect(loadFailures(NOMINAL, RUN, NAMED)).toEqual([]);
  });

  it("refuses a load whose every gesture was refused, as a whole [WF-QUA-0060-A]", () => {
    const failed = { ...NOMINAL, reads_refused: 2610, writes_refused: 290 };
    expect(loadFailures(failed, RUN, NAMED)).toHaveLength(2);
  });

  it("tolerates one entry refused, and not two, on seventy [WF-QUA-0060-A]", () => {
    const small = { ...NOMINAL, writes: 70 };
    expect(loadFailures({ ...small, writes_refused: 1 }, RUN, named(1))).toEqual([]);
    expect(loadFailures({ ...small, writes_refused: 2 }, RUN, named(2))).toEqual([
      "2 of 70 entries refused, 1 tolerated",
    ]);
  });

  it("does not tolerate an isolated refusal the log does not name [WF-QUA-0060-A]", () => {
    const small = { ...NOMINAL, writes: 70, writes_refused: 1 };
    expect(loadFailures(small, RUN, [])).toEqual([
      "1 of 70 entries refused, 0 tolerated, 1 refusal(s) not named",
    ]);
    expect(loadFailures(small, RUN, named(1))).toEqual([]);
    // The report full, what it does not name is the load's failure already, not a naming's.
    const failed = { ...NOMINAL, writes_refused: 60 };
    expect(loadFailures(failed, RUN, named(50))).toEqual([
      "60 of 290 entries refused, 2 tolerated",
    ]);
  });

  it("says, without failing, the entries refused over the tolerance when the saturation explains them, up to a tenth [US-2970]", () => {
    // 5 of 433 entries on the measure of 2026-11-27: over the tolerance of 4, far under a tenth.
    const seen = { ...NOMINAL, writes: 433, writes_refused: 5 };
    const saturation: string[] = [];
    expect(loadFailures(seen, RUN, named(5), saturation)).toEqual([]);
    expect(saturation).toEqual(["5 of 433 entries refused, 4 tolerated"]);
    // Asked without the list, it fails as it did.
    expect(loadFailures(seen, RUN, named(5))).toEqual(["5 of 433 entries refused, 4 tolerated"]);
    // Over a tenth, the load has failed as a whole, saturation or not.
    const failed = { ...NOMINAL, reads_refused: 300 };
    const none: string[] = [];
    expect(loadFailures(failed, RUN, named(50), none)).toEqual([
      "300 of 2610 readings refused, 26 tolerated",
    ]);
    expect(none).toEqual([]);
  });

  it("rounds the tolerated readings down, one at least [WF-QUA-0060-A]", () => {
    expect(refusedTolerated(70)).toBe(1);
    expect(refusedTolerated(577)).toBe(5);
    expect(refusedTolerated(2610)).toBe(26);
    const reads = { ...NOMINAL, reads: 577 };
    expect(loadFailures({ ...reads, reads_refused: 5 }, RUN, NAMED)).toEqual([]);
    expect(loadFailures({ ...reads, reads_refused: 6 }, RUN, NAMED)).toHaveLength(1);
  });

  it("reads the refusals from the log of k6 [WF-QUA-0060-A]", () => {
    const log = 'level=warning msg="refused write estimate-line: 500" source=console\nnoise\n';
    expect(refusalsOf(log)).toEqual([{ kind: "write", name: "estimate-line", status: 500 }]);
    expect(refusalsOf('msg="refused read a: 1"\n'.repeat(80))).toHaveLength(50);
  });

  it("reads two refusals, a name holding a colon, and not a noise [WF-QUA-0060-A]", () => {
    const log = [
      'time="t" level=warning msg="refused read plan: 502" source=console',
      'time="t" level=warning msg="refused write cell: a: b: 500" source=console',
      'time="t" level=info msg="a request refused by the proxy, see refused it" source=console',
      'time="t" level=info msg="refused write cell, no status" source=console',
    ].join("\n");
    expect(refusalsOf(log)).toEqual([
      { kind: "read", name: "plan", status: 502 },
      { kind: "write", name: "cell: a: b", status: 500 },
    ]);
  });

  it("composes the log without writing a missing output as text [WF-QUA-0060-A]", () => {
    expect(logText({ stdout: null, stderr: null })).toBe("\n");
    expect(logText({ stdout: "a", stderr: "b" })).toBe("a\nb");
    expect(logText({})).not.toContain("null");
  });

  it("refuses a load that wrote no summary [WF-QUA-0060-A]", () => {
    expect(loadFailures(undefined, RUN, NAMED)).toEqual(["the load wrote no summary"]);
  });

  it("refuses users refused for want of a token [WF-QUA-0060-A]", () => {
    expect(loadFailures({ ...NOMINAL, unauthorised: 12 }, RUN, NAMED)).toHaveLength(1);
  });

  it("tolerates the entries a marked revision refuses, and no other [WF-QUA-0060-A]", () => {
    const frozen = { ...NOMINAL, writes_frozen: 120 };
    expect(loadFailures(frozen, RUN, NAMED)).toEqual([]);
    expect(loadFailures(frozen, { ...RUN, frozen_s: 0 }, NAMED)).toHaveLength(2);
    expect(loadFailures({ ...NOMINAL, writes_refused: 40 }, RUN, NAMED)).toHaveLength(1);
  });

  it("refuses entries refused as frozen on a revision never frozen [WF-QUA-0060-A]", () => {
    const failures = loadFailures({ ...NOMINAL, writes_frozen: 3 }, { ...RUN, frozen_s: 0 }, NAMED);
    expect(failures).toContain("3 entries refused though the revision was never frozen");
  });

  it("tolerates every entry refused on a load frozen in whole [WF-QUA-0060-A]", () => {
    const frozen = { ...NOMINAL, writes_frozen: 290 };
    // Frozen for the whole of the load, refusing every entry is what the revision stood for.
    expect(loadFailures(frozen, { ...RUN, frozen_s: 600 }, NAMED)).toEqual([]);
  });

  it("bounds the entries refused as frozen by the share of the load the revision stood frozen [WF-QUA-0060-A]", () => {
    // Frozen for a tenth of the load: a tenth of the entries, and the slack, may be refused.
    const run = { ...RUN, frozen_s: 60 };
    expect(loadFailures({ ...NOMINAL, writes_frozen: 55 }, run, NAMED)).toEqual([]);
    expect(loadFailures({ ...NOMINAL, writes_frozen: 90 }, run, NAMED)).toHaveLength(1);
  });

  it("tolerates the readings a marked revision refuses, and no other [WF-QUA-0060-A]", () => {
    // The workload of a project left without a current revision, read after the marking.
    const frozen = { ...NOMINAL, reads_frozen: 8 };
    expect(loadFailures(frozen, RUN, NAMED)).toEqual([]);
    expect(loadFailures({ ...NOMINAL, reads_refused: 40 }, RUN, NAMED)).toHaveLength(1);
    expect(
      loadFailures({ ...NOMINAL, reads_frozen: 8, reads_refused: 40 }, RUN, NAMED),
    ).toHaveLength(1);
  });

  it("refuses readings refused as frozen on a revision never frozen [WF-QUA-0060-A]", () => {
    const failures = loadFailures({ ...NOMINAL, reads_frozen: 8 }, { ...RUN, frozen_s: 0 }, NAMED);
    expect(failures).toContain("8 readings refused though the revision was never frozen");
  });

  it("bounds the readings refused as frozen by the share of the load the revision stood frozen [WF-QUA-0060-A]", () => {
    const run = { ...RUN, frozen_s: 60 };
    expect(loadFailures({ ...NOMINAL, reads_frozen: 500 }, run, NAMED)).toEqual([]);
    expect(loadFailures({ ...NOMINAL, reads_frozen: 900 }, run, NAMED)).toHaveLength(1);
  });

  it("refuses a load that made far fewer gestures than its pauses promise [WF-QUA-0060-A]", () => {
    const few = { ...NOMINAL, gestures: 900, reads: 810, writes: 90 };
    expect(loadFailures(few, RUN, NAMED)).toHaveLength(1);
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
