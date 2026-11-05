// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { example } from "@/test/fixtures";

import { kanbanFilterHref, readKanbanFilters } from "./address";
import { columnsOf, type StartableTasks } from "./kanban-cards";
import { filtered, folded } from "./kanban-filter";

const COLUMNS = columnsOf(example("startable_tasks_milestone") as StartableTasks);
const NO_ONE = new Set<string>();

describe("the filters of the Kanban in the address", () => {
  it("reads the label and the tasks ready, `1` alone asking them", () => {
    expect(readKanbanFilters(new URLSearchParams("q=%20Mise%20&ready=1"))).toEqual({
      text: "Mise",
      ready: true,
    });
    expect(readKanbanFilters(new URLSearchParams("ready=true"))).toEqual({
      text: "",
      ready: false,
    });
    expect(readKanbanFilters(new URLSearchParams())).toEqual({ text: "", ready: false });
  });

  it("writes one filter and keeps the rest of the query, lifting an empty one", () => {
    const query = new URLSearchParams("subproject_id=s&ready=1");
    expect(kanbanFilterHref("/k", query, { text: "mise" })).toBe(
      "/k?subproject_id=s&ready=1&q=mise",
    );
    expect(kanbanFilterHref("/k", query, { ready: false })).toBe("/k?subproject_id=s");
    expect(kanbanFilterHref("/k", new URLSearchParams("q=a"), { text: "" })).toBe("/k");
  });
});

describe("what the Kanban keeps under its filters", () => {
  it("folds the case, the accents, and the ligatures", () => {
    expect(folded("Œuvre ÉTUDES Æ")).toBe("oeuvre etudes ae");
  });

  it("filters the label in every column and the tasks ready in the column not started alone", () => {
    const ready = filtered(COLUMNS, { text: "", ready: true }, NO_ONE);
    expect(ready.not_started.map((card) => card.label)).toEqual(["Réception usine"]);
    expect(ready.started).toEqual(COLUMNS.started);
    expect(ready.completed).toEqual(COLUMNS.completed);
    expect(filtered(COLUMNS, { text: "etudes", ready: false }, NO_ONE).completed).toHaveLength(2);
  });

  it("does not hide on the filter of the tasks ready a card whose predecessors are not read yet", () => {
    const [first] = COLUMNS.not_started.filter((card) => !card.predecessors_completed);
    if (first === undefined) {
      throw new Error("no task not started in the example");
    }
    const kept = filtered(COLUMNS, { text: "", ready: true }, new Set([first.node_id]));
    expect(kept.not_started.map((card) => card.node_id)).toContain(first.node_id);
  });
});
