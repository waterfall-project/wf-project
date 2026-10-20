// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import type { NodeList } from "./nodes";
import { bodyOf, gestureOfKey, gesturesOn, type StructureGestures } from "./structure-rules";

const estimate = example("nodes_estimate") as NodeList;
/** The node of the example with a label. */
function row(label: string) {
  const found = estimate.items.find(
    (node) => (node.task?.label ?? node.estimate_line?.label) === label,
  );
  if (found === undefined) {
    throw new Error(`no row ${label}`);
  }
  return found;
}
const SUMMARY = row("Poste de commande");
const LEAF = row("Câblage des armoires");
const LINE = row("Raccordement des borniers");

const STRUCTURE = { project_id: "p", revision_id: "r", structure_id: "s" };
const CATEGORY = { id: "01926f3a-7c00-7000-8000-000000000405", label: "Matériel", active: true };
/** What a grid offers, the tasks and the lines unless said. */
function offered(patch: Partial<StructureGestures> = {}): StructureGestures {
  return { structure: STRUCTURE, tasks: true, lines: true, categories: [CATEGORY], ...patch };
}
const PRESSED = { key: "Insert", ctrlKey: false, altKey: false, shiftKey: false };

describe("the gestures a row takes", () => {
  it("gives a task a task below, a sub-task, a line and its deletion, a summary no line", () => {
    expect(gesturesOn(LEAF, offered())).toEqual(["below", "child", "line", "delete"]);
    expect(gesturesOn(SUMMARY, offered())).toEqual(["below", "child", "delete"]);
  });

  it("gives a line a line below and its deletion, and the header a first task", () => {
    expect(gesturesOn(LINE, offered())).toEqual(["line", "delete"]);
    expect(gesturesOn(undefined, offered())).toEqual(["first"]);
  });

  it("gives nothing the grid does not list: no task, no line, no category to choose", () => {
    expect(gesturesOn(LEAF, offered({ tasks: false }))).toEqual(["line"]);
    expect(gesturesOn(LEAF, offered({ lines: false }))).toEqual(["below", "child", "delete"]);
    expect(gesturesOn(LEAF, offered({ categories: undefined }))).toEqual([
      "below",
      "child",
      "delete",
    ]);
    expect(gesturesOn(LINE, offered({ categories: [{ ...CATEGORY, active: false }] }))).toEqual([
      "delete",
    ]);
    expect(gesturesOn(undefined, offered({ tasks: false }))).toEqual([]);
    expect(gesturesOn(LEAF, offered({ tasks: false, lines: false }))).toEqual([]);
  });

  it("gives a milestone neither sub-task nor line", () => {
    const milestone = { ...LEAF, task: { ...LEAF.task, is_milestone: true } } as typeof LEAF;
    expect(gesturesOn(milestone, offered())).toEqual(["below", "delete"]);
  });
});

describe("the gesture a key asks", () => {
  it("asks a task below on Insert, a line below a line, a first task from no row", () => {
    expect(gestureOfKey(LEAF, PRESSED)).toBe("below");
    expect(gestureOfKey(LINE, PRESSED)).toBe("line");
    expect(gestureOfKey(undefined, PRESSED)).toBe("first");
  });

  it("asks a sub-task on Alt+Insert, a line on Ctrl+Insert, the deletion on Ctrl+Delete", () => {
    expect(gestureOfKey(LEAF, { ...PRESSED, altKey: true })).toBe("child");
    expect(gestureOfKey(LEAF, { ...PRESSED, ctrlKey: true })).toBe("line");
    expect(gestureOfKey(LEAF, { ...PRESSED, key: "Delete", ctrlKey: true })).toBe("delete");
  });

  it("leaves Shift+Insert to the paste, a bare Delete to the cell, and any other key", () => {
    expect(gestureOfKey(LEAF, { ...PRESSED, shiftKey: true })).toBeUndefined();
    expect(gestureOfKey(LEAF, { ...PRESSED, key: "Delete" })).toBeUndefined();
    expect(gestureOfKey(LEAF, { ...PRESSED, key: "a" })).toBeUndefined();
    expect(gestureOfKey(LEAF, { ...PRESSED, altKey: true, ctrlKey: true })).toBeUndefined();
  });
});

describe("the body of the node a gesture creates", () => {
  const named = { label: "Étude", line: undefined };
  const line = { label: "Pièces", line: { category: CATEGORY.id, quantity: "2" } };

  it("places a task below a row after it among its siblings, by the node it follows", () => {
    expect(bodyOf("below", LEAF, named)).toEqual({
      kind: "task",
      parent_id: LEAF.parent_id,
      after_node_id: LEAF.node_id,
      task: { label: "Étude" },
    });
  });

  it("places a sub-task last under the row, and a first task at the root, with no node to follow", () => {
    expect(bodyOf("child", LEAF, named)).toEqual({
      kind: "task",
      parent_id: LEAF.node_id,
      task: { label: "Étude" },
    });
    expect(bodyOf("first", undefined, named)).toEqual({
      kind: "task",
      parent_id: null,
      task: { label: "Étude" },
    });
  });

  it("places a line under a task, or below a line after it", () => {
    const estimateLine = { label: "Pièces", cost_category_id: CATEGORY.id, quantity: "2" };
    expect(bodyOf("line", LEAF, line)).toEqual({
      kind: "estimate_line",
      parent_id: LEAF.node_id,
      estimate_line: estimateLine,
    });
    expect(bodyOf("line", LINE, line)).toEqual({
      kind: "estimate_line",
      parent_id: LINE.parent_id,
      after_node_id: LINE.node_id,
      estimate_line: estimateLine,
    });
  });
});
