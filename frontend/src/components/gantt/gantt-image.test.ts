// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { namesWidth } from "./gantt-image";
import type { GanttRow } from "./layout";

/** The rows of the structure the fake back serves for the planning, as the Gantt reads them. */
function volumeRows(): GanttRow[] {
  const { value } = JSON.parse(
    readFileSync(
      `${import.meta.dirname}/../../../../fixtures/api/volume/nodes_thousand.json`,
      "utf-8",
    ),
  ) as { value: { items: GanttRow[] } };
  return value.items;
}

/** A row of a task named `label`, at a level. */
const named = (label: string, level: number): GanttRow => ({
  node_id: label,
  level,
  task: { label, is_summary: false, is_milestone: false },
});

describe("the column of the names of the exported Gantt", () => {
  it("takes the room of the longest name of the thousand tasks of the fake back, indented by its level [WF-PLA-0090-A]", () => {
    // « Approvisionnements — Poste de commande »: 38 characters at the second level, 12 points of
    // indent, 6 a character, 12 for the edges (e2e/planning.spec.ts holds the same width against
    // the PNG the export writes).
    expect(namesWidth(volumeRows())).toBe(252);
  });

  it.each([
    ["no more than the room of its name, in the narrowest column", [named("A", 1)], 96],
    ["indented by a level less one, at 12 points each", [named("A".repeat(20), 3)], 156],
    ["no wider than the widest column", [named("A".repeat(100), 1)], 320],
    ["none when no row bears a task", [{ node_id: "line", level: 2 }], 0],
  ] satisfies [string, GanttRow[], number][])("takes %s", (_case, rows, width) => {
    expect(namesWidth(rows)).toBe(width);
  });
});
