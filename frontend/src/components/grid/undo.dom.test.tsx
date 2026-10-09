// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import type { ApiClient } from "@/api/client";
import { costRow } from "@/components/costs/cost-grid";
import { CostsGrid } from "@/components/costs/costs-grid";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";
import { estimateReference } from "@/test/reference";

import { EstimateGrid } from "./estimate-grid";
import type { NodeList, NodeSortColumn } from "./nodes";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";

// The server of Next, as far as the grid needs it, as for the other tests of the grid.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/estimate",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined };
// The main structure of the current revision of the witness project, as the examples name it.
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const REASON = "Indisponibles tant que le serveur ne conserve pas l’historique des saisies.";
const TOLD_UNDO =
  "Annuler est indisponible : le serveur ne conserve pas encore l’historique des saisies.";
const TOLD_REDO =
  "Rétablir est indisponible : le serveur ne conserve pas encore l’historique des saisies.";

/** A part of the screen, in a language. */
function inLanguage(children: ReactNode, locale: Locale = "fr") {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      {children}
    </NextIntlClientProvider>
  );
}

/** The grid of the estimate, open to entry — a revision in progress — or not — a marked one. */
function estimateGrid(editable = true, locale: Locale = "fr") {
  return inLanguage(
    <EstimateGrid
      nodes={example("nodes_estimate") as NodeList}
      structure={STRUCTURE}
      structureVersion={1}
      reference={estimateReference()}
      editable={editable}
      tasksEditable={editable}
      query={NO_QUERY}
      filters={{}}
      preferences={undefined}
    />,
    locale,
  );
}

/** The first cell of the labels, given the focus as a click on it would. */
function focusLabel(): HTMLElement {
  const found = screen
    .getByRole("treegrid")
    .querySelector<HTMLElement>('td[data-row="1"][data-column="label"]');
  if (found === null) {
    throw new Error("no cell of label in the second row");
  }
  found.focus();
  return found;
}

/** Ctrl+Z, or Ctrl+Shift+Z, pressed on an element: whether the browser may still do its own. */
function press(element: Element, shift = false): boolean {
  return fireEvent.keyDown(element, { key: shift ? "Z" : "z", ctrlKey: true, shiftKey: shift });
}

/** What the grid announced of the shortcut, if anything. */
function told(): string | null {
  return toldNode()?.textContent ?? null;
}

/** The node the grid last announced the shortcut in, if any. */
function toldNode(): Element | undefined {
  return screen
    .queryAllByRole("status")
    .map((region) => region.firstElementChild)
    .find((node) => node !== null);
}

/** The menu of the cells, open. */
function cellMenu(): HTMLElement {
  return screen.getByRole("menu", { name: "Menu de la cellule" });
}

let client: FakeClient;

beforeEach(() => {
  client = fakeClient({ "PATCH /me/preferences": "preferences" });
  server.client = client;
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("undo and redo, placed in the grids", () => {
  it("places Undo and Redo in the bar of a grid that enters a revision in progress, unavailable, saying why, and doing nothing", async () => {
    render(estimateGrid());
    for (const [name, keys] of [
      ["Annuler", "Control+Z Meta+Z"],
      ["Rétablir", "Control+Shift+Z Meta+Shift+Z"],
    ] as const) {
      const button = screen.getByRole("button", { name });
      expect(button).toHaveAttribute("aria-disabled", "true");
      expect(button).toHaveAccessibleDescription(REASON);
      expect(button).toHaveAttribute("aria-keyshortcuts", keys);
      await userEvent.click(button);
    }
    // The reason is read by everyone, beside them.
    expect(screen.getByText(REASON)).toBeVisible();
    expect(client.calls).toEqual([]);
    // The bar that holds them: the grid around them is checked by estimate.dom.test.tsx, and the
    // first check of a file, on the whole grid, took longer than the test may last under load
    // (EP-02/L46).
    const bar = screen.getByRole("button", { name: "Annuler" }).parentElement;
    if (bar === null) {
      throw new Error("the command Undo stands in no bar");
    }
    expect(bar).toContainElement(screen.getByText(REASON));
    await expectAccessible(bar);
  });

  it("places them in the menu of a cell, opened by Shift+F10, with their shortcuts, unavailable and saying why", async () => {
    render(estimateGrid());
    const cell = focusLabel();
    await userEvent.keyboard("{Shift>}{F10}{/Shift}");
    const menu = cellMenu();
    const undo = within(menu).getByRole("menuitem", { name: /^Annuler/ });
    const redo = within(menu).getByRole("menuitem", { name: /^Rétablir/ });
    expect(undo).toHaveTextContent("Ctrl+Z");
    expect(redo).toHaveTextContent("Ctrl+Maj+Z");
    for (const item of [undo, redo]) {
      expect(item).toHaveAttribute("aria-disabled", "true");
      expect(item).toHaveAccessibleDescription(REASON);
    }
    // The menu open, the page beside it is hidden from a screen reader: the menu is what is read.
    await expectAccessible(menu);
    // Pressed, an entry does nothing: the menu stays open on the reason.
    await userEvent.click(undo);
    expect(cellMenu()).toHaveTextContent(REASON);
    // Escape closes it, and gives the focus back to the cell; nothing was asked of the server.
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).toBeNull();
    expect(cell).toHaveFocus();
    expect(client.calls).toEqual([]);
  });

  it("announces the menu on each cell by the key that opens it, where the grid offers one", () => {
    render(estimateGrid());
    const cells = screen.getByRole("treegrid").querySelectorAll("td[data-column]");
    expect(cells.length).toBeGreaterThan(0);
    // The label of a row that folds tells the keys of the folding after it.
    for (const cell of cells) {
      expect(cell).toHaveAttribute("aria-keyshortcuts", expect.stringMatching(/^Shift\+F10( |$)/));
    }
  });

  it("leaves the menu of the browser to the field of a cell being entered, whose entry it neither takes nor validates", async () => {
    render(estimateGrid());
    focusLabel();
    await userEvent.keyboard("{F2}");
    const field = screen.getByRole("textbox", { name: "Libellé" });
    await userEvent.type(field, " de câb");
    // A right click to paste, or the Menu key: nothing prevented, the browser opens its own.
    expect(fireEvent.contextMenu(field)).toBe(true);
    await userEvent.keyboard("{Shift>}{F10}{/Shift}");
    expect(screen.queryByRole("menu")).toBeNull();
    expect(field).toHaveFocus();
    expect(field).toHaveValue("Câblage des armoires de câb");
    expect(client.calls).toEqual([]);
  });

  it("opens the menu of a cell once for the key that opened it, whatever the browser sends besides", async () => {
    render(estimateGrid());
    const cell = focusLabel();
    await userEvent.keyboard("{Shift>}{F10}{/Shift}");
    const shown = cellMenu().parentElement?.getAttribute("style");
    // The native echo of the key, elsewhere: prevented, it moves nothing.
    expect(fireEvent.contextMenu(cell, { clientX: 300, clientY: 200 })).toBe(false);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(screen.getAllByRole("menu")).toHaveLength(1);
    expect(cellMenu().parentElement?.getAttribute("style")).toBe(shown);
  });

  it("opens the menu of a cell by a right click, and adds no stop to the order of tabulation", async () => {
    render(estimateGrid());
    const cell = focusLabel();
    await userEvent.pointer({ keys: "[MouseRight]", target: cell });
    // Undo and redo, after the folding of the row, the grid being a tree.
    expect(
      within(cellMenu())
        .getAllByRole("menuitem")
        .map((item) => item.textContent),
    ).toEqual(["Plier la ligne", "Tout déplier", "AnnulerCtrl+Z", "RétablirCtrl+Maj+Z"]);
    await userEvent.keyboard("{Escape}");
    // The grid stays one stop: its active cell, the only one in the order of tabulation.
    expect(screen.getByRole("treegrid").querySelectorAll('[tabindex="0"]')).toHaveLength(1);
  });

  it("takes Ctrl+Z and Ctrl+Shift+Z on the grid, and tells each unavailable", () => {
    render(estimateGrid());
    expect(told()).toBeNull();
    const cell = focusLabel();
    expect(press(cell)).toBe(false);
    expect(told()).toBe(TOLD_UNDO);
    expect(press(cell, true)).toBe(false);
    expect(told()).toBe(TOLD_REDO);
    // The same command again is told again, in a new node of the region.
    const before = toldNode();
    expect(press(cell, true)).toBe(false);
    const after = toldNode();
    expect(after).not.toBe(before);
    expect(after?.textContent).toBe(TOLD_REDO);
    // Neither opens the entry of the cell, nor asks anything of the server.
    expect(cell).toHaveFocus();
    expect(screen.queryByRole("textbox", { name: "Libellé" })).toBeNull();
    expect(client.calls).toEqual([]);
  });

  it("leaves Ctrl+Z to a field being entered — the editor of a cell, the search —, whose undo stays the browser's", async () => {
    render(estimateGrid());
    focusLabel();
    await userEvent.keyboard("{F2}");
    const field = screen.getByRole("textbox", { name: "Libellé" });
    await userEvent.type(field, " bis");
    expect(press(field)).toBe(true);
    expect(press(field, true)).toBe(true);
    expect(field).toHaveFocus();
    expect(field).toHaveValue("Câblage des armoires bis");
    await userEvent.keyboard("{Escape}");
    const search = screen.getByRole("searchbox");
    expect(press(search)).toBe(true);
    expect(told()).toBeNull();
  });

  it("takes the shortcut in the bar of the grid too, on the button Undo itself", () => {
    render(estimateGrid());
    const button = screen.getByRole("button", { name: "Annuler" });
    button.focus();
    expect(press(button)).toBe(false);
    expect(told()).toBe(TOLD_UNDO);
  });

  it("places them in the grid of the planning of a revision that may be planned", () => {
    render(
      inLanguage(
        <PlanningGrid
          nodes={example("nodes_planning") as NodeList}
          structure={STRUCTURE}
          filters={{}}
          query={NO_QUERY}
          preferences={undefined}
          undoable
        />,
      ),
    );
    expect(screen.getByRole("button", { name: "Annuler" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(press(focusLabel())).toBe(false);
    expect(told()).toBe(TOLD_UNDO);
  });

  it("is named and told in English too", async () => {
    render(estimateGrid(true, "en"));
    expect(screen.getByRole("button", { name: "Undo" })).toHaveAccessibleDescription(
      "Unavailable until the server keeps the history of the entries.",
    );
    const cell = focusLabel();
    await userEvent.keyboard("{Shift>}{F10}{/Shift}");
    const menu = screen.getByRole("menu", { name: "Cell menu" });
    expect(within(menu).getByRole("menuitem", { name: /^Redo/ })).toHaveTextContent("Ctrl+Shift+Z");
    await userEvent.keyboard("{Escape}");
    press(cell, true);
    expect(told()).toBe(
      "Redo is unavailable: the server does not keep the history of the entries yet.",
    );
  });
});

describe("what no command undoes", () => {
  it("offers no undo of a marking: the grid of a marked revision, which takes no entry, places neither command nor takes the shortcut [WF-IHM-0110-A]", async () => {
    render(estimateGrid(false));
    expect(screen.queryByRole("button", { name: "Annuler" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Rétablir" })).toBeNull();
    const cell = focusLabel();
    expect(press(cell)).toBe(true);
    expect(screen.queryByRole("status")).toBeNull();
    // The menu of the cell holds the folding of its row, a tree grid's, and neither command.
    await userEvent.pointer({ keys: "[MouseRight]", target: cell });
    expect(
      within(screen.getByRole("menu")).queryByRole("menuitem", { name: /Annuler|Rétablir/ }),
    ).toBeNull();
    await userEvent.keyboard("{Escape}");
    cell.focus();
    await userEvent.keyboard("{Shift>}{F10}{/Shift}");
    const menu = screen.getByRole("menu", { name: "Menu de la cellule" });
    expect(within(menu).getByRole("menuitem", { name: "Plier la ligne" })).toBeInTheDocument();
    expect(within(menu).queryByRole("menuitem", { name: /Annuler|Rétablir/ })).toBeNull();
  });

  it("offers no undo of the exclusion of a line of actual cost: its grid places neither command nor takes the shortcut [WF-IHM-0110-A]", async () => {
    const list = example("actual_costs") as {
      readonly items: components["schemas"]["ActualCostLine"][];
      readonly totals: Parameters<typeof CostsGrid>[0]["costs"]["totals"];
      readonly meta: { readonly passthrough_columns: string[] };
    };
    render(
      inLanguage(
        <CostsGrid
          costs={{
            items: list.items.map(costRow),
            totals: list.totals,
            kept: list.meta.passthrough_columns,
          }}
          query={{ sort: undefined, search: undefined }}
          preferences={undefined}
        />,
      ),
    );
    const grid = screen.getByRole("grid", { name: "Coûts réels" });
    expect(screen.queryByRole("button", { name: "Annuler" })).toBeNull();
    const cell = grid.querySelector("td");
    if (cell === null) {
      throw new Error("no cell in the grid of the actual costs");
    }
    expect(press(cell)).toBe(true);
    await userEvent.pointer({ keys: "[MouseRight]", target: cell });
    expect(screen.queryByRole("menu")).toBeNull();
    expect(screen.queryByRole("status")).toBeNull();
  });
});
