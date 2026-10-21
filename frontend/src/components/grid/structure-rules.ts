// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the gestures of structure of a grid are (US-0460): which a row — or the selection of
 * contiguous rows it stands in — takes, which a key asks, and the body of the node each creates
 * (`NodeCreate`) or of the move it makes (`NodeMove`), from a gesture or from rows dropped. Pure,
 * neither server nor client: the grid offers a gesture the structure it reads lists available
 * (`tasks`, `lines`), a move only where the rows shown hold the neighbour it rests on, and the
 * server judges the rest.
 */
import type { components } from "@/api/generated/schema";

import type { GridNode, StructurePath } from "./nodes";
import type { DropPlace } from "./row-selection";

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
  /**
   * The rows the grid shows, in the order of the tree, those a search or a filter leaves out
   * missing: what precedes a task among its siblings, and what bears it, only when shown.
   */
  readonly rows: readonly GridNode[];
  /** The version of the structure read, which a move carries (`NodeMove.lock_version`). */
  readonly version: number;
}

/**
 * The gestures: a first task, a task below a row, a sub-task, a line, an indentation, an
 * outdentation, a move up or down by a rank, a deletion.
 */
export type Gesture =
  "first" | "below" | "child" | "line" | "indent" | "outdent" | "up" | "down" | "delete";

/** The gestures that move nodes in the tree, with no dialog to ask. */
export type Moving = "indent" | "outdent" | "up" | "down";

const MOVING: readonly Gesture[] = ["indent", "outdent", "up", "down"] satisfies Moving[];

/** Whether a gesture moves nodes. */
export function moves(gesture: Gesture): gesture is Moving {
  return MOVING.includes(gesture);
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

/**
 * The sibling of a row at a rank (`Node.position`, from 1, the lines of a task counting before its
 * sub-tasks), if the rows the grid shows hold it. A rank names the true neighbour whatever the grid
 * leaves out: a search, a filter, the states the remaining to commit retains or the planning, which
 * reads no line, leave rows out, and the row shown above a task is not always the one the server
 * would put it under.
 */
function siblingAt(row: GridNode, rank: number, rows: readonly GridNode[]): GridNode | undefined {
  return rows.find((each) => each.parent_id === row.parent_id && each.position === rank);
}

/**
 * The nodes of a selection that bear the others — those none of whose ancestors is selected —, in
 * the order of the grid: a summary moved carries its subordinates, which the server would refuse to
 * move again under it. The ancestors are read up the rows shown, which a tree shows above each row.
 */
export function topsOf<Node extends GridNode>(
  nodes: readonly Node[],
  rows: readonly GridNode[],
): Node[] {
  const chosen = new Set(nodes.map((each) => each.node_id));
  const parents = new Map(rows.map((each) => [each.node_id, each.parent_id]));
  return nodes.filter((node) => {
    let above: string | null | undefined = node.parent_id;
    while (above !== null && above !== undefined) {
      if (chosen.has(above)) {
        return false;
      }
      above = parents.get(above);
    }
    return true;
  });
}

/** Whether nodes follow each other rank by rank among the same siblings, of one kind. */
function inRun(nodes: readonly GridNode[]): boolean {
  return nodes.every((node, at) => {
    const before = nodes[at - 1];
    return (
      before === undefined ||
      (node.parent_id === before.parent_id &&
        node.kind === before.kind &&
        node.position === before.position + 1)
    );
  });
}

/** Whether the grid lets nodes of a kind move: tasks where it lists tasks, lines where it lists lines. */
function movable(nodes: readonly GridNode[], scope: StructureGestures): boolean {
  return nodes.every((node) => (node.kind === "task" ? scope.tasks : scope.lines));
}

/** A move without the version it carries. */
type Placed = Omit<NodeMove, "lock_version">;

/**
 * The move by a rank of contiguous siblings of one kind: up, the sibling just above the first goes
 * after the last; down, they go after the sibling just below the last — each of their kind, and
 * shown.
 */
function byRank(
  gesture: "up" | "down",
  first: GridNode,
  last: GridNode,
  rows: readonly GridNode[],
): Placed | undefined {
  const neighbour =
    gesture === "up"
      ? siblingAt(first, first.position - 1, rows)
      : siblingAt(last, last.position + 1, rows);
  if (neighbour?.kind !== first.kind) {
    return undefined;
  }
  return gesture === "up"
    ? { node_ids: [neighbour.node_id], parent_id: first.parent_id, after_node_id: last.node_id }
    : { node_ids: [], parent_id: first.parent_id, after_node_id: neighbour.node_id };
}

/**
 * The move by a level of contiguous sibling tasks: an indentation puts them under the task just
 * above the first one, last (`after_node_id` absent) — none under a milestone, which bears nothing
 * —; an outdentation after their parent, under the parent of that one.
 */
function byLevel(
  gesture: "indent" | "outdent",
  first: GridNode,
  rows: readonly GridNode[],
): Placed | undefined {
  if (first.kind !== "task") {
    return undefined;
  }
  if (gesture === "indent") {
    const above = siblingAt(first, first.position - 1, rows);
    return above?.kind !== "task" || above.task?.is_milestone === true
      ? undefined
      : { node_ids: [], parent_id: above.node_id };
  }
  const parent = rows.find((each) => each.node_id === first.parent_id);
  return parent === undefined
    ? undefined
    : { node_ids: [], parent_id: parent.parent_id, after_node_id: parent.node_id };
}

/**
 * The move a gesture makes of the nodes that bear a selection, contiguous siblings of one kind, as
 * MS Project does (`byLevel`, `byRank`), the nodes moved being those, but for a move up, which moves
 * the sibling above them. None where the grid does not show the neighbour or the parent the move
 * rests on: the place never rests on a row the grid leaves out.
 */
function placeOf(
  gesture: Moving,
  tops: readonly GridNode[],
  rows: readonly GridNode[],
): Placed | undefined {
  const [first] = tops;
  const last = tops.at(-1);
  if (first === undefined || last === undefined || !inRun(tops)) {
    return undefined;
  }
  const place =
    gesture === "up" || gesture === "down"
      ? byRank(gesture, first, last, rows)
      : byLevel(gesture, first, rows);
  if (place === undefined) {
    return undefined;
  }
  return place.node_ids.length > 0
    ? place
    : { ...place, node_ids: tops.map((each) => each.node_id) };
}

/** The moves the nodes that bear the rows acted on take, in the order they are offered. */
function movesOf(rows: readonly GridNode[], scope: StructureGestures): readonly Moving[] {
  const tops = topsOf(rows, scope.rows);
  if (!movable(tops, scope)) {
    return [];
  }
  return (["indent", "outdent", "up", "down"] as const).filter(
    (gesture) => placeOf(gesture, tops, scope.rows) !== undefined,
  );
}

/**
 * The gestures a row takes, in the order they are offered, none the grid does not list: a task a
 * task below it, a sub-task unless it is a milestone, a line unless it is a summary or a milestone;
 * a line a line below it; no row — the header, an empty grid — a first task. The moves are those of
 * the rows acted on — the selection the row stands in, or the row alone —: an indentation unless the
 * first is the first of its siblings, follows a milestone, or has the grid not show the sibling that
 * precedes it, an outdentation unless it is at the root or the grid does not show its parent, up and
 * down where the grid shows the sibling of their kind just above or just below. The deletion is that
 * of the row alone, offered where no selection of several rows is acted on.
 */
export function gesturesOn(
  row: GridNode | undefined,
  scope: StructureGestures,
  acted: readonly GridNode[] = row === undefined ? [] : [row],
): readonly Gesture[] {
  if (row === undefined) {
    return scope.tasks ? ["first"] : [];
  }
  const deletes = (row.kind === "task" ? scope.tasks : scope.lines) && acted.length <= 1;
  return [
    ...createdOn(row, scope),
    ...movesOf(acted, scope),
    ...(deletes ? ["delete" as const] : []),
  ];
}

/**
 * The creations a row takes: a task a task below it, a sub-task unless it is a milestone, a line
 * unless it is a summary or a milestone; a line a line below it.
 */
function createdOn(row: GridNode, scope: StructureGestures): readonly Gesture[] {
  const milestone = row.task?.is_milestone === true;
  const task = row.kind === "task";
  const tasks: readonly Gesture[] = milestone ? ["below"] : ["below", "child"];
  const line = linesOffered(scope) && (!task || (!milestone && row.task?.is_summary !== true));
  return [...(task && scope.tasks ? tasks : []), ...(line ? ["line" as const] : [])];
}

/** The keys a gesture is asked by, as `aria-keyshortcuts` names them. */
export const GESTURE_KEYS: Readonly<Record<Gesture, string>> = {
  first: "Insert",
  below: "Insert",
  child: "Alt+Insert",
  line: "Control+Insert",
  indent: "Alt+Shift+ArrowRight",
  outdent: "Alt+Shift+ArrowLeft",
  up: "Alt+Shift+ArrowUp",
  down: "Alt+Shift+ArrowDown",
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

/** The moves the arrows ask with Alt and Shift, as MS Project does. */
const ARROWS: Readonly<Partial<Record<string, Moving>>> = {
  ArrowRight: "indent",
  ArrowLeft: "outdent",
  ArrowUp: "up",
  ArrowDown: "down",
};

/** The move an arrow asks with Alt and Shift, Ctrl and Cmd aside. */
function movingKey(pressed: Pressed): Moving | undefined {
  if (!pressed.altKey || !pressed.shiftKey || pressed.ctrlKey || pressed.metaKey === true) {
    return undefined;
  }
  return ARROWS[pressed.key];
}

/**
 * The gesture a key asks of a row, if it asks one: Insert a task below — a line below a line —,
 * Alt+Insert a sub-task, Ctrl+Insert a line, Alt+Shift+Right an indentation, Alt+Shift+Left an
 * outdentation, Alt+Shift+Up and Alt+Shift+Down a move by a rank, Ctrl+Delete the deletion.
 * Shift+Insert pastes, and is the grid's; Shift and an arrow alone extend the selection, and are the
 * grid's too; Ctrl or Cmd with the arrows is not asked — AltGr is Ctrl and Alt together.
 */
export function gestureOfKey(row: GridNode | undefined, pressed: Pressed): Gesture | undefined {
  if (pressed.key in ARROWS) {
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
 * The body of the move a gesture asks of the rows acted on — a selection of contiguous rows, or the
 * row alone —: the nodes that bear them (`topsOf`), in the order of the grid, at the place
 * `placeOf` gives — `after_node_id` absent for an indentation, which goes last (#1183). None where
 * they have no such place, or are of a kind the grid does not move. The version is that of the
 * structure, as the last write left it.
 */
export function moveOf(
  gesture: Moving,
  nodes: readonly GridNode[],
  scope: StructureGestures,
): NodeMove | undefined {
  const tops = topsOf(nodes, scope.rows);
  const place = movable(tops, scope) ? placeOf(gesture, tops, scope.rows) : undefined;
  return place === undefined ? undefined : { ...place, lock_version: scope.version };
}

/** Whether a row is one of the nodes, or under one of them, by its ancestors shown. */
function within(row: GridNode, nodes: readonly GridNode[], rows: readonly GridNode[]): boolean {
  const chosen = new Set(nodes.map((each) => each.node_id));
  const parents = new Map(rows.map((each) => [each.node_id, each.parent_id]));
  let at: string | null | undefined = row.node_id;
  while (at !== null && at !== undefined) {
    if (chosen.has(at)) {
      return true;
    }
    at = parents.get(at);
  }
  return false;
}

/**
 * Whether a task bears rows of a kind dropped under it: tasks unless it is a milestone, lines unless
 * it is a summary too.
 */
function bears(target: GridNode, kind: GridNode["kind"]): boolean {
  return (
    target.kind === "task" &&
    target.task?.is_milestone !== true &&
    (kind === "task" || target.task?.is_summary !== true)
  );
}

/**
 * The place rows dropped beside a row take: under it, last of their kind, where it bears them
 * (`bears`); before it, after the sibling just above it, or first where it is the first of its
 * siblings; after it, the last row of the grid. The rows go at the level of the row they are dropped
 * before or after, which is of their kind. None where the grid does not show the sibling the place
 * rests on, nor where the place is among the rows dropped or under them, which would leave them
 * where they are or put them under themselves.
 */
function dropPlace(
  tops: readonly GridNode[],
  target: GridNode,
  place: DropPlace,
  rows: readonly GridNode[],
): Pick<NodeMove, "parent_id" | "after_node_id"> | undefined {
  const [first] = tops;
  if (
    first === undefined ||
    tops.some((each) => each.kind !== first.kind) ||
    within(target, tops, rows)
  ) {
    return undefined;
  }
  if (place === "into") {
    return bears(target, first.kind) ? { parent_id: target.node_id } : undefined;
  }
  if (target.kind !== first.kind) {
    return undefined;
  }
  if (place === "after" || target.position === 1) {
    return {
      parent_id: target.parent_id,
      after_node_id: place === "after" ? target.node_id : null,
    };
  }
  const above = siblingAt(target, target.position - 1, rows);
  return above === undefined || within(above, tops, rows)
    ? undefined
    : { parent_id: target.parent_id, after_node_id: above.node_id };
}

/**
 * The body of the move of rows dropped beside a row (`DropPlace`): the nodes that bear them, in the
 * order of the grid, where `dropPlace` puts them. None where it puts them nowhere, or where they are
 * of a kind the grid does not move.
 */
export function dropOf(
  nodes: readonly GridNode[],
  target: GridNode,
  place: DropPlace,
  scope: StructureGestures,
): NodeMove | undefined {
  const tops = topsOf(nodes, scope.rows);
  const at = movable(tops, scope) ? dropPlace(tops, target, place, scope.rows) : undefined;
  return at === undefined
    ? undefined
    : { node_ids: tops.map((each) => each.node_id), ...at, lock_version: scope.version };
}
