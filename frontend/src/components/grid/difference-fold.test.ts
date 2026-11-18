// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { RowDifference } from "./columns";
import { foldedDifferences, gridSlots, NOT_FOLDED, openedWith } from "./difference-fold";
import { treeIndex } from "./fold";

/** A row of a tree: its identity, its parent, its level, the difference the server marks. */
interface Row {
  readonly key: string;
  readonly parent: string | null;
  readonly level: number;
  readonly difference: RowDifference | undefined;
}

// A — modified, over A1 unchanged with A11 unchanged under it, and A2 added; B unchanged; C, which
// the server marks nothing of.
const ROWS: readonly Row[] = [
  { key: "A", parent: null, level: 1, difference: "modified" },
  { key: "A1", parent: "A", level: 2, difference: "unchanged" },
  { key: "A11", parent: "A1", level: 3, difference: "unchanged" },
  { key: "A2", parent: "A", level: 2, difference: "added" },
  { key: "B", parent: null, level: 1, difference: "unchanged" },
  { key: "B1", parent: "B", level: 2, difference: "unchanged" },
  { key: "C", parent: null, level: 1, difference: undefined },
];
const rowKey = (row: Row) => row.key;
const index = treeIndex(ROWS, rowKey, {
  level: (row) => row.level,
  nature: () => null,
  parent: (row) => row.parent,
});
const marked = { rows: ROWS, rowKey, index, difference: (row: Row) => row.difference };
const ON = { on: true, opened: new Set<string>() };

describe("the rows without difference of a comparison, folded away", () => {
  it("keeps the rows marked, those above them and those the server marks nothing of, and says the runs between [WF-IHM-0170-A]", () => {
    const { shown, runs } = foldedDifferences(ROWS, marked, ON);
    expect(shown.map(rowKey)).toEqual(["A", "A2", "C"]);
    expect(runs.map((run) => run?.keys)).toEqual([
      undefined,
      ["A1", "A11"],
      ["B", "B1"],
      undefined,
    ]);
  });

  it("folds nothing while off, nor while no comparison is read [WF-IHM-0170-A]", () => {
    expect(foldedDifferences(ROWS, marked, NOT_FOLDED)).toEqual({ shown: ROWS, runs: [] });
    expect(foldedDifferences(ROWS, { ...marked, difference: undefined }, ON).shown).toBe(ROWS);
  });

  it("keeps a run unfolded with the rows under it, whatever the tree folds [WF-IHM-0170-A]", () => {
    // The tree folds B: its run is B alone; unfolded, B1 comes back with it once the tree unfolds.
    const visible = ROWS.filter((row) => row.key !== "B1");
    const run = foldedDifferences(visible, marked, ON).runs[2];
    expect(run?.keys).toEqual(["B"]);
    const opened = openedWith(new Set(), run ?? { key: "", keys: [] }, marked);
    expect([...opened].sort()).toEqual(["B", "B1"]);
    const unfolded = foldedDifferences(ROWS, marked, { on: true, opened });
    expect(unfolded.shown.map(rowKey)).toEqual(["A", "A2", "B", "B1", "C"]);
  });

  it("places the rows and the runs in their order", () => {
    const { runs, shown } = foldedDifferences(ROWS, marked, ON);
    const { slots, slotOf } = gridSlots(shown.length, runs);
    expect(
      slots.map((slot) => (slot.run === undefined ? slot.row : `run ${String(slot.before)}`)),
    ).toEqual([0, "run 1", 1, "run 2", 2]);
    expect(slotOf).toEqual([0, 2, 4]);
    expect(gridSlots(0, [{ key: "A", keys: ["A"] }]).slots).toEqual([
      { run: { key: "A", keys: ["A"] }, before: 0 },
    ]);
  });
});
