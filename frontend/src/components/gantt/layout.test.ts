// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { NodeList } from "@/components/grid/nodes";
import { example } from "@/test/fixtures";

import { finishTime, ganttLayout, startTime } from "./layout";

// The studies of the witness, without their lines: the summary from 2 March to 24 April 2026, the
// detailed studies, the desks in manual mode, the review after the studies, the reception at its
// end — a milestone, also linked from start to start to the desks —, and the design file.
const planning = example("nodes_planning") as NodeList;
const [studies, detailed, desks, review, reception, dossier] = planning.items;

/** The midnight that starts a day, in UTC. */
function day(date: string): number {
  return Date.parse(`${date}T00:00:00Z`);
}

describe("the layout of the Gantt", () => {
  it("places a task from the start of its first day to the end of its last, as the API dates it", () => {
    expect(startTime({ date: "2026-03-02", hours: "0" })).toBe(day("2026-03-02"));
    expect(finishTime({ date: "2026-04-10", hours: "8" })).toBe(day("2026-04-11"));
    // A finish at hour 0 is the very start of its day.
    expect(finishTime({ date: "2026-04-10", hours: "0.00" })).toBe(day("2026-04-10"));
  });

  it("runs its axis over the months of the dates, the first of each month a tick", () => {
    const layout = ganttLayout(planning.items);
    expect(layout.ticks.map((tick) => new Date(tick).toISOString().slice(0, 10))).toEqual([
      "2026-03-01",
      "2026-04-01",
      "2026-05-01",
    ]);
    expect(layout.at(day("2026-03-01"))).toBe(0);
    expect(layout.at(day("2026-05-01"))).toBe(1);
  });

  it("draws a bar for a task, a bracket for a summary, a diamond at its finish for a milestone, the critical path apart", () => {
    const layout = ganttLayout(planning.items);
    const at = (date: string) => layout.at(day(date));
    expect(studies && layout.bar(studies)).toEqual({
      from: at("2026-03-02"),
      to: at("2026-04-25"),
      nature: "summary",
      critical: false,
    });
    expect(detailed && layout.bar(detailed)).toEqual({
      from: at("2026-03-02"),
      to: at("2026-04-11"),
      nature: "task",
      critical: true,
    });
    expect(reception && layout.bar(reception)).toEqual({
      from: at("2026-04-25"),
      to: at("2026-04-25"),
      nature: "milestone",
      critical: true,
    });
    // The desks, in manual mode, are on no critical path; the dossier has its float.
    expect([desks, dossier].map((task) => task && layout.bar(task)?.critical)).toEqual([
      false,
      false,
    ]);
  });

  it("joins each task to its predecessors: from the finish or the start the link names, to the start or the finish", () => {
    const layout = ganttLayout(planning.items);
    const at = (date: string) => layout.at(day(date));
    // The review follows the detailed studies, finish to start: the link leaves the studies at
    // their finish, passes by the desks, and reaches the review at its start.
    const link = { out: at("2026-04-11"), in: at("2026-04-13"), down: true };
    expect(layout.links(detailed?.node_id ?? "")).toContainEqual({ ...link, part: "leaves" });
    expect(layout.links(desks?.node_id ?? "")).toContainEqual({ ...link, part: "passes" });
    expect(layout.links(review?.node_id ?? "")).toContainEqual({ ...link, part: "arrives" });
    // The reception follows the desks from start to start, two rows up: it is reached where it
    // stands, a milestone, at its finish.
    expect(layout.links(reception?.node_id ?? "")).toContainEqual({
      out: at("2026-03-02"),
      in: at("2026-04-25"),
      down: true,
      part: "arrives",
    });
    // The summary, above every link, draws none.
    expect(layout.links(studies?.node_id ?? "")).toEqual([]);
  });

  it("draws no link to a predecessor the answer does not hold, and nothing for a task without dates", () => {
    const retained = planning.items.filter((node) => node.node_id !== detailed?.node_id);
    const layout = ganttLayout(retained);
    // The review, whose one predecessor is gone, is reached by no link; the links of the
    // reception, below it, still leave it and pass it by.
    expect(layout.links(review?.node_id ?? "").map((link) => link.part)).toEqual([
      "leaves",
      "passes",
    ]);
    const undated = { node_id: "undated", task: { is_summary: false, is_milestone: false } };
    expect(layout.bar(undated)).toBeUndefined();
    expect(layout.links("unknown")).toEqual([]);
    expect(ganttLayout([undated]).ticks).toEqual([]);
  });
});
