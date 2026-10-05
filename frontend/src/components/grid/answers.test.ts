// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import { answersOf, shownRow, take } from "./answers";
import { ESTIMATE_FIELDS } from "./estimate";
import { type NodeList, type NodesWritten, nodeKey, nodesWritten, projectNodes } from "./nodes";
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
// A task of the witness estimate, and the labour, disbursement and provision lines it bears.
const TASK = "01926f3a-7c00-7000-8000-000000000522";
const LABOUR = "01926f3a-7c00-7000-8000-000000000523";
const DISBURSEMENT = "01926f3a-7c00-7000-8000-000000000524";
const PROVISION = "01926f3a-7c00-7000-8000-000000000525";

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

  // A write that moves a task in time without writing it — a link written in the planning that
  // takes « Câblage des armoires » of the witness estimate two years later, its summary
  // recalculated whole aside —: its three lines corrected anew on the year they are now consumed,
  // at 3 % a year over two years, and the task itself, which sums them (#235).
  const moved: NodesWritten = {
    ...(example("estimate_line_updated") as NodesWritten),
    nodes: [],
    ancestors: [],
    reinflated: [
      { node_id: TASK, inflated_amount: "2901.09", consumption_year: null },
      { node_id: LABOUR, inflated_amount: "1060.90", consumption_year: 2028 },
      { node_id: DISBURSEMENT, inflated_amount: "1309.74", consumption_year: 2028 },
      { node_id: PROVISION, inflated_amount: "530.45", consumption_year: 2028 },
    ],
  };

  it("lays the amounts the server answered over the lines and the task a write moved in time, the rest of each as it was [WF-DEV-0050-A]", () => {
    const shown = projectNodes(example("nodes_estimate") as NodeList, ESTIMATE_FIELDS).items;
    const before = (id: string) => shown.find((node) => node.node_id === id);
    const written = nodesWritten(moved, ESTIMATE_FIELDS, true);
    expect(written.parts.map((part) => part.key)).toEqual([TASK, LABOUR, DISBURSEMENT, PROVISION]);
    const after = (index: number, id: string) => {
      const row = before(id);
      return row === undefined ? undefined : written.parts[index]?.change(row);
    };
    expect(after(0, TASK)).toEqual({
      ...before(TASK),
      task: { ...before(TASK)?.task, inflated_amount: "2901.09" },
    });
    expect(after(2, DISBURSEMENT)).toEqual({
      ...before(DISBURSEMENT),
      estimate_line: { ...before(DISBURSEMENT)?.estimate_line, inflated_amount: "1309.74" },
    });
  });

  it("gives no amounts to a grid that reads none", () => {
    expect(nodesWritten(moved, PLANNING_FIELDS, true).parts).toEqual([]);
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
