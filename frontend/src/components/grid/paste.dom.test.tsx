// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { formatMoney } from "@/i18n/format";
import { expectAccessible } from "@/test/axe";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
  unreachable,
} from "@/test/fixtures";
import {
  APPLY,
  BLOCK,
  bodies,
  cell,
  copied,
  FIRST,
  LINE,
  LINE_4,
  labels,
  NODES,
  nodes,
  pasteOn,
  PREVIEW,
  READ,
  renderGrid,
  ROW,
  UNKNOWN,
} from "@/test/paste-grid";

import { ROW_NUMBER_KEY } from "./columns";
import type { NodeList } from "./nodes";

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

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}, hold?: Promise<unknown>): FakeClient {
  const client = fakeClient(
    { [PREVIEW]: "paste_plan", [APPLY]: "paste_applied", ...answers },
    { hold: (route) => (route === PREVIEW ? hold : undefined) },
  );
  server.client = client;
  return client;
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

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
  window.sessionStorage.clear();
});

/**
 * The rows a search retains: the lines it names and the tasks above them. Under the first task, the
 * hours of engineering and of commissioning, then the hours of supervision — not the material
 * between them, which the server would fill under the hours of commissioning.
 */
const SEARCH = "Heures";
const retained: NodeList = {
  ...nodes,
  items: nodes.items.filter((node) => node.estimate_line?.label.includes(SEARCH) ?? true),
};
/** The refusals of a block whose rows the grid does not show under its cell, by their cause. */
const UNSHOWN_ROWS = {
  folded:
    "Le bloc collé s’étendrait sur des lignes pliées : dépliez-les avant de coller, ou collez un bloc moins haut.",
  sorted:
    "Le bloc collé écrirait les lignes qui suivent la cellule dans l’ordre du plan, que le tri a déplacées : levez le tri avant de coller, ou collez un bloc moins haut.",
  unretained:
    "Le bloc collé écrirait dans des lignes du plan que la recherche ou le filtre cache : levez la recherche ou le filtre avant de coller, ou collez un bloc moins haut.",
  beyond:
    "Le bloc collé s’étendrait au-delà des lignes que la grille montre sous la cellule : collez un bloc moins haut.",
};

/**
 * The estimate of the control station sorted by amount, descending, as the server answers it:
 * the lines reordered under each task, the tasks in the order of the tree (#526).
 */
const estimateSorted = example("nodes_estimate_sorted") as NodeList;
const BY_AMOUNT = { column: "base_amount", order: "desc" } as const;

/**
 * The same estimate sorted by hours, descending: under the wiring, the disbursement and the
 * provision, which have no hours, first in the order of the plan, then the labour (#526).
 */
const estimateHours = example("nodes_estimate_hours") as NodeList;
const BY_HOURS = { column: "hours", order: "desc" } as const;

/** The index of a line of the estimate sorted by hours, found by its label in the example. */
function hoursLine(label: string): number {
  return estimateHours.items.findIndex((node) => node.estimate_line?.label === label);
}

/** Paste a block on a cell, and expect it refused, saying why, nothing asked. */
async function expectRefused(client: FakeClient, target: HTMLElement, text: string, why: string) {
  await pasteOn(target, text);
  expect(await screen.findByRole("alert")).toHaveTextContent(why);
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(bodies(client, PREVIEW)).toEqual([]);
}

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
    expect(totalAmount()).toBe("66\u202f144\u202f071,71");
    // The total corrected for inflation, as the server answered it: lines of later years in it.
    expect(totalInflated()).toBe("68\u202f962\u202f538,88");
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
    // The row refused, by its place in the block, its reason, and its cells as copied; the other
    // two to be written, the confirmation writing them alone (EP-14/L42q).
    expect(await within(dialog).findByText("2 lignes seront écrites.")).toBeVisible();
    expect(within(dialog).getByText("1 ligne est refusée :")).toBeVisible();
    const refused = within(dialog).getByRole("listitem");
    expect(refused).toHaveTextContent("Ligne 2 du bloc — Catégorie de coût inconnue.");
    expect(within(refused).getByText("Essais")).toBeVisible();
    expect(
      within(dialog).getByText(/^Confirmé, le collage écrit les lignes valides/),
    ).toBeVisible();
    expect(within(dialog).getByRole("button", { name: "Appliquer le collage" })).toBeVisible();
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
      {
        [PREVIEW]: ["paste_plan", "paste_plan_unknown_category"],
        [APPLY]: "paste_applied_partial",
      },
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
    // second's — a plan that refuses a row — and its confirmation applies the second's alone.
    await pasteOn(cell(FIRST, "label"), copied(UNKNOWN));
    const second = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    await within(second).findByText("1 ligne est refusée :");
    await act(async () => {
      release();
      await held;
    });
    expect(within(second).getByText("1 ligne est refusée :")).toBeVisible();
    expect(within(second).getByText("2 lignes seront écrites.")).toBeVisible();
    expect(bodies(client, APPLY)).toEqual([]);
    await userEvent.click(within(second).getByRole("button", { name: "Appliquer le collage" }));
    await vi.waitFor(() => {
      expect(bodies(client, APPLY)).toEqual([
        { paste_id: "01926f3a-7c00-7000-8000-000000000992", confirmed: true, lock_version: 1 },
      ]);
    });
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
    expect(totalAmount()).toBe("66\u202f144\u202f071,71");
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
    expect(totalAmount()).toBe("66\u202f144\u202f071,71");
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

  it("reaching a row of the plan the search hides is refused, saying so, and no preview is asked (#527)", async () => {
    const client = serve();
    const commissioning = retained.items.findIndex((node) => node.row_number === ROW + 1);
    expect(retained.items[commissioning + 1]?.row_number).toBeGreaterThan(ROW + 2);
    renderGrid(true, undefined, { search: SEARCH, nodes: retained });
    await expectRefused(client, cell(commissioning, "label"), "a\nb", UNSHOWN_ROWS.unretained);
    // A block of one row writes the line pasted on alone; a block of two rows from the line above,
    // the next row of the plan shown, writes the two lines the grid shows: both asked.
    await pasteOn(cell(commissioning, "label"), "a");
    await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    await userEvent.keyboard("{Escape}");
    await pasteOn(cell(commissioning - 1, "label"), "a\nb");
    await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    expect(bodies(client, PREVIEW)).toEqual([
      {
        target_node_id: retained.items[commissioning]?.node_id,
        target_column: "label",
        rows: [["a"]],
      },
      { target_node_id: LINE_4, target_column: "label", rows: [["a"], ["b"]] },
    ]);
  });

  it("reaching a row of the plan the sort moved is refused, saying so, and no preview is asked (#527)", async () => {
    const client = serve();
    // Sorted by amount, the lines of the first task come back reordered under it: the material
    // first, then the hours of engineering and of commissioning. Under the material, the grid shows
    // the hours of engineering, where the server would write the subcontracting, next in the plan.
    const lines = nodes.items.slice(FIRST, FIRST + 3);
    const [engineering, commissioning, material] = lines;
    const sorted: NodeList = {
      ...nodes,
      items: [
        ...nodes.items.slice(0, FIRST),
        ...(material === undefined ? [] : [material]),
        ...(engineering === undefined ? [] : [engineering]),
        ...(commissioning === undefined ? [] : [commissioning]),
        ...nodes.items.slice(FIRST + 3),
      ],
    };
    const sort = { column: "base_amount", order: "asc" } as const;
    renderGrid(true, undefined, { nodes: sorted, sort });
    expect(cell(FIRST, "label")).toHaveTextContent("Matériel");
    await expectRefused(client, cell(FIRST, "label"), "a\nb", UNSHOWN_ROWS.sorted);
    // From the hours of engineering, the hours of commissioning follow in the plan as on the
    // screen: asked.
    await pasteOn(cell(FIRST + 1, "label"), "a\nb");
    await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    expect(bodies(client, PREVIEW)).toEqual([
      { target_node_id: LINE_4, target_column: "label", rows: [["a"], ["b"]] },
    ]);
  });

  it("reaching past the last row shown is refused alike, with a search or without", async () => {
    // Without a search, from the last row of the answer.
    const client = serve();
    const { unmount } = renderGrid();
    await expectRefused(client, cell(nodes.items.length - 1, "label"), "a\nb", UNSHOWN_ROWS.beyond);
    unmount();
    // Under the search, from the last row it retains: the end of the plan, or rows the search left
    // out — the grid cannot tell which, and says neither.
    renderGrid(true, undefined, { search: SEARCH, nodes: retained });
    await expectRefused(
      client,
      cell(retained.items.length - 1, "label"),
      "a\nb",
      UNSHOWN_ROWS.beyond,
    );
  });

  it("tells a row folded away before the search that leaves out others in the same span", async () => {
    const client = serve();
    renderGrid(true, undefined, { search: SEARCH, nodes: retained });
    // The first task folded over its lines: from the task above it, a block of five rows would
    // fill the task, its hours of engineering and of commissioning, folded away, then the material
    // the search hides.
    const task = retained.items.findIndex((node) => node.row_number === ROW - 1);
    expect(retained.items.some((node) => node.row_number === ROW + 2)).toBe(false);
    await userEvent.click(within(cell(task, "label")).getByRole("button"));
    await expectRefused(client, cell(task - 1, "label"), "a\nb\nc\nd\ne", UNSHOWN_ROWS.folded);
  });

  it("tells the sort of a row of the plan shown above the cell, the cell the last row shown", async () => {
    const client = serve();
    // Sorted, the lines of the last task come back with its first line, the highest in the plan,
    // last of all: the next row of the plan is shown, above it.
    const at = nodes.items.length - 3;
    const [first, ...others] = nodes.items.slice(at);
    const sorted: NodeList = {
      ...nodes,
      items: [...nodes.items.slice(0, at), ...others, ...(first === undefined ? [] : [first])],
    };
    renderGrid(true, undefined, { nodes: sorted, sort: { column: "base_amount", order: "asc" } });
    await expectRefused(client, cell(nodes.items.length - 1, "label"), "a\nb", UNSHOWN_ROWS.sorted);
  });

  it("shows the estimate sorted by amount in the order of the answer, the lines reordered under each task and the tasks in place [WF-IHM-0060-A]", () => {
    // Dans la grille de devis, le tri par montant réordonne les lignes sous chaque tâche sans
    // déplacer les tâches: the server sorts (`estimate_sorted`, #526), the grid shows its order.
    serve();
    renderGrid(true, undefined, { nodes: estimateSorted, sort: BY_AMOUNT });
    const rows = estimateSorted.items.map((_, row) => cell(row, ROW_NUMBER_KEY).textContent);
    // Under the wiring, the provision, the terminal blocks, then the labour: the plan reversed.
    expect(rows).toEqual(["8", "9", "12", "11", "10", "13", "14", "15", "16", "17", "18"]);
    const wiring = estimateSorted.items.slice(2, 5).map((node) => node.estimate_line?.base_amount);
    const values = wiring.map(Number);
    expect(values).toEqual([...values].sort((a, b) => b - a));
    expect(amounts([2, 3, 4])).toEqual(wiring.map((amount) => formatMoney(amount ?? "", "fr")));
    // The factory acceptance, a milestone of no amount, stays the last, as in the tree.
    expect(cell(estimateSorted.items.length - 1, "label")).toHaveTextContent("Réception usine");
  });

  it("refuses a block from the line the sort of the estimate moved under its task, saying so, and takes one whose rows follow in the plan (#526)", async () => {
    const client = serve();
    renderGrid(true, undefined, { nodes: estimateHours, sort: BY_HOURS });
    // From the provision, moved before the labour, a block of two rows would write the row after
    // it in the plan, the next task, where the grid shows the labour: refused (L41a).
    const provision = hoursLine("Provision — risque de reprise du câblage");
    await expectRefused(client, cell(provision, "label"), "a\nb", UNSHOWN_ROWS.sorted);
    // From the terminal blocks, the provision follows in the plan as on the screen: asked.
    const blocks = hoursLine("Borniers");
    await pasteOn(cell(blocks, "label"), "a\nb");
    await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    expect(bodies(client, PREVIEW)).toEqual([
      {
        target_node_id: estimateHours.items[blocks]?.node_id,
        target_column: "label",
        rows: [["a"], ["b"]],
      },
    ]);
  });

  it("tells the search that leaves out the next row of the plan, under a sort that moves nothing", async () => {
    const client = serve();
    const commissioning = retained.items.findIndex((node) => node.row_number === ROW + 1);
    renderGrid(true, undefined, {
      search: SEARCH,
      nodes: retained,
      sort: { column: "base_amount", order: "asc" },
    });
    expect(cell(commissioning, "label")).toHaveTextContent("Heures de mise en service");
    await expectRefused(client, cell(commissioning, "label"), "a\nb", UNSHOWN_ROWS.unretained);
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
