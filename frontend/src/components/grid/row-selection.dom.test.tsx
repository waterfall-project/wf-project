// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { forgetMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeClient, fakeClient, held } from "@/test/fixtures";
import { holdReading, Reading, releaseReading } from "@/test/held-reading";

import type { NodeList, NodeSortColumn } from "./nodes";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";

// The selection of contiguous rows by their handles, and their moves — by the keys and by the menu
// of a cell (US-0460/L5) —, through the grid of the planning: rows 1 to 5 of the example
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
const [STUDIES, DETAIL, DESKS, REVIEW, MILESTONE, FILE] = [0, 1, 2, 3, 4, 5];
const movedAnswer = example("nodes_moved") as { structure_lock_version: number };
/** The counter of the structure the first move answers, which the next move sends. */
const MOVED_VERSION = movedAnswer.structure_lock_version;

/** Serve the fake back, its answers held until `hold` settles if one is given. */
function serve(hold?: Promise<unknown>): FakeClient {
  const client = fakeClient({ [MOVE]: "nodes_moved" }, { hold: () => hold });
  server.client = client;
  return client;
}

/**
 * The example read anew: the sub-tasks of « Études », by their index, in the order given and ranked
 * again, under the parent given or under « Études ».
 */
function readAnew(
  order: readonly number[],
  parents: Readonly<Record<number, number>> = {},
): NodeList {
  const children = order.map((index) => {
    const node = planning.items[index];
    const parent = parents[index] ?? STUDIES;
    const siblings = order.filter((each) => (parents[each] ?? STUDIES) === parent);
    return {
      ...node,
      parent_id: id(parent),
      level: parent === STUDIES ? node?.level : (node?.level ?? 0) + 1,
      position: siblings.indexOf(index) + 1,
    };
  });
  return { ...planning, items: [planning.items[STUDIES], ...children] } as NodeList;
}

/** Read the grid anew, as Next commits the reading held: the rows and its end in one commit. */
async function reread(view: ReturnType<typeof render>, nodes: NodeList) {
  await act(async () => {
    view.rerender(planningGrid(nodes));
    releaseReading();
    await Promise.resolve();
  });
}

const UP = "{Alt>}{Shift>}{ArrowUp}{/Shift}{/Alt}";
const DOWN = "{Alt>}{Shift>}{ArrowDown}{/Shift}{/Alt}";

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

/** Press keys while a reading anew suspends the grid, awaited as it is. */
async function keyDuringReading(keys: string) {
  await act(async () => {
    await userEvent.keyboard(keys);
  });
}

/** The moves the fake back received. */
function moved(client: FakeClient): unknown[] {
  return client.calls.filter((call) => call.route === MOVE).map((call) => call.body);
}

beforeEach(() => {
  window.sessionStorage.clear();
  forgetMessages();
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  router.refresh.mockReset();
});

afterEach(() => {
  releaseReading();
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
    // Chaque écran se parcourt entièrement au clavier et le focus reste visible : the selection a
    // click makes is made from the keys, on the handles, the focus moving with it and ringed.
    serve();
    render(planningGrid());
    await focus(handleAt(DESKS));
    await userEvent.keyboard(" ");
    expect(selectedRows()).toEqual([DESKS]);
    await userEvent.keyboard("{Shift>}{ArrowDown}{ArrowDown}{/Shift}");
    expect(selectedRows()).toEqual([DESKS, REVIEW, MILESTONE]);
    expect(handleAt(MILESTONE)).toHaveFocus();
    expect(handleAt(MILESTONE)).toHaveClass("focus-visible:ring-2");
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
    await expectAccessible(container);
  });

  it("offers no handle and selects nothing where the grid moves nothing", () => {
    serve();
    render(planningGrid(planning, false));
    expect(screen.getByRole("treegrid")).not.toHaveAttribute("aria-multiselectable");
    fireEvent.click(handleAt(DESKS));
    expect(rowAt(DESKS)).not.toHaveAttribute("aria-selected");
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

  it("lifts a selection whose end a reading anew no longer shows, rather than bring it back with it", () => {
    serve();
    const view = render(planningGrid());
    fireEvent.click(handleAt(DESKS));
    fireEvent.click(handleAt(REVIEW), { shiftKey: true });
    // A filter leaves the anchor out, and is lifted.
    view.rerender(
      planningGrid({ ...planning, items: planning.items.filter((_, index) => index !== DESKS) }),
    );
    view.rerender(planningGrid());
    expect(selectedRows()).toEqual([]);
    expect(screen.queryByText(/sélectionnée/)).toBeNull();
  });

  it("keeps the shade of a computed cell in a row selected", () => {
    serve();
    render(planningGrid());
    fireEvent.click(handleAt(STUDIES));
    const computed = rowAt(STUDIES)?.querySelector('td[aria-haspopup="dialog"]');
    expect(computed).toHaveClass("bg-muted");
    expect(rowAt(STUDIES)?.className).toContain(":not([aria-haspopup=dialog])");
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

  it("keeps the group indented selected through the reading anew that shows it under the task above [WF-PLA-0080-A]", async () => {
    // L'indentation d'un groupe de tâches déplace le groupe entier sous la tâche précédente : read
    // anew, « Pupitres opérateurs » and « Revue de conception » stand under « Études de détail »,
    // and are still the rows selected.
    holdReading(router.refresh);
    serve();
    const view = render(planningGrid(), { wrapper: Reading });
    fireEvent.click(handleAt(DESKS));
    fireEvent.click(handleAt(REVIEW), { shiftKey: true });
    await focus(cellAt(REVIEW, "label"));
    await userEvent.keyboard("{Alt>}{Shift>}{ArrowRight}{/Shift}{/Alt}");
    await screen.findByText("« Pupitres opérateurs » et la ligne suivante indentées.");
    await reread(
      view,
      readAnew([DETAIL, DESKS, REVIEW, MILESTONE, FILE], { [DESKS]: DETAIL, [REVIEW]: DETAIL }),
    );
    expect(rowAt(DESKS)).toHaveAttribute("aria-level", "3");
    expect(rowAt(REVIEW)).toHaveAttribute("aria-level", "3");
    expect(selectedRows()).toEqual([DESKS, REVIEW]);
    expect(cellAt(REVIEW, "label")).toHaveFocus();
  });

  it("moves the selection down after the sibling below it, from the menu of a cell, and up by the sibling above it going after it", async () => {
    holdReading(router.refresh);
    const client = serve();
    const view = render(planningGrid(), { wrapper: Reading });
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
    // Read anew, the selection is below « Réception des études », at the fourth and the fifth rows,
    // and the active cell with it: the keys go on from there, with no click.
    await reread(view, readAnew([DETAIL, MILESTONE, DESKS, REVIEW, FILE]));
    expect(selectedRows()).toEqual([3, 4]);
    await userEvent.keyboard(UP);
    expect(moved(client)).toEqual([
      {
        node_ids: [id(DESKS), id(REVIEW)],
        parent_id: id(STUDIES),
        after_node_id: id(MILESTONE),
        lock_version: 1,
      },
      {
        node_ids: [id(MILESTONE)],
        parent_id: id(STUDIES),
        after_node_id: id(REVIEW),
        lock_version: MOVED_VERSION,
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

describe("the moves through the reading anew they ask", () => {
  it("holds the next move until the reading anew is over, then starts it from the neighbours read", async () => {
    // A B C D, C up, then down before the reading: sent at once, the second would go from the
    // neighbours of before with the version already moved on, and leave A B D C.
    holdReading(router.refresh);
    const client = serve();
    const view = render(planningGrid(), { wrapper: Reading });
    await focus(cellAt(REVIEW, "label"));
    await userEvent.keyboard(UP);
    await screen.findByText("« Revue de conception » montée d’un rang.");
    await userEvent.keyboard(DOWN);
    expect(moved(client)).toHaveLength(1);
    // The key is taken, and the active cell stays where it was; the grid says it is busy.
    expect(cellAt(REVIEW, "label")).toHaveFocus();
    expect(screen.getByRole("treegrid")).toHaveAttribute("aria-busy", "true");
    await reread(view, readAnew([DETAIL, REVIEW, DESKS, MILESTONE, FILE]));
    expect(screen.getByRole("treegrid")).toHaveAttribute("aria-busy", "false");
    await userEvent.keyboard(DOWN);
    expect(moved(client)).toEqual([
      { node_ids: [id(DESKS)], parent_id: id(STUDIES), after_node_id: id(REVIEW), lock_version: 1 },
      {
        node_ids: [id(REVIEW)],
        parent_id: id(STUDIES),
        after_node_id: id(DESKS),
        lock_version: MOVED_VERSION,
      },
    ]);
  });

  it("holds the menu of a cell while the reading anew is under way", async () => {
    holdReading(router.refresh);
    serve();
    render(planningGrid(), { wrapper: Reading });
    await focus(cellAt(REVIEW, "label"));
    await userEvent.keyboard(UP);
    await screen.findByText("« Revue de conception » montée d’un rang.");
    // The reading suspends: the opening is awaited as it is.
    await act(async () => {
      fireEvent.contextMenu(cellAt(DESKS, "label"), { clientX: 300, clientY: 200 });
      await Promise.resolve();
    });
    const menu = await screen.findByRole("menu", { name: "Menu de la cellule" });
    expect(within(menu).getByRole("menuitem", { name: "Descendre" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });

  it("keeps the active cell and the focus on a row moved out of the selection, which the next move takes [WF-IHM-0100-A]", async () => {
    // Chaque écran se parcourt entièrement au clavier et le focus reste visible : the row moved up
    // keeps the focus once read anew, and moves on from the keys alone.
    holdReading(router.refresh);
    const client = serve();
    const view = render(planningGrid(), { wrapper: Reading });
    await focus(cellAt(MILESTONE, "label"));
    await userEvent.keyboard(UP);
    await screen.findByText("« Réception des études » montée d’un rang.");
    // « Réception des études » is now the fourth row, where « Revue de conception » was.
    await reread(view, readAnew([DETAIL, DESKS, MILESTONE, REVIEW, FILE]));
    expect(cellAt(REVIEW, "label")).toHaveAttribute("tabindex", "0");
    expect(cellAt(REVIEW, "label")).toHaveTextContent("Réception des études");
    expect(cellAt(REVIEW, "label")).toHaveFocus();
    await userEvent.keyboard(UP);
    expect(moved(client)).toEqual([
      {
        node_ids: [id(REVIEW)],
        parent_id: id(STUDIES),
        after_node_id: id(MILESTONE),
        lock_version: 1,
      },
      {
        node_ids: [id(DESKS)],
        parent_id: id(STUDIES),
        after_node_id: id(MILESTONE),
        lock_version: MOVED_VERSION,
      },
    ]);
  });

  it("leaves the active cell and the focus on the row the arrows went to while the reading anew was under way [WF-IHM-0100-A]", async () => {
    // Chaque écran se parcourt entièrement au clavier et le focus reste visible : « Revue de
    // conception » moved up, the user goes on down with the arrows before the reading comes, and
    // the reading does not take them back to the row moved.
    holdReading(router.refresh);
    serve();
    const view = render(planningGrid(), { wrapper: Reading });
    await focus(cellAt(REVIEW, "label"));
    await userEvent.keyboard(UP);
    await screen.findByText("« Revue de conception » montée d’un rang.");
    await keyDuringReading("{ArrowDown}");
    expect(cellAt(MILESTONE, "label")).toHaveFocus();
    await reread(view, readAnew([DETAIL, REVIEW, DESKS, MILESTONE, FILE]));
    expect(cellAt(MILESTONE, "label")).toHaveAttribute("tabindex", "0");
    expect(cellAt(MILESTONE, "label")).toHaveFocus();
    expect(cellAt(DESKS, "label")).toHaveAttribute("tabindex", "-1");
  });

  it("takes Alt, Shift and an arrow a move is not offered for, and leaves the active cell in place", async () => {
    const client = serve();
    render(planningGrid());
    await focus(cellAt(DETAIL, "label"));
    await userEvent.keyboard(UP);
    expect(cellAt(DETAIL, "label")).toHaveAttribute("tabindex", "0");
    expect(cellAt(DETAIL, "label")).toHaveFocus();
    expect(moved(client)).toEqual([]);
  });

  it("moves the rows selected when the gesture was asked, though the selection changed while the write was under way", async () => {
    const hold = held();
    holdReading(router.refresh);
    const client = serve(hold.until);
    const view = render(planningGrid(), { wrapper: Reading });
    fireEvent.click(handleAt(DESKS));
    fireEvent.click(handleAt(REVIEW), { shiftKey: true });
    await focus(cellAt(REVIEW, "label"));
    await userEvent.keyboard(UP);
    fireEvent.click(handleAt(FILE));
    await act(async () => {
      hold.release();
      await Promise.resolve();
    });
    await screen.findByText("« Pupitres opérateurs » et la ligne suivante montées d’un rang.");
    expect(moved(client)).toEqual([
      {
        node_ids: [id(DETAIL)],
        parent_id: id(STUDIES),
        after_node_id: id(REVIEW),
        lock_version: 1,
      },
    ]);
    // The selection is the one made since, through the reading anew too.
    expect(selectedRows()).toEqual([FILE]);
    await reread(view, readAnew([DESKS, REVIEW, DETAIL, MILESTONE, FILE]));
    expect(selectedRows()).toEqual([FILE]);
  });
});
