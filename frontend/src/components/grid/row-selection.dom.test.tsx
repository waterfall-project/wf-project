// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, createEvent, fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { forgetMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";

import type { NodeList, NodeSortColumn } from "./nodes";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";

// The selection of contiguous rows by their handles, and their moves — by the keys, by the menu of
// a cell and by a drag (US-0460/L5) —, through the grid of the planning: rows 1 to 5 of the example
// are the five sub-tasks of « Études », ranks 1 to 5, the fourth a milestone.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/planning",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined };
const MOVE =
  "POST /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/move" as const;
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const planning = example("nodes_planning") as NodeList;
const id = (index: number) => planning.items[index]?.node_id;
const [STUDIES, DETAIL, DESKS, REVIEW, MILESTONE] = [0, 1, 2, 3, 4];

/** Serve the fake back, and give it back to read its calls. */
function serve(): FakeClient {
  const client = fakeClient({ [MOVE]: "nodes_moved" });
  server.client = client;
  return client;
}

/** The grid of the planning, its tasks entered, over the nodes given. */
function planningGrid(nodes: NodeList = planning, editable = true) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PlanningGrid
        nodes={nodes}
        structure={STRUCTURE}
        structureVersion={1}
        filters={{ kinds: ["task"] }}
        query={NO_QUERY}
        preferences={undefined}
        undoable={editable}
        editable={editable}
      />
    </NextIntlClientProvider>
  );
}

/** A cell of the row at an index, by its column. */
function cellAt(row: number, column: string): HTMLElement {
  const found = screen
    .getByRole("treegrid")
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="${column}"]`);
  if (found === null) {
    throw new Error(`no cell ${column} in the row ${row.toString()}`);
  }
  return found;
}
const handleAt = (row: number) => cellAt(row, "row_number");
const rowAt = (row: number) => handleAt(row).closest("tr");

/** The rows the grid says are selected, by their index. */
function selectedRows(): number[] {
  return planning.items.flatMap((_, index) =>
    rowAt(index)?.getAttribute("aria-selected") === "true" ? [index] : [],
  );
}

/** Give a cell the focus, as the arrows of the grid would. */
async function focus(cell: HTMLElement) {
  await act(async () => {
    cell.focus();
    await Promise.resolve();
  });
}

/** The moves the fake back received. */
function moved(client: FakeClient): unknown[] {
  return client.calls.filter((call) => call.route === MOVE).map((call) => call.body);
}

/** What a drag carries, as far as the grid reads and writes it. */
function dataTransfer() {
  return { setData: vi.fn(), effectAllowed: "", dropEffect: "" };
}

/** Fire an event of a drag on an element, carrying what it carries, at a height. */
function drag(
  type: "dragStart" | "dragOver" | "drop" | "dragEnd",
  target: HTMLElement,
  carried: ReturnType<typeof dataTransfer>,
  clientY = 0,
): void {
  // The event of a drag in the document of the tests carries neither what is dragged nor where.
  const event = createEvent[type](target);
  Object.defineProperty(event, "dataTransfer", { value: carried });
  Object.defineProperty(event, "clientY", { value: clientY });
  fireEvent(target, event);
}

beforeEach(() => {
  window.sessionStorage.clear();
  forgetMessages();
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  router.refresh.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the selection of rows by their handles", () => {
  it("selects a row by a click on its handle, extends it by Shift and a click, and says how many", () => {
    serve();
    render(planningGrid());
    expect(screen.getByRole("treegrid")).toHaveAttribute("aria-multiselectable", "true");
    expect(selectedRows()).toEqual([]);
    expect(rowAt(DESKS)).toHaveAttribute("aria-selected", "false");
    fireEvent.click(handleAt(DESKS));
    expect(selectedRows()).toEqual([DESKS]);
    fireEvent.click(handleAt(MILESTONE), { shiftKey: true });
    expect(selectedRows()).toEqual([DESKS, REVIEW, MILESTONE]);
    expect(screen.getByText("3 lignes sélectionnées")).toHaveAttribute("role", "status");
    // A click without Shift starts it anew; a click on another cell leaves it.
    fireEvent.click(handleAt(DETAIL));
    fireEvent.click(cellAt(REVIEW, "label"));
    expect(selectedRows()).toEqual([DETAIL]);
  });

  it("selects from the keyboard on the column of the handles: Space, Shift and the arrows as the active cell moves, Escape lifts it [WF-IHM-0100-A]", async () => {
    // Toute action de l'interface est atteignable au clavier : the selection a click makes.
    serve();
    render(planningGrid());
    await focus(handleAt(DESKS));
    await userEvent.keyboard(" ");
    expect(selectedRows()).toEqual([DESKS]);
    await userEvent.keyboard("{Shift>}{ArrowDown}{ArrowDown}{/Shift}");
    expect(selectedRows()).toEqual([DESKS, REVIEW, MILESTONE]);
    expect(handleAt(MILESTONE)).toHaveFocus();
    await userEvent.keyboard("{Shift>}{ArrowUp}{/Shift}");
    expect(selectedRows()).toEqual([DESKS, REVIEW]);
    await userEvent.keyboard("{Escape}");
    expect(selectedRows()).toEqual([]);
  });

  it("names each handle by the number of its row, describes how it selects and moves, and passes axe [WF-IHM-0100-A]", async () => {
    serve();
    const { container } = render(planningGrid());
    const handle = handleAt(DESKS);
    expect(handle).toHaveAccessibleName("4 — poignée de la ligne");
    expect(handle).toHaveAccessibleDescription(/Alt\+Maj\+↑ et Alt\+Maj\+↓ d’un rang/);
    expect(handle.getAttribute("aria-keyshortcuts")).toContain("Shift+ArrowDown");
    expect(handle).toHaveAttribute("draggable", "true");
    await expectAccessible(container);
  });

  it("offers no handle and selects nothing where the grid moves nothing", () => {
    serve();
    render(planningGrid(planning, false));
    expect(screen.getByRole("treegrid")).not.toHaveAttribute("aria-multiselectable");
    fireEvent.click(handleAt(DESKS));
    expect(rowAt(DESKS)).not.toHaveAttribute("aria-selected");
    expect(handleAt(DESKS)).not.toHaveAttribute("draggable");
  });

  it("keeps the active cell on its row, selected, when a reading anew moves it", async () => {
    serve();
    const view = render(planningGrid());
    await focus(handleAt(DESKS));
    await userEvent.keyboard(" ");
    const [first, second, desks, review, ...rest] = planning.items;
    const reordered = { ...planning, items: [first, second, review, desks, ...rest] };
    view.rerender(planningGrid(reordered as NodeList));
    expect(handleAt(REVIEW)).toHaveAttribute("tabindex", "0");
    expect(rowAt(REVIEW)).toHaveAttribute("aria-selected", "true");
  });
});

describe("the moves of a selection", () => {
  it("indents the group of tasks selected under the task above the first one, from the keys [WF-PLA-0080-A]", async () => {
    // L'indentation d'un groupe de tâches déplace le groupe entier sous la tâche précédente : the
    // selection of « Pupitres opérateurs » and « Revue de conception » goes under « Études de détail ».
    const client = serve();
    render(planningGrid());
    fireEvent.click(handleAt(DESKS));
    fireEvent.click(handleAt(REVIEW), { shiftKey: true });
    await focus(cellAt(REVIEW, "label"));
    await userEvent.keyboard("{Alt>}{Shift>}{ArrowRight}{/Shift}{/Alt}");
    expect(moved(client)).toEqual([
      { node_ids: [id(DESKS), id(REVIEW)], parent_id: id(DETAIL), lock_version: 1 },
    ]);
    expect(
      await screen.findByText("« Pupitres opérateurs » et la ligne suivante indentées."),
    ).toBeVisible();
    expect(router.refresh).toHaveBeenCalledTimes(1);
  });

  it("moves the selection down after the sibling below it, from the menu of a cell, and up by the sibling above it going after it", async () => {
    const client = serve();
    render(planningGrid());
    fireEvent.click(handleAt(DESKS));
    fireEvent.click(handleAt(REVIEW), { shiftKey: true });
    fireEvent.contextMenu(cellAt(DESKS, "label"), { clientX: 300, clientY: 200 });
    const menu = await screen.findByRole("menu", { name: "Menu de la cellule" });
    const items = within(menu)
      .getAllByRole("menuitem")
      .map((item) => item.textContent);
    // The deletion is that of a row alone: not offered on a selection of several.
    expect(items).toEqual(expect.arrayContaining(["Indenter", "Monter", "Descendre"]));
    expect(items).not.toContain("Supprimer");
    expect(within(menu).getByRole("menuitem", { name: "Descendre" })).toHaveAttribute(
      "aria-keyshortcuts",
      "Alt+Shift+ArrowDown",
    );
    await userEvent.click(within(menu).getByRole("menuitem", { name: "Descendre" }));
    await screen.findByText("« Pupitres opérateurs » et la ligne suivante descendues d’un rang.");
    await focus(cellAt(DESKS, "label"));
    await userEvent.keyboard("{Alt>}{Shift>}{ArrowUp}{/Shift}{/Alt}");
    expect(moved(client)).toEqual([
      {
        node_ids: [id(DESKS), id(REVIEW)],
        parent_id: id(STUDIES),
        after_node_id: id(MILESTONE),
        lock_version: 1,
      },
      {
        node_ids: [id(DETAIL)],
        parent_id: id(STUDIES),
        after_node_id: id(REVIEW),
        lock_version: 2,
      },
    ]);
  });

  it("acts on the row alone from a row out of the selection", async () => {
    const client = serve();
    render(planningGrid());
    fireEvent.click(handleAt(DESKS));
    fireEvent.click(handleAt(REVIEW), { shiftKey: true });
    await focus(cellAt(MILESTONE, "label"));
    await userEvent.keyboard("{Alt>}{Shift>}{ArrowUp}{/Shift}{/Alt}");
    expect(moved(client)).toEqual([
      {
        node_ids: [id(REVIEW)],
        parent_id: id(STUDIES),
        after_node_id: id(MILESTONE),
        lock_version: 1,
      },
    ]);
  });
});

describe("the drag of rows by their handles", () => {
  /** Drag the handle of a row over the cell of another, at a height of its row of 28 points. */
  function dragOver(from: number, over: number, offset: number) {
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue(
      DOMRect.fromRect({ x: 0, y: 100, width: 100, height: 28 }),
    );
    const carried = dataTransfer();
    drag("dragStart", handleAt(from), carried);
    const target = cellAt(over, "label");
    drag("dragOver", target, carried, 100 + offset);
    return { carried, target };
  }

  it("drops the selection under a row, its middle shaded, and moves it there, last", async () => {
    const client = serve();
    render(planningGrid());
    fireEvent.click(handleAt(DESKS));
    fireEvent.click(handleAt(REVIEW), { shiftKey: true });
    const { carried, target } = dragOver(DESKS, DETAIL, 14);
    expect(carried.effectAllowed).toBe("move");
    expect(rowAt(DETAIL)).toHaveAttribute("data-drop", "into");
    drag("drop", target, carried, 114);
    expect(rowAt(DETAIL)).not.toHaveAttribute("data-drop");
    expect(
      await screen.findByText("« Pupitres opérateurs » et la ligne suivante déplacées."),
    ).toBeVisible();
    expect(moved(client)).toEqual([
      { node_ids: [id(DESKS), id(REVIEW)], parent_id: id(DETAIL), lock_version: 1 },
    ]);
  });

  it("drops a row not selected alone between two rows, before the lower one, after the sibling above it", async () => {
    const client = serve();
    render(planningGrid());
    // The lower quarter of the milestone: between it and « Dossier de conception ».
    const { carried, target } = dragOver(DETAIL, MILESTONE, 25);
    expect(selectedRows()).toEqual([DETAIL]);
    expect(rowAt(MILESTONE + 1)).toHaveAttribute("data-drop", "before");
    drag("drop", target, carried, 125);
    await screen.findByText("« Études de détail » déplacée.");
    expect(moved(client)).toEqual([
      {
        node_ids: [id(DETAIL)],
        parent_id: id(STUDIES),
        after_node_id: id(MILESTONE),
        lock_version: 1,
      },
    ]);
  });

  it("shows no indicator and drops nothing where the place is refused: under a milestone, beside the rows dragged", () => {
    const client = serve();
    render(planningGrid());
    const under = dragOver(DESKS, MILESTONE, 14);
    expect(rowAt(MILESTONE)).not.toHaveAttribute("data-drop");
    drag("drop", under.target, under.carried, 114);
    const beside = dragOver(DESKS, DESKS, 2);
    expect(rowAt(DESKS)).not.toHaveAttribute("data-drop");
    drag("drop", beside.target, beside.carried, 102);
    drag("dragEnd", handleAt(DESKS), beside.carried);
    expect(moved(client)).toEqual([]);
  });
});
