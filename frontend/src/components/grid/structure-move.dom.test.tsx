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
import { holdReading, Reading, releaseReading } from "@/test/held-reading";
import { estimateReference } from "@/test/reference";

import { EstimateGrid } from "./estimate-grid";
import type { NodeList, NodeSortColumn } from "./nodes";
import { breakdownItems, type WorkBreakdownReading } from "./planning-attachment";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";
import { RemainingGrid } from "./remaining-grid";

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

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined, size: undefined };
const MOVE =
  "POST /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/move" as const;
const TASK =
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/task";
const REMAINING =
  "PUT /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/remaining";
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const VERSION = 1;
const estimate = example("nodes_estimate") as NodeList;
const planning = example("nodes_planning") as NodeList;
const core = example("nodes_core") as NodeList;

/** The index of a row of a list, by its label. */
function rowOf(list: NodeList, label: string): number {
  return list.items.findIndex((each) => (each.task?.label ?? each.estimate_line?.label) === label);
}
const LEAF = rowOf(estimate, "Câblage des armoires");
const RISK = rowOf(estimate, "Retard de livraison des armoires");
const RELANCE = rowOf(estimate, "Relance du fournisseur");
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
function estimateGrid(editable = true, nodes = estimate) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <EstimateGrid
        nodes={nodes}
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

/** The grid of the remaining to commit, in French, which shows the whole estimate. */
function remainingGrid() {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <RemainingGrid
        nodes={estimate}
        structure={STRUCTURE}
        structureVersion={VERSION}
        filters={{}}
        editable
        query={NO_QUERY}
        preferences={undefined}
      />
    </NextIntlClientProvider>
  );
}

/** The grid of the planning of the tasks nested, its attachment entered. */
function nestedGrid(nodes: NodeList) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PlanningGrid
        nodes={nodes}
        structure={STRUCTURE}
        structureVersion={VERSION}
        filters={{ kinds: ["task"] }}
        query={NO_QUERY}
        preferences={undefined}
        undoable
        editable
        breakdown={breakdownItems(example("work_breakdown") as WorkBreakdownReading)}
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
  releaseReading();
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
    // The whole structure shows « Poste de commande » after « Études », its sibling above.
    const client = serve({ [MOVE]: "nodes_indented" });
    render(estimateGrid(true, core));
    const control = rowOf(core, "Poste de commande");
    await activate(control);
    await userEvent.keyboard("{Alt>}{Shift>}{ArrowRight}{/Shift}{/Alt}");
    expect(moved(client)).toEqual([
      {
        node_ids: [core.items[control]?.node_id],
        parent_id: core.items[rowOf(core, "Études")]?.node_id,
        lock_version: VERSION,
      },
    ]);
    expect(await screen.findByText("« Poste de commande » indentée.")).toBeVisible();
    expect(router.refresh).toHaveBeenCalledTimes(1);
  });

  it("offers it to a task with a task above it under its parent, and to no other", async () => {
    serve({});
    render(estimateGrid());
    const menu = await openMenu(TRANSPORT);
    const item = within(menu).getByRole("menuitem", { name: "Indenter" });
    expect(item).toHaveAttribute("aria-keyshortcuts", "Alt+Shift+ArrowRight");
    await userEvent.keyboard("{Escape}");
    // The risk occurred follows the factory acceptance, a milestone, which bears nothing.
    const risk = await openMenu(RISK);
    expect(within(risk).queryByRole("menuitem", { name: "Indenter" })).not.toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    // The first of its siblings has no task to go under.
    const first = await openMenu(LEAF);
    expect(within(first).queryByRole("menuitem", { name: "Indenter" })).not.toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
  });

  it("offers it only where the grid shows the sibling just above, as a reading narrowed leaves rows out [WF-PLA-0080-A]", async () => {
    // « Transport exceptionnel » is the second sub-task of its parent: the reading without
    // « Relance du fournisseur » shows no task above it, which is not its neighbour; the whole
    // reading shows the neighbour.
    const narrowed: NodeList = {
      ...estimate,
      items: estimate.items.filter((each) => each.node_id !== estimate.items[RELANCE]?.node_id),
    };
    const client = serve({});
    const { unmount } = render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <EstimateGrid
          nodes={narrowed}
          structure={STRUCTURE}
          structureVersion={VERSION}
          reference={estimateReference()}
          editable
          tasksEditable
          query={NO_QUERY}
          filters={{}}
          preferences={undefined}
        />
      </NextIntlClientProvider>,
    );
    const at = narrowed.items.findIndex((each) => each.task?.label === "Transport exceptionnel");
    const menu = await openMenu(at);
    expect(within(menu).queryByRole("menuitem", { name: "Indenter" })).not.toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await activate(at);
    await userEvent.keyboard("{Alt>}{Shift>}{ArrowRight}{/Shift}{/Alt}");
    expect(client.calls).toEqual([]);
    unmount();
    render(estimateGrid());
    const whole = await openMenu(TRANSPORT);
    expect(within(whole).getByRole("menuitem", { name: "Indenter" })).toBeInTheDocument();
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
    const menu = await openMenu(TRANSPORT);
    expect(within(menu).queryByRole("menuitem", { name: "Indenter" })).not.toBeInTheDocument();
    expect(within(menu).queryByRole("menuitem", { name: "Désindenter" })).not.toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await activate(TRANSPORT);
    await userEvent.keyboard("{Alt>}{Shift>}{ArrowRight}{/Shift}{/Alt}");
    expect(client.calls).toEqual([]);
  });

  it("carries the version the last write reached, not the one read with the page", async () => {
    // Router refresh being a no-op here, the page keeps its version: the move carries the one the
    // answer of the first named.
    const client = serve({ [MOVE]: "nodes_indented" });
    render(estimateGrid());
    await choose(TRANSPORT, "Indenter");
    await screen.findByText(/indentée\.$/);
    await choose(RELANCE, "Désindenter");
    const [first, second] = moved(client) as { lock_version: number }[];
    expect(first?.lock_version).toBe(VERSION);
    expect(second?.lock_version).toBeGreaterThan(VERSION);
  });

  it("carries the version a cell of the planning reached, not the one read with the page [WF-PLA-0080-A]", async () => {
    // A cell written moves the version of the structure (`structure_lock_version`): the indentation
    // that follows carries it, or the server would refuse it as stale. The page keeps its own.
    const nested = example("nodes_nested") as NodeList;
    const client = serve({ [TASK]: "task_attached", [MOVE]: "nodes_indented" });
    render(nestedGrid(nested));
    const mounting = rowOf(nested, "Montage des armoires sur site");
    const attachment = screen
      .getByRole("treegrid")
      .querySelector<HTMLElement>(
        `td[data-row="${mounting.toString()}"][data-column="work_breakdown"]`,
      );
    attachment?.focus();
    await userEvent.keyboard("P{Enter}");
    await vi.waitFor(() => {
      expect(client.calls.filter((call) => call.route === TASK)).toHaveLength(1);
    });
    await choose(mounting, "Indenter");
    await screen.findByText(/indentée\.$/);
    expect(moved(client)).toMatchObject([{ lock_version: 2 }]);
  });

  it("carries the version a cell of the remaining to commit reached, not the one read with the page [WF-PLA-0080-A]", async () => {
    const client = serve({ [REMAINING]: "remaining_reestimated", [MOVE]: "nodes_indented" });
    render(remainingGrid());
    const line = rowOf(estimate, "Borniers");
    const cell = screen
      .getByRole("treegrid")
      .querySelector<HTMLElement>(`td[data-row="${line.toString()}"][data-column="quantity"]`);
    cell?.focus();
    await userEvent.keyboard("{Enter}");
    await userEvent.clear(screen.getByRole("textbox", { name: "Qté" }));
    await userEvent.keyboard("2{Enter}");
    await vi.waitFor(() => {
      expect(client.calls.filter((call) => call.route === REMAINING)).toHaveLength(1);
    });
    await choose(TRANSPORT, "Indenter");
    await screen.findByText(/indentée\.$/);
    expect(moved(client)).toMatchObject([{ lock_version: 3 }]);
  });

  it("leaves the focus in a cell entered while the reading anew the move asked is under way [WF-IHM-0100-A]", async () => {
    // Chaque écran se parcourt entièrement au clavier et le focus reste visible : the field of a
    // cell opened before the reading comes keeps the focus through it, the row moved not followed.
    holdReading(router.refresh);
    serve({ [MOVE]: "nodes_indented" });
    const view = render(estimateGrid(), { wrapper: Reading });
    await choose(TRANSPORT, "Indenter");
    await screen.findByText(/indentée\.$/);
    await activate(LEAF);
    await act(async () => {
      await userEvent.keyboard("{F2}");
    });
    const field = within(screen.getByRole("treegrid")).getByRole("textbox");
    expect(field).toHaveFocus();
    await act(async () => {
      view.rerender(estimateGrid(true, { ...estimate, items: [...estimate.items] }));
      releaseReading();
      await Promise.resolve();
    });
    expect(field).toHaveFocus();
  });

  it("holds the move while a write is under way", async () => {
    const hold = held();
    const client = serve({ [MOVE]: "nodes_indented" }, hold.until);
    render(estimateGrid());
    await choose(TRANSPORT, "Indenter");
    await activate(RELANCE);
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
    ["nodes_indent_forbidden", "Cette liaison n’est pas permise.", 0],
    ["nodes_move_cycle_refused", "Cette liaison créerait une boucle.", 0],
    [
      "nodes_move_outside_work_package",
      "La tâche d’un poste doit rester dans le sous-arbre de la tâche de son lot.",
      0,
    ],
    [
      "nodes_move_after_not_sibling",
      "Le nœud après lequel se placer n’est pas parmi les frères de la nouvelle place : la grille est relue.",
      1,
    ],
  ])(
    "names the row of %s in the alert and marks it, the grid read anew only for a reading gone stale",
    async (name, sentence, reads) => {
      const client = serve({ [MOVE]: refusal(name) });
      render(estimateGrid());
      await choose(TRANSPORT, "Indenter");
      expect(moved(client)).toHaveLength(1);
      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent(
        `Refusé à la ligne ${String(estimate.items[TRANSPORT]?.row_number)}, « Transport exceptionnel » :`,
      );
      expect(alert).toHaveTextContent(sentence);
      expect(labelAt(TRANSPORT)).toBeInvalid();
      // Nothing was written; a node to follow that is no sibling says the reading is stale, so
      // the grid is read anew, and the refusal stays told.
      expect(router.refresh).toHaveBeenCalledTimes(reads);
      expect(readMessages().messages).toMatchObject([{ tone: "refusal" }]);
    },
  );

  it("names the task of the lot and that of the post a move would take out of its subtree, as the contract gives them [WF-PLA-0170-A]", async () => {
    serve({ [MOVE]: refusal("nodes_move_outside_work_package") });
    render(estimateGrid());
    await choose(TRANSPORT, "Indenter");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      /La tâche d’un poste doit rester dans le sous-arbre de la tâche de son lot\. Tâche du lot\s:\s« Poste de commande »\. Tâche du poste en cause\s:\s« Câblage des armoires »\./,
    );
  });

  it("names the task and both roles a move would leave without a working hour, as the grid of the estimate knows them [WF-PLA-0010-A]", async () => {
    serve({ [MOVE]: refusal("nodes_move_without_hours") });
    render(estimateGrid());
    await choose(TRANSPORT, "Indenter");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Une tâche n’aurait plus aucune heure travaillée");
    expect(alert).toHaveTextContent("Ingénieur électricien");
    expect(alert).toHaveTextContent("Technicien de mise en service");
    expect(alert).toHaveTextContent("Câblage des armoires");
  });

  it("names the task of a move refused from the planning, whose grid reads no role: the roles are left unnamed, by no identifier [WF-PLA-0010-A]", async () => {
    // The planning lists tasks and reads no estimate line nor the settings of the resources: the
    // roles of the refusal stay unnamed, and the notice says so.
    // This fallback sentence does not yet hold the Vérif of WF-PLA-0010 (« en nommant les deux
    // rôles »): the decision of #1684 is awaited, and this test freezes the sentence as it is. It will have to
    // change with that decision.
    serve({ [MOVE]: refusal("nodes_move_without_hours") });
    render(planningGrid());
    await choose(REVIEW, "Indenter");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Câblage des armoires");
    expect(alert).toHaveTextContent("Les calendriers de ses rôles ne se recoupent aucun jour.");
    expect(alert).not.toHaveTextContent("000000000451");
  });

  it("names the row and the condition when a line is moved to a task completed: the move is refused, nothing moves [WF-DEV-0050-A]", async () => {
    // Le déplacement d'une ligne vers une tâche terminée est refusé.
    const client = serve({
      [MOVE]: { problem: example("nodes_move_completed_refused") as Problem & { status: 409 } },
    });
    render(estimateGrid());
    await choose(TRANSPORT, "Indenter");
    expect(moved(client)).toHaveLength(1);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      `Refusé à la ligne ${String(estimate.items[TRANSPORT]?.row_number)}, « Transport exceptionnel » :`,
    );
    expect(alert).toHaveTextContent("tâche non terminée");
    expect(labelAt(TRANSPORT)).toBeInvalid();
    expect(readMessages().messages).toMatchObject([{ tone: "refusal" }]);
  });
});
