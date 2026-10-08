// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";
import { estimateReference } from "@/test/reference";

import { EstimateGrid } from "./estimate-grid";
import { FOLD_STORAGE_PREFIX, foldShortcut } from "./fold";
import type { NodeFilters, NodeList, NodeSortColumn } from "./nodes";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";
import { RemainingGrid } from "./remaining-grid";

// The server of Next, as far as the grid needs it, as for the other tests of the grid.
const server = vi.hoisted((): { client: FakeClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/projects/p/revisions/r/planning",
  useSearchParams: () => new URLSearchParams(),
}));

type Node = components["schemas"]["Node"];

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined };
// The main structure of the current revision of the witness project, as the examples name it.
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
// The preview of a paste.
const PREVIEW =
  "POST /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste-preview";
// The sub-project « Essais et mise en service » of the witness project.
const TESTS = "01926f3a-7c00-7000-8000-000000000802";
// The witness planning of four levels of tasks (`nodes_nested`): the installation on site, the
// batch of the control room under it, the subtree the occurrence of a risk merged under the
// batch, and its two tasks.
const nested = example("nodes_nested") as NodeList;
const INSTALLATION = "Installation sur site";
const CONTROL_ROOM = "Poste de commande";
const WIRING = "Câblage des armoires";
const OCCURRED = "Risque survenu — Retard de livraison des armoires";
const REMINDER = "Relance du fournisseur";
const TRANSPORT = "Transport exceptionnel";
const ACCEPTANCE = "Réception usine";
const ASSEMBLY = "Montage des armoires sur site";
const COMMISSIONING = "Mise en service";
const UNDER_CONTROL_ROOM = [WIRING, OCCURRED, REMINDER, TRANSPORT, ACCEPTANCE];

/** The grid of the planning on an answer, read for a revision, narrowed or not. */
function planning(
  nodes: NodeList = nested,
  {
    query = NO_QUERY,
    filters = { kinds: ["task"] },
    revision = STRUCTURE.revision_id,
  }: { query?: GridQuery<NodeSortColumn>; filters?: NodeFilters; revision?: string } = {},
) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PlanningGrid
        nodes={nodes}
        structure={{ ...STRUCTURE, revision_id: revision }}
        filters={filters}
        query={query}
        preferences={undefined}
      />
    </NextIntlClientProvider>
  );
}

/** The grid of the estimate of the witness batch of the control room, its tasks and their lines. */
function estimate(filters: { subproject_id?: string } = {}) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <EstimateGrid
        nodes={example("nodes_estimate") as NodeList}
        structure={STRUCTURE}
        structureVersion={1}
        reference={estimateReference()}
        editable
        tasksEditable
        query={NO_QUERY}
        filters={filters}
        preferences={undefined}
      />
    </NextIntlClientProvider>
  );
}

/** The grid of the remaining to commit of the witness batch, for the states of tasks asked. */
function remaining(progress: NonNullable<NodeFilters["progress"]>, subproject?: string) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <RemainingGrid
        nodes={example("nodes_estimate") as NodeList}
        structure={STRUCTURE}
        filters={subproject === undefined ? { progress } : { progress, subproject_id: subproject }}
        editable={false}
        query={NO_QUERY}
        preferences={undefined}
      />
    </NextIntlClientProvider>
  );
}

/** The labels of the rows the grid renders, in their order. */
function labels(): string[] {
  return [...document.querySelectorAll('tbody td[data-column="label"]')].map(
    (cell) => cell.textContent,
  );
}

/** The row of a label. */
function rowOf(label: string): HTMLElement {
  const row = screen
    .getAllByRole("row")
    .find((candidate) => candidate.querySelector('td[data-column="label"]')?.textContent === label);
  if (row === undefined) {
    throw new Error(`no row of ${label}`);
  }
  return row;
}

/** The cell of a column in the row of a label. */
function cellOf(label: string, column: string): HTMLElement {
  const cell = rowOf(label).querySelector<HTMLElement>(`td[data-column="${column}"]`);
  if (cell === null) {
    throw new Error(`no cell ${column} in the row of ${label}`);
  }
  return cell;
}

/** Press a key of the folding on a cell, on a QWERTY keyboard: Alt, Shift and a key of the main block. */
function press(cell: HTMLElement, key: "-" | "+" | "*") {
  const code = { "-": "Minus", "+": "Equal", "*": "Digit8" }[key];
  fireEvent.keyDown(cell, { key: key === "-" ? "_" : key, code, altKey: true, shiftKey: true });
}

/** Press a key of the folding on a cell, on an AZERTY keyboard: Alt, and Shift for plus alone. */
function pressAzerty(cell: HTMLElement, key: "-" | "+" | "*") {
  const code = { "-": "Digit6", "+": "Slash", "*": "Backslash" }[key];
  fireEvent.keyDown(cell, { key, code, altKey: true, shiftKey: key === "+" });
}

/** A key pressed, as the folding reads it. */
function keyOf({
  altGraph = false,
  ...pressed
}: {
  key: string;
  code: string;
  shiftKey?: boolean;
  ctrlKey?: boolean;
  altGraph?: boolean;
}) {
  return {
    altKey: true,
    shiftKey: false,
    ctrlKey: false,
    metaKey: false,
    getModifierState: () => altGraph,
    ...pressed,
  };
}

/** Open the menu of a cell from the keyboard, the cell given the focus. */
async function openMenuOf(cell: HTMLElement): Promise<HTMLElement> {
  await userEvent.click(cell);
  await userEvent.keyboard("{Shift>}{F10}{/Shift}");
  return screen.getByRole("menu", { name: "Menu de la cellule" });
}

beforeEach(() => {
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
  window.sessionStorage.clear();
});

describe("the tree of the grid of the planning", () => {
  it("is a tree grid whose rows tell their level, their place among their siblings and whether they are unfolded", async () => {
    const { container } = render(planning());
    const grid = screen.getByRole("treegrid", { name: "Grille de planning" });
    expect(grid).toHaveAttribute("aria-rowcount", "11");
    expect(rowOf(INSTALLATION)).toHaveAttribute("aria-level", "1");
    expect(rowOf(INSTALLATION)).toHaveAttribute("aria-expanded", "true");
    expect(rowOf(CONTROL_ROOM)).toHaveAttribute("aria-level", "2");
    expect(rowOf(CONTROL_ROOM)).toHaveAttribute("aria-posinset", "1");
    expect(rowOf(CONTROL_ROOM)).toHaveAttribute("aria-setsize", "3");
    expect(rowOf(COMMISSIONING)).toHaveAttribute("aria-posinset", "3");
    expect(rowOf(REMINDER)).toHaveAttribute("aria-level", "4");
    // A row under which nothing folds is no branch: neither expanded nor collapsed.
    expect(rowOf(REMINDER)).not.toHaveAttribute("aria-expanded");
    expect(within(rowOf(REMINDER)).queryByRole("button")).toBeNull();
    expect(within(cellOf(INSTALLATION, "label")).getByRole("button")).toHaveAccessibleName("Plier");
    await expectAccessible(container);
  });

  it("folds and unfolds a summary by the button of its label, the rows under it taken out of the grid", async () => {
    render(planning());
    await userEvent.click(within(cellOf(CONTROL_ROOM, "label")).getByRole("button"));
    expect(rowOf(CONTROL_ROOM)).toHaveAttribute("aria-expanded", "false");
    expect(labels()).toEqual([INSTALLATION, CONTROL_ROOM, ASSEMBLY, COMMISSIONING]);
    expect(screen.getByRole("treegrid")).toHaveAttribute("aria-rowcount", "6");
    // The cell of the label is the active one, the focus on it.
    expect(cellOf(CONTROL_ROOM, "label")).toHaveFocus();
    const unfold = within(cellOf(CONTROL_ROOM, "label")).getByRole("button");
    expect(unfold).toHaveAccessibleName("Déplier");
    await userEvent.click(unfold);
    expect(rowOf(CONTROL_ROOM)).toHaveAttribute("aria-expanded", "true");
    expect(labels()).toEqual(nested.items.map((node) => node.task?.label));
  });

  it("folds the row of the active cell by Alt and minus and unfolds it by Alt and plus, as in Microsoft Project", async () => {
    render(planning());
    await userEvent.click(cellOf(OCCURRED, "duration"));
    press(cellOf(OCCURRED, "duration"), "-");
    expect(rowOf(OCCURRED)).toHaveAttribute("aria-expanded", "false");
    expect(labels()).not.toContain(REMINDER);
    expect(cellOf(OCCURRED, "duration")).toHaveFocus();
    press(cellOf(OCCURRED, "duration"), "+");
    expect(rowOf(OCCURRED)).toHaveAttribute("aria-expanded", "true");
    expect(labels()).toContain(REMINDER);
    // The keys are told on the label of the rows that fold, and there alone.
    expect(cellOf(OCCURRED, "label")).toHaveAttribute(
      "aria-keyshortcuts",
      "Shift+F10 Alt+- Alt+Plus Alt+*",
    );
    expect(cellOf(OCCURRED, "duration")).toHaveAttribute("aria-keyshortcuts", "Shift+F10");
    expect(cellOf(REMINDER, "label")).toHaveAttribute("aria-keyshortcuts", "Shift+F10");
  });

  it("folds the row above from a row under which nothing folds, the active cell going to it", async () => {
    render(planning());
    await userEvent.click(cellOf(TRANSPORT, "start"));
    press(cellOf(TRANSPORT, "start"), "-");
    expect(rowOf(OCCURRED)).toHaveAttribute("aria-expanded", "false");
    expect(cellOf(OCCURRED, "start")).toHaveFocus();
    // Unfolding a row under which nothing folds does nothing.
    await userEvent.click(cellOf(ACCEPTANCE, "start"));
    press(cellOf(ACCEPTANCE, "start"), "+");
    expect(labels()).not.toContain(REMINDER);
  });

  it("folds and unfolds on an AZERTY keyboard, minus and * without Shift", async () => {
    render(planning());
    await userEvent.click(cellOf(OCCURRED, "label"));
    pressAzerty(cellOf(OCCURRED, "label"), "-");
    expect(rowOf(OCCURRED)).toHaveAttribute("aria-expanded", "false");
    pressAzerty(cellOf(OCCURRED, "label"), "+");
    expect(rowOf(OCCURRED)).toHaveAttribute("aria-expanded", "true");
    press(cellOf(OCCURRED, "label"), "-");
    pressAzerty(cellOf(OCCURRED, "label"), "*");
    expect(labels()).toHaveLength(nested.items.length);
  });

  it("reads the character of a key in the layout the browser tells, Option on a Mac typing another", async () => {
    // A Mac AZERTY keyboard: the key of minus where a QWERTY one has equals.
    const layout = new Map([["Equal", "-"]]);
    Object.defineProperty(navigator, "keyboard", {
      value: { getLayoutMap: () => Promise.resolve(layout) },
      configurable: true,
    });
    try {
      render(planning());
      await userEvent.click(cellOf(OCCURRED, "label"));
      fireEvent.keyDown(cellOf(OCCURRED, "label"), { key: "—", code: "Equal", altKey: true });
      expect(rowOf(OCCURRED)).toHaveAttribute("aria-expanded", "false");
    } finally {
      Reflect.deleteProperty(navigator, "keyboard");
    }
  });

  it("unfolds the rows above those a filter on a sub-project retains", async () => {
    const { rerender } = render(planning());
    await userEvent.click(within(cellOf(CONTROL_ROOM, "label")).getByRole("button"));
    expect(labels()).not.toContain(WIRING);
    rerender(planning(nested, { filters: { kinds: ["task"], subproject_id: TESTS } }));
    expect(rowOf(CONTROL_ROOM)).toHaveAttribute("aria-expanded", "true");
    expect(labels()).toContain(WIRING);
  });

  it("moves through the rows that stay alone, the arrows skipping those folded away", async () => {
    render(planning());
    await userEvent.click(cellOf(CONTROL_ROOM, "label"));
    press(cellOf(CONTROL_ROOM, "label"), "-");
    await userEvent.keyboard("{ArrowDown}");
    expect(cellOf(ASSEMBLY, "label")).toHaveFocus();
    await userEvent.keyboard("{ArrowUp}{ArrowUp}");
    expect(cellOf(INSTALLATION, "label")).toHaveFocus();
    // Folded above the active cell, the tree keeps it on its row.
    await userEvent.click(cellOf(COMMISSIONING, "label"));
    press(cellOf(INSTALLATION, "label"), "-");
    expect(labels()).toEqual([INSTALLATION]);
    expect(cellOf(INSTALLATION, "label")).toHaveFocus();
    // Alt and * unfolds the whole tree.
    press(cellOf(INSTALLATION, "label"), "*");
    expect(labels()).toHaveLength(nested.items.length);
    expect(cellOf(INSTALLATION, "label")).toHaveFocus();
  });

  it("folds the tree whole, down to a level, or unfolds it whole, from its bar", async () => {
    render(planning());
    await userEvent.click(screen.getByRole("button", { name: "Arbre" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Tout plier" }));
    expect(labels()).toEqual([INSTALLATION]);
    await userEvent.click(screen.getByRole("button", { name: "Arbre" }));
    const menu = screen.getByRole("menu");
    // Down to each level that has rows to fold: the batch at the second, the risk at the third.
    const items = within(menu).getAllByRole("menuitem");
    const names = ["Tout déplier", "Tout plier", "Jusqu’au niveau 2", "Jusqu’au niveau 3"];
    expect(items).toHaveLength(names.length);
    names.forEach((name, at) => {
      expect(items[at]).toHaveAccessibleName(name);
    });
    expect(within(menu).getByRole("menuitem", { name: "Tout déplier" })).toHaveAttribute(
      "aria-keyshortcuts",
      "Alt+*",
    );
    await userEvent.click(within(menu).getByRole("menuitem", { name: "Jusqu’au niveau 3" }));
    expect(labels()).toEqual([
      INSTALLATION,
      CONTROL_ROOM,
      WIRING,
      OCCURRED,
      ACCEPTANCE,
      ASSEMBLY,
      COMMISSIONING,
    ]);
    await userEvent.click(screen.getByRole("button", { name: "Arbre" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Tout déplier" }));
    expect(labels()).toHaveLength(nested.items.length);
  });

  it("presents the same tree in the Gantt, folded alike: a summary folded in the grid is folded in the Gantt, and the other way round — Une récapitulative pliée dans la grille l’est dans le Gantt, et réciproquement. [WF-PLA-0090-A]", async () => {
    render(planning());
    const bars = () =>
      [...document.querySelectorAll('tbody td[data-column="gantt"]')].filter(
        (cell) => within(cell as HTMLElement).queryByRole("img") !== null,
      ).length;
    expect(bars()).toBe(nested.items.length);
    // Folded in the grid: the bars under it leave the Gantt, whose bracket offers to unfold it.
    await userEvent.click(within(cellOf(CONTROL_ROOM, "label")).getByRole("button"));
    expect(bars()).toBe(nested.items.length - UNDER_CONTROL_ROOM.length);
    expect(within(cellOf(CONTROL_ROOM, "gantt")).getByRole("button")).toHaveAccessibleName(
      "Déplier",
    );
    // Unfolded from the Gantt: the grid unfolds.
    await userEvent.click(within(cellOf(CONTROL_ROOM, "gantt")).getByRole("button"));
    expect(rowOf(CONTROL_ROOM)).toHaveAttribute("aria-expanded", "true");
    expect(labels()).toEqual(expect.arrayContaining(UNDER_CONTROL_ROOM));
    expect(cellOf(CONTROL_ROOM, "gantt")).toHaveFocus();
    // Folded from the Gantt, by its button or by the keys on its cell: the grid folds.
    await userEvent.click(within(cellOf(OCCURRED, "gantt")).getByRole("button"));
    expect(within(cellOf(OCCURRED, "label")).getByRole("button")).toHaveAccessibleName("Déplier");
    expect(labels()).not.toContain(REMINDER);
    press(cellOf(INSTALLATION, "gantt"), "-");
    expect(labels()).toEqual([INSTALLATION]);
    // Folding modifies no task: nothing is sent.
    expect(server.client?.calls).toEqual([]);
  });

  it("unfolds the rows above those a search retains — La recherche sur un libellé ne laisse voir que les tâches correspondantes et leurs parents. [WF-PLA-0080-A]", async () => {
    const { rerender } = render(planning());
    await userEvent.click(within(cellOf(CONTROL_ROOM, "label")).getByRole("button"));
    expect(labels()).not.toContain(REMINDER);
    // The answer of the search: the task it retains, and the rows above it.
    const searched: NodeList = {
      ...nested,
      items: nested.items.filter((node) =>
        [INSTALLATION, CONTROL_ROOM, OCCURRED, REMINDER].includes(node.task?.label ?? ""),
      ),
    };
    rerender(
      planning(searched, {
        query: { sort: undefined, search: "Relance" },
        filters: { kinds: ["task"], search: "Relance" },
      }),
    );
    expect(labels()).toEqual([INSTALLATION, CONTROL_ROOM, OCCURRED, REMINDER]);
    expect(rowOf(CONTROL_ROOM)).toHaveAttribute("aria-expanded", "true");
    // Once for the search: the user folds it again.
    await userEvent.click(within(cellOf(CONTROL_ROOM, "label")).getByRole("button"));
    expect(labels()).toEqual([INSTALLATION, CONTROL_ROOM]);
    // The search lifted, the tree is as it was left.
    rerender(planning());
    expect(labels()).toEqual([INSTALLATION, CONTROL_ROOM, ASSEMBLY, COMMISSIONING]);
  });

  it("keeps its folds for the session, by revision and by grid, sending nothing to the server", async () => {
    const { unmount } = render(planning());
    await userEvent.click(within(cellOf(OCCURRED, "label")).getByRole("button"));
    unmount();
    render(planning());
    expect(rowOf(OCCURRED)).toHaveAttribute("aria-expanded", "false");
    expect(labels()).not.toContain(REMINDER);
    const kept = window.sessionStorage.getItem(
      `${FOLD_STORAGE_PREFIX}planning:${STRUCTURE.revision_id}`,
    );
    const occurred = nested.items.find((node) => node.task?.label === OCCURRED);
    expect(kept).toContain(occurred?.node_id);
    expect(server.client?.calls).toEqual([]);
  });

  it("does not take the folds of another revision", async () => {
    const { unmount } = render(planning());
    await userEvent.click(within(cellOf(OCCURRED, "label")).getByRole("button"));
    unmount();
    render(planning(nested, { revision: "01926f3a-7c00-7000-8000-000000000101" }));
    expect(rowOf(OCCURRED)).toHaveAttribute("aria-expanded", "true");
  });

  it("reads back nothing it did not write: what has not the shape written folds nothing", () => {
    const key = `${FOLD_STORAGE_PREFIX}planning:${STRUCTURE.revision_id}`;
    window.sessionStorage.setItem(key, '{"collapsed":[1],"revealed":""}');
    const { unmount } = render(planning());
    expect(labels()).toHaveLength(nested.items.length);
    unmount();
    window.sessionStorage.setItem(key, "{");
    render(planning());
    expect(labels()).toHaveLength(nested.items.length);
  });

  it("reads back what it kept in memory when the storage refuses to write, never what it held before", async () => {
    const { unmount } = render(planning());
    await userEvent.click(within(cellOf(CONTROL_ROOM, "label")).getByRole("button"));
    unmount();
    const storage = window.sessionStorage;
    vi.stubGlobal("sessionStorage", {
      getItem: (key: string) => storage.getItem(key),
      setItem: () => {
        throw new DOMException("quota", "QuotaExceededError");
      },
    });
    try {
      render(planning());
      expect(labels()).not.toContain(WIRING);
      await userEvent.click(within(cellOf(CONTROL_ROOM, "label")).getByRole("button"));
      // Unfolded, though the storage still holds the fold: the memory, newer, is read first.
      expect(labels()).toContain(WIRING);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("folds in memory alone when the browser refuses its storage", async () => {
    const refused = () => {
      throw new DOMException("refused", "SecurityError");
    };
    vi.stubGlobal("sessionStorage", { getItem: refused, setItem: refused });
    try {
      render(planning(nested, { revision: "01926f3a-7c00-7000-8000-0000000001ff" }));
      await userEvent.click(within(cellOf(CONTROL_ROOM, "label")).getByRole("button"));
      expect(labels()).toEqual([INSTALLATION, CONTROL_ROOM, ASSEMBLY, COMMISSIONING]);
      await userEvent.click(within(cellOf(CONTROL_ROOM, "label")).getByRole("button"));
      expect(labels()).toHaveLength(nested.items.length);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  it("keeps the active cell in the header when the bar folds the tree, and a double click on a button enters nothing", async () => {
    render(estimate());
    await userEvent.click(cellOf(CONTROL_ROOM, "label"));
    await userEvent.keyboard("{ArrowUp}");
    const header = screen.getByRole("columnheader", { name: "Libellé" });
    expect(header).toHaveFocus();
    await userEvent.click(screen.getByRole("button", { name: "Arbre" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Tout plier" }));
    expect(labels()).toEqual([CONTROL_ROOM]);
    expect(header).toHaveAttribute("tabindex", "0");
    // The label of a task is entered on a double click; not on one on its button.
    await userEvent.dblClick(within(cellOf(CONTROL_ROOM, "label")).getByRole("button"));
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(labels()).toEqual([CONTROL_ROOM]);
  });

  it("renders the rows that stay alone, those folded away out of the window", async () => {
    // A summary over a thousand tasks, built from the witness: folded, a single row stays.
    const [first, second] = nested.items;
    if (first === undefined || second === undefined) {
      throw new Error("the example nodes_nested has changed");
    }
    const identifier = (index: number) =>
      `01926f3a-7c00-7000-8000-${String(900000 + index).padStart(12, "0")}`;
    const tasks = Array.from({ length: 1000 }, (_, index): Node => ({
      ...second,
      node_id: identifier(index),
      lineage_id: identifier(index),
      parent_id: first.node_id,
      row_number: index + 2,
      task:
        second.task === undefined || second.task === null
          ? null
          : { ...second.task, label: `Tâche ${String(index)}` },
    }));
    render(planning({ ...nested, items: [first, ...tasks] }));
    expect(labels().length).toBeLessThan(100);
    await userEvent.click(within(cellOf(INSTALLATION, "label")).getByRole("button"));
    expect(labels()).toEqual([INSTALLATION]);
    expect(screen.getByRole("treegrid")).toHaveAttribute("aria-rowcount", "3");
    expect(document.querySelectorAll('tbody tr[aria-hidden="true"]')).toHaveLength(0);
  });
});

describe("the tree of the grids of the estimate and of the remaining to commit", () => {
  it("folds a task over its lines in the estimate, and keeps its folds apart from the planning's", async () => {
    const { unmount } = render(estimate());
    expect(screen.getByRole("treegrid", { name: "Grille de devis" })).toBeInTheDocument();
    await userEvent.click(within(cellOf(WIRING, "label")).getByRole("button"));
    expect(rowOf(WIRING)).toHaveAttribute("aria-expanded", "false");
    expect(labels()).not.toContain("Borniers");
    unmount();
    render(planning());
    expect(rowOf(WIRING)).not.toHaveAttribute("aria-expanded");
    expect(labels()).toHaveLength(nested.items.length);
  });

  it("unfolds the rows above those a filter on a sub-project retains", async () => {
    const { unmount } = render(estimate());
    await userEvent.click(within(cellOf(CONTROL_ROOM, "label")).getByRole("button"));
    expect(labels()).toEqual([CONTROL_ROOM]);
    unmount();
    render(estimate({ subproject_id: TESTS }));
    expect(rowOf(CONTROL_ROOM)).toHaveAttribute("aria-expanded", "true");
    expect(labels()).toContain("Borniers");
  });

  it("folds in the remaining to commit too, the states of the tasks asked its scope, which unfolds nothing, a sub-project a filter, which does", async () => {
    const { rerender } = render(remaining(["started"]));
    const grid = screen.getByRole("treegrid", { name: "Grille de reste à engager" });
    await userEvent.click(cellOf(WIRING, "label"));
    press(cellOf(WIRING, "label"), "-");
    expect(rowOf(WIRING)).toHaveAttribute("aria-expanded", "false");
    expect(within(grid).queryByText("Borniers")).toBeNull();
    rerender(remaining(["started", "not_started"]));
    expect(rowOf(WIRING)).toHaveAttribute("aria-expanded", "false");
    rerender(remaining(["started"]));
    expect(rowOf(WIRING)).toHaveAttribute("aria-expanded", "false");
    expect(within(grid).queryByText("Borniers")).toBeNull();
    rerender(remaining(["started"], TESTS));
    expect(rowOf(WIRING)).toHaveAttribute("aria-expanded", "true");
    expect(within(grid).getByText("Borniers")).toBeInTheDocument();
  });

  it("folds the row of a cell from its menu, Shift+F10, in every browser, the focus given back to the cell", async () => {
    render(remaining(["started"]));
    const menu = await openMenuOf(cellOf(WIRING, "label"));
    expect(within(menu).queryByRole("menuitem", { name: "Déplier la ligne" })).toBeNull();
    await userEvent.click(within(menu).getByRole("menuitem", { name: "Plier la ligne" }));
    expect(screen.queryByRole("menu")).toBeNull();
    expect(rowOf(WIRING)).toHaveAttribute("aria-expanded", "false");
    expect(labels()).not.toContain("Borniers");
    expect(cellOf(WIRING, "label")).toHaveFocus();
  });

  it("unfolds the row of a cell from its menu, and unfolds the whole tree, the focus given back to the cell", async () => {
    render(remaining(["started"]));
    await userEvent.click(within(cellOf(WIRING, "label")).getByRole("button"));
    let menu = await openMenuOf(cellOf(WIRING, "finish"));
    expect(within(menu).queryByRole("menuitem", { name: "Plier la ligne" })).toBeNull();
    await userEvent.click(within(menu).getByRole("menuitem", { name: "Déplier la ligne" }));
    expect(rowOf(WIRING)).toHaveAttribute("aria-expanded", "true");
    expect(cellOf(WIRING, "finish")).toHaveFocus();
    // From a line, its task folded; the focus goes to the task, the line folded away.
    // From a line, the item names the task it folds.
    menu = await openMenuOf(cellOf("Borniers", "label"));
    expect(within(menu).queryByRole("menuitem", { name: "Plier la ligne" })).toBeNull();
    await userEvent.click(within(menu).getByRole("menuitem", { name: `Plier « ${WIRING} »` }));
    expect(labels()).not.toContain("Borniers");
    expect(cellOf(WIRING, "label")).toHaveFocus();
    menu = await openMenuOf(cellOf(CONTROL_ROOM, "label"));
    await userEvent.click(within(menu).getByRole("menuitem", { name: "Tout déplier" }));
    expect(labels()).toContain("Borniers");
    expect(cellOf(CONTROL_ROOM, "label")).toHaveFocus();
  });

  it("refuses a block pasted over a row folded away, asking nothing, and asks it once unfolded", async () => {
    const client = fakeClient({ [PREVIEW]: "paste_plan" });
    server.client = client;
    render(estimate());
    await userEvent.click(within(cellOf(WIRING, "label")).getByRole("button"));
    cellOf(WIRING, "label").focus();
    await userEvent.paste("a\nb");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Le bloc collé s’étendrait sur des lignes pliées : dépliez-les avant de coller, ou collez un bloc moins haut.",
    );
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(client.calls.filter((call) => call.route === PREVIEW)).toEqual([]);
    // A block of one row fills the task alone: asked.
    await userEvent.paste("a");
    await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    await userEvent.keyboard("{Escape}");
    await userEvent.click(within(cellOf(WIRING, "label")).getByRole("button"));
    cellOf(WIRING, "label").focus();
    await userEvent.paste("a\nb");
    await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    expect(client.calls.filter((call) => call.route === PREVIEW).map((call) => call.body)).toEqual([
      expect.objectContaining({ target_column: "label", rows: [["a"]] }),
      expect.objectContaining({ target_column: "label", rows: [["a"], ["b"]] }),
    ]);
  });
});

describe("the keys the grid tells", () => {
  /** Run on a Mac, its browser telling the layout of the keyboard or not. */
  function onMac(layout: boolean): () => void {
    Object.defineProperty(navigator, "userAgent", {
      value: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
      configurable: true,
    });
    if (layout) {
      Object.defineProperty(navigator, "keyboard", {
        value: { getLayoutMap: () => Promise.resolve(new Map()) },
        configurable: true,
      });
    }
    return () => {
      Reflect.deleteProperty(navigator, "userAgent");
      Reflect.deleteProperty(navigator, "keyboard");
    };
  }

  it("are Shift+F10 alone on a Mac whose browser does not tell the layout, the keys of Option read nowhere", async () => {
    const restore = onMac(false);
    try {
      render(planning());
      expect(cellOf(OCCURRED, "label")).toHaveAttribute("aria-keyshortcuts", "Shift+F10");
      const menu = await openMenuOf(cellOf(OCCURRED, "label"));
      for (const item of within(menu).getAllByRole("menuitem")) {
        expect(item).not.toHaveAttribute("aria-keyshortcuts");
      }
      await userEvent.keyboard("{Escape}");
      await userEvent.click(screen.getByRole("button", { name: "Arbre" }));
      const all = screen.getByRole("menuitem", { name: "Tout déplier" });
      expect(all).not.toHaveAttribute("aria-keyshortcuts");
      expect(all).toHaveTextContent(/^Tout déplier$/);
    } finally {
      restore();
    }
  });

  it("are minus and plus on a Mac whose browser tells the layout, never *, which Option does not type", () => {
    const restore = onMac(true);
    try {
      render(planning());
      expect(cellOf(OCCURRED, "label")).toHaveAttribute(
        "aria-keyshortcuts",
        "Shift+F10 Alt+- Alt+Plus",
      );
    } finally {
      restore();
    }
  });

  it("offer the whole tree unfolded in the menu of the empty row of a grid read only: never an empty menu", async () => {
    const empty = example("nodes_estimate") as NodeList;
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <RemainingGrid
          nodes={{ ...empty, items: [] }}
          structure={STRUCTURE}
          filters={{ progress: ["started"] }}
          editable={false}
          query={NO_QUERY}
          preferences={undefined}
        />
      </NextIntlClientProvider>,
    );
    await userEvent.pointer({
      keys: "[MouseRight]",
      target: screen.getByText("Aucune ligne ne répond à la demande."),
    });
    const menu = screen.getByRole("menu", { name: "Menu de la cellule" });
    expect(
      within(menu)
        .getAllByRole("menuitem")
        .map((item) => item.textContent),
    ).toEqual(["Tout déplier"]);
  });
});

describe("the keys of the folding", () => {
  it("are read by the character, Shift or not, with Alt and never Ctrl: on QWERTY, AZERTY and the keypad", () => {
    expect(foldShortcut(keyOf({ key: "_", code: "Minus", shiftKey: true }), undefined)).toBe(
      "collapse",
    );
    expect(foldShortcut(keyOf({ key: "-", code: "Digit6" }), undefined)).toBe("collapse");
    expect(foldShortcut(keyOf({ key: "*", code: "Backslash" }), undefined)).toBe("expandAll");
    expect(foldShortcut(keyOf({ key: "*", code: "Digit8", shiftKey: true }), undefined)).toBe(
      "expandAll",
    );
    expect(foldShortcut(keyOf({ key: "+", code: "Equal", shiftKey: true }), undefined)).toBe(
      "expand",
    );
    expect(foldShortcut(keyOf({ key: "-", code: "NumpadSubtract" }), undefined)).toBe("collapse");
    expect(foldShortcut(keyOf({ key: "+", code: "NumpadAdd" }), undefined)).toBe("expand");
    expect(foldShortcut(keyOf({ key: "*", code: "NumpadMultiply" }), undefined)).toBe("expandAll");
    // Option on a Mac types another character: by the place of the key alone, nothing.
    expect(
      foldShortcut(keyOf({ key: "—", code: "Equal", shiftKey: true }), undefined),
    ).toBeUndefined();
    expect(foldShortcut(keyOf({ key: "a", code: "KeyA" }), undefined)).toBeUndefined();
    expect(
      foldShortcut(keyOf({ key: "-", code: "Digit6", ctrlKey: true }), undefined),
    ).toBeUndefined();
    expect(
      foldShortcut({ ...keyOf({ key: "-", code: "Digit6" }), altKey: false }, undefined),
    ).toBeUndefined();
  });

  it("read the character the layout the browser tells bears, before the one Option typed", () => {
    // On a Mac AZERTY keyboard, the key of minus is at the place of equals on a QWERTY one.
    const macAzerty = new Map([
      ["Equal", "-"],
      ["Slash", "="],
      ["Digit8", "!"],
    ]);
    expect(foldShortcut(keyOf({ key: "—", code: "Equal" }), macAzerty)).toBe("collapse");
    expect(foldShortcut(keyOf({ key: "≠", code: "Slash" }), macAzerty)).toBe("expand");
    // The character typed first: what the layout says the key bears comes after.
    expect(foldShortcut(keyOf({ key: "*", code: "Digit8", shiftKey: true }), macAzerty)).toBe(
      "expandAll",
    );
    expect(
      foldShortcut(keyOf({ key: "*", code: "Digit8", shiftKey: true }), new Map([["Digit8", "_"]])),
    ).toBe("expandAll");
    expect(
      foldShortcut(
        keyOf({ key: "*", code: "BracketRight", shiftKey: true }),
        new Map([["BracketRight", "+"]]),
      ),
    ).toBe("expandAll");
  });

  it("are not read without the layout where Option types another character — Safari, Firefox on a Mac —, nor with AltGr", () => {
    // Option and minus on a Mac: an en dash, which names no command; the menu of the cell folds.
    expect(foldShortcut(keyOf({ key: "–", code: "Minus" }), undefined)).toBeUndefined();
    expect(
      foldShortcut(keyOf({ key: "-", code: "Digit6", altGraph: true }), undefined),
    ).toBeUndefined();
  });
});
