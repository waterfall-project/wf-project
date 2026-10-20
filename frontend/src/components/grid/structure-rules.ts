// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the gestures of structure of a grid are (US-0460): which a row takes, which a key asks, and
 * the body of the node each creates (`NodeCreate`) or of the move it makes (`NodeMove`). Pure, neither server nor client: the grid
 * offers a gesture the structure it reads lists available (`tasks`, `lines`), and the server judges
 * the rest.
 */
import type { components } from "@/api/generated/schema";

import type { GridNode, StructurePath } from "./nodes";

/** The body of a node created. */
type NodeCreate = components["schemas"]["NodeCreate"];

/** The body of nodes moved. */
type NodeMove = components["schemas"]["NodeMove"];

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
  /** The rows the grid reads, in the order of the tree: what precedes a task, and what bears it. */
  readonly rows: readonly GridNode[];
  /** The version of the structure read, which a move carries (`NodeMove.lock_version`). */
  readonly version: number;
}

/**
 * The gestures: a first task, a task below a row, a sub-task, a line, an indentation, an
 * outdentation, a deletion.
 */
export type Gesture = "first" | "below" | "child" | "line" | "indent" | "outdent" | "delete";

/** The gestures that move tasks in the tree, with no dialog to ask. */
export type Moving = "indent" | "outdent";

/** Whether a gesture moves tasks. */
export function moves(gesture: Gesture): gesture is Moving {
  return gesture === "indent" || gesture === "outdent";
}

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

/** The task that precedes a task among its siblings, as the grid shows them. */
function precedingSibling(row: GridNode, rows: readonly GridNode[]): GridNode | undefined {
  const at = rows.findIndex((each) => each.node_id === row.node_id);
  return rows
    .slice(0, Math.max(at, 0))
    .findLast((each) => each.kind === "task" && each.parent_id === row.parent_id);
}

/**
 * The place a task takes by an indentation or an outdentation, as MS Project does: an indentation
 * puts it under the task that precedes it, in the last place (`after_node_id` absent) — none for
 * the first of its siblings, nor under a milestone, which bears nothing —; an outdentation puts it
 * after its parent, under the parent of that one — none for a task already at the root.
 */
function placeOf(
  gesture: Moving,
  row: GridNode,
  rows: readonly GridNode[],
): Pick<NodeMove, "parent_id" | "after_node_id"> | undefined {
  if (gesture === "indent") {
    const above = precedingSibling(row, rows);
    return above === undefined || above.task?.is_milestone === true
      ? undefined
      : { parent_id: above.node_id };
  }
  const parent = rows.find((each) => each.node_id === row.parent_id);
  return parent === undefined
    ? undefined
    : { parent_id: parent.parent_id, after_node_id: parent.node_id };
}

/** The gestures a task takes: a task below it, a sub-task, a line, its move, its deletion. */
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
    const movable = (["indent", "outdent"] as const).filter(
      (gesture) => placeOf(gesture, row, scope.rows) !== undefined,
    );
    gestures.push(...movable, "delete");
  }
  return gestures;
}

/**
 * The gestures a row takes, in the order they are offered, none the grid does not list. A task
 * takes a task below it, a sub-task unless it is a milestone, a line unless it is a summary or a
 * milestone, an indentation unless it is the first of its siblings or follows a milestone, an
 * outdentation unless it is at the root, and its deletion; a line takes a line below it and its deletion; no row — the header,
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
  indent: "Alt+Shift+ArrowRight",
  outdent: "Alt+Shift+ArrowLeft",
  delete: "Control+Delete",
};

/** A key pressed. */
interface Pressed {
  readonly key: string;
  readonly ctrlKey: boolean;
  readonly altKey: boolean;
  readonly shiftKey: boolean;
  readonly metaKey?: boolean | undefined;
}

/** The move an arrow asks with Alt and Shift: right indents, left outdents, Ctrl and Cmd aside. */
function movingKey(pressed: Pressed): Moving | undefined {
  if (!pressed.altKey || !pressed.shiftKey || pressed.ctrlKey || pressed.metaKey === true) {
    return undefined;
  }
  return pressed.key === "ArrowRight" ? "indent" : "outdent";
}

/**
 * The gesture a key asks of a row, if it asks one: Insert a task below — a line below a line —,
 * Alt+Insert a sub-task, Ctrl+Insert a line, Alt+Shift+Right an indentation, Alt+Shift+Left an
 * outdentation, Ctrl+Delete the deletion. Shift+Insert pastes, and is the grid's; Ctrl or Cmd with
 * the arrows is not asked — AltGr is Ctrl and Alt together.
 */
export function gestureOfKey(row: GridNode | undefined, pressed: Pressed): Gesture | undefined {
  if (pressed.key === "ArrowRight" || pressed.key === "ArrowLeft") {
    return movingKey(pressed);
  }
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
 * row after it among its siblings, a sub-task or a line at the end of the row, a line below a line
 * after it. The place is named by the node to follow (`after_node_id`), never by a rank a filtered
 * grid could not count; without it, the node goes last under its parent (#1183). The server gives
 * the rest: a task created is a leaf, automatic, of one day, without predecessor (WF-DEV-0050).
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
          after_node_id: row.node_id,
          estimate_line: line,
        }
      : { kind: "estimate_line", parent_id: row?.node_id ?? null, estimate_line: line };
  }
  const task = { label: entered.label };
  if (gesture === "below" && row !== undefined) {
    return { kind: "task", parent_id: row.parent_id, after_node_id: row.node_id, task };
  }
  return { kind: "task", parent_id: gesture === "child" ? (row?.node_id ?? null) : null, task };
}

/**
 * The body of the move a gesture asks of tasks: the nodes in the order of the grid, under the
 * parent and after the node the place of the first one names (`placeOf`) — absent for an
 * indentation, which goes last (#1183). Made for a list of nodes, a selection of contiguous rows;
 * none when the first one has no such place. The version is that of the structure read.
 */
export function moveOf(
  gesture: Moving,
  nodes: readonly GridNode[],
  scope: StructureGestures,
): NodeMove | undefined {
  const [first] = nodes;
  const place = first === undefined ? undefined : placeOf(gesture, first, scope.rows);
  return place === undefined
    ? undefined
    : { node_ids: nodes.map((each) => each.node_id), ...place, lock_version: scope.version };
}
