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
import { estimateReference } from "@/test/reference";

import { EstimateGrid } from "./estimate-grid";
import type { NodeList, NodeSortColumn } from "./nodes";
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
const LINE =
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/estimate-line";
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
// The sub-project « Essais et mise en service » of the witness project.
const TESTS = "01926f3a-7c00-7000-8000-000000000802";
// A role of the reference data, deactivated.
const AUTOMATION_ENGINEER = "01926f3a-7c00-7000-8000-000000000453";
// The rows of the estimate, by their index: its line of labour, its disbursement, its provision.
const LABOUR = 2;
const DISBURSEMENT = 3;
const PROVISION = 4;
const estimate = example("nodes_estimate") as NodeList;

/** Serve the fake back, and give it back to read its calls. */
function serve(): FakeClient {
  const client = fakeClient({ [LINE]: "estimate_line_updated" });
  server.client = client;
  return client;
}

/** The grid of the estimate on an answer, in French, open to entry. */
function grid(nodes: NodeList) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <EstimateGrid
        nodes={nodes}
        structure={STRUCTURE}
        structureVersion={1}
        reference={estimateReference()}
        editable
        tasksEditable
        query={NO_QUERY}
        filters={{}}
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

/** The writes of lines the grid sent: what was written. */
function written(client: FakeClient) {
  return client.calls.filter((call) => call.route === LINE).map((call) => call.body);
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the sub-project, the payment delay and the deactivated object of a line (#349)", () => {
  it("presents the sub-project and the payment delay of a line as the server gives them, and enters them where the node accepts them", async () => {
    const client = serve();
    const read = structuredClone(estimate);
    const disbursement = read.items[DISBURSEMENT]?.estimate_line;
    if (disbursement !== undefined && disbursement !== null) {
      disbursement.payment_delay_days = 30;
    }
    render(grid(read));
    expect(cell(LABOUR, "subproject")).toHaveTextContent(/^Poste de commande$/);
    expect(cell(PROVISION, "subproject")).toHaveTextContent(/^$/);
    expect(cell(DISBURSEMENT, "payment_delay_days")).toHaveTextContent(/^30$/);
    expect(cell(LABOUR, "payment_delay_days")).toHaveTextContent(/^$/);
    // A line of labour takes no payment delay (WF-DEV-0020); a disbursement does, a whole number
    // of days, which the contract takes as an integer.
    expect(cell(LABOUR, "payment_delay_days")).toHaveAttribute("aria-readonly", "true");
    cell(DISBURSEMENT, "payment_delay_days").focus();
    await userEvent.keyboard("{Enter}");
    const field = screen.getByRole("textbox", { name: "Délai de paiement (j)" });
    expect(field).toHaveValue("30");
    expect(field).toHaveAttribute("inputmode", "numeric");
    await userEvent.clear(field);
    await userEvent.keyboard("1,5{Enter}");
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Ce n’est pas un nombre : saisissez-le comme 30.",
    );
    await userEvent.clear(field);
    await userEvent.keyboard("045{Enter}");
    // The sub-project, from the list of the project; « Aucun » for a line out of any.
    cell(LABOUR, "subproject").focus();
    await userEvent.keyboard("{Enter}");
    const list = screen.getByRole("combobox", { name: "Sous-projet" });
    expect(
      within(list)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["Aucun", "SP-CMD — Poste de commande", "SP-ESS — Essais et mise en service"]);
    await userEvent.selectOptions(list, TESTS);
    await userEvent.keyboard("{Enter}");
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(2);
    });
    expect(written(client)).toEqual([
      { payment_delay_days: 45, lock_version: 1 },
      { subproject_id: TESTS, lock_version: 1 },
    ]);
  });

  it("marks the lines that bear a deactivated role, as the server says it, and keeps them readable [WF-REF-0010-A]", async () => {
    serve();
    // The role « Automaticien », deactivated since the line took it: the server names it, and
    // says the line employs a deactivated object (#305).
    const read = structuredClone(estimate);
    const labour = read.items[LABOUR]?.estimate_line;
    if (labour !== undefined && labour !== null) {
      labour.resource_role_id = AUTOMATION_ENGINEER;
      labour.resource_role_label = "Automaticien";
      labour.uses_inactive_object = true;
    }
    const { container } = render(grid(read));
    expect(screen.getByRole("columnheader", { name: "Objet désactivé" })).toBeInTheDocument();
    expect(
      within(cell(LABOUR, "inactive_object")).getByRole("img", {
        name: "Emploie un objet désactivé",
      }),
    ).toBeInTheDocument();
    // A mark of its own, no zone of the scale of signals.
    expect(
      within(cell(LABOUR, "inactive_object")).queryByRole("img", { name: "Vigilance" }),
    ).toBeNull();
    expect(cell(DISBURSEMENT, "inactive_object")).toBeEmptyDOMElement();
    // The line stays readable: its role by the label the server gives, its figures as they are.
    expect(cell(LABOUR, "resource_role")).toHaveTextContent(/^Automaticien$/);
    expect(cell(LABOUR, "label")).toHaveTextContent("Raccordement des borniers");
    await expectAccessible(container);
  });
});
