// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the submenus « Chronologies » and « Sous-projet » of the menu of a cell are (US-0480,
 * WF-PLA-0060, WF-PRJ-0050): the timelines a task is inscribed to, and the sub-project a line of the
 * estimate or of the remaining to commit bears. Which row takes one is what the row says of itself
 * (`editable_fields`), never a deduction of the grid; which rows a choice acts on, and the body of the
 * write each of them is sent. Pure, neither server nor client.
 */
import type { components } from "@/api/generated/schema";
import type { CommandOffer } from "@/components/commands/offer";

import type { RowsWritten } from "./columns";
import type { GridNode, NodesWritten } from "./nodes";

/** An inscription of a task: to a timeline, or to the time/time tracking of a milestone. */
export type TrackingEntry = components["schemas"]["TrackingEntry"];

/** A timeline or a sub-project the menu offers, by its identifier and its label. */
export interface ChoiceOption {
  readonly id: string;
  readonly label: string;
  /** The code that names it before its label, a sub-project's, which alone is unique in a project. */
  readonly code?: string | undefined;
}

/** What a write of the menu answered, as the grid reads it, its totals left as they are. */
export type RowsApplied<Row> = Omit<RowsWritten<Row, never>, "totals">;

/** The timelines of the project, and the inscriptions a row bears. */
export interface TrackingChoices<Row extends GridNode> {
  /** The project the timelines belong to, where a timeline is created. */
  readonly project: string;
  /** The timelines of the project. */
  readonly timelines: readonly ChoiceOption[];
  /**
   * What the project lists of `manage_timelines`, which creates a timeline: none, and the creation is
   * not offered; unavailable, and it is offered greyed out with what it lacks.
   */
  readonly creation: CommandOffer | undefined;
  /** The inscriptions a row bears, as the grid reads them. */
  readonly entries: (row: Row) => readonly TrackingEntry[];
}

/** The sub-projects of the project, and the one a row bears. */
export interface SubprojectChoices<Row extends GridNode> {
  readonly subprojects: readonly ChoiceOption[];
  /** The sub-project a row bears, if it does. */
  readonly current: (row: Row) => string | null;
}

/** What a grid offers in the submenus of its cells; each is offered where the grid gives it. */
export interface RowChoices<Row extends GridNode> {
  readonly tracking?: TrackingChoices<Row> | undefined;
  readonly subproject?: SubprojectChoices<Row> | undefined;
  /** What a write answered, as the grid reads it: the rows written in place of the rows read. */
  readonly written: (written: NodesWritten) => RowsApplied<Row>;
}

/** What a choice changes of the rows it acts on. */
export type RowChange =
  | { readonly kind: "timeline"; readonly id: string; readonly on: boolean }
  | { readonly kind: "milestone"; readonly on: boolean }
  | { readonly kind: "subproject"; readonly id: string | null };

/** Whether a row names the inscriptions among the fields it accepts (`task.tracking`). */
export function trackable(row: GridNode): boolean {
  return (
    row.task !== undefined && row.task !== null && row.editable_fields.includes("task.tracking")
  );
}

/** Whether a row names its sub-project among the fields it accepts (`estimate_line.subproject_id`). */
export function portable(row: GridNode): boolean {
  return (
    row.estimate_line !== undefined &&
    row.estimate_line !== null &&
    row.editable_fields.includes("estimate_line.subproject_id")
  );
}

/** Whether a row is a milestone, which alone is inscribed to the time/time tracking. */
export function milestoneOf(row: GridNode): boolean {
  return row.task?.is_milestone === true;
}

/** Whether a change applies to a row: the row names the field, a milestone for the tracking. */
export function appliesTo(change: RowChange, row: GridNode): boolean {
  if (change.kind === "subproject") {
    return portable(row);
  }
  return trackable(row) && (change.kind === "timeline" || milestoneOf(row));
}

/** Whether an inscription is the time/time tracking, or to the timeline of an identifier. */
function inscribed(entry: TrackingEntry, change: RowChange): boolean {
  return change.kind === "milestone"
    ? entry.kind === "milestone_tracking"
    : change.kind === "timeline" && entry.kind === "timeline" && entry.timeline_id === change.id;
}

/**
 * The whole list of the inscriptions a task has once a change is made: the ones it has, the change
 * added when it is made and not there already, or taken away. The server replaces the list.
 */
export function entriesAfter(
  entries: readonly TrackingEntry[],
  change: RowChange,
): readonly TrackingEntry[] {
  if (change.kind === "subproject") {
    return entries;
  }
  const kept = entries.filter((entry) => !inscribed(entry, change));
  if (!change.on) {
    return kept;
  }
  return [
    ...kept,
    change.kind === "timeline"
      ? { kind: "timeline", timeline_id: change.id }
      : { kind: "milestone_tracking" },
  ];
}

/** Whether the rows an inscription is made on already bear it, for the row the menu opened on. */
export function isInscribed(entries: readonly TrackingEntry[], change: RowChange): boolean {
  return entries.some((entry) => inscribed(entry, change));
}

/**
 * Whether a row is already in the state a change aims at: inscribed or not as asked, or bearing the
 * sub-project chosen. A write that changes nothing is not sent.
 */
export function isSettled<Row extends GridNode>(
  change: RowChange,
  row: Row,
  choices: RowChoices<Row>,
): boolean {
  if (change.kind === "subproject") {
    return (choices.subproject?.current(row) ?? null) === change.id;
  }
  return isInscribed(choices.tracking?.entries(row) ?? [], change) === change.on;
}
