// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import {
  act,
  cleanup,
  createEvent,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";
import { expectAccessible } from "@/test/axe";
import * as pasted from "@/test/paste-grid";
import { estimateReference } from "@/test/reference";

import { ESTIMATE_FIELDS, type EstimateNode } from "./estimate";
import { EstimateGrid } from "./estimate-grid";
import { FOLD_STORAGE_PREFIX } from "./fold";
import { type NodeList, type NodeRows, type NodesWritten, projectNodes } from "./nodes";
import type { FoldReach } from "./fold";
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
// A change undone reads the page anew from the server action (`history.ts`).
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
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
const UNDO = "POST /projects/{project_id}/revisions/{revision_id}/undo";
const TASK =
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/task";
const UNCHANGED = ["Études de détail", "Pupitres opérateurs", REVIEW, "Réception des études"];

/** The planning compared, each task marked as `marks` says, unchanged when it does not. */
function compared(
  marks: Readonly<Record<string, "modified" | "added">>,
  from: NodeList = planning,
): NodeRows<PlanningNode> {
  const list: NodeList = {
    ...from,
    items: from.items.map((node) => {
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
function planningGrid(nodes: NodeRows<PlanningNode>, comparing = true, undoable = false) {
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
        undoable={undoable}
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

  it("draws in the row of a run the stretch of the link that crosses it, so that a vertical link is not cut [WF-PLA-0090-A]", async () => {
    // « Dossier de conception » follows « Études », the four tasks between them folded away.
    const [studies] = planning.items;
    const linked: NodeList = {
      ...planning,
      items: planning.items.map((node) =>
        node.task?.label === DESIGN
          ? {
              ...node,
              predecessors: [
                {
                  predecessor_node_id: studies?.node_id ?? "",
                  predecessor_row_number: studies?.row_number ?? 0,
                  link_type: "finish_to_start" as const,
                  lag: { value: "0", unit: "d" as const },
                },
              ],
            }
          : node,
      ),
    };
    render(planningGrid(compared(MARKED, linked)));
    await userEvent.click(differencesOnly());
    const run = screen.getByRole("button", { name: "4 lignes sans écart repliées" }).closest("tr");
    const gantt = run?.querySelector<HTMLElement>('td[data-column="gantt"]');
    // The link leaves the row of « Études », reaches the row of « Dossier de conception », and runs
    // the whole height of the row of the run between them: not cut there.
    const stretch = gantt?.querySelectorAll("g[data-link] line");
    expect(stretch).toHaveLength(1);
    expect(stretch?.[0]).toHaveAttribute("y1", "0");
    expect(stretch?.[0]).toHaveAttribute("y2", "100%");
    // The cell of the run still spans the columns before the Gantt, and says what it folds.
    expect(run?.querySelector("td[data-run]")).toHaveAttribute("colspan");
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
    expect(run).toHaveAttribute("aria-keyshortcuts", "Enter Space Alt+Plus Alt+*");
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

  it("is not offered on a grid that reads no comparison, which shows every row [WF-IHM-0170-A]", () => {
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

describe("the row of a run, its keys and its places", () => {
  /** Focus the run of the grid folded in the middle, from the row before it. */
  async function focusRun() {
    render(planningGrid(compared(MARKED)));
    await userEvent.click(differencesOnly());
    labelOf(SUMMARY).focus();
    await userEvent.keyboard("{ArrowDown}");
    expect(document.activeElement).toHaveAttribute("data-run");
  }

  /** The row index of the cell that holds the focus. */
  function focusedRow(): string | undefined {
    return (document.activeElement as HTMLElement | null)?.dataset.row;
  }

  it("keeps a row written shown while the folding is on, read back unchanged, the focus and the active cell on it [WF-IHM-0170-A]", async () => {
    const wiring = "Câblage des armoires";
    const renamed = "Câblage et repérage des armoires";
    const nested = example("nodes_nested") as NodeList;
    server.client = fakeClient({ [TASK]: "task_renamed" });
    const { rerender } = render(planningGrid(compared({ [wiring]: "modified" }, nested)));
    await userEvent.click(differencesOnly());
    expect(labels()).toContain(wiring);
    labelOf(wiring).focus();
    await userEvent.keyboard(`${renamed}{Enter}`);
    expect(await screen.findByText(renamed)).toBeInTheDocument();
    // Read anew, the row renamed — the version after the write — now marked unchanged.
    rerender(
      planningGrid({
        ...compared({}, nested),
        items: compared({}, nested).items.map((node) =>
          node.task?.label === wiring
            ? { ...node, lock_version: 3, task: { ...node.task, label: renamed } }
            : node,
        ),
      }),
    );
    expect(labels()).toEqual([renamed]);
    expect(labelOf(renamed)).toHaveAttribute("tabindex", "0");
    expect(labelOf(renamed)).toHaveFocus();
  });

  it("keeps nothing of a row written on a grid that reads no comparison, the folding stored on left as it was [WF-IHM-0170-A]", async () => {
    const wiring = "Câblage des armoires";
    const nested = example("nodes_nested") as NodeList;
    const key = `${FOLD_STORAGE_PREFIX}planning:${STRUCTURE.revision_id}`;
    const stored = '{"collapsed":[],"revealed":"","differences":{"on":true,"opened":[]}}';
    window.sessionStorage.setItem(key, stored);
    server.client = fakeClient({ [TASK]: "task_renamed" });
    render(planningGrid(projectNodes(nested, PLANNING_FIELDS, PLANNING_KINDS), false));
    labelOf(wiring).focus();
    await userEvent.keyboard("Câblage et repérage des armoires{Enter}");
    await vi.waitFor(() => {
      expect(server.client?.calls.some((call) => call.route === TASK)).toBe(true);
    });
    expect(window.sessionStorage.getItem(key)).toBe(stored);
  });

  /** The planning of the witness read anew, the design file marked as `mark` says, renamed or not. */
  function readAnew(mark: "modified" | "unchanged", label = DESIGN) {
    const read = compared(mark === "modified" ? MARKED : { [SUMMARY]: "modified" });
    return {
      ...read,
      items: read.items.map((node) =>
        node.task?.label === DESIGN
          ? { ...node, lock_version: 3, task: { ...node.task, label } }
          : node,
      ),
    };
  }

  it("keeps the row of the active cell shown when an undo, read anew, marks it unchanged: a row written before the folding stays under the cursor [WF-IHM-0170-A]", async () => {
    server.client = fakeClient({ [UNDO]: "undo_task_renamed" });
    const { rerender } = render(planningGrid(compared(MARKED), true, true));
    await userEvent.click(differencesOnly());
    expect(labels()).toContain(DESIGN);
    labelOf(DESIGN).focus();
    await userEvent.keyboard("{Control>}z{/Control}");
    await vi.waitFor(() => {
      expect(server.client?.calls.some((call) => call.route === UNDO)).toBe(true);
    });
    // Read anew, the design file back to the state the base holds: marked unchanged.
    rerender(planningGrid(readAnew("unchanged"), true, true));
    expect(labels()).toContain(DESIGN);
    expect(labelOf(DESIGN)).toHaveAttribute("tabindex", "0");
    expect(labelOf(DESIGN)).toHaveFocus();
  });

  it("keeps the rows of a block pasted shown while the folding is on, read back unchanged [WF-IHM-0170-A]", async () => {
    // The twelve rows of the estimate the examples paste on, their three lines marked.
    const shown = (marked: boolean, from: NodeList = pasted.nodes) =>
      projectNodes(
        {
          ...from,
          items: from.items.map((node, at) => ({
            ...node,
            difference:
              marked && at >= pasted.FIRST && at < pasted.FIRST + 3
                ? ("modified" as const)
                : ("unchanged" as const),
            changes: [],
            base: null,
            deltas: null,
          })),
        },
        ESTIMATE_FIELDS,
      );
    const grid = (nodes: NodeRows<EstimateNode>) => (
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <EstimateGrid
          filters={{}}
          reference={estimateReference()}
          editable
          tasksEditable
          nodes={nodes}
          structure={pasted.STRUCTURE}
          structureVersion={pasted.STRUCTURE_VERSION}
          query={NO_QUERY}
          preferences={undefined}
          comparing
        />
      </NextIntlClientProvider>
    );
    server.client = fakeClient({
      [pasted.PREVIEW]: "paste_plan",
      [pasted.APPLY]: "paste_applied",
    });
    const { rerender } = render(grid(shown(true)));
    await userEvent.click(differencesOnly());
    // The three lines marked, under their summaries; every other row folded.
    const summaries = labels().slice(0, -3);
    expect(labels()).toEqual([...summaries, ...pasted.READ]);
    labelOf(pasted.READ[0] ?? "").focus();
    await userEvent.paste(pasted.copied(pasted.BLOCK));
    const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Appliquer le collage" }));
    const written = pasted.BLOCK.map(([label]) => label ?? "");
    await vi.waitFor(() => {
      expect(labels()).toEqual([...summaries, ...written]);
    });
    // Read anew, the rows written as the example answered them, every row marked unchanged.
    const applied = example("paste_applied") as NodesWritten;
    const reading: NodeList = {
      ...pasted.nodes,
      items: pasted.nodes.items.map(
        (node) => applied.nodes.find((one) => one.node_id === node.node_id) ?? node,
      ),
    };
    rerender(grid(shown(false, reading)));
    // The comparison read anew once the paste answered takes the place of what it answered
    // (US-2340): the summaries above, unchanged, fold away, as above a row renamed; the rows
    // written stay in view.
    expect(labels()).toEqual(written);
  });

  it.each<[FoldReach, string]>([
    ["all", "Enter Space Alt+Plus Alt+*"],
    ["row", "Enter Space Alt+Plus"],
    ["none", "Enter Space"],
  ])("names the keys that unfold as far as they reach: %s [WF-IHM-0170-A]", async (reach, keys) => {
    const mac = reach !== "all";
    if (mac) {
      Object.defineProperty(navigator, "userAgent", {
        value:
          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
        configurable: true,
      });
    }
    if (reach === "row") {
      Object.defineProperty(navigator, "keyboard", {
        value: { getLayoutMap: () => Promise.resolve(new Map()) },
        configurable: true,
      });
    }
    try {
      await focusRun();
      expect(document.activeElement).toHaveAttribute("aria-keyshortcuts", keys);
    } finally {
      Reflect.deleteProperty(navigator, "userAgent");
      Reflect.deleteProperty(navigator, "keyboard");
    }
  });

  it.each([
    ["Home", "{Home}", "0"],
    ["End", "{End}", "0"],
    ["Page Up", "{PageUp}", "0"],
    ["Page Down", "{PageDown}", "1"],
    ["Ctrl and Home", "{Control>}{Home}{/Control}", "0"],
    ["Ctrl and End", "{Control>}{End}{/Control}", "1"],
  ])(
    "leaves %s to the grid, from the row next to the run [WF-IHM-0170-A]",
    async (_, keys, row) => {
      await focusRun();
      await userEvent.keyboard(keys);
      expect(document.activeElement).not.toHaveAttribute("data-run");
      expect(focusedRow()).toBe(row);
    },
  );

  it("takes the down arrow of the last run without scrolling the page [WF-IHM-0170-A]", async () => {
    render(planningGrid(compared({ [SUMMARY]: "modified", [UNCHANGED[0] ?? ""]: "added" })));
    await userEvent.click(differencesOnly());
    labelOf(UNCHANGED[0] ?? "").focus();
    await userEvent.keyboard("{ArrowDown}");
    const run = document.activeElement as HTMLElement;
    expect(run).toHaveAttribute("data-run");
    const event = createEvent.keyDown(run, { key: "ArrowDown" });
    fireEvent(run, event);
    expect(event.defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(run);
  });

  it("folds a comparison without difference to one run, reached from the header and unfolded [WF-IHM-0170-A]", async () => {
    const list = example("comparison_identical") as NodeList;
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <EstimateGrid
          filters={{}}
          reference={estimateReference()}
          editable
          tasksEditable
          nodes={projectNodes(list, ESTIMATE_FIELDS) as NodeRows<never>}
          structure={STRUCTURE}
          structureVersion={1}
          query={NO_QUERY}
          preferences={undefined}
          comparing
        />
      </NextIntlClientProvider>,
    );
    await userEvent.click(differencesOnly());
    expect(labels()).toEqual([]);
    expect(screen.getAllByRole("button", { name: /sans écart repliées$/ })).toHaveLength(1);
    const header = document.querySelector<HTMLElement>("th[data-column]");
    await act(async () => {
      header?.focus();
      await Promise.resolve();
    });
    await userEvent.keyboard("{ArrowDown}");
    expect(document.activeElement).toHaveAttribute("data-run");
    await userEvent.keyboard("{Enter}");
    expect(labels().length).toBeGreaterThan(0);
    expect(document.activeElement).toHaveAttribute("data-row", "0");
  });

  it("refuses a block pasted from the last row before a run, which it would span, asking nothing [WF-IHM-0170-A]", async () => {
    render(planningGrid(compared(MARKED)));
    await userEvent.click(differencesOnly());
    labelOf(SUMMARY).focus();
    await userEvent.paste("a\nb");
    expect(await screen.findByRole("alert")).toHaveTextContent("lignes pliées");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(calls()).toBe(0);
  });

  it("counts, in a selection that spans a run, the rows shown alone [WF-IHM-0170-A]", async () => {
    render(planningGrid(compared(MARKED)));
    await userEvent.click(differencesOnly());
    const handle = (label: string): HTMLElement => {
      const found = document.querySelector<HTMLElement>(
        `td[data-row="${labelOf(label).dataset.row ?? ""}"][data-column="row_number"]`,
      );
      if (found === null) {
        throw new Error(`no handle for ${label}`);
      }
      return found;
    };
    fireEvent.click(handle(SUMMARY));
    fireEvent.click(handle(DESIGN), { shiftKey: true });
    expect(screen.getByText("2 lignes sélectionnées")).toBeVisible();
    const selected = [...document.querySelectorAll("tr[aria-selected='true']")];
    expect(selected).toHaveLength(2);
    expect(selected.map((row) => row.textContent.includes("repliées"))).toEqual([false, false]);
  });
});
