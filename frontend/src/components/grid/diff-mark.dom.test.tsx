// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Locale } from "@/i18n/locale";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";
import { estimateReference } from "@/test/reference";

import { DiffMark, differenceTint } from "./diff-mark";
import { EstimateGrid } from "./estimate-grid";
import type { NodeList, NodeSortColumn } from "./nodes";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";

// The server of Next, as far as the grid needs it, as for the other tests of the grid.
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/projects/p/revisions/r/estimate",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined, size: undefined };
// The amendment 2 of the current revision of the witness project, as the examples name it.
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000203",
};
// The installation on site read on the amendment: a task modified and one added, a summary modified
// only by what it holds, a line unchanged, a line removed, read in its place.
const amendment = example("nodes_amendment") as NodeList;

/** The grid of the estimate over nodes, a differential or not, in a language. */
function estimate(differential: boolean, locale: Locale = "fr") {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <EstimateGrid
        nodes={amendment}
        structure={STRUCTURE}
        structureVersion={1}
        reference={estimateReference()}
        editable={false}
        tasksEditable={false}
        query={NO_QUERY}
        filters={{}}
        preferences={undefined}
        differential={differential}
      />
    </NextIntlClientProvider>
  );
}

/** The grid of the planning over nodes, a differential, entered. */
function planning(nodes: NodeList) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PlanningGrid
        nodes={nodes}
        structure={STRUCTURE}
        structureVersion={1}
        filters={{ kinds: ["task"] }}
        query={NO_QUERY}
        preferences={undefined}
        undoable
        editable
        differential
      />
    </NextIntlClientProvider>
  );
}

/** The cell of a row, by its index among the rows of the answer, and of a column, by its key. */
function cell(row: number, column: string): HTMLElement {
  const found = screen
    .getByRole("treegrid")
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="${column}"]`);
  if (found === null) {
    throw new Error(`no cell ${column} in the row ${row.toString()}`);
  }
  return found;
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the mark of a difference", () => {
  it("writes + for a node added, - for a node removed and M for a node modified, in a column at the start of the grid", async () => {
    const { container } = render(estimate(true));
    const grid = screen.getByRole("treegrid");
    const headers = within(grid).getAllByRole("columnheader");
    expect(headers[0]).toHaveAccessibleName("Écart");
    // The marks, in the order of the tree, a summary modified by what it holds included, the node
    // unchanged bearing none; the word of each is read by who does not see its character.
    expect(amendment.items.map((_, row) => cell(row, "diff_mark").textContent)).toEqual([
      "MModifié",
      "MModifié",
      "",
      "-Retiré",
      "+Ajouté",
      "+Ajouté",
      "+Ajouté",
      "MModifié",
      "MModifié",
    ]);
    await expectAccessible(container);
  });

  it("tints a row only where it writes a mark: the colour never says a difference alone", () => {
    render(estimate(true));
    const tinted = amendment.items.map((_, row) => {
      const mark = cell(row, "diff_mark");
      return [mark.closest("tr")?.className.includes("bg-diff-") === true, mark.textContent !== ""];
    });
    expect(tinted.every(([colour, character]) => colour === character)).toBe(true);
    expect(tinted.filter(([colour]) => colour)).toHaveLength(8);
  });

  it("presents as modified a task moved under another summary [WF-REV-0080-A]", () => {
    // Une tâche déplacée sous une autre récapitulative est présentée modifiée.
    render(estimate(true));
    const moved = amendment.items.findIndex(
      (each) => each.kind === "task" && each.changes?.includes("parent") === true,
    );
    expect(amendment.items[moved]?.task?.label).toBe("Mise en service");
    expect(cell(moved, "label")).toHaveTextContent("Mise en service");
    expect(cell(moved, "diff_mark")).toHaveTextContent("MModifié");
  });

  it("names a difference in the language of the interface", () => {
    render(estimate(true, "en"));
    expect(screen.getAllByRole("columnheader")[0]).toHaveAccessibleName("Change");
    expect(cell(3, "diff_mark")).toHaveTextContent("-Removed");
    expect(cell(4, "diff_mark")).toHaveTextContent("+Added");
    expect(cell(0, "diff_mark")).toHaveTextContent("MModified");
  });

  it("has no column of marks on a structure that is no differential", () => {
    render(estimate(false));
    expect(screen.queryByRole("columnheader", { name: "Écart" })).not.toBeInTheDocument();
    expect(
      screen.getByRole("treegrid").querySelector('[data-column="diff_mark"]'),
    ).not.toBeInTheDocument();
  });

  it("marks the tasks of the planning of a differential too", () => {
    const tasks: NodeList = {
      ...amendment,
      items: amendment.items.filter((each) => each.kind === "task"),
    };
    render(planning(tasks));
    expect(tasks.items.map((_, row) => cell(row, "diff_mark").textContent)).toEqual([
      "MModifié",
      "MModifié",
      "+Ajouté",
      "+Ajouté",
      "MModifié",
    ]);
  });

  it("keeps the predecessors of a task a differential removes read only, where those of the others are entered", () => {
    // The task « Reprise des essais de câblage », added by the amendment, read as if it were removed.
    const removed: NodeList = {
      ...amendment,
      items: amendment.items
        .filter((each) => each.kind === "task")
        .map((each) =>
          each.task?.label === "Reprise des essais de câblage"
            ? { ...each, difference: "removed" as const }
            : each,
        ),
    };
    render(planning(removed));
    const row = removed.items.findIndex((each) => each.difference === "removed");
    const other = removed.items.findIndex((each) => each.difference === "modified");
    expect(cell(row, "predecessors")).toHaveAttribute("aria-readonly", "true");
    expect(cell(other, "predecessors")).not.toHaveAttribute("aria-readonly");
  });
});

describe("the tint of a row", () => {
  it.each([
    ["added", "bg-diff-added"],
    ["removed", "bg-diff-removed"],
    ["modified", "bg-diff-modified"],
  ] as const)(
    "is the one of a node %s, and none for a node unchanged or with no difference",
    (difference, tint) => {
      expect(differenceTint(difference)).toContain(tint);
      expect(differenceTint("unchanged")).toBeNull();
      expect(differenceTint(null)).toBeNull();
      expect(differenceTint(undefined)).toBeNull();
    },
  );

  it("writes nothing for a node unchanged", () => {
    const { container } = render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
        <DiffMark difference="unchanged" />
      </NextIntlClientProvider>,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
