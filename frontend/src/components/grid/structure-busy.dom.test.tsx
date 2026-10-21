// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { forgetMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeAnswers, type FakeClient, fakeClient, held } from "@/test/fixtures";
import { APPLY, BLOCK, cell, copied, FIRST, pasteOn, PREVIEW, renderGrid } from "@/test/paste-grid";

import type { NodeList, NodeSortColumn } from "./nodes";
import { breakdownItems, type WorkBreakdownReading } from "./planning-attachment";
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

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined };
const NODES = "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes";
const MOVE = `POST ${NODES}/move` as const;
const TASK = `PATCH ${NODES}/{node_id}/task` as const;
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

/** Serve the fake back, the calls of a route held until `hold` settles, and give it back. */
function serve(answers: FakeAnswers, held?: { route: string; until: Promise<unknown> }) {
  const client = fakeClient(answers, {
    hold: (route) => (route === held?.route ? held.until : undefined),
  });
  server.client = client;
  return client;
}

/** The grid of the planning of the nested tasks on a structure, entered, its attachment too. */
function grid(structure = STRUCTURE) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PlanningGrid
        nodes={nested}
        structure={structure}
        structureVersion={VERSION}
        filters={{ kinds: ["task"] }}
        query={NO_QUERY}
        preferences={undefined}
        undoable
        editable
        breakdown={breakdown}
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

describe("a grid busy with any of its writes", () => {
  it("holds the gestures while a cell written is under way, and moves with the version it reached once answered", async () => {
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

  it("holds the gestures while a paste applied is under way", async () => {
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

  it("applies nothing of an answer once the grid shows another structure: no reading anew, nor its version", async () => {
    // A move sent in the main structure, answered once the grid shows the amendment: the grid is not
    // read anew for it, nor waits for it, and the next move of the amendment carries its own version.
    const hold = held();
    const client = serve({ [MOVE]: "nodes_indented" }, { route: MOVE, until: hold.until });
    const view = render(grid());
    await indent(MOUNTING);
    expect(moves(client)).toHaveLength(1);
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
});
