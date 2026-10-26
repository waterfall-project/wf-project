// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { findOffer } from "@/components/commands/offer";
import type { Revision } from "@/components/context/read-only";
import { forgetMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeAnswers, type FakeClient, fakeClient, held } from "@/test/fixtures";
import { APPLY, BLOCK, cell, copied, FIRST, pasteOn, PREVIEW, renderGrid } from "@/test/paste-grid";

import type { NodeList, NodeSortColumn } from "./nodes";
import { breakdownItems, type WorkBreakdownReading } from "./planning-attachment";
import { PLANNING_GRID } from "./planning";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";

// The grid busy with any of its writes — a gesture, a cell entered, a paste applied —, and what an
// answer does once the grid shows another structure (decision of the author of 2026-10-21, #1224).
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/planning",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined, size: undefined };
const NODES = "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes";
const MOVE = `POST ${NODES}/move` as const;
const TASK = `PATCH ${NODES}/{node_id}/task` as const;
const PREDECESSORS = `PUT ${NODES}/{node_id}/predecessors` as const;
const SKELETON = "POST /projects/{project_id}/revisions/{revision_id}/skeleton";
// The main structure of the current revision of the witness project, and the amendment 2 prepared
// beside it, as the examples name them.
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const AMENDMENT = { ...STRUCTURE, structure_id: "01926f3a-7c00-7000-8000-000000000203" };
const VERSION = 1;
const nested = example("nodes_nested") as NodeList;
const breakdown = breakdownItems(example("work_breakdown") as WorkBreakdownReading);
const MOUNTING = nested.items.findIndex(
  (node) => node.task?.label === "Montage des armoires sur site",
);
const COMMISSIONING = nested.items.findIndex((node) => node.task?.label === "Mise en service");
// The nested tasks read anew without « Réception usine », the row just above the mounting: the
// mounting is one row up.
const RECEPTION = nested.items.findIndex((node) => node.task?.label === "Réception usine");
const withoutReception: NodeList = {
  ...nested,
  items: nested.items.filter((_, index) => index !== RECEPTION),
};
const empty = example("nodes_empty") as NodeList;
// The skeleton the revision opened today offers, its main structure without a task.
const skeleton = findOffer(
  (example("revision_without_tasks") as Revision).available_commands,
  "generate_skeleton",
);

// The columns these tests write in — the label, the attachment, the predecessors —, the others
// hidden, the Gantt among them: each indentation renders the grid anew two or three times, and the
// whole grid, its Gantt drawn, took twice as long, near a second for the test of a late answer on the
// workstation, past its five seconds on a runner of the chain under coverage (#1474).
const WRITTEN = new Set(["label", "work_breakdown", "predecessors"]);
const PREFERENCES = {
  hidden_columns: PLANNING_GRID.columns
    .map((column) => column.key)
    .filter((key) => !WRITTEN.has(key)),
};

/** Serve the fake back, the calls of a route held until `hold` settles, and give it back. */
function serve(answers: FakeAnswers, held?: { route: string; until: Promise<unknown> }) {
  const client = fakeClient(answers, {
    hold: (route) => (route === held?.route ? held.until : undefined),
  });
  server.client = client;
  return client;
}

/**
 * The grid of the planning of tasks — the nested ones unless told — on a structure, entered, its
 * attachment too, and the skeleton when it is offered; only the columns written are shown.
 */
function grid(
  structure = STRUCTURE,
  { nodes = nested, offer }: { readonly nodes?: NodeList; readonly offer?: typeof skeleton } = {},
) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PlanningGrid
        nodes={nodes}
        structure={structure}
        structureVersion={VERSION}
        filters={{ kinds: ["task"] }}
        query={NO_QUERY}
        preferences={PREFERENCES}
        undoable
        editable
        breakdown={breakdown}
        skeleton={offer}
      />
    </NextIntlClientProvider>
  );
}

/** The cell of a row of the grid, by its index, and of a column, by its key. */
function cellAt(row: number, column: string): HTMLElement {
  const found = screen
    .getByRole("treegrid")
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="${column}"]`);
  if (found === null) {
    throw new Error(`no cell ${column} in the row ${row.toString()}`);
  }
  return found;
}

/** Make a cell the active one, as a click does. */
async function activate(target: HTMLElement) {
  await act(async () => {
    target.focus();
    await Promise.resolve();
  });
}

/** Indent the task of a row from the keyboard, as Alt+Shift+Right does. */
async function indent(row: number) {
  await activate(cellAt(row, "label"));
  await userEvent.keyboard("{Alt>}{Shift>}{ArrowRight}{/Shift}{/Alt}");
}

/** The moves the fake back received, as the grid sent them. */
function moves(client: FakeClient): unknown[] {
  return client.calls.filter((call) => call.route === MOVE).map((call) => call.body);
}

beforeEach(async () => {
  // The test before may end with a menu open: its unmount, at the cleanup, leaves a timer of the
  // focus scope of Radix, which gives the focus back to the page when it fires. Let it fire before
  // the test begins, else it takes the focus from the first cell this one activates (#1224).
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
  window.sessionStorage.clear();
  forgetMessages();
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  router.refresh.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("a grid busy with any of its writes", () => {
  it("holds the gestures while a cell written is under way, and moves with the version it reached once answered (#1224)", async () => {
    // The attachment of the mounting under way: the indentation pressed meanwhile would leave with
    // the version the answer is about to move on, and be refused.
    const hold = held();
    const client = serve(
      { [TASK]: "task_attached", [MOVE]: "nodes_indented" },
      { route: TASK, until: hold.until },
    );
    render(grid());
    await activate(cellAt(MOUNTING, "work_breakdown"));
    await userEvent.keyboard("P{Enter}");
    const table = screen.getByRole("treegrid");
    await vi.waitFor(() => {
      expect(table).toHaveAttribute("aria-busy", "true");
    });
    await indent(MOUNTING);
    expect(moves(client)).toEqual([]);
    fireEvent.contextMenu(cellAt(MOUNTING, "label"), { clientX: 300, clientY: 200 });
    const menu = await screen.findByRole("menu", { name: "Menu de la cellule" });
    expect(within(menu).getByRole("menuitem", { name: "Indenter" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    await userEvent.keyboard("{Escape}");
    await act(async () => {
      hold.release();
      await hold.until;
    });
    await vi.waitFor(() => {
      expect(table).toHaveAttribute("aria-busy", "false");
    });
    await indent(MOUNTING);
    await screen.findByText(/indentée\.$/);
    expect(moves(client)).toMatchObject([{ lock_version: 2 }]);
  });

  it("holds the gestures while the predecessors entered are under way, and moves with the version they reached once answered (#1224)", async () => {
    // The links of the mounting under way: the indentation pressed meanwhile would leave with the
    // version the answer is about to move on, and be refused.
    const hold = held();
    const client = serve(
      { [PREDECESSORS]: "predecessor_set", [MOVE]: "nodes_indented" },
      { route: PREDECESSORS, until: hold.until },
    );
    render(grid());
    await activate(cellAt(MOUNTING, "predecessors"));
    await userEvent.keyboard("{F2}");
    const field = within(screen.getByRole("treegrid")).getByRole("textbox");
    await userEvent.clear(field);
    await userEvent.type(field, "19FD+2 j{Enter}");
    const table = screen.getByRole("treegrid");
    await vi.waitFor(() => {
      expect(table).toHaveAttribute("aria-busy", "true");
    });
    await indent(MOUNTING);
    expect(moves(client)).toEqual([]);
    await act(async () => {
      hold.release();
      await hold.until;
    });
    await vi.waitFor(() => {
      expect(table).toHaveAttribute("aria-busy", "false");
    });
    // The answer is that of the witness at full size: the mounting in it is the first of its
    // siblings, so that the gesture is made on the task after it, « Mise en service ».
    await indent(COMMISSIONING);
    await screen.findByText(/indentée\.$/);
    expect(moves(client)).toMatchObject([{ lock_version: 2 }]);
  });

  it("holds the gestures while the skeleton generated is under way (#1224)", async () => {
    // The skeleton moves the structure on: a first task inserted meanwhile would leave with the
    // version its answer is about to move on, and be refused.
    const hold = held();
    serve(
      { [SKELETON]: { example: "skeleton_generated", status: 201 } },
      { route: SKELETON, until: hold.until },
    );
    render(grid(STRUCTURE, { nodes: empty, offer: skeleton }));
    await userEvent.click(
      screen.getByRole("button", { name: "Engendrer le squelette de planning" }),
    );
    const table = screen.getByRole("treegrid");
    await vi.waitFor(() => {
      expect(table).toHaveAttribute("aria-busy", "true");
    });
    const first = screen.getByRole("button", { name: "Insérer une tâche" });
    expect(first).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(first);
    expect(screen.queryByRole("dialog")).toBeNull();
    await act(async () => {
      hold.release();
      await hold.until;
    });
    await vi.waitFor(() => {
      expect(table).toHaveAttribute("aria-busy", "false");
    });
  });

  it("holds the gestures while a paste applied is under way (#1224)", async () => {
    const hold = held();
    serve(
      { [PREVIEW]: "paste_plan", [APPLY]: "paste_applied" },
      { route: APPLY, until: hold.until },
    );
    renderGrid();
    await pasteOn(cell(FIRST, "label"), copied(BLOCK));
    const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    await userEvent.click(
      await within(dialog).findByRole("button", { name: "Appliquer le collage" }),
    );
    fireEvent.contextMenu(cell(FIRST - 1, "label"), { clientX: 300, clientY: 200 });
    const menu = await screen.findByRole("menu", { name: "Menu de la cellule" });
    expect(within(menu).getByRole("menuitem", { name: "Insérer au-dessous" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    await userEvent.keyboard("{Escape}");
    await act(async () => {
      hold.release();
      await hold.until;
    });
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    fireEvent.contextMenu(cell(FIRST - 1, "label"), { clientX: 300, clientY: 200 });
    const after = await screen.findByRole("menu", { name: "Menu de la cellule" });
    expect(within(after).getByRole("menuitem", { name: "Insérer au-dessous" })).not.toHaveAttribute(
      "aria-disabled",
    );
  });

  it("applies nothing of an answer once the grid shows another structure: no reading anew, nor its version (#1224)", async () => {
    // A move sent in the main structure, answered once the grid shows the amendment: the grid is not
    // read anew for it, nor waits for it, and the next move of the amendment carries its own version.
    const hold = held();
    const client = serve({ [MOVE]: "nodes_indented" }, { route: MOVE, until: hold.until });
    const view = render(grid());
    await indent(MOUNTING);
    await vi.waitFor(() => {
      expect(moves(client)).toHaveLength(1);
    });
    view.rerender(grid(AMENDMENT));
    expect(screen.getByRole("treegrid")).toHaveAttribute("aria-busy", "false");
    await act(async () => {
      hold.release();
      await hold.until;
    });
    await screen.findByText(/indentée\.$/);
    expect(router.refresh).not.toHaveBeenCalled();
    await indent(MOUNTING);
    await vi.waitFor(() => {
      expect(moves(client)).toHaveLength(2);
    });
    expect(moves(client)[1]).toMatchObject({ lock_version: VERSION });
    // Its own answer, in the structure shown, reads the grid anew.
    await vi.waitFor(() => {
      expect(router.refresh).toHaveBeenCalledTimes(1);
    });
  });

  it("keeps the version the other structure moved on to by its own writes when a late answer of the first arrives (#1224)", async () => {
    // A move sent in the main structure, held, answered at its version 3 (`nodes_moved`), once the
    // amendment shown moved on to its version 2 by a move of its own (`nodes_indented`): the
    // amendment keeps its 2, the main structure takes its 3.
    const hold = held();
    const client = fakeClient(
      { [MOVE]: ["nodes_moved", "nodes_indented"] },
      { hold: (route, index) => (route === MOVE && index === 0 ? hold.until : undefined) },
    );
    server.client = client;
    const view = render(grid());
    await indent(MOUNTING);
    await vi.waitFor(() => {
      expect(moves(client)).toHaveLength(1);
    });
    view.rerender(grid(AMENDMENT));
    await indent(MOUNTING);
    await vi.waitFor(() => {
      expect(router.refresh).toHaveBeenCalledTimes(1);
    });
    await act(async () => {
      hold.release();
      await hold.until;
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    // The late answer reads nothing anew for the amendment.
    expect(router.refresh).toHaveBeenCalledTimes(1);
    await indent(MOUNTING);
    await vi.waitFor(() => {
      expect(moves(client)).toHaveLength(3);
    });
    expect(moves(client)[2]).toMatchObject({ lock_version: 2 });
    // Back on the main structure, the next move carries the version its own answer reached.
    view.rerender(grid());
    await indent(MOUNTING);
    await vi.waitFor(() => {
      expect(moves(client)).toHaveLength(4);
    });
    expect(moves(client)[3]).toMatchObject({ lock_version: 3 });
  });

  it("follows no row moved in a structure left once back on it (#1224)", async () => {
    // A move sent in the main structure, answered once the grid shows the amendment, then the main
    // structure shown again, read anew with the mounting one row up: the active cell stays where it
    // is, the row the late answer moved is not followed.
    const hold = held();
    const client = serve({ [MOVE]: "nodes_indented" }, { route: MOVE, until: hold.until });
    const view = render(grid());
    await indent(MOUNTING);
    await vi.waitFor(() => {
      expect(moves(client)).toHaveLength(1);
    });
    view.rerender(grid(AMENDMENT));
    await act(async () => {
      hold.release();
      await hold.until;
    });
    await screen.findByText(/indentée\.$/);
    view.rerender(grid(STRUCTURE, { nodes: withoutReception }));
    expect(cellAt(MOUNTING - 1, "label")).toHaveTextContent("Montage des armoires sur site");
    expect(cellAt(MOUNTING - 1, "label")).toHaveAttribute("tabindex", "-1");
    expect(cellAt(MOUNTING, "label")).toHaveAttribute("tabindex", "0");
  });
});
