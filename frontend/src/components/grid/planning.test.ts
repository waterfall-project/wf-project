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

describe("a cell of a task written on a node read without its task", () => {
  it.each(["label", "description", "scheduling_mode", "duration", "start", "finish"])(
    "refuses the entry of %s, and its write sends nothing that would carry the version alone (#819.8)",
    async (key) => {
      if (desks === undefined) {
        throw new Error("the example lacks the desks");
      }
      const task = vi.fn<PlanningWrites["task"]>();
      const writes: PlanningWrites = {
        task,
        modes: (mode) => mode,
        suffix: (unit) => unit,
        written: (value) => value,
      };
      const entry = planningGrid(writes).columns.find((column) => column.key === key)?.entry;
      const bare: PlanningNode = { ...desks, task: null };
      expect(entry?.in(desks)).toBe(true);
      expect(entry?.in(bare)).toBe(false);
      await expect(entry?.write(bare, null)).rejects.toThrow(/without its task/);
      expect(task).not.toHaveBeenCalled();
    },
  );
});
