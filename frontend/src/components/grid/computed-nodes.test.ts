// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import { COMPUTED_FLOAT, computedAmount, computedWhereNamed } from "./computed-nodes";
import type { NodeList } from "./nodes";

const estimate = example("nodes_estimate") as NodeList;
const planning = example("nodes_planning") as NodeList;

describe("the cells of a structure the server computes", () => {
  it("are read node by node in its computed fields, never from its mode nor its nature", () => {
    const quantity = computedWhereNamed("estimate_line.quantity");
    const disbursement = computedWhereNamed("estimate_line.unit_disbursement");
    const hours = computedWhereNamed("estimate_line.hours");
    const computed = (cells: typeof quantity) =>
      estimate.items.filter((node) => cells.in(node)).map((node) => node.row_number);
    // The provision of row 12 alone: its quantity and its unit disbursement come from its risk.
    expect(computed(quantity)).toEqual([12]);
    expect(computed(disbursement)).toEqual([12]);
    expect(computed(hours)).toEqual([]);
    expect(quantity.whole).toBe(false);

    const finish = computedWhereNamed("task.finish");
    // In the planning, the manual task of row 4 enters its dates; the others compute them.
    expect(planning.items.filter((node) => finish.in(node)).map((node) => node.row_number)).toEqual(
      [1, 2, 5, 6, 7],
    );
  });

  it("name the field of the contract each shows, which the refusal asks the server about", () => {
    const [summary] = planning.items;
    expect(summary === undefined ? null : computedWhereNamed("task.finish").field(summary)).toBe(
      "task.finish",
    );
    // An amount is the task's in a task, the line's in a line.
    const amount = computedAmount("reestimated_amount");
    expect(estimate.items.map((node) => amount.field(node))).toEqual([
      "task.reestimated_amount",
      "task.reestimated_amount",
      "estimate_line.reestimated_amount",
      "estimate_line.reestimated_amount",
      "estimate_line.reestimated_amount",
      "task.reestimated_amount",
      "task.reestimated_amount",
      "estimate_line.reestimated_amount",
      "task.reestimated_amount",
      "estimate_line.reestimated_amount",
      "task.reestimated_amount",
    ]);
    expect(summary === undefined ? null : COMPUTED_FLOAT.field(summary)).toBe("task.total_float");
  });

  it("are the amounts in every row, and the float in every task", () => {
    const amount = computedAmount("budgeted_amount");
    expect(amount.whole).toBe(true);
    expect(estimate.items.every((node) => amount.in(node))).toBe(true);
    expect(COMPUTED_FLOAT.whole).toBe(true);
    expect(
      estimate.items.filter((node) => COMPUTED_FLOAT.in(node)).map((node) => node.row_number),
    ).toEqual([8, 9, 13, 14, 16, 18]);
  });
});
