// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the submenu « Chronologies » of the menu of a cell is (US-0480, WF-PLA-0060): the timelines
 * a task is inscribed to. Which row takes one is what the row says of itself (`editable_fields`),
 * never a deduction of the grid; which rows a choice acts on, and the body of the write each of
 * them is sent. Pure, neither server nor client.
 */
import type { components } from "@/api/generated/schema";
import type { CommandOffer } from "@/components/commands/offer";

import type { RowsWritten } from "./columns";
import type { GridNode, NodesWritten } from "./nodes";

/** An inscription of a task: to a timeline, or to the time/time tracking of a milestone. */
export type TrackingEntry = components["schemas"]["TrackingEntry"];

/** A timeline the menu offers, by its identifier and its label. */
export interface ChoiceOption {
  readonly id: string;
  readonly label: string;
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

/** What a grid offers in the submenus of its cells, where the grid gives it. */
export interface RowChoices<Row extends GridNode> {
  readonly tracking?: TrackingChoices<Row> | undefined;
  /** What a write answered, as the grid reads it: the rows written in place of the rows read. */
  readonly written: (written: NodesWritten) => RowsApplied<Row>;
}

/** What a choice changes of the rows it acts on. */
export type RowChange =
  | { readonly kind: "timeline"; readonly id: string; readonly on: boolean }
  | { readonly kind: "milestone"; readonly on: boolean };

/** Whether a row names the inscriptions among the fields it accepts (`task.tracking`). */
export function trackable(row: GridNode): boolean {
  return (
    row.task !== undefined && row.task !== null && row.editable_fields.includes("task.tracking")
  );
}

/** Whether a row is a milestone, which alone is inscribed to the time/time tracking. */
export function milestoneOf(row: GridNode): boolean {
  return row.task?.is_milestone === true;
}

/** Whether a change applies to a row: the row names the field, a milestone for the tracking. */
export function appliesTo(change: RowChange, row: GridNode): boolean {
  return trackable(row) && (change.kind === "timeline" || milestoneOf(row));
}

/** Whether an inscription is the time/time tracking, or to the timeline of an identifier. */
function inscribed(entry: TrackingEntry, change: RowChange): boolean {
  return change.kind === "milestone"
    ? entry.kind === "milestone_tracking"
    : entry.kind === "timeline" && entry.timeline_id === change.id;
}

/**
 * The whole list of the inscriptions a task has once a change is made: the ones it has, the change
 * added when it is made and not there already, or taken away. The server replaces the list.
 */
export function entriesAfter(
  entries: readonly TrackingEntry[],
  change: RowChange,
): readonly TrackingEntry[] {
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
