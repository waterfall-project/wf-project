// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import { computedAlways, computedWhereNamed, nodeDependency, subordinates } from "./computed-nodes";
import { ESTIMATE_FIELDS } from "./estimate";
import { type NodeList, projectNodes } from "./nodes";

const estimate = example("nodes_estimate") as NodeList;
const planning = example("nodes_planning") as NodeList;
const volume = example("volume/nodes_thousand") as NodeList;

/** The index of the row of a label in an answer. */
function indexOf(list: NodeList, label: string): number {
  const index = list.items.findIndex(
    (node) => (node.task?.label ?? node.estimate_line?.label) === label,
  );
  expect(index).toBeGreaterThanOrEqual(0);
  return index;
}

/** The labels of rows of an answer, by their indices. */
function labels(list: NodeList, indices: readonly number[]): (string | undefined)[] {
  return indices.map((index) => {
    const node = list.items[index];
    return node?.task?.label ?? node?.estimate_line?.label;
  });
}

describe("the subordinates of a row, found by the order and the levels of the answer", () => {
  it("are the rows one level down that follow it, until the next of its level", () => {
    const summary = indexOf(planning, "Études");
    expect(labels(planning, subordinates(planning.items, summary))).toEqual([
      "Études de détail",
      "Pupitres opérateurs",
      "Revue de conception",
      "Réception des études",
    ]);
    // A task without subordinates has none, and the last row of the answer neither.
    expect(subordinates(planning.items, indexOf(planning, "Revue de conception"))).toEqual([]);
    expect(subordinates(planning.items, planning.items.length - 1)).toEqual([]);
    expect(subordinates(planning.items, planning.items.length)).toEqual([]);
  });

  it("are of a kind, or all: the tasks of a summary, the lines a task bears", () => {
    const summary = indexOf(estimate, "Poste de commande");
    expect(labels(estimate, subordinates(estimate.items, summary, "task"))).toEqual([
      "Câblage des armoires",
      "Réception usine",
    ]);
    // Two levels down, the lines of its first task are not its own.
    expect(labels(estimate, subordinates(estimate.items, summary))).toEqual([
      "Câblage des armoires",
      "Réception usine",
    ]);
    expect(
      labels(estimate, subordinates(estimate.items, indexOf(estimate, "Câblage des armoires"))),
    ).toEqual([
      "Raccordement des borniers",
      "Borniers",
      "Provision — risque de reprise du câblage",
    ]);
    expect(subordinates(estimate.items, indexOf(estimate, "Câblage des armoires"), "task")).toEqual(
      [],
    );
  });

  it("are found among the six thousand rows of the volume: the three lots of the first phase", () => {
    const tasks = subordinates(volume.items, 0, "task");
    expect(tasks.map((index) => volume.items[index]?.row_number)).toEqual([2, 201, 401]);
    expect(labels(volume, tasks)).toEqual([
      "Études — Poste de commande",
      "Études — Ligne d'essais",
      "Études — Utilités",
    ]);
  });
});

describe("the cells of a structure the server computes", () => {
  it("are read node by node in its computed fields, never from its mode nor its nature", () => {
    const quantity = computedWhereNamed("estimate_line.quantity", "figure");
    const disbursement = computedWhereNamed("estimate_line.unit_disbursement", "figure");
    const hours = computedWhereNamed("estimate_line.hours", "figure");
    const computed = (cells: typeof quantity) =>
      estimate.items.filter((node) => cells.in(node)).map((node) => node.row_number);
    // The provision of row 5 alone: its quantity and its unit disbursement come from its risk.
    expect(computed(quantity)).toEqual([5]);
    expect(computed(disbursement)).toEqual([5]);
    expect(computed(hours)).toEqual([]);
    expect(quantity.whole).toBe(false);

    const finish = computedWhereNamed("task.finish_date", "dates");
    // In the planning, the manual task of row 3 enters its dates; the others compute them.
    expect(planning.items.filter((node) => finish.in(node)).map((node) => node.row_number)).toEqual(
      [1, 2, 4, 5, 6],
    );
  });

  it("are the amounts in every row, and the float in every task", () => {
    const amount = computedAlways("budgeted");
    const float = computedAlways("float");
    expect(amount.whole).toBe(true);
    expect(estimate.items.every((node) => amount.in(node))).toBe(true);
    expect(estimate.items.filter((node) => float.in(node)).map((node) => node.row_number)).toEqual([
      1, 2, 6,
    ]);
  });
});

describe("what a computed value depends on", () => {
  const at = (list: NodeList, label: string) => indexOf(list, label);
  // The rows as the grid of the estimate reads them: without the scheduling mode of a task.
  const unmoded = projectNodes(estimate, ESTIMATE_FIELDS).items;

  it("is, for the amount of a line of labour, its quantity, its effort and its rate; for the budgeted, the reference", () => {
    const labour = at(estimate, "Raccordement des borniers");
    expect(nodeDependency(estimate.items, labour, "budgeted")).toEqual({
      reasons: ["labour", "budgeted"],
      rows: null,
    });
    expect(nodeDependency(estimate.items, labour, "reestimated")).toEqual({
      reasons: ["labour", "reestimated"],
      rows: null,
    });
    expect(computedAlways("budgeted").dependsOn(estimate.items, labour)).toEqual(
      nodeDependency(estimate.items, labour, "budgeted"),
    );
  });

  it("is, for the dates of a summary, its subordinates, named by their rows [WF-IHM-0030-A]", () => {
    const summary = at(planning, "Études");
    const dependency = computedWhereNamed("task.finish_date", "dates").dependsOn(
      planning.items,
      summary,
    );
    expect(dependency.reasons).toEqual(["summary"]);
    expect(labels(planning, dependency.rows ?? [])).toEqual([
      "Études de détail",
      "Pupitres opérateurs",
      "Revue de conception",
      "Réception des études",
    ]);
    // Its duration and its progress too.
    for (const value of ["duration", "progress"] as const) {
      expect(nodeDependency(planning.items, summary, value)).toEqual(dependency);
    }
  });

  it("is, for the dates of a task in automatic mode, its duration, its links and its calendar, read from its mode", () => {
    const automatic = at(planning, "Revue de conception");
    expect(nodeDependency(planning.items, automatic, "dates")).toEqual({
      reasons: ["automatic"],
      rows: null,
    });
    // The rules the contract describes stop there: the rest the refusal cannot tell (#168).
    const unknown = { reasons: ["unknown"], rows: null };
    expect(nodeDependency(planning.items, automatic, "duration")).toEqual(unknown);
    expect(nodeDependency(planning.items, automatic, "progress")).toEqual(unknown);
    expect(nodeDependency(planning.items, at(planning, "Pupitres opérateurs"), "dates")).toEqual(
      unknown,
    );
    // Nor from a row that does not bear its mode.
    expect(nodeDependency(unmoded, at(estimate, "Câblage des armoires"), "dates")).toEqual(unknown);
  });

  it("is, for the amount of a task, what it bears; for a line, the rule of its nature", () => {
    const task = at(estimate, "Câblage des armoires");
    const amount = nodeDependency(estimate.items, task, "budgeted");
    expect(amount.reasons).toEqual(["taskAmount", "budgeted"]);
    expect(labels(estimate, amount.rows ?? [])).toEqual([
      "Raccordement des borniers",
      "Borniers",
      "Provision — risque de reprise du câblage",
    ]);
    // A milestone bears nothing: its amount depends on no row the answer holds.
    expect(nodeDependency(estimate.items, at(estimate, "Réception usine"), "reestimated")).toEqual({
      reasons: ["taskAmount", "reestimated"],
      rows: [],
    });
    expect(nodeDependency(estimate.items, at(estimate, "Borniers"), "budgeted").reasons).toEqual([
      "disbursement",
      "budgeted",
    ]);
    const provision = at(estimate, "Provision — risque de reprise du câblage");
    expect(nodeDependency(estimate.items, provision, "budgeted").reasons).toEqual([
      "provision",
      "budgeted",
    ]);
  });

  it("is, for a figure of a provision, its risk, read from its nature; for another line, unknown", () => {
    const provision = at(estimate, "Provision — risque de reprise du câblage");
    expect(nodeDependency(unmoded, provision, "figure")).toEqual({
      reasons: ["provision"],
      rows: null,
    });
    expect(nodeDependency(unmoded, at(estimate, "Borniers"), "figure")).toEqual({
      reasons: ["unknown"],
      rows: null,
    });
  });

  it("is, for the float of a task in automatic mode, its earliest and latest dates; a task in manual mode bears none", () => {
    const float = computedAlways("float");
    expect(float.dependsOn(planning.items, at(planning, "Revue de conception"))).toEqual({
      reasons: ["float"],
      rows: null,
    });
    expect(float.dependsOn(planning.items, at(planning, "Pupitres opérateurs"))).toEqual({
      reasons: ["manualFloat"],
      rows: null,
    });
    expect(float.dependsOn(unmoded, at(estimate, "Câblage des armoires"))).toEqual({
      reasons: ["unknown"],
      rows: null,
    });
  });

  it("is nothing for a row the answer does not hold", () => {
    expect(nodeDependency(planning.items, planning.items.length, "dates")).toEqual({
      reasons: [],
      rows: null,
    });
  });
});
