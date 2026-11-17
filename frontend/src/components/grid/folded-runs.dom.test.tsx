// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { cleanup, render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";
import { expectAccessible } from "@/test/axe";
import { estimateReference } from "@/test/reference";

import { ESTIMATE_FIELDS } from "./estimate";
import { EstimateGrid } from "./estimate-grid";
import { FOLD_STORAGE_PREFIX } from "./fold";
import { type NodeList, type NodeRows, projectNodes } from "./nodes";
import { PLANNING_FIELDS, PLANNING_KINDS, type PlanningNode } from "./planning";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";
import { REMAINING_FIELDS } from "./remaining";
import { RemainingGrid } from "./remaining-grid";

// The server of Next, as far as the grids need it: the fake back behind the actions, whose calls
// say what the grid asked — nothing, for a folding —, and the router, whose navigations say the
// address changed — never, for a folding.
const server = vi.hoisted((): { client: FakeClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }));
vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/planning",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<never> = { sort: undefined, search: undefined, size: undefined };
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};

// The planning of the witness, compared to a base: the summary « Études » carries a difference, which
// « Dossier de conception » bears; the four tasks between them bear none.
const planning = example("nodes_planning") as NodeList;
const SUMMARY = "Études";
const DESIGN = "Dossier de conception";
const REVIEW = "Revue de conception";
const UNCHANGED = ["Études de détail", "Pupitres opérateurs", REVIEW, "Réception des études"];

/** The planning compared, each task marked as `marks` says, unchanged when it does not. */
function compared(marks: Readonly<Record<string, "modified" | "added">>): NodeRows<PlanningNode> {
  const list: NodeList = {
    ...planning,
    items: planning.items.map((node) => {
      const difference = marks[node.task?.label ?? ""] ?? "unchanged";
      return {
        ...node,
        difference,
        changes: [],
        base: null,
        deltas: null,
      } as typeof node;
    }),
  };
  return projectNodes(list, PLANNING_FIELDS, PLANNING_KINDS);
}

const MARKED = { [SUMMARY]: "modified", [DESIGN]: "modified" } as const;

/** The grid of the planning of the witness, compared or not. */
function planningGrid(nodes: NodeRows<PlanningNode>, comparing = true) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PlanningGrid
        nodes={nodes}
        structure={STRUCTURE}
        structureVersion={1}
        filters={{}}
        query={NO_QUERY}
        preferences={undefined}
        editable
        comparing={comparing}
      />
    </NextIntlClientProvider>
  );
}

/** The labels of the tasks the grid renders, in their order. */
function labels(): string[] {
  return [...document.querySelectorAll<HTMLElement>('td[data-column="label"]')].map((cell) =>
    cell.textContent.trim(),
  );
}

/** The cell of the label of a task. */
function labelOf(label: string): HTMLElement {
  const cell = [...document.querySelectorAll<HTMLElement>('td[data-column="label"]')].find(
    (candidate) => candidate.textContent.trim() === label,
  );
  if (cell === undefined) {
    throw new Error(`no row of ${label}`);
  }
  return cell;
}

/** « Écarts seulement », in the bar of the grid. */
function differencesOnly(): HTMLElement {
  return screen.getByRole("button", { name: "Écarts seulement" });
}

/** The text of the totals row. */
function totals(): string {
  return document.querySelector("tfoot")?.textContent ?? "";
}

/** Every call the grid made to the fake back. */
function calls(): number {
  return server.client?.calls.length ?? 0;
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1000);
  window.sessionStorage.clear();
  server.client = fakeClient({});
  router.push.mockClear();
  router.replace.mockClear();
  router.refresh.mockClear();
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("« Écarts seulement » on a grid that reads a comparison", () => {
  it("folds the rows without difference, keeps the rows marked and their summaries, says each run folded and keeps the totals [WF-IHM-0170-A]", async () => {
    render(planningGrid(compared(MARKED)));
    const before = totals();
    expect(differencesOnly()).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(differencesOnly());
    expect(differencesOnly()).toHaveAttribute("aria-pressed", "true");
    expect(labels()).toEqual([SUMMARY, DESIGN]);
    // The run of the four tasks between them, in their place, told by its number of rows.
    const run = screen.getByRole("button", { name: "4 lignes sans écart repliées" });
    expect(run).toHaveAttribute("aria-expanded", "false");
    const rows = [...document.querySelectorAll("tbody tr[aria-rowindex]")];
    expect(rows.map((row) => row.textContent.includes("repliées"))).toEqual([false, true, false]);
    expect(totals()).toBe(before);
    // Nothing asked of the server, the address unchanged.
    expect(calls()).toBe(0);
    expect(router.push).not.toHaveBeenCalled();
    expect(router.replace).not.toHaveBeenCalled();
    expect(router.refresh).not.toHaveBeenCalled();
  });

  it("unfolds a run at the click, and keeps it unfolded while the folding is on [WF-IHM-0170-A]", async () => {
    render(planningGrid(compared(MARKED)));
    await userEvent.click(differencesOnly());
    await userEvent.click(screen.getByRole("button", { name: "4 lignes sans écart repliées" }));
    expect(labels()).toEqual([SUMMARY, ...UNCHANGED, DESIGN]);
    expect(differencesOnly()).toHaveAttribute("aria-pressed", "true");
    // The first row of the run is the active cell.
    expect(labelOf(UNCHANGED[0] ?? "")).toHaveAttribute("tabindex", "0");
  });

  it("stops the arrows on the row of a run, which Enter unfolds, the focus on its first row [WF-IHM-0170-A]", async () => {
    render(planningGrid(compared(MARKED)));
    await userEvent.click(differencesOnly());
    labelOf(SUMMARY).focus();
    await userEvent.keyboard("{ArrowDown}");
    const run = document.activeElement;
    expect(run).toHaveAttribute("data-run");
    expect(run?.textContent).toBe("4 lignes sans écart repliées");
    expect(run).toHaveAttribute("aria-keyshortcuts", "Enter Space Alt+Plus");
    // Down to the row after it, up again to it, up to the row before it.
    await userEvent.keyboard("{ArrowDown}");
    expect(document.activeElement).toBe(labelOf(DESIGN));
    await userEvent.keyboard("{ArrowUp}");
    expect(document.activeElement).toHaveAttribute("data-run");
    await userEvent.keyboard("{ArrowUp}");
    expect(document.activeElement).toBe(labelOf(SUMMARY));
    await userEvent.keyboard("{ArrowDown}{Enter}");
    expect(labels()).toEqual([SUMMARY, ...UNCHANGED, DESIGN]);
    expect(document.activeElement).toBe(labelOf(UNCHANGED[0] ?? ""));
  });

  it.each([
    ["Space", " "],
    ["Alt and plus", "{Alt>}+{/Alt}"],
  ])("unfolds the run focused by %s [WF-IHM-0170-A]", async (_, keys) => {
    render(planningGrid(compared(MARKED)));
    await userEvent.click(differencesOnly());
    labelOf(DESIGN).focus();
    await userEvent.keyboard(`{ArrowUp}${keys}`);
    expect(labels()).toEqual([SUMMARY, ...UNCHANGED, DESIGN]);
  });

  it("counts the rows of the runs among the rows of the grid, for a reader of the screen [WF-IHM-0170-A]", async () => {
    render(planningGrid(compared({ [SUMMARY]: "modified", [UNCHANGED[0] ?? ""]: "added" })));
    await userEvent.click(differencesOnly());
    // Études, Études de détail, then the run of the four after them, at the end.
    const grid = screen.getByRole("treegrid");
    expect(grid).toHaveAttribute("aria-rowcount", "5");
    const run = screen.getByRole("button", { name: "4 lignes sans écart repliées" });
    expect(run.closest("tr")).toHaveAttribute("aria-rowindex", "4");
    // The down arrow from the last row reaches the run after it; the up arrow leaves it.
    labelOf(UNCHANGED[0] ?? "").focus();
    await userEvent.keyboard("{ArrowDown}");
    expect(document.activeElement).toHaveAttribute("data-run");
    await userEvent.keyboard("{ArrowDown}");
    expect(document.activeElement).toHaveAttribute("data-run");
  });

  it("keeps a run unfolded through a reading anew, and shows a row a write made differ in a branch folded [WF-IHM-0170-A]", async () => {
    const { rerender } = render(planningGrid(compared(MARKED)));
    await userEvent.click(differencesOnly());
    // A write — a date in « Dossier de conception » — reads the grid anew: « Revue de conception »,
    // which the server now marks modified, comes into view, the run split around it.
    rerender(planningGrid(compared({ ...MARKED, [REVIEW]: "modified" })));
    expect(labels()).toEqual([SUMMARY, REVIEW, DESIGN]);
    expect(screen.getByRole("button", { name: "2 lignes sans écart repliées" })).toBeVisible();
    expect(screen.getByRole("button", { name: "1 ligne sans écart repliée" })).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "2 lignes sans écart repliées" }));
    // Read anew with the marks of before: the rows unfolded stay.
    rerender(planningGrid(compared(MARKED)));
    expect(labels()).toEqual([SUMMARY, ...UNCHANGED.slice(0, 2), DESIGN]);
    expect(screen.getByRole("button", { name: "2 lignes sans écart repliées" })).toBeVisible();
  });

  it("folds on the marks of the server alone: a summary marked unchanged over a row marked stays, a row marked unchanged with a base folds [WF-IHM-0170-A]", async () => {
    const nodes = compared({ [DESIGN]: "modified" });
    const items = nodes.items.map((node) =>
      node.task?.label === UNCHANGED[1] ? { ...node, base: { task: { label: "Pupitres" } } } : node,
    );
    render(planningGrid({ ...nodes, items }));
    await userEvent.click(differencesOnly());
    expect(labels()).toEqual([SUMMARY, DESIGN]);
  });

  it("has a grid whose runs folded meet the rules of accessibility [WF-IHM-0170-A]", async () => {
    const { container } = render(planningGrid(compared(MARKED)));
    await userEvent.click(differencesOnly());
    await expectAccessible(container);
  });

  it("is kept in the tab, by grid and by revision, and lifted folds back nothing", async () => {
    const { unmount } = render(planningGrid(compared(MARKED)));
    await userEvent.click(differencesOnly());
    const kept = window.sessionStorage.getItem(
      `${FOLD_STORAGE_PREFIX}planning:${STRUCTURE.revision_id}`,
    );
    expect(JSON.parse(kept ?? "null")).toMatchObject({ differences: { on: true, opened: [] } });
    unmount();
    render(planningGrid(compared(MARKED)));
    expect(labels()).toEqual([SUMMARY, DESIGN]);
    await userEvent.click(differencesOnly());
    expect(labels()).toEqual([SUMMARY, ...UNCHANGED, DESIGN]);
    expect(screen.queryByRole("button", { name: /repliées?$/ })).toBeNull();
  });

  it("is not offered on a grid that reads no comparison, which shows every row", () => {
    window.sessionStorage.setItem(
      `${FOLD_STORAGE_PREFIX}planning:${STRUCTURE.revision_id}`,
      '{"collapsed":[],"revealed":"","differences":{"on":true,"opened":[]}}',
    );
    render(planningGrid(compared(MARKED), false));
    expect(screen.queryByRole("button", { name: "Écarts seulement" })).toBeNull();
    expect(labels()).toEqual([SUMMARY, ...UNCHANGED, DESIGN]);
  });

  it.each([
    {
      name: "estimate",
      fields: ESTIMATE_FIELDS,
      grid: (nodes: NodeRows<never>) => (
        <EstimateGrid
          filters={{}}
          reference={estimateReference()}
          editable
          tasksEditable
          nodes={nodes}
          structure={STRUCTURE}
          structureVersion={1}
          query={NO_QUERY}
          preferences={undefined}
          comparing
        />
      ),
    },
    {
      name: "remaining to commit",
      fields: REMAINING_FIELDS,
      grid: (nodes: NodeRows<never>) => (
        <RemainingGrid
          nodes={nodes}
          structure={STRUCTURE}
          structureVersion={1}
          filters={{}}
          editable
          query={NO_QUERY}
          preferences={undefined}
          comparing
        />
      ),
    },
  ])(
    "is offered in the bar of the $name, and folds it [WF-IHM-0170-A]",
    async ({ fields, grid }) => {
      // The comparison of the current revision to the reference, its first line marked unchanged.
      const list = example("comparison_current") as NodeList;
      const items = list.items.map((node, at) =>
        at === 2 ? { ...node, difference: "unchanged" as const } : node,
      );
      const nodes = projectNodes({ ...list, items }, fields) as NodeRows<never>;
      render(
        <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
          {grid(nodes)}
        </NextIntlClientProvider>,
      );
      await userEvent.click(differencesOnly());
      expect(screen.getByRole("button", { name: "1 ligne sans écart repliée" })).toBeVisible();
      expect(labels()).not.toContain("Câblage sur site");
      expect(labels()).toContain("Assistance aux essais de câblage");
    },
  );
});
