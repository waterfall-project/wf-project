// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cards of the Kanban of the start of the tasks (FBS-4.5.3, WF-RAE-0030), as the screen keeps
 * them: what a card shows and offers of a task, taken from the node the API gives (`KanbanTask`),
 * and nothing more — the page reads a thousand tasks, and a card that carried its node whole would
 * send the browser the predecessors, the tracking and the amounts of each. The gestures of a card
 * are those the API lists for it (`available_commands`, WF-IHM-0090), with the state each sends
 * (`KanbanCommandAvailability.progress`); the screen deduces none of it from the nature of the task
 * or from its lines (WF-ARC-0020).
 *
 * Pure, and neither server nor client: the page cuts the cards, the Kanban moves them.
 */
import type { components, operations } from "@/api/generated/schema";

import { SEARCH } from "@/components/grid/query";
import { progressHref, type TaskProgress } from "./address";

/** The answer of `listStartableTasks`: the tasks not started, started and completed. */
export type StartableTasks =
  operations["listStartableTasks"]["responses"][200]["content"]["application/json"];

/** A task of the Kanban, as the API reads it: a node and the gestures of its card. */
export type KanbanTask = components["schemas"]["KanbanTask"];

/** A gesture of a card, as the API lists it: available or not, and the state it sends. */
export type CardGesture = KanbanTask["available_commands"][number];

/** The structure the tasks of the Kanban live in: where a gesture is written. */
export interface KanbanStructure {
  readonly project_id: string;
  readonly revision_id: string;
  readonly structure_id: string;
}

/** The gestures that happen on a date the user enters: the start and the completion of a task. */
export const DATED: ReadonlySet<CardGesture["command"]> = new Set(["start", "complete"]);

/** A card of the Kanban: a task, what it shows, and the gestures it lists. */
export interface KanbanCard {
  readonly node_id: string;
  /** The version of the node read, which a gesture goes on from. */
  readonly lock_version: number;
  readonly row_number: number;
  readonly label: string;
  /** The state of the task, which is the column of its card. */
  readonly state: TaskProgress;
  readonly is_milestone: boolean;
  /** The finish of the task, as a date of the planning; none when it has none. */
  readonly finish: string | undefined;
  readonly finish_overdue: boolean;
  /** The date the task was completed, for a task completed. */
  readonly completed_on: string | undefined;
  /** Whether every predecessor is completed, as the API says it of a task not started. */
  readonly predecessors_completed: boolean;
  /** The gestures of the card, in the order of the API; none without the permission to make them. */
  readonly commands: readonly CardGesture[];
}

/** The cards of the three columns, each in the order of the plan. */
export type KanbanColumns = Readonly<Record<TaskProgress, readonly KanbanCard[]>>;

/** The columns of the Kanban in their order, each with the key of its title in the catalogue. */
export const COLUMNS = [
  ["not_started", "notStarted"],
  ["started", "started"],
  ["completed", "completed"],
] as const satisfies readonly (readonly [TaskProgress, string])[];

/** The key of the title of each column in the catalogue. */
export const TITLE: Readonly<Record<TaskProgress, "notStarted" | "started" | "completed">> = {
  not_started: "notStarted",
  started: "started",
  completed: "completed",
};

/**
 * The card of a task in a state: what it shows of its node, and the gestures it lists — none for a
 * node the API answered a gesture with, which lists none until the screen reads it anew.
 */
export function cardOf(
  node: components["schemas"]["Node"] & Partial<Pick<KanbanTask, "available_commands">>,
  state: TaskProgress,
  predecessorsCompleted = false,
): KanbanCard {
  const task = node.task;
  return {
    node_id: node.node_id,
    lock_version: node.lock_version,
    row_number: node.row_number,
    label: task?.label ?? "",
    state,
    is_milestone: task?.is_milestone === true,
    finish: task?.finish?.date,
    finish_overdue: task?.finish_overdue === true,
    completed_on: task?.completed_on ?? undefined,
    predecessors_completed: predecessorsCompleted,
    commands: (node.available_commands ?? []).map(
      ({ command, is_available, missing_conditions, progress }) => ({
        command,
        is_available,
        missing_conditions,
        progress,
      }),
    ),
  };
}

/** The cards of the answer of `listStartableTasks`, by column. */
export function columnsOf(tasks: StartableTasks): KanbanColumns {
  return {
    not_started: tasks.not_started.map((node) =>
      cardOf(node, "not_started", node.predecessors_completed),
    ),
    started: tasks.started.map((node) => cardOf(node, "started")),
    completed: tasks.completed.map((node) => cardOf(node, "completed")),
  };
}

/** The version of each node the columns hold. */
function versionsRead(columns: KanbanColumns): ReadonlyMap<string, number> {
  const read = new Map<string, number>();
  for (const [state] of COLUMNS) {
    for (const card of columns[state]) {
      read.set(card.node_id, card.lock_version);
    }
  }
  return read;
}

/**
 * The answers the columns read do not yet overtake: those of a node the columns hold at an older
 * version, or not at all. The answers themselves when none is overtaken, so that a state that keeps
 * them is not written for nothing.
 */
export function unanswered(
  columns: KanbanColumns,
  answered: Readonly<Record<string, KanbanCard>>,
): Readonly<Record<string, KanbanCard>> {
  const read = versionsRead(columns);
  const kept = Object.entries(answered).filter(
    ([id, card]) => (read.get(id) ?? -1) < card.lock_version,
  );
  return kept.length === Object.keys(answered).length ? answered : Object.fromEntries(kept);
}

/**
 * The columns once the cards the API answered a gesture with replace theirs: a card answered goes to
 * the column of its new state, in the order of the plan, unless the columns read since already hold
 * the node at that version or a later one — the most recent wins, by the counter of the node.
 */
export function replaced(
  columns: KanbanColumns,
  answered: Readonly<Record<string, KanbanCard>>,
): KanbanColumns {
  const cards = Object.values(answered);
  if (cards.length === 0) {
    return columns;
  }
  const read = versionsRead(columns);
  const newer = cards.filter((card) => (read.get(card.node_id) ?? -1) < card.lock_version);
  if (newer.length === 0) {
    return columns;
  }
  const answeredIds = new Set(newer.map((card) => card.node_id));
  const column = (state: TaskProgress) =>
    [
      ...columns[state].filter((card) => !answeredIds.has(card.node_id)),
      ...newer.filter((card) => card.state === state),
    ].sort((a, b) => a.row_number - b.row_number);
  return {
    not_started: column("not_started"),
    started: column("started"),
    completed: column("completed"),
  };
}

/**
 * The address of the grid of the remaining to commit on a task: its label searched, and the tasks
 * not started shown too when the task is not started — the grid shows the lines of the tasks
 * started alone otherwise (WF-RAE-0040).
 */
export function remainingHref(pathname: string, card: KanbanCard): string {
  return progressHref(
    pathname,
    new URLSearchParams({ [SEARCH]: card.label }),
    card.state === "not_started",
  );
}

/** The position of a card in the columns: its column, and its place in it. */
interface Place {
  readonly column: number;
  readonly index: number;
}

/** Where a card is, among the columns. */
function placeOf(columns: KanbanColumns, id: string): Place | undefined {
  for (const [column, [state]] of COLUMNS.entries()) {
    const index = columns[state].findIndex((card) => card.node_id === id);
    if (index >= 0) {
      return { column, index };
    }
  }
  return undefined;
}

/** The cards of the column at a place of the row of columns; none past its ends. */
function cardsAt(columns: KanbanColumns, column: number): readonly KanbanCard[] {
  const state = COLUMNS[column]?.[0];
  return state === undefined ? [] : columns[state];
}

/**
 * The card a sideways arrow leads to: in the nearest column that holds any, at the same place, or
 * the last card when the column holds fewer.
 */
function acrossFrom(columns: KanbanColumns, place: Place, step: 1 | -1): string | undefined {
  for (let at = place.column + step; at >= 0 && at < COLUMNS.length; at += step) {
    const cards = cardsAt(columns, at);
    if (cards.length > 0) {
      return cards[Math.min(place.index, cards.length - 1)]?.node_id;
    }
  }
  return undefined;
}

/**
 * The card the arrows, Home and End lead to from a card (WF-IHM-0100): the up and down arrows, Home
 * and End within its column, the sideways arrows in the nearest column that holds any, at the same
 * place. None for a key that leads nowhere.
 */
export function focusOf(columns: KanbanColumns, id: string, key: string): string | undefined {
  const place = placeOf(columns, id);
  if (place === undefined) {
    return undefined;
  }
  const column = cardsAt(columns, place.column);
  switch (key) {
    case "ArrowDown":
      return column[place.index + 1]?.node_id;
    case "ArrowUp":
      return column[place.index - 1]?.node_id;
    case "Home":
      return column[0]?.node_id;
    case "End":
      return column.at(-1)?.node_id;
    case "ArrowRight":
      return acrossFrom(columns, place, 1);
    case "ArrowLeft":
      return acrossFrom(columns, place, -1);
    default:
      return undefined;
  }
}
