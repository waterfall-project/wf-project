// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeClient, fakeClient, type Problem } from "@/test/fixtures";
import { estimateReference } from "@/test/reference";
import { SHOWN } from "@/test/grid-preferences";

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

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined, size: undefined };
const LINE =
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/estimate-line";
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
// A role of the reference data, deactivated.
const AUTOMATION_ENGINEER = "01926f3a-7c00-7000-8000-000000000453";
// The rows of the estimate, by their index: its line of labour, its disbursement, its provision.
const LABOUR = 2;
const DISBURSEMENT = 3;
const PROVISION = 4;
// A line out of any sub-project, so none with actual costs to keep it: « Frais de relance ».
const REMINDER = 7;
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
        preferences={SHOWN}
      />
    </NextIntlClientProvider>
  );
}

/** The cell of a row, by its index among the rows of the answer, and of a column, by its key. */
function cell(row: number, column: string): HTMLElement {
  const found = screen
    .getByRole("treegrid")
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

describe("the refusal of a cell that would leave a task without a working hour (#779)", () => {
  it("names the task by its label and the role by the label the grid knows, from the refusal of the contract [WF-PLA-0010-A]", async () => {
    const client = fakeClient({
      [LINE]: { problem: example("estimate_line_without_hours") as Problem & { status: 422 } },
    });
    server.client = client;
    render(grid(estimate));
    cell(LABOUR, "resource_role").focus();
    await userEvent.keyboard("{Enter}");
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Rôle" }),
      "Monteur câbleur",
    );
    await userEvent.keyboard("{Tab}");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Une tâche n’aurait plus aucune heure travaillée");
    expect(alert).toHaveTextContent("Rôle dont le calendrier n’a aucune heure");
    expect(alert).toHaveTextContent("Monteur câbleur");
    expect(alert).toHaveTextContent("Tâche en cause");
    expect(alert).toHaveTextContent("Câblage des armoires");
    expect(written(client)).toEqual([
      { resource_role_id: "01926f3a-7c00-7000-8000-000000000454", lock_version: 1 },
    ]);
  });

  it("says the roles of the refusal are unnamed, by no identifier and no blank, when neither a line shown nor the roles the session reads know them [WF-PLA-0010-A]", async () => {
    // An estimator reads the active roles alone (`resource_settings.read` missing): the two roles of
    // the refusal are deactivated, and no line of the grid bears them.
    const refused = example("estimate_line_without_hours") as Problem & { status: 422 };
    const unknown = [AUTOMATION_ENGINEER, "01926f3a-7c00-7000-8000-000000000455"];
    const client = fakeClient({
      [LINE]: {
        problem: { ...refused, params: { ...refused.params, resource_role_ids: unknown } },
      },
    });
    server.client = client;
    const reference = estimateReference();
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <EstimateGrid
          nodes={estimate}
          structure={STRUCTURE}
          structureVersion={1}
          reference={{ ...reference, roles: reference.roles?.filter((role) => role.active) }}
          editable
          tasksEditable
          query={NO_QUERY}
          filters={{}}
          preferences={SHOWN}
        />
      </NextIntlClientProvider>,
    );
    cell(LABOUR, "resource_role").focus();
    await userEvent.keyboard("{Enter}");
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Rôle" }),
      "Monteur câbleur",
    );
    await userEvent.keyboard("{Tab}");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Les calendriers de ses rôles ne se recoupent aucun jour.");
    expect(alert).toHaveTextContent("Câblage des armoires");
    expect(alert).not.toHaveTextContent("000000000453");
    expect(alert).not.toHaveTextContent("Automaticien");
  });
});

describe("the sub-project, the payment delay and the deactivated object of a line (#349)", () => {
  it("presents the sub-project and the payment delay of a line as the server gives them, and enters the delay where the node accepts it, on a line of labour as on a disbursement, the sub-project being chosen from the menu of the cell [WF-DEV-0020-A]", async () => {
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
    expect(cell(LABOUR, "payment_delay_days")).toHaveTextContent(/^0$/);
    // A line of labour takes a delay as a disbursement does, its node accepting it (#785): the cell
    // follows `editable_fields`, with no rule of its own; a delay is a whole number of days, which
    // the contract takes as an integer.
    expect(cell(LABOUR, "payment_delay_days")).not.toHaveAttribute("aria-readonly");
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
    // The sub-project is read only in its column, whichever the line: it is chosen from the menu of
    // the cell (US-0480).
    expect(cell(LABOUR, "subproject")).toHaveAttribute("aria-readonly", "true");
    expect(cell(REMINDER, "subproject")).toHaveAttribute("aria-readonly", "true");
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(1);
    });
    expect(written(client)).toEqual([{ payment_delay_days: 45, lock_version: 1 }]);
    // The same on a line of labour: the delay is entered and sent as the node accepts it.
    cell(LABOUR, "payment_delay_days").focus();
    await userEvent.keyboard("{Enter}");
    await userEvent.keyboard("20{Enter}");
    await vi.waitFor(() => {
      expect(written(client)).toHaveLength(2);
    });
    expect(written(client)).toEqual([
      { payment_delay_days: 45, lock_version: 1 },
      { payment_delay_days: 20, lock_version: 1 },
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
