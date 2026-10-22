// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import {
  columnsOf,
  focusOf,
  type KanbanCard,
  type KanbanColumns,
  remainingHref,
  replaced,
  type StartableTasks,
} from "./kanban-cards";

const COLUMNS: KanbanColumns = columnsOf(example("startable_tasks") as StartableTasks);

/** The card of a task, by its label. */
function named(label: string): KanbanCard {
  const found = Object.values(COLUMNS)
    .flat()
    .find((card) => card.label === label);
  if (found === undefined) {
    throw new Error(`no card for ${label}`);
  }
  return found;
}

describe("the cards of the Kanban", () => {
  it("lists the gestures of a card as the API gives them, with the state each sends", () => {
    expect(
      named("Montage des armoires sur site").commands.map((c) => [c.command, c.progress]),
    ).toEqual([
      ["start", "started"],
      ["complete", "completed"],
      ["enter_remaining", null],
    ]);
    expect(named("Études de détail").state).toBe("completed");
  });

  it("puts the card answered in the column of its state, in the order of the plan, unless the columns read hold it as recent", () => {
    const milestone = named("Réception usine");
    const answered = { ...milestone, state: "completed" as const, lock_version: 3, commands: [] };
    const shown = replaced(COLUMNS, { [milestone.node_id]: answered });
    expect(shown.not_started.map((card) => card.node_id)).not.toContain(milestone.node_id);
    expect(shown.completed.map((card) => card.row_number)).toEqual(
      [...COLUMNS.completed.map((card) => card.row_number), milestone.row_number].sort(
        (a, b) => a - b,
      ),
    );
    // Read again at the version answered: the columns read win, with their gestures.
    const read = { ...COLUMNS, completed: [...COLUMNS.completed, answered] };
    expect(replaced(read, { [milestone.node_id]: answered })).toBe(read);
    expect(replaced(COLUMNS, {})).toBe(COLUMNS);
  });

  it("leads to the grid of the remaining to commit on a task, the tasks not started shown for one", () => {
    expect(remainingHref("/r", named("Montage des armoires sur site"))).toBe(
      "/r?search=Montage+des+armoires+sur+site&progress=not_started%2Cstarted",
    );
    expect(remainingHref("/r", named("Câblage des armoires"))).toBe(
      "/r?search=C%C3%A2blage+des+armoires",
    );
  });

  describe("the card the arrows lead to [WF-IHM-0100-A]", () => {
    const base = named("Réception usine");
    const cards = (...ids: string[]): KanbanCard[] => ids.map((id) => ({ ...base, node_id: id }));
    const ids = (a: string[], b: string[], c: string[]): KanbanColumns => ({
      not_started: cards(...a),
      started: cards(...b),
      completed: cards(...c),
    });

    it("goes up and down within the column, and stops at its ends", () => {
      const columns = ids(["a1", "a2", "a3"], ["b1"], ["c1"]);
      expect(focusOf(columns, "a1", "ArrowDown")).toBe("a2");
      expect(focusOf(columns, "a3", "ArrowUp")).toBe("a2");
      expect(focusOf(columns, "a1", "ArrowUp")).toBeUndefined();
      expect(focusOf(columns, "a3", "ArrowDown")).toBeUndefined();
    });

    it("goes to the first and to the last card of the column with Home and End", () => {
      const columns = ids(["a1", "a2", "a3"], ["b1"], ["c1"]);
      expect(focusOf(columns, "a2", "Home")).toBe("a1");
      expect(focusOf(columns, "a2", "End")).toBe("a3");
      expect(focusOf(columns, "a1", "Home")).toBe("a1");
      expect(focusOf(columns, "a3", "End")).toBe("a3");
    });

    it("keeps the place across columns, and skips an empty column", () => {
      const columns = ids(["a1", "a2", "a3"], [], ["c1", "c2", "c3"]);
      expect(focusOf(columns, "a2", "ArrowRight")).toBe("c2");
      expect(focusOf(columns, "c3", "ArrowLeft")).toBe("a3");
    });

    it("leads to the last card of a column shorter than the place", () => {
      const columns = ids(["a1", "a2", "a3"], ["b1", "b2"], ["c1"]);
      expect(focusOf(columns, "a3", "ArrowRight")).toBe("b2");
      expect(focusOf(columns, "b2", "ArrowRight")).toBe("c1");
      expect(focusOf(columns, "b2", "ArrowLeft")).toBe("a2");
    });

    it("leads nowhere past the outer columns, for another key, or for an unknown card", () => {
      const columns = ids(["a1"], ["b1"], ["c1"]);
      expect(focusOf(columns, "a1", "ArrowLeft")).toBeUndefined();
      expect(focusOf(columns, "c1", "ArrowRight")).toBeUndefined();
      expect(focusOf(ids(["a1"], [], []), "a1", "ArrowRight")).toBeUndefined();
      expect(focusOf(columns, "a1", "PageDown")).toBeUndefined();
      expect(focusOf(columns, "unknown", "ArrowDown")).toBeUndefined();
    });
  });
});
