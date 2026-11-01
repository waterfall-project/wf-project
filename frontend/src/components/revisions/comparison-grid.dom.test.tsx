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
// The same sub-tree where « Mise en service » is moved under « Installation sur site ».
const MOVED = example("comparison_moved") as RevisionComparison;
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
  it("marks each node as the server marks it, in a column at the start [WF-REV-0080-A]", () => {
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
    // The example of the contract, as it is: the server marks « Mise en service » modified, its
    // `changes` naming the parent, and its `parent_id` the summary it moved under.
    const moved = MOVED.items.findIndex((node) => node.changes.includes("parent"));
    expect(MOVED.items[moved]).toMatchObject({
      kind: "task",
      difference: "modified",
      changes: ["parent"],
      parent_id: "01926f3a-7c00-7000-8000-000000000561",
    });
    render(grid(MOVED));
    expect(cell(moved, "label")).toHaveTextContent("Mise en service");
    expect(cell(moved, "diff_mark")).toHaveTextContent("MModifié");
    expect(cell(moved, "changes")).toHaveTextContent("Rattachement");
  });

  it("leaves the mark of an unchanged node empty and its row untinted [WF-REV-0080-A]", () => {
    render(grid(VOLUME));
    const unchanged = VOLUME.items.findIndex((node) => node.difference === "unchanged");
    expect(unchanged).toBeGreaterThanOrEqual(0);
    expect(cell(unchanged, "diff_mark")).toBeEmptyDOMElement();
    const row = cell(unchanged, "diff_mark").closest("tr");
    expect(row?.className).not.toMatch(/bg-diff-/);
  });

  it("names what changes of a node as the server names it, nothing for a node that keeps its own values [WF-REV-0080-A]", () => {
    render(grid(COMPARISON));
    const wired = indexOfLabel(COMPARISON, "Câblage sur site");
    // The line changed sub-project between the two revisions: it is modified on that ground too (E-01).
    expect(COMPARISON.items[wired]?.changes).toEqual(["reestimated_amount", "subproject"]);
    expect(cell(wired, "changes")).toHaveTextContent("Montant réestimé");
    expect(cell(wired, "changes")).toHaveTextContent("Sous-projet");
    expect(cell(indexOfLabel(COMPARISON, "Installation sur site"), "changes")).toHaveTextContent(
      "",
    );
  });

  it("wraps the changes of a node that bears all six, none cut off", () => {
    const all = [
      "dates",
      "duration",
      "progress",
      "budgeted_amount",
      "reestimated_amount",
      "parent",
    ] as const;
    render(
      grid({
        ...COMPARISON,
        items: COMPARISON.items.map((node, index) =>
          index === 0 ? { ...node, changes: [...all] } : node,
        ),
      }),
    );
    const changes = cell(0, "changes");
    expect(within(changes).getAllByText(/./)).toHaveLength(6);
    expect(changes.querySelector("span.flex")).toHaveClass("flex-wrap");
  });

  // Non-regression tests: the tint and the read only grid are those of the dense grid, which
  // WF-REV-0080-A does not verify.
  it("tints the rows of the nodes marked and no other (non-regression)", () => {
    render(grid(COMPARISON));
    const tinted = screen
      .getAllByRole("row")
      .filter((row) => /bg-diff-(added|removed|modified)/.test(row.className));
    // Every node of this window is marked.
    expect(tinted).toHaveLength(COMPARISON.items.length);
  });

  it("is read only: no header sorts, no search is offered, no cell takes an entry (non-regression)", () => {
    render(grid(COMPARISON));
    for (const header of screen.getAllByRole("columnheader")) {
      expect(within(header).queryByRole("button")).not.toBeInTheDocument();
    }
    expect(screen.queryByRole("searchbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Annuler|Rétablir/ })).not.toBeInTheDocument();
  });

  it("tells the totals of the revision compared as the server computes them (non-regression)", () => {
    render(grid(COMPARISON));
    expect(screen.getByRole("grid")).toHaveAccessibleName("Nœuds comparés");
    expect(screen.getByText("Total — 3 tâches, 4 lignes")).toBeInTheDocument();
  });

  it("is accessible [WF-IHM-0100-A]", async () => {
    const { container } = render(grid(COMPARISON));
    await expectAccessible(container);
  });

  it("mounts a window of the nodes of the comparison of the whole structure, not the whole (#1201, non-regression)", () => {
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
