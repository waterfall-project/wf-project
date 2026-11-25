// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { OwnEstimateEntry } from "@/components/revisions/own-estimate-entry";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient, held } from "@/test/fixtures";
import { SHOWN } from "@/test/grid-preferences";
import { estimateReference } from "@/test/reference";

import { EstimateGrid } from "./estimate-grid";
import type { NodeList, NodeSortColumn } from "./nodes";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";

// The gestures of structure, the sub-project of a line and the timelines of a task, on the own
// estimate of a risk in arrears whose update signals nothing (US-3140, #4818).
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/estimate",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined, size: undefined };
const STRUCTURE_PATH = "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}";
const REPORT = `GET ${STRUCTURE_PATH}/rebase` as const;
const REBASE = `POST ${STRUCTURE_PATH}/rebase` as const;
const NODES = `GET ${STRUCTURE_PATH}/nodes` as const;
const CREATE = `POST ${STRUCTURE_PATH}/nodes` as const;
const DELETE = `DELETE ${STRUCTURE_PATH}/nodes/{node_id}` as const;
const MOVE = `POST ${STRUCTURE_PATH}/nodes/move` as const;
const LINE = `PATCH ${STRUCTURE_PATH}/nodes/{node_id}/estimate-line` as const;
const TRACKING = `PUT ${STRUCTURE_PATH}/nodes/{node_id}/tracking` as const;
// The counter of the own estimate once the update is applied (`structure_rebased_risk`).
const UPDATED = 6;
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000206",
};
const UPDATE = {
  [REPORT]: "structure_rebase_report_risk_clean",
  [REBASE]: "structure_rebased_risk",
  [NODES]: "nodes_risk_estimate",
} as const;
const [LABOUR, REWORK, RECABLING] = [4, 5, 6];
const read = example("nodes_risk_estimate") as NodeList;
// The rows as the page read them before the update: those the gestures touch, at a counter it moved.
const BEFORE = 0;
const estimate: NodeList = {
  ...read,
  items: read.items.map((node, row) => (row >= LABOUR ? { ...node, lock_version: BEFORE } : node)),
};

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  router.refresh.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

/** A grid under the guard of the own estimate in arrears, on the structure read at a counter. */
function guarded(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <OwnEstimateEntry
        estimate={{
          projectId: STRUCTURE.project_id,
          revisionId: STRUCTURE.revision_id,
          structureId: STRUCTURE.structure_id,
          label: "Indisponibilité de l'automaticien",
        }}
        late
        recompose={false}
      >
        {children}
      </OwnEstimateEntry>
    </NextIntlClientProvider>
  );
}

function estimateGrid() {
  return guarded(
    <EstimateGrid
      nodes={estimate}
      structure={STRUCTURE}
      structureVersion={5}
      reference={estimateReference()}
      editable
      tasksEditable
      differential
      query={NO_QUERY}
      filters={{}}
      preferences={SHOWN}
    />,
  );
}

/** The cell of the label of a row, by its index among the rows of the answer. */
function cell(row: number, column = "label"): HTMLElement {
  const found = screen
    .getByRole("treegrid")
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="${column}"]`);
  if (found === null) {
    throw new Error(`no cell ${column} in the row ${row.toString()}`);
  }
  return found;
}

async function openMenu(row: number): Promise<HTMLElement> {
  fireEvent.contextMenu(cell(row), { clientX: 300, clientY: 200 });
  return screen.findByRole("menu", { name: "Menu de la cellule" });
}

async function choose(row: number, name: string) {
  const menu = await openMenu(row);
  await userEvent.click(within(menu).getByRole("menuitem", { name }));
}

/** The last of the items a submenu lists. */
function lastOf(items: readonly HTMLElement[]): HTMLElement {
  const last = items.at(-1);
  if (last === undefined) {
    throw new Error("the submenu lists nothing");
  }
  return last;
}

/** The counter of a row as the update left it, which the nodes read again carry. */
function counterOf(row: number): number {
  const node = read.items[row];
  if (node === undefined) {
    throw new Error("no such row");
  }
  return node.lock_version;
}

/** Enter another role into the labour line: the cell is edited, and left. */
async function enterRole(): Promise<void> {
  cell(LABOUR, "resource_role").focus();
  await userEvent.keyboard("{Enter}");
  await userEvent.selectOptions(screen.getByRole("combobox", { name: "Rôle" }), "Monteur câbleur");
  await userEvent.keyboard("{Tab}");
}

describe("the gestures on an own estimate in arrears whose update signals nothing", () => {
  it("updates, reads the nodes again, and deletes the line once, with the counter of the line read again [US-3140] [WF-RIS-0070-A]", async () => {
    const client = fakeClient({ ...UPDATE, [DELETE]: "node_deleted" });
    server.client = client;
    render(estimateGrid());
    await choose(LABOUR, "Supprimer");
    await waitFor(() => {
      expect(client.calls.map((call) => call.route)).toEqual([REPORT, REBASE, NODES, DELETE]);
    });
    expect(counterOf(LABOUR)).not.toBe(BEFORE);
    expect(client.calls[3]?.query.get("lock_version")).toBe(counterOf(LABOUR).toString());
    expect(client.calls[3]?.path).toContain(read.items[LABOUR]?.node_id);
    expect(screen.queryByText(/Saisissez de nouveau/)).toBeNull();
  });

  it("moves the task once, from the counter of the structure the update moved on to, not the grid's [US-3140] [WF-RIS-0070-A]", async () => {
    const client = fakeClient({ ...UPDATE, [MOVE]: "nodes_moved" });
    server.client = client;
    render(estimateGrid());
    await choose(REWORK, "Monter");
    await waitFor(() => {
      expect(client.calls.map((call) => call.route)).toEqual([REPORT, REBASE, NODES, MOVE]);
    });
    expect(client.calls[3]?.body).toMatchObject({
      lock_version: UPDATED,
    });
    expect(screen.queryByText(/Saisissez de nouveau/)).toBeNull();
  });

  it("creates the node once after the update, and tells nothing to enter again [US-3140] [WF-RIS-0070-A]", async () => {
    const client = fakeClient({ ...UPDATE, [CREATE]: { example: "node_created", status: 201 } });
    server.client = client;
    render(estimateGrid());
    await choose(REWORK, "Insérer au-dessous");
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Libellé" }), {
      target: { value: "Essais" },
    });
    await userEvent.click(within(dialog).getByRole("button", { name: "Créer" }));
    await waitFor(() => {
      expect(client.calls.map((call) => call.route)).toEqual([REPORT, REBASE, NODES, CREATE]);
    });
    expect(screen.queryByText(/Saisissez de nouveau/)).toBeNull();
  });

  it("writes the sub-project of the line once, with the counter of the line read again [US-3140] [WF-RIS-0070-A]", async () => {
    const client = fakeClient({ ...UPDATE, [LINE]: "estimate_line_subproject_changed" });
    server.client = client;
    render(estimateGrid());
    await choose(RECABLING, "Sous-projet");
    const submenu = await screen.findByRole("menu", { name: "Sous-projet" });
    await userEvent.click(lastOf(within(submenu).getAllByRole("menuitemradio")));
    await waitFor(() => {
      expect(client.calls.map((call) => call.route)).toEqual([REPORT, REBASE, NODES, LINE]);
    });
    expect(client.calls[3]?.body).toMatchObject({ lock_version: counterOf(RECABLING) });
    expect(client.calls[3]?.path).toContain(read.items[RECABLING]?.node_id);
    expect(screen.queryByText(/Saisissez de nouveau/)).toBeNull();
  });

  it("withholds the inscription to the timelines after the update, and tells to enter it again [US-3140] [WF-RIS-0070-A]", async () => {
    const client = fakeClient({ ...UPDATE, [TRACKING]: "node_tracked" });
    server.client = client;
    // A variant, passed to the grid and never served: the tasks, which list their timelines among the
    // fields they accept, as the example does not.
    const tasks: NodeList = {
      ...read,
      items: read.items
        .filter((node) => node.kind === "task")
        .map((node) => ({ ...node, editable_fields: [...node.editable_fields, "task.tracking"] })),
    };
    render(
      guarded(
        <PlanningGrid
          nodes={tasks}
          structure={STRUCTURE}
          structureVersion={5}
          filters={{ kinds: ["task"] }}
          query={NO_QUERY}
          preferences={SHOWN}
          undoable
          editable
          timelines={[{ id: "01926f3a-7c00-7000-8000-000000000901", label: "Jalons client" }]}
        />,
      ),
    );
    await choose(0, "Chronologies");
    const submenu = await screen.findByRole("menu", { name: "Chronologies" });
    await userEvent.click(lastOf(within(submenu).getAllByRole("menuitemcheckbox")));
    expect(await screen.findByText(/est à jour\. Saisissez de nouveau\./)).toBeVisible();
    expect(client.calls.some((call) => call.route === TRACKING)).toBe(false);
  });

  it("refuses a gesture as busy while a cell entry held for the update is written, so none goes from the counters of the grid [US-3140] [WF-RIS-0070-A]", async () => {
    const answers = {
      ...UPDATE,
      [LINE]: "estimate_line_updated",
      [DELETE]: "node_deleted",
    } as const;
    const wait = held();
    const client = fakeClient(answers, {
      hold: (route) => (route === LINE ? wait.until : undefined),
    });
    server.client = client;
    render(estimateGrid());
    await enterRole();
    await waitFor(() => {
      expect(client.calls.map((call) => call.route)).toContain(LINE);
    });
    // The entry is on its way, unanswered: the grid is busy, and the gesture is not offered.
    const menu = await openMenu(REWORK);
    const deletion = within(menu).getByRole("menuitem", { name: "Supprimer" });
    expect(deletion).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(deletion);
    await userEvent.keyboard("{Escape}");
    wait.release();
    await waitFor(() => {
      expect(screen.getByRole("treegrid")).toHaveAttribute("aria-busy", "false");
    });
    expect(client.calls.some((call) => call.route === DELETE)).toBe(false);
  });

  it("writes the sub-project of each line selected from the counter of that line read again [US-3140] [WF-RIS-0070-A]", async () => {
    // The own estimate of a risk occurred, whose two lines accept their sub-project: the page read
    // them at a counter the update moved.
    const occurred = example("nodes_risk_estimate_occurred") as NodeList;
    const lines = occurred.items.filter((node) =>
      node.editable_fields.includes("estimate_line.subproject_id"),
    );
    const [first, second] = lines;
    expect(lines).toHaveLength(2);
    const before: NodeList = {
      ...occurred,
      items: occurred.items.map((node) =>
        lines.includes(node) ? { ...node, lock_version: BEFORE } : node,
      ),
    };
    const client = fakeClient({
      ...UPDATE,
      [NODES]: "nodes_risk_estimate_occurred",
      [LINE]: "estimate_line_subproject_changed",
    });
    server.client = client;
    render(
      guarded(
        <EstimateGrid
          nodes={before}
          structure={STRUCTURE}
          structureVersion={5}
          reference={estimateReference()}
          editable
          tasksEditable
          differential
          query={NO_QUERY}
          filters={{}}
          preferences={SHOWN}
        />,
      ),
    );
    const rows = lines.map((line) => occurred.items.indexOf(line));
    fireEvent.click(cell(rows[0] ?? 0, "row_number"));
    fireEvent.click(cell(rows[1] ?? 0, "row_number"), { shiftKey: true });
    await choose(rows[0] ?? 0, "Sous-projet");
    const submenu = await screen.findByRole("menu", { name: "Sous-projet" });
    await userEvent.click(lastOf(within(submenu).getAllByRole("menuitemradio")));
    await waitFor(() => {
      expect(client.calls.filter((call) => call.route === LINE)).toHaveLength(2);
    });
    const written = client.calls.filter((call) => call.route === LINE);
    // Each line goes to its own node, with the counter read again for it, never the grid's.
    expect(written[0]?.path).toContain(first?.node_id);
    expect(written[1]?.path).toContain(second?.node_id);
    expect(written.map((call) => call.body)).toMatchObject([
      { lock_version: first?.lock_version },
      { lock_version: second?.lock_version },
    ]);
    expect(first?.lock_version).not.toBe(BEFORE);
  });

  it.each([
    ["Supprimer", REWORK],
    ["Monter", REWORK],
    ["Indenter", REWORK],
  ])(
    "writes nothing and tells the node gone when the update removed it: %s [US-3140] [WF-RIS-0070-A]",
    async (gesture, row) => {
      const client = fakeClient({
        ...UPDATE,
        [NODES]: "nodes_empty",
        [DELETE]: "node_deleted",
        [MOVE]: "nodes_moved",
      });
      server.client = client;
      render(estimateGrid());
      await choose(row, gesture);
      expect(await screen.findByText(/cet élément n’existe pas/)).toBeVisible();
      expect(client.calls.map((call) => call.route)).toEqual([REPORT, REBASE, NODES]);
    },
  );
});
