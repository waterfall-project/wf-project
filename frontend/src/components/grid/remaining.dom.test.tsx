// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";

import type { NodeFilters, NodeList, NodeSortColumn } from "./nodes";
import type { GridQuery } from "./query";
import { RemainingGrid } from "./remaining-grid";

// The server of Next, as far as the grid needs it, as for the other tests of the grid.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/projects/p/revisions/r/remaining",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined };
const REMAINING =
  "PUT /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/remaining";
const NODES = "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes";
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
// The rows of the estimate of the witness, by their index: the wiring of the cabinets, started,
// its line of labour, its disbursement and its provision; a line of a task completed; the
// factory acceptance, a milestone not started.
const WIRING = 1;
const LABOUR = 2;
const DISBURSEMENT = 3;
const PROVISION = 4;
const COMPLETED_LINE = 7;
const ACCEPTANCE = 10;
// The rows of the studies of the witness: the operator desks, started and past their finish.
const DESKS = 3;

/** Serve the fake back, and give it back to read its calls. */
function serve(): FakeClient {
  const client = fakeClient({ [REMAINING]: "remaining_reestimated", [NODES]: "nodes_estimate" });
  server.client = client;
  return client;
}

/** The grid of the remaining to commit on an answer, in French. */
function grid(
  nodes: NodeList = example("nodes_estimate") as NodeList,
  {
    editable = true,
    filters = { progress: ["started"] },
  }: { editable?: boolean; filters?: NodeFilters } = {},
) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <RemainingGrid
        nodes={nodes}
        structure={STRUCTURE}
        filters={filters}
        editable={editable}
        query={NO_QUERY}
        preferences={undefined}
      />
    </NextIntlClientProvider>
  );
}

/** The cell of a row, by its index among the rows of the answer, and of a column, by its key. */
function cell(row: number, column: string): HTMLElement {
  const found = screen
    .getByRole("grid")
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="${column}"]`);
  if (found === null) {
    throw new Error(`no cell ${column} in the row ${row.toString()}`);
  }
  return found;
}

/** The re-estimations the grid sent: what was written. */
function written(client: FakeClient) {
  return client.calls.filter((call) => call.route === REMAINING).map((call) => call.body);
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the grid of the remaining to commit", () => {
  it("presents of each line its budgeted amount, its figures and its amount re-estimated before and now, the amounts computed [WF-RAE-0040-A]", async () => {
    // Les montants et les grandeurs sont présents pour chaque ligne, au reste à engager précédent
    // et courant: the figures at the previous one first, then those of now (#424).
    serve();
    const { container } = render(grid());
    const table = screen.getByRole("grid", { name: "Grille de reste à engager" });
    const headers = within(table)
      .getAllByRole("columnheader")
      .map((header) => header.textContent);
    expect(headers.filter((name) => /Montant|Qté|Charge|Débours|Réestimé/.test(name))).toEqual([
      expect.stringMatching(/Montant budgété$/),
      "Qté à la revue précédente",
      "Charge (h) à la revue précédente",
      "Débours unit. à la revue précédente",
      expect.stringMatching(/Réestimé à la revue précédente$/),
      "Qté",
      "Charge (h)",
      "Débours unit.",
      expect.stringMatching(/Montant réestimé$/),
    ]);
    for (const name of [
      "Libellé",
      "Avancement",
      "Fin",
      "Fin dépassée",
      "Calculé Montant budgété",
      "Qté à la revue précédente",
      "Charge (h) à la revue précédente",
      "Débours unit. à la revue précédente",
      "Calculé Réestimé à la revue précédente",
      "Qté",
      "Charge (h)",
      "Débours unit.",
      "Calculé Montant réestimé",
    ]) {
      expect(within(table).getByRole("columnheader", { name })).toBeInTheDocument();
    }
    // The figures at the previous remaining to commit, kept by the server and never computed nor
    // entered: none in the witness before its first review.
    for (const column of ["previous_quantity", "previous_hours", "previous_unit_disbursement"]) {
      expect(cell(LABOUR, column)).toHaveTextContent(/^$/);
      expect(cell(LABOUR, column)).toHaveAttribute("aria-readonly", "true");
    }
    // The provision of the risk of rewiring: budgeted at the 250 the reference knew, re-estimated
    // at its 500 now, before any review.
    expect(cell(PROVISION, "budgeted_amount")).toHaveTextContent(/250,00$/);
    expect(cell(PROVISION, "reestimated_amount")).toHaveTextContent(/500,00$/);
    expect(cell(PROVISION, "previous_reestimated_amount")).toHaveAccessibleName(/^Calculé$/);
    expect(cell(LABOUR, "hours")).toHaveTextContent(/^12,5$/);
    expect(cell(DISBURSEMENT, "unit_disbursement")).toHaveTextContent(/^1\s234,56$/);
    // A task: its progress named, its finish shown; no figure of a line.
    expect(within(cell(WIRING, "progress")).getByRole("img", { name: "Démarrée" })).toBeVisible();
    expect(cell(WIRING, "finish")).toHaveTextContent("30/06/2026");
    expect(within(cell(ACCEPTANCE, "progress")).getByRole("img", { name: "Non démarrée" })).toBe(
      within(cell(ACCEPTANCE, "progress")).getByRole("img"),
    );
    // The totals of the answer, never a sum of the rows.
    expect(within(table).getAllByRole("row").at(-1)).toHaveTextContent(
      /^Total — 6 tâches, 5 lignes.*2\s484,56.*12,5.*2\s934,56$/,
    );
    await expectAccessible(container);
  });

  it("re-estimates a figure of a line, the amount following as the server answers it and never entered [WF-RAE-0040-A]", async () => {
    // La saisie d'une charge de 80 heures sur une ligne budgétée à 100 heures donne un montant
    // réestimé de 80 fois le taux ; le montant n'est pas saisissable. Here 10 h on a line budgeted
    // at 12.5 h, the same ratio of four fifths: 10 times the rate of 80.00, 800.00, as the server
    // answers it.
    const client = serve();
    render(grid());
    expect(cell(LABOUR, "reestimated_amount")).toHaveAttribute("aria-readonly", "true");
    cell(LABOUR, "hours").focus();
    await userEvent.keyboard("{Enter}");
    const field = screen.getByRole("textbox", { name: "Charge (h)" });
    expect(field).toHaveValue("12,5");
    await userEvent.clear(field);
    await userEvent.keyboard("10{Enter}");
    await vi.waitFor(() => {
      expect(cell(LABOUR, "reestimated_amount")).toHaveTextContent(/800,00$/);
    });
    expect(written(client)).toEqual([
      { reestimated_amount_basis: { hours: "10" }, lock_version: 1 },
    ]);
    expect(cell(LABOUR, "hours")).toHaveTextContent(/^10$/);
    expect(cell(WIRING, "reestimated_amount")).toHaveTextContent(/2\s534,56$/);
    // The totals of the reading, narrowed to the tasks started, read anew by the same request —
    // never those of the whole structure the write answered.
    await vi.waitFor(() => {
      expect(client.calls.filter((call) => call.route === NODES)).toHaveLength(1);
    });
    const read = client.calls.find((call) => call.route === NODES);
    expect(Object.fromEntries(read?.query ?? [])).toEqual({
      progress: "started",
      fields: "node_id",
    });
    expect(screen.getByRole("grid").querySelector("tfoot")).not.toHaveTextContent(/121\s334,56/);
  });

  it("re-estimates a quantity, and a unit disbursement emptied, each figure alone", async () => {
    const client = serve();
    render(grid());
    cell(DISBURSEMENT, "quantity").focus();
    await userEvent.keyboard("{Enter}");
    await userEvent.clear(screen.getByRole("textbox", { name: "Qté" }));
    await userEvent.keyboard("2{Enter}");
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(1);
    });
    cell(DISBURSEMENT, "unit_disbursement").focus();
    await userEvent.keyboard("{Enter}");
    await userEvent.clear(screen.getByRole("textbox", { name: "Débours unit." }));
    await userEvent.keyboard("{Enter}");
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(2);
    });
    expect(written(client)).toEqual([
      { reestimated_amount_basis: { quantity: "2" }, lock_version: 1 },
      { reestimated_amount_basis: { unit_disbursement: null }, lock_version: 1 },
    ]);
  });

  it("offers no re-estimation of a line of a task completed, nor of the figures of a provision, which the server computes [WF-RAE-0040-A]", () => {
    // La modification d'une ligne portée par une tâche terminée est refusée : the line says it
    // takes none (`remaining_entry`), and the grid offers none.
    serve();
    render(grid());
    expect(cell(COMPLETED_LINE, "unit_disbursement")).toHaveAttribute("aria-readonly", "true");
    expect(cell(COMPLETED_LINE, "quantity")).toHaveAttribute("aria-readonly", "true");
    expect(cell(PROVISION, "unit_disbursement")).toHaveAccessibleName(/^Calculé 500,00$/);
    expect(cell(LABOUR, "unit_disbursement")).toHaveAttribute("aria-readonly", "true");
    expect(cell(LABOUR, "hours")).not.toHaveAttribute("aria-readonly");
  });

  it("marks a task started whose finish is past, as the server says it, and enters no finish [WF-RAE-0040-A]", () => {
    // Une tâche démarrée dont la fin est dépassée est signalée ; sa date n'est pas modifiable
    // depuis cette grille.
    serve();
    render(grid(example("nodes") as NodeList));
    expect(
      within(cell(DESKS, "finish_overdue")).getByRole("img", {
        name: "Tâche démarrée dont la fin est dépassée",
      }),
    ).toBeInTheDocument();
    expect(cell(DESKS - 1, "finish_overdue")).toBeEmptyDOMElement();
    expect(cell(DESKS, "finish")).toHaveTextContent("24/04/2026");
    expect(cell(DESKS, "finish")).toHaveAttribute("aria-readonly", "true");
  });

  it("places undo and redo where the remaining to commit may be entered, and enters nothing elsewhere", () => {
    serve();
    const { unmount } = render(grid());
    expect(screen.getByRole("button", { name: "Annuler" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    expect(screen.getByRole("button", { name: "Rétablir" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );
    unmount();
    render(grid(undefined, { editable: false }));
    expect(screen.queryByRole("button", { name: "Annuler" })).toBeNull();
    expect(cell(LABOUR, "hours")).toHaveAttribute("aria-readonly", "true");
  });
});
