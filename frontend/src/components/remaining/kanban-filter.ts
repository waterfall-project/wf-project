// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the Kanban of the start of the tasks keeps of its cards under the filters of its address
 * (`address.ts`): the label searched, which narrows the three columns, and the tasks ready, which
 * narrows the column of the tasks not started alone and keeps the cards whose predecessors the API
 * says are all completed (`predecessors_completed`) — the front computes nothing of it
 * (WF-ARC-0020). The label is searched as the grids search theirs: whatever the case and the
 * accents.
 *
 * Pure, and neither server nor client.
 */
import type { KanbanFilters } from "./address";
import type { KanbanCard, KanbanColumns } from "./kanban-cards";

/** A text folded for a search: small letters, without accents nor marks, « œ » and « æ » spelt out. */
export function folded(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/œ/g, "oe")
    .replace(/æ/g, "ae");
}

/**
 * The columns the filters keep, each card in its place. The tasks ready narrow the tasks not
 * started alone. A card in `unknown` — answered a gesture, its predecessors not read yet — stays
 * under that filter: it is not hidden on what nobody knows of it.
 */
export function filtered(
  columns: KanbanColumns,
  { text, ready }: KanbanFilters,
  unknown: ReadonlySet<string>,
): KanbanColumns {
  const needle = folded(text);
  const keeps = (card: KanbanCard) =>
    folded(card.label).includes(needle) &&
    (!ready ||
      card.state !== "not_started" ||
      card.predecessors_completed ||
      unknown.has(card.node_id));
  return {
    not_started: columns.not_started.filter(keeps),
    started: columns.started.filter(keeps),
    completed: columns.completed.filter(keeps),
  };
}
