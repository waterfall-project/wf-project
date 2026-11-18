// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { cleanup, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import type { ApiClient } from "@/api/client";
import { example, fakeClient } from "@/test/fixtures";
import { expectAccessible } from "@/test/axe";
import { estimateReference } from "@/test/reference";

import { ESTIMATE_FIELDS } from "./estimate";
import { EstimateGrid } from "./estimate-grid";
import { type NodeList, type NodeRows, type NodesWritten, projectNodes } from "./nodes";
import { PLANNING_FIELDS, PLANNING_KINDS, type PlanningNode } from "./planning";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";
import { REMAINING_FIELDS } from "./remaining";
import { RemainingGrid } from "./remaining-grid";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/estimate",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<never> = { sort: undefined, search: undefined, size: undefined };
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};

// The current revision of the witness compared to the reference it comes from.
type Comparison = NodeList &
  Pick<
    components["schemas"]["RevisionComparison"],
    "base_totals" | "totals_delta" | "amount_deltas"
  >;
const comparison = example("comparison_current") as Comparison;

/**
 * The same comparison, its re-estimated amount read, in the base, and their gap as given: the
 * contract has no example of totals that weigh 1 000 against 1 200, only `comparison_current`.
 */
function weighing(read: string, base: string, gap: string, counts = { read: 3, base: 3, gap: 0 }) {
  return {
    ...comparison,
    totals: { ...comparison.totals, reestimated_amount: read, estimate_line_count: counts.read },
    base_totals: {
      ...comparison.base_totals,
      reestimated_amount: base,
      estimate_line_count: counts.base,
    },
    totals_delta: {
      ...comparison.totals_delta,
      reestimated_amount: gap,
      estimate_line_count: counts.gap,
    },
  };
}

// A frame that lays out: the rows of the answer are in the window of the rows in view.
beforeEach(() => {
  router.refresh.mockReset();
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1000);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

/** The grid of the estimate on a comparison. */
function estimateOf(answer: Comparison) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <EstimateGrid
        filters={{}}
        reference={estimateReference()}
        editable
        tasksEditable
        nodes={projectNodes(answer, ESTIMATE_FIELDS)}
        structure={STRUCTURE}
        structureVersion={1}
        query={NO_QUERY}
        preferences={undefined}
        comparing
      />
    </NextIntlClientProvider>
  );
}

/** The totals row of the grid on the screen. */
function totalsRow(): HTMLElement {
  const row = document.querySelector<HTMLElement>("tfoot tr");
  if (row === null) {
    throw new Error("no totals row");
  }
  return row;
}

describe("the totals row of a comparison (US-2350)", () => {
  it("says the total of the revision read, that of the base and their difference, and is marked modified [WF-IHM-0160-A]", () => {
    render(estimateOf(weighing("1200.00", "1000.00", "200.00")));
    const row = totalsRow();
    expect(row).toHaveAttribute("data-difference", "modified");
    expect(within(row).getByText(/^1\D200,00/)).toBeInTheDocument();
    expect(within(row).getByText(/1\D000,00/)).toBeInTheDocument();
    expect(within(row).getByText(/\+200,00/)).toBeInTheDocument();
    // The base and the difference are named for a reader of the screen, and the mark says the word.
    expect(within(row).getAllByText("Base :").length).toBeGreaterThan(0);
    expect(within(row).getAllByText("Écart :").length).toBeGreaterThan(0);
    expect(within(row).getByText("Modifié")).toBeInTheDocument();
  });

  it("counts a line removed since the base in the total of the base and in the difference, not in the total read [WF-IHM-0160-A]", () => {
    // 100 of a line removed: the base weighs 1 000, the revision read 900, the difference is -100.
    render(estimateOf(weighing("900.00", "1000.00", "-100.00", { read: 3, base: 4, gap: -1 })));
    const row = totalsRow();
    expect(within(row).getByText(/^900,00/)).toBeInTheDocument();
    expect(within(row).getByText(/1\D000,00/)).toBeInTheDocument();
    expect(within(row).getByText(/^-100,00|^−100,00/)).toBeInTheDocument();
    expect(within(row).getByText(/Base : Total — 3 tâches, 4 lignes/)).toBeInTheDocument();
    expect(within(row).getByText(/^Total — 3 tâches, 3 lignes/)).toBeInTheDocument();
    expect(row).toHaveAttribute("data-difference", "modified");
  });

  it("does not mark the row when the totals are equal [WF-IHM-0160-A]", () => {
    // The contract has no example of equal totals: those of `comparison_current`, its base made of
    // them and every total of the difference zero, as for an identical pair.
    const identical: Comparison = {
      ...comparison,
      base_totals: comparison.totals,
      totals_delta: {
        task_count: 0,
        estimate_line_count: 0,
        hours: "0",
        base_amount: "0.00",
        budgeted_amount: "0.00",
        reestimated_amount: "0.00",
      },
    };
    render(estimateOf(identical));
    const row = totalsRow();
    expect(row).not.toHaveAttribute("data-difference");
    expect(within(row).queryByText("Modifié")).toBeNull();
    // It still says the three, the base as the answer gave it.
    expect(within(row).getAllByText("Base :").length).toBeGreaterThan(0);
  });

  it("does the same on the grid of the planning, whose total is what it counts, and of the remaining to commit [WF-IHM-0160-A]", () => {
    const planned = example("nodes_planning") as NodeList;
    const nodes = projectNodes(
      {
        ...planned,
        base_totals: { ...planned.totals, task_count: planned.totals.task_count - 1 },
        totals_delta: { ...comparison.totals_delta, task_count: 1 },
        amount_deltas: [],
      },
      PLANNING_FIELDS,
      PLANNING_KINDS,
    ) as NodeRows<PlanningNode>;
    const { unmount } = render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <PlanningGrid
          nodes={nodes}
          structure={STRUCTURE}
          structureVersion={1}
          filters={{}}
          query={NO_QUERY}
          preferences={undefined}
          editable={false}
          comparing
        />
      </NextIntlClientProvider>,
    );
    const row = totalsRow();
    expect(row).toHaveAttribute("data-difference", "modified");
    expect(within(row).getByText(/^Base : Total — /)).toBeInTheDocument();
    expect(within(row).getByText(/^Écart : Total — /)).toBeInTheDocument();
    unmount();
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <RemainingGrid
          nodes={projectNodes(weighing("1200.00", "1000.00", "200.00"), REMAINING_FIELDS)}
          structure={STRUCTURE}
          structureVersion={1}
          filters={{}}
          editable={false}
          query={NO_QUERY}
          preferences={undefined}
          comparing
        />
      </NextIntlClientProvider>,
    );
    expect(totalsRow()).toHaveAttribute("data-difference", "modified");
    expect(within(totalsRow()).getAllByText("Base :").length).toBeGreaterThan(0);
  });

  it("says the figures of the answer alone out of a comparison", () => {
    const plain = example("nodes_estimate") as NodeList;
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <EstimateGrid
          filters={{}}
          reference={estimateReference()}
          editable
          tasksEditable
          nodes={projectNodes(plain, ESTIMATE_FIELDS)}
          structure={STRUCTURE}
          structureVersion={1}
          query={NO_QUERY}
          preferences={undefined}
        />
      </NextIntlClientProvider>,
    );
    const row = totalsRow();
    expect(row).not.toHaveAttribute("data-difference");
    expect(within(row).queryByText("Base :")).toBeNull();
    expect(screen.queryByRole("button", { name: "Écarts de montants" })).toBeNull();
  });

  it.each([
    ["the difference and the amounts", { totals_delta: undefined, amount_deltas: undefined }],
    ["the difference", { totals_delta: undefined }],
    ["the amounts", { amount_deltas: undefined }],
    ["the base and the amounts", { base_totals: undefined, amount_deltas: undefined }],
    ["the base and the difference", { base_totals: undefined, totals_delta: undefined }],
    ["the base", { base_totals: undefined }],
  ])("fails on a comparison that leaves out %s", (_name, left) => {
    const half = { ...comparison, ...left } as unknown as NodeList;
    expect(() => projectNodes(half, ESTIMATE_FIELDS)).toThrow(RangeError);
  });
});

describe("the totals row of a comparison, once a write answered (US-2350)", () => {
  const LINE =
    "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/estimate-line";
  const redated = example("estimate_line_redated") as NodesWritten;

  /** Write the line of the wiring, and wait for the page to be asked anew. */
  async function write() {
    server.client = fakeClient({ [LINE]: "estimate_line_redated" });
    const view = render(estimateOf(comparison));
    const wiring = comparison.items.findIndex(
      (node) => (node.task?.label ?? node.estimate_line?.label) === "Câblage sur site",
    );
    const cell = document.querySelector<HTMLElement>(
      `td[data-row="${wiring.toString()}"][data-column="hours"]`,
    );
    if (cell === null) {
      throw new Error("no cell to write");
    }
    cell.focus();
    await userEvent.keyboard("121{Enter}");
    await vi.waitFor(() => {
      expect(router.refresh).toHaveBeenCalledTimes(1);
    });
    return view;
  }

  it.each([
    ["other totals", () => weighing("1300.00", "1000.00", "300.00")],
    ["the totals the write left", () => structuredClone(comparison)],
  ])(
    "says the total of the answer alone, then the three again once the page is read anew with %s [WF-IHM-0160-A]",
    async (_name, again) => {
      const { rerender } = await write();
      // The answer of the write gave the totals: the base and the difference read before are not
      // the totals shown.
      expect(redated.totals).toBeDefined();
      expect(within(totalsRow()).queryByText("Base :")).toBeNull();
      expect(totalsRow()).not.toHaveAttribute("data-difference");
      rerender(estimateOf(again()));
      const row = totalsRow();
      expect(within(row).getAllByText("Base :").length).toBeGreaterThan(0);
      expect(within(row).getAllByText("Écart :").length).toBeGreaterThan(0);
      // The mark follows the difference read.
      expect(row).toHaveAttribute("data-difference", "modified");
    },
  );

  it("marks no more the row of a page read anew whose totals are equal [WF-IHM-0160-A]", async () => {
    const { rerender } = await write();
    const equal: Comparison = {
      ...comparison,
      base_totals: comparison.totals,
      totals_delta: {
        task_count: 0,
        estimate_line_count: 0,
        hours: "0",
        base_amount: "0.00",
        budgeted_amount: "0.00",
        reestimated_amount: "0.00",
      },
    };
    rerender(estimateOf(equal));
    expect(within(totalsRow()).getAllByText("Base :").length).toBeGreaterThan(0);
    expect(totalsRow()).not.toHaveAttribute("data-difference");
  });
});

describe("the differences of amounts of a comparison (US-2350)", () => {
  /** The grids that offer them, by their names. */
  const grids = [
    ["estimate", () => estimateOf(comparison)],
    [
      "remaining to commit",
      () => (
        <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
          <RemainingGrid
            nodes={projectNodes(comparison, REMAINING_FIELDS)}
            structure={STRUCTURE}
            structureVersion={1}
            filters={{}}
            editable={false}
            query={NO_QUERY}
            preferences={undefined}
            comparing
          />
        </NextIntlClientProvider>
      ),
    ],
  ] as const;

  it.each(grids)(
    "opens from the command of the %s grid with the pointer, and says each deviation by its name [WF-IHM-0160-A]",
    async (_name, grid) => {
      render(grid());
      const command = screen.getByRole("button", { name: "Écarts de montants" });
      expect(command).toHaveAttribute("aria-haspopup", "dialog");
      await userEvent.click(command);
      const dialog = screen.getByRole("dialog", { name: "Écarts de montants à la base" });
      const table = within(dialog).getByRole("table", { name: "Écarts de montants à la base" });
      // By cost type and by sub-project, the key `unassigned` named by the front.
      expect(within(table).getByText("Provision")).toBeInTheDocument();
      expect(within(table).getByText("Hors sous-projet")).toBeInTheDocument();
      expect(within(table).getAllByText(/600\D000,00/).length).toBeGreaterThan(0);
      await expectAccessible(dialog);
    },
  );

  it.each(grids)(
    "opens from the command of the %s grid with the keyboard, and gives the focus back on Escape [WF-IHM-0160-A]",
    async (_name, grid) => {
      render(grid());
      const command = screen.getByRole("button", { name: "Écarts de montants" });
      command.focus();
      await userEvent.keyboard("{Enter}");
      expect(screen.getByRole("dialog")).toBeInTheDocument();
      await userEvent.keyboard("{Escape}");
      expect(screen.queryByRole("dialog")).toBeNull();
      expect(command).toHaveFocus();
    },
  );

  it("writes the sign in front of a positive deviation, as the columns of difference do [WF-IHM-0160-A]", async () => {
    // The deviations of the contract example are all negative: one is made positive.
    const grown: Comparison = {
      ...comparison,
      amount_deltas: comparison.amount_deltas.map((delta, at) =>
        at === 0 ? { ...delta, budgeted_delta: "250.00", reestimated_delta: "-10.00" } : delta,
      ),
    };
    render(estimateOf(grown));
    await userEvent.click(screen.getByRole("button", { name: "Écarts de montants" }));
    const table = screen.getByRole("table", { name: "Écarts de montants à la base" });
    expect(within(table).getByText(/^\+250,00/)).toBeInTheDocument();
    expect(within(table).getByText(/^-10,00/)).toBeInTheDocument();
  });

  it("is not offered by the planning, which has no amount to compare [WF-IHM-0160-A]", () => {
    const planned = example("nodes_planning") as NodeList;
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <PlanningGrid
          nodes={
            projectNodes(
              {
                ...planned,
                base_totals: planned.totals,
                totals_delta: comparison.totals_delta,
                amount_deltas: [],
              },
              PLANNING_FIELDS,
              PLANNING_KINDS,
            ) as NodeRows<PlanningNode>
          }
          structure={STRUCTURE}
          structureVersion={1}
          filters={{}}
          query={NO_QUERY}
          preferences={undefined}
          editable={false}
          comparing
        />
      </NextIntlClientProvider>,
    );
    expect(screen.queryByRole("button", { name: "Écarts de montants" })).toBeNull();
  });
});
