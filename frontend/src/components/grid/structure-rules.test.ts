// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import type { NodeList } from "./nodes";
import {
  bodyOf,
  gestureOfKey,
  gesturesOn,
  dropOf,
  moveOf,
  type StructureGestures,
  topsOf,
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
const RELANCE = row("Relance du fournisseur");
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
    expect(gesturesOn(LEAF, offered())).toEqual([
      "below",
      "child",
      "line",
      "outdent",
      "down",
      "delete",
    ]);
    expect(gesturesOn(SUMMARY, offered())).toEqual(["below", "child", "delete"]);
  });

  it("gives a line a line below, its move down among the lines, and its deletion, and the header a first task", () => {
    expect(gesturesOn(LINE, offered())).toEqual(["line", "down", "delete"]);
    expect(gesturesOn(undefined, offered())).toEqual(["first"]);
  });

  it("gives nothing the grid does not list: no task, no line, no category to choose", () => {
    expect(gesturesOn(LEAF, offered({ tasks: false }))).toEqual(["line"]);
    expect(gesturesOn(LEAF, offered({ lines: false }))).toEqual([
      "below",
      "child",
      "outdent",
      "down",
      "delete",
    ]);
    expect(gesturesOn(LEAF, offered({ categories: undefined }))).toEqual([
      "below",
      "child",
      "outdent",
      "down",
      "delete",
    ]);
    expect(gesturesOn(LINE, offered({ categories: [{ ...CATEGORY, active: false }] }))).toEqual([
      "down",
      "delete",
    ]);
    // A line moves where the grid lists the lines.
    expect(gesturesOn(LINE, offered({ lines: false }))).toEqual([]);
    expect(gesturesOn(undefined, offered({ tasks: false }))).toEqual([]);
    expect(gesturesOn(LEAF, offered({ tasks: false, lines: false }))).toEqual([]);
  });

  it("gives a milestone neither sub-task nor line", () => {
    const milestone = { ...LEAF, task: { ...LEAF.task, is_milestone: true } } as typeof LEAF;
    expect(gesturesOn(milestone, offered())).toEqual(["below", "outdent", "down", "delete"]);
  });

  it("gives an indentation to a task that has a sibling above it, bearing tasks, and an outdentation to a task under another", () => {
    expect(gesturesOn(TRANSPORT, offered())).toEqual([
      "below",
      "child",
      "line",
      "indent",
      "outdent",
      "up",
      "delete",
    ]);
    expect(gesturesOn(MILESTONE, offered())).toEqual([
      "below",
      "indent",
      "outdent",
      "up",
      "down",
      "delete",
    ]);
    // The first of its siblings has nothing to go under; a task at the root has nothing to leave.
    expect(gesturesOn(LEAF, offered())).not.toContain("indent");
    expect(gesturesOn(SUMMARY, offered())).not.toContain("outdent");
    expect(gesturesOn(SUMMARY, offered())).not.toContain("indent");
    // A line is moved with the move of its task; it takes neither.
    expect(gesturesOn(LINE, offered())).not.toContain("indent");
    expect(gesturesOn(LINE, offered())).not.toContain("outdent");
  });

  it("gives an indentation only where the grid shows the sibling just above, whatever a search or a filter leaves out [WF-PLA-0080-A]", () => {
    // The rank of a node counts its siblings, lines included: the one above must be that less one.
    const withoutRelance = estimate.items.filter((each) => each.node_id !== RELANCE.node_id);
    expect(gesturesOn(TRANSPORT, offered())).toContain("indent");
    expect(gesturesOn(TRANSPORT, offered({ rows: withoutRelance }))).not.toContain("indent");
    // The parent being shown, the outdentation does not rest on a row left out.
    expect(gesturesOn(TRANSPORT, offered({ rows: withoutRelance }))).toContain("outdent");
    // The parent left out, there is no place after it.
    const withoutSummary = estimate.items.filter((each) => each.node_id !== SUMMARY.node_id);
    expect(gesturesOn(RISK, offered({ rows: withoutSummary }))).not.toContain("outdent");
  });

  it("gives no indentation under a milestone, which bears nothing, and none where the grid lists no task", () => {
    const rows = estimate.items.map((each) =>
      each.node_id === RELANCE.node_id
        ? { ...each, task: { ...each.task, is_milestone: true } }
        : each,
    ) as typeof estimate.items;
    expect(gesturesOn(TRANSPORT, offered({ rows }))).not.toContain("indent");
    expect(gesturesOn(TRANSPORT, offered())).toContain("indent");
    // The risk occurred stands after the factory acceptance, a milestone: it goes under none.
    expect(gesturesOn(RISK, offered())).not.toContain("indent");
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

  it("asks an indentation on Alt+Shift+Right, an outdentation on Alt+Shift+Left, a move by a rank on Alt+Shift+Up and Down", () => {
    const arrow = { ...PRESSED, key: "ArrowRight", altKey: true, shiftKey: true };
    expect(gestureOfKey(LEAF, arrow)).toBe("indent");
    expect(gestureOfKey(LEAF, { ...arrow, key: "ArrowLeft" })).toBe("outdent");
    expect(gestureOfKey(LEAF, { ...arrow, key: "ArrowUp" })).toBe("up");
    expect(gestureOfKey(LEAF, { ...arrow, key: "ArrowDown" })).toBe("down");
    // Shift and an arrow alone extend the selection.
    expect(gestureOfKey(LEAF, { ...arrow, key: "ArrowDown", altKey: false })).toBeUndefined();
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
  it("puts the active task, a summary with its group, under the task above it, last [WF-PLA-0080-A]", () => {
    // Part of the criterion — the active row, not a selection of several tasks (US-0460/L5): the
    // summary is moved by its identifier alone, its subordinates going with it on the server.
    const rows = estimate.items.map((each) =>
      each.node_id === MILESTONE.node_id
        ? { ...each, task: { ...each.task, is_milestone: false } }
        : each,
    ) as typeof estimate.items;
    expect(moveOf("indent", [RISK], offered({ rows }))).toEqual({
      node_ids: [RISK.node_id],
      parent_id: MILESTONE.node_id,
      lock_version: 4,
    });
    expect(moveOf("indent", [TRANSPORT], offered())).toEqual({
      node_ids: [TRANSPORT.node_id],
      parent_id: RELANCE.node_id,
      lock_version: 4,
    });
    // Under the milestone just above it, the summary goes nowhere.
    expect(moveOf("indent", [RISK], offered())).toBeUndefined();
  });

  it("puts a task after its parent, under the parent of that one", () => {
    expect(moveOf("outdent", [TRANSPORT], offered())).toEqual({
      node_ids: [TRANSPORT.node_id],
      parent_id: RISK.parent_id,
      after_node_id: RISK.node_id,
      lock_version: 4,
    });
  });

  it("moves the group of a selection, the nodes that bear its rows, under the task above the first one [WF-PLA-0080-A]", () => {
    // L'indentation d'un groupe de tâches déplace le groupe entier sous la tâche précédente : the
    // selection from MILESTONE to RISK holds the subordinates of RISK, which go with it.
    const selection = estimate.items.slice(estimate.items.indexOf(MILESTONE));
    expect(moveOf("indent", selection, offered())).toEqual({
      node_ids: [MILESTONE.node_id, RISK.node_id],
      parent_id: LEAF.node_id,
      lock_version: 4,
    });
    expect(moveOf("outdent", selection, offered())).toEqual({
      node_ids: [MILESTONE.node_id, RISK.node_id],
      parent_id: SUMMARY.parent_id,
      after_node_id: SUMMARY.node_id,
      lock_version: 4,
    });
  });

  it("moves nothing that is not a run of siblings rank by rank, of one kind", () => {
    // Out of the order of the grid, under two parents, or a task and a line.
    expect(moveOf("indent", [RISK, MILESTONE], offered())).toBeUndefined();
    expect(moveOf("outdent", [TRANSPORT, MILESTONE], offered())).toBeUndefined();
    expect(moveOf("up", [row("Affrètement"), MILESTONE], offered())).toBeUndefined();
  });

  it("moves a run by a rank: down after the sibling below the last, up by the sibling above the first going after the last", () => {
    expect(moveOf("down", [LEAF, MILESTONE], offered())).toEqual({
      node_ids: [LEAF.node_id, MILESTONE.node_id],
      parent_id: SUMMARY.node_id,
      after_node_id: RISK.node_id,
      lock_version: 4,
    });
    const run = estimate.items.slice(
      estimate.items.indexOf(LEAF),
      estimate.items.indexOf(MILESTONE),
    );
    expect(moveOf("down", run, offered())).toEqual({
      node_ids: [LEAF.node_id],
      parent_id: SUMMARY.node_id,
      after_node_id: MILESTONE.node_id,
      lock_version: 4,
    });
    expect(moveOf("up", [MILESTONE, RISK], offered())).toEqual({
      node_ids: [LEAF.node_id],
      parent_id: SUMMARY.node_id,
      after_node_id: RISK.node_id,
      lock_version: 4,
    });
    // A line moves among the lines of its task: the last one has none below it.
    expect(moveOf("up", [row("Borniers")], offered())).toMatchObject({
      node_ids: [LINE.node_id],
      after_node_id: row("Borniers").node_id,
    });
    expect(moveOf("down", [row("Provision — risque de reprise du câblage")], offered())).toBe(
      undefined,
    );
  });

  it("moves by a rank only where the grid shows the neighbour, of the kind of the run, and the kind moves", () => {
    const withoutMilestone = estimate.items.filter((each) => each.node_id !== MILESTONE.node_id);
    expect(moveOf("down", [LEAF], offered({ rows: withoutMilestone }))).toBeUndefined();
    expect(moveOf("up", [RISK], offered({ rows: withoutMilestone }))).toBeUndefined();
    expect(moveOf("down", [LINE], offered({ lines: false }))).toBeUndefined();
    expect(moveOf("down", [LEAF], offered({ tasks: false }))).toBeUndefined();
  });

  it("asks nothing where the grid does not show the sibling above the first node, the one shown being farther [WF-PLA-0080-A]", () => {
    const withoutRelance = estimate.items.filter((each) => each.node_id !== RELANCE.node_id);
    // The sub-task of rank 1 is not shown above the one of rank 2, which would go under it: the
    // risk occurred, of rank 3, shows the factory acceptance of rank 2 above it and bears nothing.
    expect(moveOf("indent", [TRANSPORT], offered({ rows: withoutRelance }))).toBeUndefined();
    expect(moveOf("indent", [TRANSPORT], offered())).toBeDefined();
  });

  it("asks nothing where the first node has no such place", () => {
    expect(moveOf("indent", [LEAF], offered())).toBeUndefined();
    expect(moveOf("outdent", [SUMMARY], offered())).toBeUndefined();
    expect(moveOf("indent", [], offered())).toBeUndefined();
  });
});

describe("the nodes that bear a selection", () => {
  it("keeps those none of whose ancestors is selected, in the order of the grid", () => {
    const selection = estimate.items.slice(estimate.items.indexOf(LEAF));
    expect(topsOf(selection, estimate.items)).toEqual([LEAF, MILESTONE, RISK]);
    expect(topsOf([TRANSPORT, row("Affrètement")], estimate.items)).toEqual([TRANSPORT]);
  });
});

describe("the body of the move of rows dropped", () => {
  const affretement = row("Affrètement");
  it("puts rows dropped under a task last under it, the nodes that bear them only", () => {
    expect(dropOf([TRANSPORT, affretement], LEAF, "into", offered())).toEqual({
      node_ids: [TRANSPORT.node_id],
      parent_id: LEAF.node_id,
      lock_version: 4,
    });
    // A line goes under a task that bears lines: no summary, no milestone.
    expect(dropOf([affretement], LEAF, "into", offered())).toMatchObject({
      parent_id: LEAF.node_id,
    });
    expect(dropOf([affretement], RISK, "into", offered())).toBeUndefined();
    expect(dropOf([TRANSPORT], MILESTONE, "into", offered())).toBeUndefined();
  });

  it("puts rows dropped before a row after the sibling above it, or first, at its level", () => {
    expect(dropOf([TRANSPORT], RISK, "before", offered())).toEqual({
      node_ids: [TRANSPORT.node_id],
      parent_id: SUMMARY.node_id,
      after_node_id: MILESTONE.node_id,
      lock_version: 4,
    });
    expect(dropOf([TRANSPORT], LEAF, "before", offered())).toMatchObject({
      parent_id: SUMMARY.node_id,
      after_node_id: null,
    });
    expect(dropOf([LEAF], MILESTONE, "after", offered())).toMatchObject({
      parent_id: SUMMARY.node_id,
      after_node_id: MILESTONE.node_id,
    });
  });

  it("drops nowhere the place would rest on a row left out, on the rows dropped or under them, or by another kind", () => {
    const withoutMilestone = estimate.items.filter((each) => each.node_id !== MILESTONE.node_id);
    expect(
      dropOf([TRANSPORT], RISK, "before", offered({ rows: withoutMilestone })),
    ).toBeUndefined();
    // Where they stand already, under themselves, or a task before a line.
    expect(dropOf([MILESTONE], RISK, "before", offered())).toBeUndefined();
    expect(dropOf([RISK], TRANSPORT, "into", offered())).toBeUndefined();
    expect(dropOf([RISK], RISK, "before", offered())).toBeUndefined();
    expect(dropOf([TRANSPORT], LINE, "before", offered())).toBeUndefined();
    expect(dropOf([TRANSPORT, LINE], LEAF, "into", offered())).toBeUndefined();
    expect(dropOf([TRANSPORT], LEAF, "into", offered({ tasks: false }))).toBeUndefined();
  });
});

describe("the nodes a differential removes", () => {
  // The installation on site read on the amendment 2: under « Montage des armoires sur site », the
  // line « Câblage sur site » is unchanged and the line after it is removed, read in its place.
  const amendment = example("nodes_amendment") as NodeList;
  /** The node of the amendment with a label. */
  const inAmendment = (label: string) => {
    const found = amendment.items.find(
      (node) => (node.task?.label ?? node.estimate_line?.label) === label,
    );
    if (found === undefined) {
      throw new Error(`no row ${label}`);
    }
    return found;
  };
  const REMOVED = inAmendment("Assistance aux essais de câblage");
  const BEFORE = inAmendment("Câblage sur site");
  const MOUNTING = inAmendment("Montage des armoires sur site");
  const scope = offered({ rows: amendment.items });

  it("takes no gesture: nothing is created beside it, nothing deleted, nothing moved (#1185)", () => {
    expect(REMOVED.difference).toBe("removed");
    expect(gesturesOn(BEFORE, scope)).toEqual(["line", "delete"]);
    expect(gesturesOn(REMOVED, scope)).toEqual([]);
    expect(gesturesOn(REMOVED, scope, [REMOVED])).toEqual([]);
  });

  it("is moved neither alone nor in a selection, nor is the node next to it moved onto it (#1185)", () => {
    for (const gesture of ["indent", "outdent", "up", "down"] as const) {
      expect(moveOf(gesture, [REMOVED], scope)).toBeUndefined();
      expect(moveOf(gesture, [BEFORE, REMOVED], scope)).toBeUndefined();
    }
    // The line before it would go down after it, a place that is no more of the structure.
    expect(moveOf("down", [BEFORE], scope)).toBeUndefined();
  });

  it("is a place nothing is dropped at, and nothing removed is dropped (#1185)", () => {
    expect(dropOf([BEFORE], REMOVED, "after", scope)).toBeUndefined();
    expect(dropOf([BEFORE], REMOVED, "before", scope)).toBeUndefined();
    expect(dropOf([REMOVED], MOUNTING, "into", scope)).toBeUndefined();
  });
});
