// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the gestures of structure of a grid are (US-0460): which a row takes, which a key asks, and
 * the body of the node each creates (`NodeCreate`). Pure, neither server nor client: the grid
 * offers a gesture the structure it reads lists available (`tasks`, `lines`), and the server judges
 * the rest.
 */
import type { components } from "@/api/generated/schema";

import type { GridNode, StructurePath } from "./nodes";

/** The body of a node created. */
type NodeCreate = components["schemas"]["NodeCreate"];

/** A category of cost a line is created from. */
export interface LineCategory {
  readonly id: string;
  readonly label: string;
  /** Whether it may still be chosen. */
  readonly active: boolean;
}

/** What a grid offers of the gestures of structure, as the structure it reads lists its commands. */
export interface StructureGestures {
  /** The structure the gestures write in. */
  readonly structure: StructurePath;
  /** Whether tasks are created and deleted: the grid lists the command that writes the planning. */
  readonly tasks: boolean;
  /** Whether lines are created and deleted. */
  readonly lines: boolean;
  /** The categories a line is created from; none, and no line is created. */
  readonly categories: readonly LineCategory[] | undefined;
}

/** The gestures: a first task, a task below a row, a sub-task, a line, a deletion. */
export type Gesture = "first" | "below" | "child" | "line" | "delete";

/** What a dialog of creation gathered: the label, and for a line its category and its quantity. */
export interface Entered {
  readonly label: string;
  readonly line: { readonly category: string; readonly quantity: string } | undefined;
}

/** The label of a row, task or line. */
export function labelOf(row: GridNode): string {
  return row.task?.label ?? row.estimate_line?.label ?? "";
}

/** Whether a line may be created: the grid lists it, and a category may be chosen. */
function linesOffered(scope: StructureGestures): boolean {
  return scope.lines && (scope.categories ?? []).some((category) => category.active);
}

/** The gestures a task takes: a task below it, a sub-task, a line, its deletion. */
function onTask(row: GridNode, scope: StructureGestures): readonly Gesture[] {
  const milestone = row.task?.is_milestone === true;
  const summary = row.task?.is_summary === true;
  const gestures: Gesture[] = [];
  if (scope.tasks) {
    gestures.push("below");
    if (!milestone) {
      gestures.push("child");
    }
  }
  if (linesOffered(scope) && !milestone && !summary) {
    gestures.push("line");
  }
  if (scope.tasks) {
    gestures.push("delete");
  }
  return gestures;
}

/**
 * The gestures a row takes, in the order they are offered, none the grid does not list. A task
 * takes a task below it, a sub-task unless it is a milestone, a line unless it is a summary or a
 * milestone, and its deletion; a line takes a line below it and its deletion; no row — the header,
 * an empty grid — a first task.
 */
export function gesturesOn(
  row: GridNode | undefined,
  scope: StructureGestures,
): readonly Gesture[] {
  if (row === undefined) {
    return scope.tasks ? ["first"] : [];
  }
  if (row.kind === "task") {
    return onTask(row, scope);
  }
  return [
    ...(linesOffered(scope) ? (["line"] as const) : []),
    ...(scope.lines ? (["delete"] as const) : []),
  ];
}

/** The keys a gesture is asked by, as `aria-keyshortcuts` names them. */
export const GESTURE_KEYS: Readonly<Record<Gesture, string>> = {
  first: "Insert",
  below: "Insert",
  child: "Alt+Insert",
  line: "Control+Insert",
  delete: "Control+Delete",
};

/** A key pressed. */
interface Pressed {
  readonly key: string;
  readonly ctrlKey: boolean;
  readonly altKey: boolean;
  readonly shiftKey: boolean;
}

/**
 * The gesture a key asks of a row, if it asks one: Insert a task below — a line below a line —,
 * Alt+Insert a sub-task, Ctrl+Insert a line, Ctrl+Delete the deletion. Shift+Insert pastes, and is
 * the grid's.
 */
export function gestureOfKey(row: GridNode | undefined, pressed: Pressed): Gesture | undefined {
  if (pressed.shiftKey) {
    return undefined;
  }
  if (pressed.key === "Delete") {
    return pressed.ctrlKey && !pressed.altKey ? "delete" : undefined;
  }
  if (pressed.key !== "Insert") {
    return undefined;
  }
  if (pressed.altKey) {
    return pressed.ctrlKey ? undefined : "child";
  }
  if (pressed.ctrlKey) {
    return "line";
  }
  if (row === undefined) {
    return "first";
  }
  return row.kind === "estimate_line" ? "line" : "below";
}

/**
 * The body of the node a gesture creates from a row, with what its dialog gathered: a task below a
 * row at the place after it among its siblings, a sub-task or a line at the end of the row, a line
 * below a line at the place after it. The server gives the rest: a task created is a leaf,
 * automatic, of one day, without predecessor (WF-DEV-0050).
 */
export function bodyOf(gesture: Gesture, row: GridNode | undefined, entered: Entered): NodeCreate {
  if (entered.line !== undefined) {
    const line = {
      label: entered.label,
      cost_category_id: entered.line.category,
      quantity: entered.line.quantity,
    };
    return row?.kind === "estimate_line"
      ? {
          kind: "estimate_line",
          parent_id: row.parent_id,
          position: row.position + 1,
          estimate_line: line,
        }
      : { kind: "estimate_line", parent_id: row?.node_id ?? null, estimate_line: line };
  }
  const task = { label: entered.label };
  if (gesture === "below" && row !== undefined) {
    return { kind: "task", parent_id: row.parent_id, position: row.position + 1, task };
  }
  return { kind: "task", parent_id: gesture === "child" ? (row?.node_id ?? null) : null, task };
}
