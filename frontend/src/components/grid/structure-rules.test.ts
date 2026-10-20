// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import type { NodeList } from "./nodes";
import {
  bodyOf,
  gestureOfKey,
  gesturesOn,
  moveOf,
  type StructureGestures,
} from "./structure-rules";

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
const RISK = row("Risque survenu — Retard de livraison des armoires");
const TRANSPORT = row("Transport exceptionnel");
const MILESTONE = row("Réception usine");

const STRUCTURE = { project_id: "p", revision_id: "r", structure_id: "s" };
const CATEGORY = { id: "01926f3a-7c00-7000-8000-000000000405", label: "Matériel", active: true };
/** What a grid offers, the tasks and the lines unless said. */
function offered(patch: Partial<StructureGestures> = {}): StructureGestures {
  return {
    structure: STRUCTURE,
    tasks: true,
    lines: true,
    categories: [CATEGORY],
    rows: estimate.items,
    version: 4,
    ...patch,
  };
}
const PRESSED = { key: "Insert", ctrlKey: false, altKey: false, shiftKey: false };

describe("the gestures a row takes", () => {
  it("gives a task a task below, a sub-task, a line and its deletion, a summary no line", () => {
    expect(gesturesOn(LEAF, offered())).toEqual(["below", "child", "line", "outdent", "delete"]);
    expect(gesturesOn(SUMMARY, offered())).toEqual(["below", "child", "delete"]);
  });

  it("gives a line a line below and its deletion, and the header a first task", () => {
    expect(gesturesOn(LINE, offered())).toEqual(["line", "delete"]);
    expect(gesturesOn(undefined, offered())).toEqual(["first"]);
  });

  it("gives nothing the grid does not list: no task, no line, no category to choose", () => {
    expect(gesturesOn(LEAF, offered({ tasks: false }))).toEqual(["line"]);
    expect(gesturesOn(LEAF, offered({ lines: false }))).toEqual([
      "below",
      "child",
      "outdent",
      "delete",
    ]);
    expect(gesturesOn(LEAF, offered({ categories: undefined }))).toEqual([
      "below",
      "child",
      "outdent",
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
    expect(gesturesOn(milestone, offered())).toEqual(["below", "outdent", "delete"]);
  });

  it("gives an indentation to a task that has a sibling above it, bearing tasks, and an outdentation to a task under another", () => {
    expect(gesturesOn(RISK, offered())).toEqual(["below", "child", "indent", "outdent", "delete"]);
    // The first of its siblings has nothing to go under; a task at the root has nothing to leave.
    expect(gesturesOn(LEAF, offered())).not.toContain("indent");
    expect(gesturesOn(SUMMARY, offered())).not.toContain("outdent");
    expect(gesturesOn(SUMMARY, offered())).not.toContain("indent");
    // A line is moved with the move of its task; it takes neither.
    expect(gesturesOn(LINE, offered())).toEqual(["line", "delete"]);
  });

  it("gives no indentation under a milestone, which bears nothing, and none where the grid lists no task", () => {
    const rows = estimate.items.map((each) =>
      each.node_id === RISK.node_id
        ? { ...each, task: { ...each.task, is_milestone: true } }
        : each,
    ) as typeof estimate.items;
    expect(gesturesOn(MILESTONE, offered({ rows }))).not.toContain("indent");
    expect(gesturesOn(MILESTONE, offered())).toContain("indent");
    expect(gesturesOn(RISK, offered({ tasks: false }))).toEqual([]);
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

  it("asks an indentation on Alt+Shift+Right and an outdentation on Alt+Shift+Left, and no other arrow", () => {
    const arrow = { ...PRESSED, key: "ArrowRight", altKey: true, shiftKey: true };
    expect(gestureOfKey(LEAF, arrow)).toBe("indent");
    expect(gestureOfKey(LEAF, { ...arrow, key: "ArrowLeft" })).toBe("outdent");
    expect(gestureOfKey(LEAF, { ...arrow, key: "ArrowUp" })).toBeUndefined();
    expect(gestureOfKey(LEAF, { ...arrow, shiftKey: false })).toBeUndefined();
    expect(gestureOfKey(LEAF, { ...arrow, altKey: false })).toBeUndefined();
    // AltGr is Ctrl and Alt together, and Cmd is the Mac's own.
    expect(gestureOfKey(LEAF, { ...arrow, ctrlKey: true })).toBeUndefined();
    expect(gestureOfKey(LEAF, { ...arrow, metaKey: true })).toBeUndefined();
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

describe("the body of the move a gesture asks", () => {
  it("puts a task, and the summary that bears its group, under the task above it, last [WF-PLA-0080-A]", () => {
    // L'indentation d'un groupe de tâches déplace le groupe entier sous la tâche précédente : the
    // summary is moved by its identifier alone, its subordinates going with it on the server.
    expect(moveOf("indent", [RISK], offered())).toEqual({
      node_ids: [RISK.node_id],
      parent_id: LEAF.node_id,
      lock_version: 4,
    });
  });

  it("puts a task after its parent, under the parent of that one", () => {
    expect(moveOf("outdent", [TRANSPORT], offered())).toEqual({
      node_ids: [TRANSPORT.node_id],
      parent_id: RISK.parent_id,
      after_node_id: RISK.node_id,
      lock_version: 4,
    });
  });

  it("names every node of a list in the order given, the place being that of the first", () => {
    expect(moveOf("indent", [RISK, MILESTONE], offered())).toMatchObject({
      node_ids: [RISK.node_id, MILESTONE.node_id],
      parent_id: LEAF.node_id,
    });
  });

  it("asks nothing where the first node has no such place", () => {
    expect(moveOf("indent", [LEAF], offered())).toBeUndefined();
    expect(moveOf("outdent", [SUMMARY], offered())).toBeUndefined();
    expect(moveOf("indent", [], offered())).toBeUndefined();
  });
});
