// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { forgetMessages, readMessages } from "@/components/notices/message-history";
import { CATALOGUES } from "@/i18n/catalogues";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  held,
  type Problem,
} from "@/test/fixtures";
import { estimateReference } from "@/test/reference";

import { EstimateGrid } from "./estimate-grid";
import type { NodeList, NodeSortColumn } from "./nodes";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";

// The indentation and the outdentation of the tasks of a grid (US-0460/L4, WF-PLA-0080): what the
// gesture sends to `moveNodes`, what the grid does of the answer, and the refusals said at the row.
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
const VERSION = 1;
const estimate = example("nodes_estimate") as NodeList;
const planning = example("nodes_planning") as NodeList;

/** The index of a row of a list, by its label. */
function rowOf(list: NodeList, label: string): number {
  return list.items.findIndex((each) => (each.task?.label ?? each.estimate_line?.label) === label);
}
const LEAF = rowOf(estimate, "Câblage des armoires");
const RISK = rowOf(estimate, "Risque survenu — Retard de livraison des armoires");
const TRANSPORT = rowOf(estimate, "Transport exceptionnel");
const REVIEW = rowOf(planning, "Revue de conception");
const DESIGN = rowOf(planning, "Études de détail");

/** The refusals the contract cites for `moveNodes`, as the envelope the fake back serves. */
const refusal = (name: string) => ({ problem: example(name) as Problem & { status: 422 } });

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers, hold?: Promise<unknown>): FakeClient {
  const client = fakeClient(answers, { hold: () => hold });
  server.client = client;
  return client;
}

/** The grid of the estimate, in French. */
function estimateGrid(editable = true) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <EstimateGrid
        nodes={estimate}
        structure={STRUCTURE}
        structureVersion={VERSION}
        reference={estimateReference()}
        editable={editable}
        tasksEditable={editable}
        query={NO_QUERY}
        filters={{}}
        preferences={undefined}
      />
    </NextIntlClientProvider>
  );
}

/** The grid of the planning, in French. */
function planningGrid(editable = true) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PlanningGrid
        nodes={planning}
        structure={STRUCTURE}
        structureVersion={VERSION}
        filters={{ kinds: ["task"] }}
        query={NO_QUERY}
        preferences={undefined}
        undoable={editable}
        editable={editable}
      />
    </NextIntlClientProvider>
  );
}

/** The cell of the label of the row at an index. */
function labelAt(row: number): HTMLElement {
  const found = screen
    .getByRole("treegrid")
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="label"]`);
  if (found === null) {
    throw new Error(`no label for the row ${row.toString()}`);
  }
  return found;
}

/** Make a row the active one, as a click on its label does. */
async function activate(row: number): Promise<HTMLElement> {
  const cell = labelAt(row);
  await act(async () => {
    cell.focus();
    await Promise.resolve();
  });
  return cell;
}

/** Open the menu of the cell of a row's label, by a right click. */
async function openMenu(row: number): Promise<HTMLElement> {
  fireEvent.contextMenu(labelAt(row), { clientX: 300, clientY: 200 });
  return screen.findByRole("menu", { name: "Menu de la cellule" });
}

/** Choose a gesture in the menu of a row. */
async function choose(row: number, name: string) {
  const menu = await openMenu(row);
  await userEvent.click(within(menu).getByRole("menuitem", { name }));
}

/** The moves the fake back received, as the grid sent them. */
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
  vi.restoreAllMocks();
});

describe("the indentation of a task", () => {
  it("moves the task under the task above it, last, from the menu of its cell, and reads the grid anew [WF-PLA-0080-A]", async () => {
    // L'indentation d'un groupe de tâches déplace le groupe entier sous la tâche précédente : the
    // gesture sends `moveNodes` with the selection and the task above it as the parent, and the
    // grid is read anew, whose rows take the place of the rows read.
    const client = serve({ [MOVE]: "nodes_indented" });
    render(planningGrid());
    await choose(REVIEW, "Indenter");
    expect(moved(client)).toEqual([
      {
        node_ids: [planning.items[REVIEW]?.node_id],
        parent_id: planning.items[REVIEW - 1]?.node_id,
        lock_version: VERSION,
      },
    ]);
    expect(await screen.findByText("« Revue de conception » indentée.")).toBeVisible();
    expect(router.refresh).toHaveBeenCalledTimes(1);
    expect(readMessages().messages).toMatchObject([
      {
        tone: "success",
        sentence: "« Revue de conception » indentée.",
        object: "Revue de conception",
      },
    ]);
  });

  it("moves a summary alone, the server carrying its subordinates with it, on Alt+Shift+Right [WF-PLA-0080-A]", async () => {
    // Le groupe entier : a summary is named by its own identifier, its subordinates going with it.
    const client = serve({ [MOVE]: "nodes_indented" });
    render(estimateGrid());
    await activate(RISK);
    await userEvent.keyboard("{Alt>}{Shift>}{ArrowRight}{/Shift}{/Alt}");
    expect(moved(client)).toEqual([
      {
        node_ids: [estimate.items[RISK]?.node_id],
        parent_id: estimate.items[LEAF]?.node_id,
        lock_version: VERSION,
      },
    ]);
    expect(
      await screen.findByText("« Risque survenu — Retard de livraison des armoires » indentée."),
    ).toBeVisible();
    expect(router.refresh).toHaveBeenCalledTimes(1);
  });

  it("offers it to a task with a task above it under its parent, and to no other", async () => {
    serve({});
    render(estimateGrid());
    const menu = await openMenu(RISK);
    const item = within(menu).getByRole("menuitem", { name: "Indenter" });
    expect(item).toHaveAttribute("aria-keyshortcuts", "Alt+Shift+ArrowRight");
    await userEvent.keyboard("{Escape}");
    // The first of its siblings has no task to go under.
    const first = await openMenu(LEAF);
    expect(within(first).queryByRole("menuitem", { name: "Indenter" })).not.toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
  });

  it("does nothing on the keys where the task has no place to go", async () => {
    const client = serve({});
    render(estimateGrid());
    await activate(LEAF);
    await userEvent.keyboard("{Alt>}{Shift>}{ArrowRight}{/Shift}{/Alt}");
    expect(client.calls).toEqual([]);
    expect(router.refresh).not.toHaveBeenCalled();
  });

  it("offers neither the menu item nor the key to a grid the structure lists read only", async () => {
    const client = serve({});
    render(estimateGrid(false));
    const menu = await openMenu(RISK);
    expect(within(menu).queryByRole("menuitem", { name: "Indenter" })).not.toBeInTheDocument();
    expect(within(menu).queryByRole("menuitem", { name: "Désindenter" })).not.toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await activate(RISK);
    await userEvent.keyboard("{Alt>}{Shift>}{ArrowRight}{/Shift}{/Alt}");
    expect(client.calls).toEqual([]);
  });

  it("carries the version the last write reached, not the one read with the page", async () => {
    // Router refresh being a no-op here, the page keeps its version: the move carries the one the
    // answer of the first named.
    const client = serve({ [MOVE]: "nodes_indented" });
    render(estimateGrid());
    await choose(RISK, "Indenter");
    await screen.findByText(/indentée\.$/);
    await choose(TRANSPORT, "Désindenter");
    const [first, second] = moved(client) as { lock_version: number }[];
    expect(first?.lock_version).toBe(VERSION);
    expect(second?.lock_version).toBeGreaterThan(VERSION);
  });

  it("holds the move while a write is under way", async () => {
    const hold = held();
    const client = serve({ [MOVE]: "nodes_indented" }, hold.until);
    render(estimateGrid());
    await choose(RISK, "Indenter");
    await activate(TRANSPORT);
    await userEvent.keyboard("{Alt>}{Shift>}{ArrowLeft}{/Shift}{/Alt}");
    expect(moved(client)).toHaveLength(1);
    hold.release();
    await screen.findByText(/indentée\.$/);
  });
});

describe("the outdentation of a task", () => {
  it("puts the task after its parent, under the parent of that one, on Alt+Shift+Left [WF-PLA-0080-A]", async () => {
    const client = serve({ [MOVE]: "nodes_moved" });
    render(estimateGrid());
    await activate(TRANSPORT);
    await userEvent.keyboard("{Alt>}{Shift>}{ArrowLeft}{/Shift}{/Alt}");
    expect(moved(client)).toEqual([
      {
        node_ids: [estimate.items[TRANSPORT]?.node_id],
        parent_id: estimate.items[RISK]?.parent_id,
        after_node_id: estimate.items[RISK]?.node_id,
        lock_version: VERSION,
      },
    ]);
    expect(await screen.findByText("« Transport exceptionnel » désindentée.")).toBeVisible();
    expect(router.refresh).toHaveBeenCalledTimes(1);
  });

  it("is offered from the menu to a task under another, and not to a task at the root", async () => {
    serve({});
    render(planningGrid());
    const under = await openMenu(DESIGN);
    expect(within(under).getByRole("menuitem", { name: "Désindenter" })).toHaveAttribute(
      "aria-keyshortcuts",
      "Alt+Shift+ArrowLeft",
    );
    await userEvent.keyboard("{Escape}");
    const root = await openMenu(0);
    expect(within(root).queryByRole("menuitem", { name: "Désindenter" })).not.toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
  });
});

describe("the refusal of a move, said to the row in cause", () => {
  it.each([
    ["nodes_indent_forbidden", "Cette liaison n’est pas permise."],
    ["nodes_move_cycle_refused", "Cette liaison créerait une boucle."],
    [
      "nodes_move_after_not_sibling",
      "Le nœud après lequel se placer n’est pas parmi les frères de la nouvelle place : relisez la grille.",
    ],
  ])(
    "names the row of %s in the alert, marks it and reads nothing anew",
    async (name, sentence) => {
      const client = serve({ [MOVE]: refusal(name) });
      render(estimateGrid());
      await choose(RISK, "Indenter");
      expect(moved(client)).toHaveLength(1);
      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent(
        `Refusé à la ligne ${String(estimate.items[RISK]?.row_number)}, « Risque survenu — Retard de livraison des armoires » :`,
      );
      expect(alert).toHaveTextContent(sentence);
      expect(labelAt(RISK)).toBeInvalid();
      expect(router.refresh).not.toHaveBeenCalled();
      expect(readMessages().messages).toMatchObject([{ tone: "refusal" }]);
    },
  );
});
