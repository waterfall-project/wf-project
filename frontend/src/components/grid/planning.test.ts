// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it, vi } from "vitest";

import { example } from "@/test/fixtures";

import type { NodeList } from "./nodes";
import { planningGrid, type PlanningNode, type PlanningWrites } from "./planning";

// The desks of `nodes_planning`, in manual mode, their task read; the same node read without it.
const desks = (example("nodes_planning") as NodeList).items.find(
  (node) => node.task?.label === "Pupitres opérateurs",
) as PlanningNode | undefined;

/** The writes of a grid of the planning that sends nothing: the names are the keys themselves. */
function writesOf(task: PlanningWrites["task"]): PlanningWrites {
  return {
    task,
    modes: (mode) => mode,
    suffix: (unit) => unit,
    written: (value) => value,
    predecessors: {
      code: (link) => link,
      suffix: (unit) => unit,
      resolve: () => undefined,
      write: vi.fn<PlanningWrites["predecessors"]["write"]>(),
    },
  };
}

describe("a cell of a task written on a node read without its task", () => {
  it.each(["label", "description", "scheduling_mode", "duration", "start", "finish"])(
    "refuses the entry of %s, and its write sends nothing that would carry the version alone (#819.8)",
    async (key) => {
      if (desks === undefined) {
        throw new Error("the example lacks the desks");
      }
      const task = vi.fn<PlanningWrites["task"]>();
      const entry = planningGrid(writesOf(task)).columns.find(
        (column) => column.key === key,
      )?.entry;
      const bare: PlanningNode = { ...desks, task: null };
      expect(entry?.in(desks)).toBe(true);
      expect(entry?.in(bare)).toBe(false);
      await expect(entry?.write(bare, null)).rejects.toThrow(/without its task/);
      expect(task).not.toHaveBeenCalled();
    },
  );
});

describe("a cell of a task written with a value its column cannot write", () => {
  it.each([
    { key: "scheduling_mode", value: "sometimes", reason: /is not a scheduling mode/ },
    { key: "scheduling_mode", value: null, reason: /is not a scheduling mode/ },
    { key: "duration", value: "two days", reason: /is not a duration/ },
    { key: "duration", value: null, reason: /is not a duration/ },
  ])(
    "guards the empty request: rejects $value in the cell $key, and sends nothing that would carry the version alone (#1250)",
    async ({ key, value, reason }) => {
      if (desks === undefined) {
        throw new Error("the example lacks the desks");
      }
      const task = vi.fn<PlanningWrites["task"]>();
      const entry = planningGrid(writesOf(task)).columns.find(
        (column) => column.key === key,
      )?.entry;
      await expect(entry?.write(desks, value)).rejects.toThrow(reason);
      expect(task).not.toHaveBeenCalled();
    },
  );
});
