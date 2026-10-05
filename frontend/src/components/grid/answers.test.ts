// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import { answersOf, shownRow, take } from "./answers";
import { ESTIMATE_FIELDS } from "./estimate";
import {
  type AnyNodeFields,
  type NodeList,
  type NodesWritten,
  nodeKey,
  nodesWritten,
  projectNodes,
} from "./nodes";
import { PLANNING_FIELDS, type PlanningNode } from "./planning";

// The witness planning, and the link that reschedules two of its tasks (`predecessor_set`): the
// review written, its summary recalculated, the acceptance that follows it moved to 29 April, and
// the design file, its dates unchanged, put on the critical path.
const planning = example("nodes_planning") as NodeList;
const linked = example("predecessor_set") as NodesWritten;
const REVIEW = "01926f3a-7c00-7000-8000-000000000524";
const ACCEPTANCE = "01926f3a-7c00-7000-8000-000000000525";
const DESIGN_FILE = "01926f3a-7c00-7000-8000-000000000526";
const SUMMARY = "01926f3a-7c00-7000-8000-000000000521";

/** The rows of the witness planning, as the grid of the planning reads them. */
const rows = projectNodes(planning, PLANNING_FIELDS).items;

/** A row of the witness planning, by its node. */
function row(id: string): PlanningNode {
  const found = rows.find((node) => node.node_id === id);
  if (found === undefined) {
    throw new Error(`no node ${id} in the witness planning`);
  }
  return found;
}

describe("what a write answers, as a grid reads it", () => {
  it("gives the nodes written and their ancestors whole, and the tasks rescheduled by their schedule alone", () => {
    const written = nodesWritten(linked, PLANNING_FIELDS, true);
    expect(written.rows.map(nodeKey)).toEqual([REVIEW]);
    expect(written.changed.map(nodeKey)).toEqual([SUMMARY]);
    expect(written.parts.map((part) => part.key)).toEqual([ACCEPTANCE, DESIGN_FILE]);
    expect(written.totals).toEqual(linked.totals);
    expect(written.order).toBe(2);

    // The schedule laid over the row shown, the rest of it as it was.
    const [acceptance, file] = written.parts;
    const moved = acceptance?.change(row(ACCEPTANCE));
    expect(moved?.task).toEqual({
      ...row(ACCEPTANCE).task,
      start: { date: "2026-04-29", hours: "8" },
      finish: { date: "2026-04-29", hours: "8" },
    });
    expect(moved?.lock_version).toBe(row(ACCEPTANCE).lock_version);
    const critical = file?.change(row(DESIGN_FILE));
    expect(critical?.task?.is_critical).toBe(true);
    expect(critical?.task?.total_float).toEqual({ value: "0", unit: "d" });
    expect(critical?.task?.start).toEqual(row(DESIGN_FILE).task?.start);
  });

  it("gives no schedule to a grid that reads no date, and no totals to a filtered one", () => {
    const written = nodesWritten(linked, ESTIMATE_FIELDS, false);
    expect(written.parts).toEqual([]);
    expect(written.totals).toBeUndefined();
  });

  // A duration lengthened in the planning of the volume (`task_lengthened`): « Revue 3.1.27 »
  // finishes on 31 December 2026, and « Reprise 3.1.30 », which follows it, is pushed into 2027 —
  // rescheduled, its lines corrected anew on the year they are now consumed, and the task itself,
  // which sums them.
  const volume = example("volume/nodes_thousand") as NodeList;
  const lengthened = example("volume/task_lengthened") as NodesWritten;
  const SUCCESSOR = "01926f3a-7c00-7000-8000-000100001387";
  const amountOf = new Map(lengthened.reinflated.map((each) => [each.node_id, each]));

  it("lays the amounts the server answered over the lines and the task a write moved into the next year, the rest of each as it was", () => {
    const rows = projectNodes(volume, ESTIMATE_FIELDS).items;
    const written = nodesWritten(lengthened, ESTIMATE_FIELDS, true);
    // The grid of the estimate reads no date: the amounts alone, the successor and its lines.
    expect(written.parts.map((part) => part.key)).toEqual([...amountOf.keys()]);
    expect(written.parts[0]?.key).toBe(SUCCESSOR);
    for (const part of written.parts) {
      const before = rows.find((node) => node.node_id === part.key);
      if (before === undefined) {
        throw new Error(`no node ${part.key} in the volume`);
      }
      const inflated_amount = amountOf.get(part.key)?.inflated_amount;
      expect(part.change(before)).toEqual(
        before.task === undefined || before.task === null
          ? { ...before, estimate_line: { ...before.estimate_line, inflated_amount } }
          : { ...before, task: { ...before.task, inflated_amount } },
      );
    }
  });

  it("gives no amounts to a grid that reads none", () => {
    const parts = nodesWritten(lengthened, PLANNING_FIELDS, true).parts;
    expect(parts.map((part) => part.key)).toEqual(
      lengthened.rescheduled.map((each) => each.node_id),
    );
  });

  // A grid that reads both the schedule of a task and its amount corrected for inflation.
  const BOTH = {
    node: [],
    task: ["start", "finish", "inflated_amount"],
    line: ["inflated_amount"],
  } as const satisfies AnyNodeFields;
  const bothRows = projectNodes(volume, BOTH).items;
  type BothRow = (typeof bothRows)[number];
  const moved = { start: { date: "2027-01-01", hours: "0" }, inflated_amount: "87891.73" };

  it("lays both the schedule and the amount of a task one write answers in both lists", () => {
    const written = nodesWritten(lengthened, BOTH, true);
    // One part by row, the schedule and the amount composed.
    const keys = written.parts.map((part) => part.key);
    expect(new Set(keys).size).toBe(keys.length);
    const answers = answersOf<BothRow, unknown>(bothRows);
    take(answers, written, nodeKey);
    expect(shownRow(answers, nodeKey, SUCCESSOR)?.task).toMatchObject(moved);
  });

  it("lays both the schedule and the amount of a task two writes answer one after the other, whatever the order they come back in", () => {
    const dated = nodesWritten({ ...lengthened, reinflated: [] }, BOTH, true);
    const priced = nodesWritten({ ...lengthened, rescheduled: [] }, BOTH, true);
    for (const [first, second] of [
      [
        { ...dated, order: 2 },
        { ...priced, order: 3 },
      ],
      [
        { ...priced, order: 3 },
        { ...dated, order: 2 },
      ],
    ] as const) {
      const answers = answersOf<BothRow, unknown>(bothRows);
      take(answers, first, nodeKey);
      take(answers, second, nodeKey);
      expect(shownRow(answers, nodeKey, SUCCESSOR)?.task).toMatchObject(moved);
    }
  });
});

describe("the answers of a reading", () => {
  it("lay a schedule answered later over a row an earlier write answers whole after it, never keeping that row out", () => {
    const answers = answersOf<PlanningNode, unknown>(rows);
    // The schedule of the next write arrives first, alone.
    const later = nodesWritten(linked, PLANNING_FIELDS, true);
    take(answers, { ...later, rows: [], changed: [], order: 3 }, nodeKey);
    expect(shownRow(answers, nodeKey, ACCEPTANCE)?.task?.start).toEqual({
      date: "2026-04-29",
      hours: "8",
    });
    // Then the earlier write answers the same task whole: its label and its version stand, the
    // later schedule laid over them.
    const before = row(ACCEPTANCE);
    const task = before.task;
    if (task === undefined || task === null) {
      throw new Error("the acceptance of the witness planning is a task");
    }
    const renamed: PlanningNode = {
      ...before,
      lock_version: before.lock_version + 1,
      task: { ...task, label: "Réception" },
    };
    take(
      answers,
      { rows: [renamed], changed: [], parts: [], totals: undefined, order: 2 },
      nodeKey,
    );
    const shown = shownRow(answers, nodeKey, ACCEPTANCE);
    expect(shown?.task?.label).toBe("Réception");
    expect(shown?.lock_version).toBe(before.lock_version + 1);
    expect(shown?.task?.start).toEqual({ date: "2026-04-29", hours: "8" });
  });

  it("keep no schedule that changes nothing of what the grid reads, which then keeps out no row", () => {
    const estimateRows = projectNodes(planning, ESTIMATE_FIELDS).items;
    const answers = answersOf<(typeof estimateRows)[number], unknown>(estimateRows);
    const schedules = nodesWritten(linked, PLANNING_FIELDS, true).parts;
    take(
      answers,
      {
        rows: [],
        changed: [],
        parts: schedules.map((part) => ({
          key: part.key,
          change: (node) => node,
        })),
        totals: undefined,
        order: 3,
      },
      nodeKey,
    );
    expect(answers.parts.size).toBe(0);
  });
});
