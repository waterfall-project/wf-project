// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example } from "@/test/fixtures";

import { ComparisonGrid } from "./comparison-grid";
import { comparisonRows } from "./comparison-rows";
import type { RevisionComparison } from "./revision-comparison";

// The server of Next, as far as the grid needs it, as for the other tests of the grid.
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/projects/p/revisions",
  useSearchParams: () => new URLSearchParams(),
}));

// The sub-tree of « Installation sur site »: two nodes added, two removed, five modified.
const COMPARISON = example("comparison") as RevisionComparison;
const VOLUME = example("volume/comparison_volume") as RevisionComparison;

/** The grid of a comparison, in French. */
function grid(comparison: RevisionComparison) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <ComparisonGrid
        rows={comparisonRows(comparison.items)}
        totals={comparison.totals}
        preferences={undefined}
      />
    </NextIntlClientProvider>
  );
}

/** The cell of a row, by its index among the rows of the comparison, and of a column, by its key. */
function cell(row: number, column: string): HTMLElement {
  const found = screen
    .getByRole("grid")
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="${column}"]`);
  if (found === null) {
    throw new Error(`no cell ${column} in the row ${row.toString()}`);
  }
  return found;
}

/** The index of the node of a comparison that bears a label. */
function indexOfLabel(comparison: RevisionComparison, label: string): number {
  return comparison.items.findIndex((node) => (node.task ?? node.estimate_line)?.label === label);
}

beforeEach(() => {
  // Laid out as a browser would: a window of rows in view.
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the grid of the comparison of two revisions", () => {
  it("marks each node as the server marks it, in a column at the start, the unchanged one apart", () => {
    render(grid(COMPARISON));
    const header = screen.getAllByRole("columnheader");
    expect(header[0]).toHaveAccessibleName("Écart");
    expect(header.map((each) => each.getAttribute("data-column"))).toEqual([
      "diff_mark",
      "row_number",
      "label",
      "changes",
    ]);
    const marks = { added: "+Ajouté", removed: "-Retiré", modified: "MModifié" } as const;
    COMPARISON.items.forEach((node, row) => {
      expect(cell(row, "diff_mark")).toHaveTextContent(
        marks[node.difference as keyof typeof marks],
      );
    });
    // The number of each node, as the API computes it, and its label.
    expect(cell(0, "row_number")).toHaveTextContent("15");
    expect(cell(0, "label")).toHaveTextContent("Installation sur site");
  });

  it("presents as modified a task moved under another summary [WF-REV-0080-A]", () => {
    // Une tâche déplacée sous une autre récapitulative est présentée modifiée.
    // The comparison of the witness bears no task moved: « Mise en service », which the server marks
    // modified, is read as the server marks a task moved, its `changes` naming the parent.
    const moved = indexOfLabel(COMPARISON, "Mise en service");
    expect(COMPARISON.items[moved]).toMatchObject({ kind: "task", difference: "modified" });
    render(
      grid({
        ...COMPARISON,
        items: COMPARISON.items.map((node, index) =>
          index === moved ? { ...node, changes: ["parent"] } : node,
        ),
      }),
    );
    expect(cell(moved, "label")).toHaveTextContent("Mise en service");
    expect(cell(moved, "diff_mark")).toHaveTextContent("MModifié");
    expect(cell(moved, "changes")).toHaveTextContent("Rattachement");
  });

  it("names what changes of a node as the server names it, nothing for a node that keeps its own values", () => {
    render(grid(COMPARISON));
    const wired = indexOfLabel(COMPARISON, "Câblage sur site");
    expect(COMPARISON.items[wired]?.changes).toEqual(["reestimated_amount"]);
    expect(cell(wired, "changes")).toHaveTextContent("Montant réestimé");
    expect(cell(indexOfLabel(COMPARISON, "Installation sur site"), "changes")).toHaveTextContent(
      "",
    );
  });

  it("tints the rows of the nodes marked and no other", () => {
    render(grid(COMPARISON));
    const tinted = screen
      .getAllByRole("row")
      .filter((row) => /bg-diff-(added|removed|modified)/.test(row.className));
    // Every node of this window is marked.
    expect(tinted).toHaveLength(COMPARISON.items.length);
  });

  it("is read only: no header sorts, no search is offered, no cell takes an entry", () => {
    render(grid(COMPARISON));
    for (const header of screen.getAllByRole("columnheader")) {
      expect(within(header).queryByRole("button")).not.toBeInTheDocument();
    }
    expect(screen.queryByRole("searchbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Annuler|Rétablir/ })).not.toBeInTheDocument();
  });

  it("tells the totals of the revision compared as the server computes them", () => {
    render(grid(COMPARISON));
    expect(screen.getByRole("grid")).toHaveAccessibleName("Nœuds comparés");
    expect(screen.getByText("Total — 3 tâches, 4 lignes")).toBeInTheDocument();
  });

  it("is accessible", async () => {
    const { container } = render(grid(COMPARISON));
    await expectAccessible(container);
  });

  it("mounts a window of the nodes of the comparison of the whole structure, not the whole (#1201)", () => {
    // 5 999 nodes of the volume of the witness, 2 770 of them modified by their values.
    const modified = VOLUME.items.filter((node) => node.difference === "modified");
    expect(VOLUME.items).toHaveLength(5999);
    expect(modified.length).toBeGreaterThan(2770);
    render(grid(VOLUME));
    expect(screen.getByRole("grid")).toHaveAttribute("aria-rowcount", "6001");
    const mounted = screen.getAllByRole("row").length;
    expect(mounted).toBeGreaterThan(10);
    expect(mounted).toBeLessThan(120);
    expect(cell(0, "label")).toHaveTextContent(VOLUME.items[0]?.task?.label ?? "?");
  });
});
