// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";
import { RemainingGrid } from "./remaining-grid";

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
const NODES = "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes";
const CREATE = `POST ${NODES}` as const;
const DELETE = `DELETE ${NODES}/{node_id}` as const;
const MOVE = `POST ${NODES}/move` as const;
// The main structure of the current revision of the witness project, as the examples name it.
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
// The rows of the estimate, found by their label in the example (#400): the summary « Poste de
// commande », the task « Câblage des armoires » and its line of labour, a task completed and its line.
const estimate = example("nodes_estimate") as NodeList;
/** The index of a row of the estimate. */
function rowOf(label: string): number {
  return estimate.items.findIndex(
    (node) => (node.task?.label ?? node.estimate_line?.label) === label,
  );
}
const SUMMARY = rowOf("Poste de commande");
const TASK = rowOf("Câblage des armoires");
const LINE = rowOf("Raccordement des borniers");
const COMPLETED = rowOf("Relance du fournisseur");
const node = (row: number) => estimate.items[row];
const planning = example("nodes_planning") as NodeList;
const categories = estimateReference().categories ?? [];
const CATEGORY = categories.find((category) => category.active)?.id ?? "";

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers, hold?: Promise<unknown>): FakeClient {
  const client = fakeClient(answers, { hold: () => hold });
  server.client = client;
  return client;
}

/** The grid of the estimate, entered or read only, in French. */
function estimateGrid(editable = true, tasksEditable = true, nodes: NodeList = estimate) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <EstimateGrid
        nodes={nodes}
        structure={STRUCTURE}
        structureVersion={1}
        reference={estimateReference()}
        editable={editable}
        tasksEditable={tasksEditable}
        query={NO_QUERY}
        filters={{}}
        preferences={undefined}
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

/** The gestures of structure the menu of a row offers, in the order it offers them. */
async function offered(row: number): Promise<string[]> {
  const menu = await openMenu(row);
  const names = within(menu)
    .getAllByRole("menuitem")
    .map((item) => item.textContent)
    .filter((text) => /Insérer|Supprimer/.test(text));
  await userEvent.keyboard("{Escape}");
  return names;
}

/** The body of the only node created. */
function created(client: FakeClient): unknown {
  return client.calls.filter((call) => call.route === CREATE).map((call) => call.body)[0];
}

/** Name a node in the dialog opened, and send it. */
async function create(label: string) {
  const dialog = screen.getByRole("dialog");
  fireEvent.change(within(dialog).getByRole("textbox", { name: "Libellé" }), {
    target: { value: label },
  });
  await userEvent.click(within(dialog).getByRole("button", { name: "Créer" }));
}

/** The grid of the planning, entered or read only, over the nodes given. */
function planningGrid(nodes: NodeList, editable: boolean) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PlanningGrid
        nodes={nodes}
        structure={STRUCTURE}
        filters={{ kinds: ["task"] }}
        query={NO_QUERY}
        preferences={undefined}
        undoable={editable}
        editable={editable}
      />
    </NextIntlClientProvider>
  );
}

/** The grid of the remaining to commit, entered or read only, its categories given or not. */
function remainingGrid(editable: boolean, withCategories = true, nodes: NodeList = estimate) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <RemainingGrid
        nodes={nodes}
        structure={STRUCTURE}
        structureVersion={1}
        filters={{ progress: ["started"] }}
        editable={editable}
        categories={withCategories ? categories : undefined}
        query={NO_QUERY}
        preferences={undefined}
      />
    </NextIntlClientProvider>
  );
}

/** The refusal of a line created under a task completed, as the fake back gives it (#1184). */
const CREATE_COMPLETED_REFUSED = {
  problem: example("estimate_line_completed_refused") as Problem & { status: 409 },
};
/**
 * The refusal of a deletion under a task completed, which the contract has no example of, and of
 * a version no longer the current one, whose example waits on #1210.
 */
const COMPLETED_REFUSED = {
  problem: {
    code: "STATE_FORBIDS_OPERATION",
    status: 409,
    params: { missing_condition: "task_not_completed" },
  },
} as const;
const STALE_REFUSED = {
  problem: { code: "STALE_LOCK_VERSION", status: 412, params: { expected_lock_version: 3 } },
} as const;

beforeEach(() => {
  window.sessionStorage.clear();
  forgetMessages();
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  // The implementation a test gave `refresh` (`holdReading`) goes with the test.
  router.refresh.mockReset();
});

afterEach(() => {
  // A reading a test held is let go, so that none outlives it.
  releaseReading();
  vi.restoreAllMocks();
});

describe("the gestures that create tasks and lines in a grid of the structure", () => {
  it("inserts a task below the row of a cell, after it among its siblings, and reads the grid anew", async () => {
    const client = serve({ [CREATE]: { example: "node_created", status: 201 } });
    render(estimateGrid());
    await choose(TASK, "Insérer au-dessous");
    const dialog = screen.getByRole("dialog", { name: "Insérer au-dessous" });
    // The dialog names the row it acts under.
    expect(dialog).toHaveAccessibleDescription(
      new RegExp(`^Ligne ${String(node(TASK)?.row_number)}, « Câblage des armoires »\\. `),
    );
    await create("Note de calcul des protections");
    expect(created(client)).toEqual({
      kind: "task",
      parent_id: node(TASK)?.parent_id,
      after_node_id: node(TASK)?.node_id,
      task: { label: "Note de calcul des protections" },
    });
    // The server's reading prevails: the page is read anew, the dialog gone, the creation said.
    expect(await screen.findByText("« Note de calcul des protections » créée.")).toBeVisible();
    expect(router.refresh).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    // The success is noted in the history of the messages, once, with the node it is about.
    const { messages } = readMessages();
    expect(messages).toHaveLength(1);
    expect(messages[0]).toMatchObject({
      tone: "success",
      sentence: "« Note de calcul des protections » créée.",
      object: "Note de calcul des protections",
    });
  });

  it("inserts a sub-task at the end of the row, with no node to follow", async () => {
    const client = serve({ [CREATE]: { example: "node_created_child", status: 201 } });
    render(estimateGrid());
    await choose(TASK, "Insérer une sous-tâche");
    await create("Relevé des réglages");
    expect(created(client)).toEqual({
      kind: "task",
      parent_id: node(TASK)?.node_id,
      task: { label: "Relevé des réglages" },
    });
  });

  it("inserts a line under a task, named, of a category and of a quantity", async () => {
    const client = serve({ [CREATE]: { example: "estimate_line_created", status: 201 } });
    render(estimateGrid());
    await choose(TASK, "Insérer une ligne");
    const dialog = screen.getByRole("dialog", { name: "Insérer une ligne" });
    fireEvent.change(within(dialog).getByRole("combobox", { name: "Catégorie" }), {
      target: { value: CATEGORY },
    });
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Quantité" }), {
      target: { value: "2,5" },
    });
    await create("Consommables d’essais");
    expect(created(client)).toEqual({
      kind: "estimate_line",
      parent_id: node(TASK)?.node_id,
      estimate_line: {
        label: "Consommables d’essais",
        cost_category_id: CATEGORY,
        quantity: "2.5",
      },
    });
    expect(await screen.findByText("« Consommables d’essais » créée.")).toBeVisible();
  });

  it("inserts a line below a line, after it, and refuses a quantity that is no number", async () => {
    const client = serve({ [CREATE]: { example: "estimate_line_created", status: 201 } });
    render(estimateGrid());
    await choose(LINE, "Insérer une ligne");
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Quantité" }), {
      target: { value: "beaucoup" },
    });
    await create("Pièces");
    expect(within(dialog).getByRole("textbox", { name: "Quantité" })).toBeInvalid();
    expect(client.calls.filter((call) => call.route === CREATE)).toEqual([]);
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Quantité" }), {
      target: { value: "3" },
    });
    await userEvent.click(within(dialog).getByRole("button", { name: "Créer" }));
    expect(created(client)).toMatchObject({
      kind: "estimate_line",
      parent_id: node(LINE)?.parent_id,
      after_node_id: node(LINE)?.node_id,
    });
  });

  it("asks a label before it creates anything", async () => {
    const client = serve({});
    render(estimateGrid());
    await choose(TASK, "Insérer au-dessous");
    await create("   ");
    expect(screen.getByRole("textbox", { name: "Libellé" })).toBeInvalid();
    expect(client.calls).toEqual([]);
  });

  it("offers a line to a task that takes one alone, and a sub-task to what is not a line", async () => {
    serve({});
    render(estimateGrid());
    expect(await offered(SUMMARY)).toEqual([
      "Insérer au-dessous",
      "Insérer une sous-tâche",
      "Supprimer",
    ]);
    expect(await offered(TASK)).toEqual([
      "Insérer au-dessous",
      "Insérer une sous-tâche",
      "Insérer une ligne",
      "Supprimer",
    ]);
    expect(await offered(LINE)).toEqual(["Insérer une ligne", "Supprimer"]);
  });

  it("creates the first task of a grid with no row, from its bar", async () => {
    const client = serve({ [CREATE]: { example: "node_created", status: 201 } });
    render(planningGrid(example("nodes_empty") as NodeList, true));
    await userEvent.click(screen.getByRole("button", { name: "Insérer une tâche" }));
    await create("Études");
    expect(created(client)).toEqual({ kind: "task", parent_id: null, task: { label: "Études" } });
  });
});

describe("the refusal of the first task of a grid with no row", () => {
  it("is told in the alert, naming the task tried, and noted once in the history of the messages", async () => {
    const client = serve({ [CREATE]: CREATE_COMPLETED_REFUSED });
    render(planningGrid(example("nodes_empty") as NodeList, true));
    await userEvent.click(screen.getByRole("button", { name: "Insérer une tâche" }));
    await create("Études");
    expect(client.calls.map((call) => call.route)).toEqual([CREATE]);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Création de « Études » refusée :");
    expect(alert).toHaveTextContent("Condition non remplie");
    const { messages } = readMessages();
    expect(messages).toHaveLength(1);
    expect(messages[0]).toMatchObject({ tone: "refusal", object: "Études" });
    expect(router.refresh).not.toHaveBeenCalled();
  });
});

describe("the gestures that delete tasks and lines", () => {
  it("deletes a line at once, and reads the grid anew", async () => {
    const client = serve({ [DELETE]: "node_deleted" });
    render(estimateGrid());
    await choose(LINE, "Supprimer");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(client.calls.map((call) => [call.route, call.path.split("/").at(-1)])).toEqual([
      [DELETE, node(LINE)?.node_id],
    ]);
    expect(await screen.findByText("« Raccordement des borniers » supprimée.")).toBeVisible();
    expect(router.refresh).toHaveBeenCalledTimes(1);
    expect(readMessages().messages).toMatchObject([
      { tone: "success", sentence: "« Raccordement des borniers » supprimée." },
    ]);
  });

  describe("the focus of a row deleted at once", () => {
    const without = () =>
      estimateGrid(true, true, {
        ...estimate,
        items: estimate.items.filter((_, index) => index !== LINE),
      });

    /** Delete the line at once, the reading of the grid being held. */
    async function deleteHeld() {
      holdReading(router.refresh);
      serve({ [DELETE]: "node_deleted" });
      const view = render(estimateGrid(), { wrapper: Reading });
      await activate(LINE);
      await userEvent.keyboard("{Control>}{Delete}{/Control}");
      await screen.findByText("« Raccordement des borniers » supprimée.");
      return view;
    }

    const filter = () => {
      const field = document.createElement("input");
      document.body.append(field);
      field.focus();
      return field;
    };

    it("gives the focus back to a cell when the reading removes the cell and nothing else has it", async () => {
      const view = await deleteHeld();
      await act(async () => {
        view.rerender(without());
        await Promise.resolve();
      });
      await waitFor(() => {
        expect(screen.getByRole("treegrid")).toContainElement(
          document.activeElement instanceof HTMLElement ? document.activeElement : null,
        );
      });
    });

    it("gives the focus back when the removal and the end of the reading come in one commit, as Next commits them", async () => {
      const view = await deleteHeld();
      await act(async () => {
        view.rerender(without());
        releaseReading();
        await Promise.resolve();
      });
      await waitFor(() => {
        expect(screen.getByRole("treegrid")).toContainElement(
          document.activeElement instanceof HTMLElement ? document.activeElement : null,
        );
      });
    });

    it("forgets the cell of a reading that was not seen, so a later removal takes no focus", async () => {
      // `refresh` returns at once here: the reading is over before it was observed.
      serve({ [DELETE]: "node_deleted" });
      const view = render(estimateGrid());
      await activate(LINE);
      await userEvent.keyboard("{Control>}{Delete}{/Control}");
      await screen.findByText("« Raccordement des borniers » supprimée.");
      const field = filter();
      await act(async () => {
        view.rerender(without());
        await Promise.resolve();
      });
      expect(document.activeElement).toBe(field);
      field.remove();
    });

    it("does not take the focus from a field the user went to during the reading", async () => {
      const view = await deleteHeld();
      const field = filter();
      await act(async () => {
        view.rerender(without());
        await Promise.resolve();
      });
      await act(async () => {
        releaseReading();
        await Promise.resolve();
      });
      expect(document.activeElement).toBe(field);
      field.remove();
    });

    it("forgets the cell once the reading is over, so a later removal takes no focus", async () => {
      const view = await deleteHeld();
      // The cell is recycled, and stays connected through the reading.
      await act(async () => {
        view.rerender(estimateGrid());
        await Promise.resolve();
      });
      await act(async () => {
        releaseReading();
        await Promise.resolve();
      });
      const field = filter();
      await act(async () => {
        view.rerender(without());
        await Promise.resolve();
      });
      expect(document.activeElement).toBe(field);
      field.remove();
    });
  });

  it("confirms the deletion of a summary, which carries its subordinates away, before it sends it", async () => {
    const client = serve({ [DELETE]: "node_summary_deleted" });
    render(estimateGrid());
    await choose(SUMMARY, "Supprimer");
    const dialog = screen.getByRole("dialog", { name: "Supprimer « Poste de commande » ?" });
    expect(dialog).toHaveTextContent("ses tâches subordonnées, leurs lignes et leurs liaisons");
    expect(client.calls).toEqual([]);
    await userEvent.click(within(dialog).getByRole("button", { name: "Annuler" }));
    expect(client.calls).toEqual([]);
    await choose(SUMMARY, "Supprimer");
    await userEvent.click(
      within(screen.getByRole("dialog")).getByRole("button", { name: "Supprimer" }),
    );
    expect(client.calls.map((call) => call.route)).toEqual([DELETE]);
    expect(await screen.findByText("« Poste de commande » supprimée.")).toBeVisible();
  });
});

describe("the refusal of a gesture, said to the row in cause", () => {
  it("names the row a line was refused under a task completed, marks its label and has the refusal describe it [WF-DEV-0050-A]", async () => {
    // La création d'une ligne sous une tâche terminée est refusée : the refusal is told above the
    // grid, naming the row — its number and its label —, which is marked and described by it.
    const client = serve({ [CREATE]: CREATE_COMPLETED_REFUSED });
    render(estimateGrid());
    await choose(COMPLETED, "Insérer une ligne");
    await create("Pièces");
    expect(client.calls.map((call) => call.route)).toEqual([CREATE]);
    const row = node(COMPLETED);
    const alert = await screen.findByRole("alert");
    // The row is named inside the alert, which is read whole.
    expect(alert).toHaveTextContent(
      `Refusé à la ligne ${String(row?.row_number)}, « Relance du fournisseur » :`,
    );
    expect(alert).toHaveTextContent("Condition non remplie");
    const cell = labelAt(COMPLETED);
    expect(cell).toBeInvalid();
    expect(cell.getAttribute("aria-describedby")).toBeTruthy();
    expect(
      alert.querySelector(`#${CSS.escape(cell.getAttribute("aria-describedby") ?? "")}`),
    ).not.toBeNull();
    // Nothing was written: the grid is not read anew, and the dialog is gone.
    expect(router.refresh).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    // The refusal is noted once, about the node tried.
    const { messages } = readMessages();
    expect(messages).toHaveLength(1);
    expect(messages[0]).toMatchObject({ tone: "refusal", object: "Pièces" });
  });

  it("says a node to follow that is no sibling by its reason, at the row it was asked from", async () => {
    // The envelope says only that the entry is invalid; its field says why (`NODE_NOT_SIBLING`).
    serve({
      [CREATE]: { problem: example("node_create_after_not_sibling") as Problem & { status: 422 } },
    });
    render(estimateGrid());
    await choose(TASK, "Insérer au-dessous");
    await create("Note de calcul des protections");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      `Refusé à la ligne ${String(node(TASK)?.row_number)}, « Câblage des armoires » :`,
    );
    expect(alert).toHaveTextContent(
      "Le nœud après lequel se placer n’est pas parmi les frères de la nouvelle place : la grille est relue.",
    );
    // The reading is stale: the grid is read anew, and the refusal stays told.
    expect(router.refresh).toHaveBeenCalledTimes(1);
  });

  it("gives the focus back to the grid when the reading a node that is no sibling asks removes the cell that had it", async () => {
    // The refusal comes from a reading gone stale: the reading anew may no longer hold the row.
    holdReading(router.refresh);
    serve({
      [MOVE]: { problem: example("nodes_move_after_not_sibling") as Problem & { status: 422 } },
    });
    const view = render(estimateGrid(), { wrapper: Reading });
    const risk = rowOf("Risque survenu — Retard de livraison des armoires");
    await activate(risk);
    await userEvent.keyboard("{Alt>}{Shift>}{ArrowRight}{/Shift}{/Alt}");
    await screen.findByRole("alert");
    expect(router.refresh).toHaveBeenCalledTimes(1);
    await act(async () => {
      view.rerender(
        estimateGrid(true, true, {
          ...estimate,
          items: estimate.items.filter((_, index) => index !== risk),
        }),
      );
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(screen.getByRole("treegrid")).toContainElement(
        document.activeElement instanceof HTMLElement ? document.activeElement : null,
      );
    });
  });

  it("passes every write of the hook, the deletion too, through the reading of the reason of a field, which leaves a refusal without field as it is", async () => {
    // `byField` holds for `deleteNode` as for `createNode` and `moveNodes`; the contract cites no
    // field for a deletion, so its refusal is told by its own code.
    serve({ [DELETE]: COMPLETED_REFUSED });
    render(estimateGrid());
    await choose(LINE, "Supprimer");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      `Refusé à la ligne ${String(node(LINE)?.row_number)}, « Raccordement des borniers » :`,
    );
    expect(alert).toHaveTextContent("Condition non remplie");
    expect(router.refresh).not.toHaveBeenCalled();
  });

  it("marks the row it was asked from, though the active row changed while the write was under way", async () => {
    const hold = held();
    serve({ [DELETE]: STALE_REFUSED }, hold.until);
    render(estimateGrid());
    await choose(LINE, "Supprimer");
    await activate(TASK);
    hold.release();
    await screen.findByRole("alert");
    expect(labelAt(LINE)).toBeInvalid();
    expect(labelAt(TASK)).not.toBeInvalid();
  });

  it("says a stale version at the row, with the offer to read it anew", async () => {
    serve({ [DELETE]: STALE_REFUSED });
    render(estimateGrid());
    await choose(LINE, "Supprimer");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      `Refusé à la ligne ${String(node(LINE)?.row_number)}, « Raccordement des borniers » :`,
    );
    expect(screen.getByRole("button", { name: "Recharger" })).toBeInTheDocument();
    expect(labelAt(LINE)).toBeInvalid();
  });

  it("forgets the refusal once the notice is dismissed, and the row is no longer marked", async () => {
    serve({ [DELETE]: STALE_REFUSED });
    render(estimateGrid());
    await choose(LINE, "Supprimer");
    await screen.findByRole("alert");
    await userEvent.click(screen.getByRole("button", { name: "Fermer l’avis" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(labelAt(LINE)).not.toBeInvalid();
  });
});

describe("the keys of the gestures", () => {
  it("inserts a line on Insert, abandons the dialog on Escape with the focus on the cell, and deletes on Ctrl+Delete", async () => {
    const client = serve({ [DELETE]: "node_deleted" });
    render(estimateGrid());
    const cell = await activate(LINE);
    await userEvent.keyboard("{Insert}");
    expect(screen.getByRole("dialog", { name: "Insérer une ligne" })).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
    expect(cell).toHaveFocus();
    await userEvent.keyboard("{Control>}{Delete}{/Control}");
    expect(client.calls.map((call) => call.route)).toEqual([DELETE]);
  });

  it("leaves Insert and Ctrl+Delete to a cell being entered", async () => {
    const client = serve({ [DELETE]: "node_deleted" });
    render(estimateGrid());
    await activate(LINE);
    await userEvent.keyboard("{F2}");
    const input = within(screen.getByRole("treegrid")).getByRole("textbox");
    expect(input).toHaveFocus();
    await userEvent.keyboard("{Insert}{Control>}{Delete}{/Control}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(client.calls).toEqual([]);
  });

  it("inserts a sub-task on Alt+Insert", async () => {
    serve({});
    render(estimateGrid());
    await activate(TASK);
    await userEvent.keyboard("{Alt>}{Insert}{/Alt}");
    expect(screen.getByRole("dialog", { name: "Insérer une sous-tâche" })).toBeInTheDocument();
  });

  it("holds the commands, inactive, while a write is under way", async () => {
    const hold = held();
    serve({ [DELETE]: "node_deleted" }, hold.until);
    render(estimateGrid());
    await choose(LINE, "Supprimer");
    const menu = await openMenu(LINE);
    await waitFor(() => {
      expect(within(menu).getByRole("menuitem", { name: "Supprimer" })).toHaveAttribute(
        "aria-disabled",
        "true",
      );
    });
    await userEvent.keyboard("{Escape}");
    hold.release();
    await screen.findByText("« Raccordement des borniers » supprimée.");
    const after = await openMenu(LINE);
    expect(within(after).getByRole("menuitem", { name: "Supprimer" })).not.toHaveAttribute(
      "aria-disabled",
    );
  });
});

describe("the grids that offer no gesture", () => {
  it("offers none in the estimate the structure does not list available: no menu item, no key [WF-DEV-0050-A]", async () => {
    const client = serve({});
    render(estimateGrid(false, true));
    expect(await offered(TASK)).toEqual([]);
    await activate(TASK);
    await userEvent.keyboard("{Insert}");
    await userEvent.keyboard("{Control>}{Delete}{/Control}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(client.calls).toEqual([]);
  });

  it("offers a line, and no task, in the estimate where the planning is not listed", async () => {
    serve({});
    render(estimateGrid(true, false));
    expect(await offered(TASK)).toEqual(["Insérer une ligne"]);
    expect(await offered(LINE)).toEqual(["Insérer une ligne", "Supprimer"]);
  });

  it("creates tasks in the planning, which has no line", async () => {
    serve({});
    render(planningGrid(planning, true));
    expect(await offered(0)).toEqual(["Insérer au-dessous", "Insérer une sous-tâche", "Supprimer"]);
  });

  it("offers the planning read only no gesture", async () => {
    serve({});
    render(planningGrid(planning, false));
    expect(await offered(0)).toEqual([]);
    expect(screen.queryByRole("button", { name: "Insérer une tâche" })).not.toBeInTheDocument();
  });

  it("creates in the remaining to commit where the structure lists it available, and nowhere else [WF-RAE-0040-A]", async () => {
    serve({});
    const { unmount } = render(remainingGrid(true));
    expect(await offered(TASK)).toEqual([
      "Insérer au-dessous",
      "Insérer une sous-tâche",
      "Insérer une ligne",
      "Supprimer",
    ]);
    unmount();
    // Sur un projet qui n'est pas En cours, la grille ne propose ni création ni suppression.
    const client = serve({});
    const readOnly = render(remainingGrid(false));
    expect(await offered(TASK)).toEqual([]);
    await activate(TASK);
    await userEvent.keyboard("{Insert}{Alt>}{Insert}{/Alt}{Control>}{Insert}{Delete}{/Control}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(client.calls).toEqual([]);
    readOnly.unmount();
    const empty = render(remainingGrid(false, true, example("nodes_empty") as NodeList));
    expect(screen.queryByRole("button", { name: "Insérer une tâche" })).not.toBeInTheDocument();
    empty.unmount();
  });

  it("offers no line where no category can be chosen", async () => {
    serve({});
    render(remainingGrid(true, false));
    expect(await offered(TASK)).toEqual([
      "Insérer au-dessous",
      "Insérer une sous-tâche",
      "Supprimer",
    ]);
  });
});
