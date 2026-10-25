// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cards the API answered the gestures of the Kanban with, kept apart from the render: a reading
 * of the tasks that overtakes an answer forgets it, once the reading is committed, so that a later
 * reading at an older version cannot bring it back (`unanswered`). The screen reads them as an
 * external store (`useSyncExternalStore`), and changes what it keeps in its callbacks and once a
 * reading is committed, never while it renders.
 */
import { type KanbanCard, type KanbanColumns, unanswered } from "./kanban-cards";

/** The cards answered, by node. */
export type Answered = Readonly<Record<string, KanbanCard>>;

/** The answers of the gestures of a Kanban, and who listens to them. */
export class AnsweredCards {
  private cards: Answered = {};
  private outdated = false;
  private readonly listeners = new Set<() => void>();

  /** The answers now; the same object until they change. */
  readonly snapshot = (): Answered => this.cards;

  /** Whether a reading ended without bringing an answer's version; the same until it changes. */
  readonly lapsed = (): boolean => this.outdated;

  /** Listen to the changes of the answers; give the way to stop. */
  readonly subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  /** Keep the card an answer gave for its node, in place of the one before. */
  readonly answer = (card: KanbanCard): void => {
    this.set({ ...this.cards, [card.node_id]: card });
  };

  /** Forget the answers the columns read overtake. */
  readonly read = (columns: KanbanColumns): void => {
    this.set(unanswered(columns, this.cards));
  };

  /** A reading ended with an answer unreached: the cards answered are not up to date. */
  readonly lapse = (): void => {
    this.mark(true);
  };

  /** The tasks are read anew, or a gesture is made: the cards answered are no more outdated. */
  readonly settle = (): void => {
    this.mark(false);
  };

  private mark(outdated: boolean): void {
    if (outdated === this.outdated) {
      return;
    }
    this.outdated = outdated;
    this.notify();
  }

  private notify(): void {
    for (const listener of this.listeners) {
      listener();
    }
  }

  private set(next: Answered): void {
    if (next === this.cards) {
      return;
    }
    this.cards = next;
    this.notify();
  }
}
