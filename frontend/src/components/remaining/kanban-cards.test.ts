// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import {
  columnsOf,
  gestureToward,
  type KanbanCard,
  type KanbanColumns,
  moveOf,
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

  it("finds the gesture that leads a card to a state among those it lists, never by its nature", () => {
    expect(gestureToward(named("Réception usine"), "completed")?.command).toBe("complete");
    // A milestone completed reopens to not started, any other task to started.
    expect(gestureToward(named("Réception des études"), "not_started")?.command).toBe("reopen");
    expect(gestureToward(named("Études de détail"), "started")?.command).toBe("reopen");
    // None leads a task started, or a task completed that is no milestone, to not started.
    expect(gestureToward(named("Câblage des armoires"), "not_started")).toBeUndefined();
    expect(gestureToward(named("Études de détail"), "not_started")).toBeUndefined();
    // The gesture that lacks conditions is found all the same, so that the card can say why.
    expect(gestureToward(named("Montage des armoires sur site"), "completed")?.is_available).toBe(
      false,
    );
  });

  it("moves the focus by the arrows from card to card, and from column to column at the same place", () => {
    const first = COLUMNS.not_started[0]?.node_id ?? "";
    const second = COLUMNS.not_started[1]?.node_id ?? "";
    expect(moveOf(COLUMNS, first, "ArrowDown", false)).toEqual({ kind: "focus", id: second });
    expect(moveOf(COLUMNS, first, "ArrowUp", false)).toBeUndefined();
    expect(moveOf(COLUMNS, second, "ArrowRight", false)).toEqual({
      kind: "focus",
      id: COLUMNS.started[1]?.node_id,
    });
    expect(moveOf(COLUMNS, first, "ArrowLeft", false)).toBeUndefined();
    expect(moveOf(COLUMNS, first, "End", false)).toEqual({
      kind: "focus",
      id: COLUMNS.not_started.at(-1)?.node_id,
    });
    expect(moveOf(COLUMNS, first, "x", false)).toBeUndefined();
  });

  it("skips an empty column, and lands on the last card of a shorter one", () => {
    const shorter = { ...COLUMNS, started: [], completed: COLUMNS.completed.slice(0, 2) };
    const third = COLUMNS.not_started[2]?.node_id ?? "";
    expect(moveOf(shorter, third, "ArrowRight", false)).toEqual({
      kind: "focus",
      id: shorter.completed[1]?.node_id,
    });
  });

  it("carries a card to the neighbouring column by Shift and a sideways arrow, none past the ends", () => {
    const first = COLUMNS.not_started[0]?.node_id ?? "";
    expect(moveOf(COLUMNS, first, "ArrowRight", true)).toEqual({ kind: "carry", state: "started" });
    expect(moveOf(COLUMNS, first, "ArrowLeft", true)).toBeUndefined();
    expect(moveOf(COLUMNS, first, "ArrowDown", true)).toBeUndefined();
    expect(moveOf(COLUMNS, "unknown", "ArrowDown", false)).toBeUndefined();
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
});
