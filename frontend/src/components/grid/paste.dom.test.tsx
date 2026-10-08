// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
  unreachable,
} from "@/test/fixtures";
import { estimateReference } from "@/test/reference";

import type { GridPreferences } from "./settings";

import { EstimateGrid } from "./estimate-grid";
import type { NodeList, NodeSortColumn, NodesWritten } from "./nodes";
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
const PREVIEW =
  "POST /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste-preview";
const APPLY =
  "POST /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste";
const LINE =
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/estimate-line";
// The main structure of the current revision of the witness project, and its version, as
// `listCostStructures` gives them.
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const STRUCTURE_VERSION = 1;
const NODES = `/projects/${STRUCTURE.project_id}/revisions/${STRUCTURE.revision_id}/structures/${STRUCTURE.structure_id}/nodes`;

// Twelve rows of the structure the fake back serves, from the first phase drawn after the core:
// the phase, its lot, its first task, then its lines « Heures d'ingénierie », « Heures de mise en
// service » and « Matériel », on which the rows applied of the examples land (`paste_applied`),
// found by their identifiers in the examples, never by a number written here (#400).
const volume = example("volume/nodes_thousand") as NodeList;
const LINE_4 = (example("paste_applied") as NodesWritten).nodes[0]?.node_id ?? "";
const FIRST = 3;
const START = volume.items.findIndex((node) => node.node_id === LINE_4) - FIRST;
const nodes: NodeList = { ...volume, items: volume.items.slice(START, START + 12) };
// The number of the first line written, as the structure numbers it.
const ROW = nodes.items[FIRST]?.row_number ?? 0;

// A block of three rows and four columns — label, category, role, quantity —, as a spreadsheet
// copies it; the same, its second row naming a category the reference does not know.
const BLOCK = [
  ["Heures de câblage et repérage", "Ingénierie électrique", "Ingénieur électricien", "1"],
  ["Heures d'essais", "Mise en service", "Technicien de mise en service", "1"],
  ["Matériel de câblage", "Matériel électrique", "", "24"],
];
const UNKNOWN = [BLOCK[0] ?? [], ["Heures d'essais", "Essais", "", "1"], BLOCK[2] ?? []];

/** A block as the clipboard holds it: tab-separated values, each row ended. */
function copied(block: readonly (readonly string[])[]): string {
  return block.map((row) => `${row.join("\t")}\n`).join("");
}

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}, hold?: Promise<unknown>): FakeClient {
  const client = fakeClient(
    { [PREVIEW]: "paste_plan", [APPLY]: "paste_applied", ...answers },
    { hold: (route) => (route === PREVIEW ? hold : undefined) },
  );
  server.client = client;
  return client;
}

/** The grid of the estimate on the rows, open to entry or not, with the settings kept if any. */
function renderGrid(editable = true, preferences?: GridPreferences) {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <EstimateGrid
        filters={{}}
        nodes={nodes}
        structure={STRUCTURE}
        structureVersion={STRUCTURE_VERSION}
        reference={estimateReference()}
        editable={editable}
        tasksEditable
        query={NO_QUERY}
        preferences={preferences}
      />
    </NextIntlClientProvider>,
  );
}

/** The cell of a row, by its index among the rows of the answer, and of a column, by its key. */
function cell(row: number, column: string): HTMLElement {
  const found = screen
    .getByRole("treegrid", { hidden: true })
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="${column}"]`);
  if (found === null) {
    throw new Error(`no cell ${column} in the row ${row.toString()}`);
  }
  return found;
}

/** The labels of the rows 4 to 6. */
function labels(): string[] {
  return [0, 1, 2].map((offset) => cell(FIRST + offset, "label").textContent);
}

/** The amounts at the year of reference of rows, by their index, without the mark Σ. */
function amounts(rows: readonly number[]): string[] {
  return rows.map((row) => cell(row, "base_amount").textContent.replace(/^Calculé/, ""));
}

/** The total amount at the year of reference, at the foot of the grid. */
function totalAmount(): string | null | undefined {
  const row = screen.getByRole("treegrid", { hidden: true }).querySelector("tfoot tr");
  return row?.querySelectorAll("td")[10]?.textContent;
}

/** The total amount corrected for inflation, at the foot of the grid. */
function totalInflated(): string | null | undefined {
  const row = screen.getByRole("treegrid", { hidden: true }).querySelector("tfoot tr");
  return row?.querySelectorAll("td")[11]?.textContent;
}

/** Paste a block on a cell, as the browser hands it at the event `paste`. */
async function pasteOn(target: HTMLElement, text: string): Promise<void> {
  target.focus();
  await userEvent.paste(text);
}

/** The bodies a route was called with. */
function bodies(client: FakeClient, route: string): unknown[] {
  return client.calls.filter((call) => call.route === route).map((call) => call.body);
}

const READ = ["Heures d'ingénierie", "Heures de mise en service", "Matériel"];

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("a block pasted from a spreadsheet", () => {
  it("of three rows and four columns produces a report before writing, then the three rows expected once confirmed [WF-IHM-0050-A]", async () => {
    const client = serve();
    renderGrid();
    await pasteOn(cell(FIRST, "label"), copied(BLOCK));

    // The server is asked the plan of the block as copied, from the node and column of the cell.
    const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    expect(bodies(client, PREVIEW)).toEqual([
      { target_node_id: LINE_4, target_column: "label", rows: BLOCK },
    ]);
    expect(client.calls[0]?.path).toBe(`${NODES}/paste-preview`);
    // The report says what was pasted, from where, and what the server would write and refuse.
    expect(dialog).toHaveAccessibleDescription(
      `Bloc de 3 lignes sur 4 colonnes, à partir de la ligne ${ROW.toString()}, colonne « Libellé » : rien n’est écrit avant votre confirmation.`,
    );
    // One announced region holds the waiting, then the report.
    await within(dialog).findByText("3 lignes seront écrites.");
    expect(within(dialog).getByRole("status")).toHaveTextContent("3 lignes seront écrites.");
    expect(within(dialog).getByText("Aucune ligne n’est refusée.")).toBeVisible();
    // Nothing is written before the confirmation.
    expect(bodies(client, APPLY)).toEqual([]);
    expect(labels()).toEqual(READ);
    await expectAccessible(dialog);

    await userEvent.click(within(dialog).getByRole("button", { name: "Appliquer le collage" }));
    // One operation, the plan confirmed with the version of the structure read.
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(bodies(client, APPLY)).toEqual([
      { paste_id: "01926f3a-7c00-7000-8000-000000000991", confirmed: true, lock_version: 1 },
    ]);
    expect(client.calls.at(-1)?.path).toBe(`${NODES}/paste`);
    // The three rows the server wrote, in place of those read.
    expect(labels()).toEqual([
      "Heures de câblage et repérage",
      "Heures d'essais",
      "Matériel de câblage",
    ]);
    expect(cell(FIRST + 2, "quantity")).toHaveTextContent("24");
    expect(cell(FIRST + 2, "base_amount")).toHaveTextContent(/^42\s379,44/);
    expect(cell(FIRST + 2, "inflated_amount")).toHaveTextContent(/^42\s379,44/);
    // The tasks above them, recalculated, and the totals of the structure, as the server answered.
    expect(amounts([0, 1, 2])).toEqual([
      "7\u202f469\u202f299,12",
      "2\u202f607\u202f299,00",
      "63\u202f757,17",
    ]);
    expect(totalAmount()).toBe("65\u202f644\u202f571,71");
    // The total corrected for inflation, as the server answered it: lines of later years in it.
    expect(totalInflated()).toBe("68\u202f463\u202f038,88");
    expect(screen.queryByRole("alert")).toBeNull();
    await vi.waitFor(() => {
      expect(cell(FIRST, "label")).toHaveFocus();
    });
  });

  it("whose cell names an unknown category signals that row, and modifies no row once abandoned [WF-IHM-0050-A]", async () => {
    const client = serve({ [PREVIEW]: "paste_plan_unknown_category" });
    renderGrid();
    await pasteOn(cell(FIRST, "label"), copied(UNKNOWN));

    const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    expect(bodies(client, PREVIEW)).toEqual([
      { target_node_id: LINE_4, target_column: "label", rows: UNKNOWN },
    ]);
    // The row refused, by its place in the block, its reason, and its cells as copied; the
    // report promises no write, since a refused row blocks the whole of it.
    expect(
      await within(dialog).findByText(
        "2 lignes sont valides ; rien ne sera écrit tant qu’une ligne est refusée.",
      ),
    ).toBeVisible();
    expect(within(dialog).getByText("1 ligne est refusée :")).toBeVisible();
    const refused = within(dialog).getByRole("listitem");
    expect(refused).toHaveTextContent("Ligne 2 du bloc — Catégorie de coût inconnue.");
    expect(within(refused).getByText("Essais")).toBeVisible();
    // A paste partly invalid is not applied: abandoning it is all the dialog offers.
    expect(within(dialog).queryByRole("button", { name: "Appliquer le collage" })).toBeNull();
    expect(within(dialog).getByText(/la grille reste inchangée/)).toBeVisible();
    await expectAccessible(dialog);

    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(bodies(client, APPLY)).toEqual([]);
    expect(labels()).toEqual(READ);
    await vi.waitFor(() => {
      expect(cell(FIRST, "label")).toHaveFocus();
    });
  });

  it("is abandoned by its button too, a plan that refuses nothing left unapplied [WF-IHM-0050-A]", async () => {
    const client = serve();
    renderGrid();
    await pasteOn(cell(FIRST, "label"), copied(BLOCK));
    const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    await within(dialog).findByText("3 lignes seront écrites.");
    await userEvent.click(within(dialog).getByRole("button", { name: "Abandonner" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(bodies(client, APPLY)).toEqual([]);
    expect(labels()).toEqual(READ);
  });

  it("wider than the grid from its cell is refused, saying so, and nothing is asked [WF-IHM-0050-A]", async () => {
    const client = serve();
    renderGrid();
    // Eighteen columns from the label, where a line has seventeen in the contract (#223, #424). The
    // browser aims the event at the text of the cell a click left the caret in, the cell keeping
    // the focus.
    const wide = BLOCK.map((row) => [...row, ...Array.from({ length: 14 }, () => "")]);
    const label = cell(FIRST, "label");
    label.focus();
    const text = label.querySelector(".truncate") ?? label;
    fireEvent.paste(text, { clipboardData: { getData: () => copied(wide) } });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Les données collées ont plus de colonnes que la grille.");
    expect(alert).toHaveTextContent(
      "La grille accepte au plus 17 colonnes à partir de cette cellule.",
    );
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(client.calls).toEqual([]);
    expect(labels()).toEqual(READ);
  });

  it("wider than the grid as the server sees it is refused, saying so [WF-IHM-0050-A]", async () => {
    const tooWide = example("paste_too_wide") as Problem & { readonly status: 422 };
    const client = serve({ [PREVIEW]: { problem: tooWide } });
    renderGrid();
    await pasteOn(cell(FIRST, "quantity"), copied([["2", "33"]]));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Les données collées ont plus de colonnes que la grille.");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(bodies(client, PREVIEW)).toEqual([
      { target_node_id: LINE_4, target_column: "quantity", rows: [["2", "33"]] },
    ]);
    expect(bodies(client, APPLY)).toEqual([]);
  });

  it("is not offered on a grid read only: nothing is asked, no report shows", async () => {
    const client = serve();
    renderGrid(false);
    await pasteOn(cell(FIRST, "label"), copied(BLOCK));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(client.calls).toEqual([]);
    expect(labels()).toEqual(READ);
  });

  it("shows, after an abandon, the plan of the next paste, never the first's answered late", async () => {
    let release: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    const client = fakeClient(
      { [PREVIEW]: ["paste_plan", "paste_plan_unknown_category"], [APPLY]: "paste_applied" },
      { hold: (route, index) => (route === PREVIEW && index === 0 ? held : undefined) },
    );
    server.client = client;
    renderGrid();
    await pasteOn(cell(FIRST, "label"), copied(BLOCK));
    const first = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    expect(within(first).getByRole("status")).toHaveTextContent("Lecture du compte rendu…");
    expect(within(first).queryByRole("button", { name: "Appliquer le collage" })).toBeNull();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();

    // A second block is pasted; the plan of the first arrives then: the report stays the
    // second's — a plan that refuses a row — and never offers to apply the first's.
    await pasteOn(cell(FIRST, "label"), copied(UNKNOWN));
    const second = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    await within(second).findByText("1 ligne est refusée :");
    await act(async () => {
      release();
      await held;
    });
    expect(within(second).getByText("1 ligne est refusée :")).toBeVisible();
    expect(within(second).queryByRole("button", { name: "Appliquer le collage" })).toBeNull();
    expect(bodies(client, APPLY)).toEqual([]);
  });

  it("tells nothing of a preview the server refused once it was abandoned", async () => {
    let release: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    const tooWide = example("paste_too_wide") as Problem & { readonly status: 422 };
    const client = serve({ [PREVIEW]: { problem: tooWide } }, held);
    renderGrid();
    await pasteOn(cell(FIRST, "quantity"), copied([["2", "33"]]));
    await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    await userEvent.keyboard("{Escape}");
    await act(async () => {
      release();
      await held;
    });
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(bodies(client, APPLY)).toEqual([]);
  });

  it("keeps what a paste answered when a cell written before it answers after it, earlier in the structure: its rows, the tasks above them, the totals (#421)", async () => {
    let release: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    // The paste answers the structure at its version 4, the cell written before it at 3 (#421).
    const client = fakeClient(
      { [PREVIEW]: "paste_plan", [APPLY]: "paste_applied", [LINE]: "estimate_line_entered" },
      { hold: (route) => (route === LINE ? held : undefined) },
    );
    server.client = client;
    renderGrid();
    // The label of the row 4 is entered and validated: its write leaves, the server yet to
    // answer; the block is then pasted on the same row and confirmed, and answers first.
    cell(FIRST, "label").focus();
    await userEvent.keyboard("X{Enter}");
    await pasteOn(cell(FIRST, "label"), copied(BLOCK));
    const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    await userEvent.click(
      await within(dialog).findByRole("button", { name: "Appliquer le collage" }),
    );
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    // The paste answered first: its rows shown, the cell under way showing what was validated.
    expect(labels()).toEqual(["X", "Heures d'essais", "Matériel de câblage"]);
    // The write answers after it, earlier in the structure: it takes back none of the paste's.
    await act(async () => {
      release();
      await held;
    });
    await vi.waitFor(() => {
      expect(labels()).toEqual([
        "Heures de câblage et repérage",
        "Heures d'essais",
        "Matériel de câblage",
      ]);
    });
    expect(amounts([0, 1, 2])).toEqual([
      "7\u202f469\u202f299,12",
      "2\u202f607\u202f299,00",
      "63\u202f757,17",
    ]);
    expect(totalAmount()).toBe("65\u202f644\u202f571,71");
    expect(bodies(client, LINE)).toEqual([{ label: "X", lock_version: 1 }]);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  /**
   * Write the label of rows, each refused in turn, the server answering none until a block pasted
   * on the row 4 is applied; then let them answer.
   */
  async function refusedAroundPaste(
    rows: readonly number[],
    refusals: NonNullable<FakeAnswers[typeof LINE]>,
  ): Promise<FakeClient> {
    let release: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    const client = fakeClient(
      { [PREVIEW]: "paste_plan", [APPLY]: "paste_applied", [LINE]: refusals },
      { hold: (route) => (route === LINE ? held : undefined) },
    );
    server.client = client;
    renderGrid();
    for (const row of rows) {
      cell(row, "label").focus();
      await userEvent.keyboard("X{Enter}");
    }
    await pasteOn(cell(FIRST, "label"), copied(BLOCK));
    const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    await userEvent.click(
      await within(dialog).findByRole("button", { name: "Appliquer le collage" }),
    );
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    await act(async () => {
      release();
      await held;
    });
    // Each write answered: no cell shows what was validated any more.
    await vi.waitFor(() => {
      expect(screen.getByRole("treegrid").querySelector('[aria-busy="true"]')).toBeNull();
    });
    return client;
  }

  const STALE = { problem: { code: "STALE_LOCK_VERSION", status: 412 } } as const;
  const MARKED = { problem: { code: "REVISION_MARKED", status: 409 } } as const;

  it("keeps quiet the refusal of a cell written before a paste of its row (#202)", async () => {
    await refusedAroundPaste([FIRST], [STALE]);
    expect(labels()[0]).toBe("Heures de câblage et repérage");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("tells the refusal of a row the paste did not write, whatever the quiet refusal answered after it (#202)", async () => {
    // The row 8, out of the block, is refused first; the row 4, which the paste wrote, last.
    const client = await refusedAroundPaste([FIRST + 4, FIRST], [MARKED, STALE]);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(/marquée/);
    expect(alert).not.toHaveTextContent(/modifié cette donnée/);
    expect(labels()[0]).toBe("Heures de câblage et repérage");
    expect(bodies(client, LINE)).toHaveLength(2);
  });

  it("carries the highest version of the structure told, and keeps what the later paste answered, whatever the order the answers come back in (#421)", async () => {
    let releaseLine: () => void = () => undefined;
    const heldLine = new Promise<void>((resolve) => {
      releaseLine = resolve;
    });
    let releaseApply: () => void = () => undefined;
    const heldApply = new Promise<void>((resolve) => {
      releaseApply = resolve;
    });
    // The cell written answers the structure at its version 3, the paste that follows it at 4.
    const client = fakeClient(
      { [PREVIEW]: "paste_plan", [APPLY]: "paste_applied", [LINE]: "estimate_line_entered" },
      {
        hold: (route, index) =>
          route === LINE ? heldLine : route === APPLY && index === 0 ? heldApply : undefined,
      },
    );
    server.client = client;
    renderGrid();
    cell(FIRST, "label").focus();
    await userEvent.keyboard("X{Enter}");
    await pasteOn(cell(FIRST, "label"), copied(BLOCK));
    const first = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    await userEvent.click(
      await within(first).findByRole("button", { name: "Appliquer le collage" }),
    );
    // The write answers first, version 3; the paste answers after it, version 4.
    await act(async () => {
      releaseLine();
      await heldLine;
    });
    await act(async () => {
      releaseApply();
      await heldApply;
    });
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    // The paste, later in the structure, shows its rows, the tasks above them and the totals.
    expect(labels()).toEqual([
      "Heures de câblage et repérage",
      "Heures d'essais",
      "Matériel de câblage",
    ]);
    expect(amounts([0, 1, 2])).toEqual([
      "7\u202f469\u202f299,12",
      "2\u202f607\u202f299,00",
      "63\u202f757,17",
    ]);
    expect(totalAmount()).toBe("65\u202f644\u202f571,71");
    await pasteOn(cell(FIRST, "label"), copied(BLOCK));
    const second = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    await userEvent.click(
      await within(second).findByRole("button", { name: "Appliquer le collage" }),
    );
    await vi.waitFor(() => {
      expect(bodies(client, APPLY)).toHaveLength(2);
    });
    expect(
      bodies(client, APPLY).map((body) => (body as { lock_version: number }).lock_version),
    ).toEqual([1, 4]);
  });

  it("whose span reaches a column of the contract the grid does not present is refused, naming it, and nothing is asked [WF-IHM-0050-A]", async () => {
    const client = serve();
    renderGrid();
    // After the payment delay, the server fills the year of consumption, which the grid of the
    // estimate does not present: where the user saw the amount (#223).
    await pasteOn(cell(FIRST, "payment_delay_days"), copied([["12", "3"]]));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "Le bloc collé s’étendrait sur la colonne « Année de consommation », que cette grille ne présente pas : collez un bloc plus étroit.",
    );
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(client.calls).toEqual([]);
    // The block of one column is asked.
    await pasteOn(cell(FIRST, "payment_delay_days"), copied([["12"]]));
    await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    expect(bodies(client, PREVIEW)).toEqual([
      { target_node_id: LINE_4, target_column: "payment_delay_days", rows: [["12"]] },
    ]);
  });

  it("whose span crosses a hidden column is refused, naming it, and nothing is asked", async () => {
    const client = serve();
    // The role hidden: the server would fill it where the user saw the quantity (#200).
    renderGrid(true, { hidden_columns: ["resource_role"] });
    await pasteOn(cell(FIRST, "label"), copied(BLOCK));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "Le bloc collé s’étendrait sous la colonne « Rôle », qui est masquée : affichez-la avant de coller, ou collez un bloc plus étroit.",
    );
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(client.calls).toEqual([]);
    expect(labels()).toEqual(READ);
  });

  it("from the column of the row numbers lands on the first column, the label", async () => {
    const client = serve();
    renderGrid();
    await pasteOn(cell(FIRST, "row_number"), copied(BLOCK));
    await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    expect(bodies(client, PREVIEW)).toEqual([
      { target_node_id: LINE_4, target_column: "label", rows: BLOCK },
    ]);
  });

  it("is taken at the document, wherever the browser aims the event, the cell told by the focus", async () => {
    const client = serve();
    renderGrid();
    cell(FIRST, "label").focus();
    const header = screen.getByRole("columnheader", { name: "Libellé" });
    fireEvent.paste(header, { clipboardData: { getData: () => copied(BLOCK) } });
    await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    expect(bodies(client, PREVIEW)).toEqual([
      { target_node_id: LINE_4, target_column: "label", rows: BLOCK },
    ]);
  });

  it("tells the API out of reach at the confirmation, the grid left as it was", async () => {
    const client = fakeClient(
      { [PREVIEW]: "paste_plan", [APPLY]: "paste_applied" },
      {
        // The browser could not reach the server of Next: its `fetch` rejected (`rejected`).
        hold: (route) =>
          route === APPLY ? Promise.reject(new TypeError("Failed to fetch")) : undefined,
      },
    );
    server.client = client;
    renderGrid();
    await pasteOn(cell(FIRST, "label"), copied(BLOCK));
    const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    await userEvent.click(
      await within(dialog).findByRole("button", { name: "Appliquer le collage" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("Le service est injoignable");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(labels()).toEqual(READ);
  });

  it("tells a confirmation the server refuses, the grid left as it was", async () => {
    serve({ [APPLY]: { problem: { code: "STATE_FORBIDS_OPERATION", status: 409 } } });
    renderGrid();
    await pasteOn(cell(FIRST, "label"), copied(BLOCK));
    const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    await userEvent.click(
      await within(dialog).findByRole("button", { name: "Appliquer le collage" }),
    );
    expect(await screen.findByRole("alert")).toBeVisible();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(labels()).toEqual(READ);
  });

  it("tells the API out of reach, and takes nothing pasted in an entry under way", async () => {
    server.client = unreachable();
    renderGrid();
    await pasteOn(cell(FIRST, "label"), copied(BLOCK));
    expect(await screen.findByRole("alert")).toHaveTextContent("Le service est injoignable");
    expect(screen.queryByRole("dialog")).toBeNull();

    // In the field of a cell entered, a paste is the field's.
    await vi.waitFor(() => {
      expect(cell(FIRST, "label")).toHaveFocus();
    });
    await userEvent.keyboard("{Enter}");
    const field = screen.getByRole("textbox", { name: "Libellé" });
    await userEvent.clear(field);
    await userEvent.paste("Heures");
    expect(field).toHaveValue("Heures");
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
