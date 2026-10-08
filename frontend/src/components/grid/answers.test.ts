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

// A duration lengthened in the planning of the witness (`task_lengthened`), the core incrusted at
// the head of the structure of a thousand tasks (#376): the task written, its two summaries
// recalculated, and the tasks of its chain rescheduled — those before it given less float, their
// dates as they were; its successor, and those after it in the chain, moved into 2027. The nodes
// and their figures are read from the examples, never written here (#400).
const volume = example("volume/nodes_thousand") as NodeList;
const lengthened = example("volume/task_lengthened") as NodesWritten;
const MOUNTING = lengthened.nodes[0]?.node_id ?? "";
const [shrunk] = lengthened.rescheduled;
const DESIGN_FILE = shrunk?.node_id ?? "";
const FLOAT = shrunk?.total_float;

/** The rows of the witness planning, as the grid of the planning reads them. */
const rows = projectNodes(volume, PLANNING_FIELDS).items;

/** A row of the witness planning, by its node. */
function row(id: string): PlanningNode {
  const found = rows.find((node) => node.node_id === id);
  if (found === undefined) {
    throw new Error(`no node ${id} in the planning of the witness`);
  }
  return found;
}

describe("what a write answers, as a grid reads it", () => {
  it("gives the nodes written and their ancestors whole, and the tasks rescheduled by their schedule alone", () => {
    const written = nodesWritten(lengthened, PLANNING_FIELDS, true);
    expect(written.rows.map(nodeKey)).toEqual([MOUNTING]);
    expect(written.changed.map(nodeKey)).toEqual(lengthened.ancestors.map(nodeKey));
    expect(written.changed).toHaveLength(2);
    expect(written.parts.map((part) => part.key)).toEqual(
      lengthened.rescheduled.map((each) => each.node_id),
    );
    expect(written.totals).toEqual(lengthened.totals);
    expect(written.order).toBe(2);

    // The schedule laid over the row shown, the rest of it as it was: less float, no date moved.
    const [file] = written.parts;
    const later = file?.change(row(DESIGN_FILE));
    expect(later?.task).toEqual({ ...row(DESIGN_FILE).task, total_float: FLOAT });
    expect(later?.lock_version).toBe(row(DESIGN_FILE).lock_version);
  });

  it("gives no schedule to a grid that reads no date, and no totals to a filtered one", () => {
    // Its schedule alone: the amounts moved in time are the next test's.
    const written = nodesWritten({ ...lengthened, reinflated: [] }, ESTIMATE_FIELDS, false);
    expect(written.parts).toEqual([]);
    expect(written.totals).toBeUndefined();
  });

  // The successor of the task lengthened, pushed into 2027: rescheduled, its lines corrected anew
  // on the year they are now consumed, and the task itself, which sums them.
  const SUCCESSOR = lengthened.reinflated[0]?.node_id ?? "";
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
  const moved = {
    start: lengthened.rescheduled.find((each) => each.node_id === SUCCESSOR)?.start,
    inflated_amount: lengthened.reinflated[0]?.inflated_amount,
  };

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
    const later = nodesWritten(lengthened, PLANNING_FIELDS, true);
    take(answers, { ...later, rows: [], changed: [], order: 3 }, nodeKey);
    expect(shownRow(answers, nodeKey, DESIGN_FILE)?.task?.total_float).toEqual(FLOAT);
    // Then the earlier write answers the same task whole: its label and its version stand, the
    // later schedule laid over them.
    const before = row(DESIGN_FILE);
    const task = before.task;
    if (task === undefined || task === null) {
      throw new Error("a task of the chain lengthened is a task");
    }
    const renamed: PlanningNode = {
      ...before,
      lock_version: before.lock_version + 1,
      task: { ...task, label: "Dossier" },
    };
    take(
      answers,
      { rows: [renamed], changed: [], parts: [], totals: undefined, order: 2 },
      nodeKey,
    );
    const shown = shownRow(answers, nodeKey, DESIGN_FILE);
    expect(shown?.task?.label).toBe("Dossier");
    expect(shown?.lock_version).toBe(before.lock_version + 1);
    expect(shown?.task?.total_float).toEqual(FLOAT);
  });

  it("lay two parts of the calendar of one task answered in the wrong order so that the later wins, and let go of those a later row whole covers", () => {
    const answers = answersOf<PlanningNode, unknown>(rows);
    // A task given its float by the write of order 3, another by that of order 2; the later
    // answers first.
    const schedule = lengthened.rescheduled.find((each) => each.node_id === DESIGN_FILE);
    if (schedule === undefined) {
      throw new Error("the duration lengthened reschedules a task of its chain");
    }
    const earlier: NodesWritten = {
      ...lengthened,
      rescheduled: [{ ...schedule, total_float: { value: "1", unit: "d" } }],
    };
    const parts = (written: NodesWritten, order: number) => ({
      ...nodesWritten(written, PLANNING_FIELDS, true),
      rows: [],
      changed: [],
      order,
    });
    take(answers, parts(lengthened, 3), nodeKey);
    take(answers, parts(earlier, 2), nodeKey);
    expect(shownRow(answers, nodeKey, DESIGN_FILE)?.task?.total_float).toEqual(FLOAT);
    expect(answers.parts.get(DESIGN_FILE)?.map((part) => part.order)).toEqual([2, 3]);
    // The design file answered whole by the write of order 2: its part of order 2 is covered, let
    // go; that of order 3 stands over the row (#355).
    const whole = (order: number) => ({
      rows: [row(DESIGN_FILE)],
      changed: [],
      parts: [],
      totals: undefined,
      order,
    });
    take(answers, whole(2), nodeKey);
    expect(answers.parts.get(DESIGN_FILE)?.map((part) => part.order)).toEqual([3]);
    expect(shownRow(answers, nodeKey, DESIGN_FILE)?.task?.total_float).toEqual(FLOAT);
    take(answers, whole(3), nodeKey);
    expect(answers.parts.has(DESIGN_FILE)).toBe(false);
    // A part that comes after a later row whole is covered as it comes: never kept.
    take(answers, whole(5), nodeKey);
    take(answers, parts(lengthened, 3), nodeKey);
    expect(answers.parts.has(DESIGN_FILE)).toBe(false);
    expect(shownRow(answers, nodeKey, DESIGN_FILE)?.task?.total_float).toEqual(
      row(DESIGN_FILE).task?.total_float,
    );
  });

  it("keep no schedule that changes nothing of what the grid reads, which then keeps out no row", () => {
    const estimateRows = projectNodes(volume, ESTIMATE_FIELDS).items;
    const answers = answersOf<(typeof estimateRows)[number], unknown>(estimateRows);
    const schedules = nodesWritten(lengthened, PLANNING_FIELDS, true).parts;
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
