// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";
import { estimateReference } from "@/test/reference";

import { EstimateGrid } from "./estimate-grid";
import type { NodeList, NodesWritten } from "./nodes";

// The server of Next, as far as the grid needs it, as for the other tests of the grid.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/projects/p/revisions/r/estimate",
  useSearchParams: () => new URLSearchParams(),
}));

const LINE =
  "PATCH /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/estimate-line";
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const CABLE_FITTER = "01926f3a-7c00-7000-8000-000000000454";

// The installation on site of the witness (`nodes_installation`), by the index of its rows: the
// summary; the mounting of the cabinets, its wiring on site and its assistance to the tests; the
// commissioning, which follows the mounting, and its line. The wiring on site given to the cable
// fitter, on the week of four days, puts the mounting on the days both its roles work: it finishes
// in 2027, and the commissioning starts and is consumed there (`estimate_line_redated`).
const SUMMARY = 0;
const MOUNTING = 1;
const ON_SITE = 2;
const TESTS = 3;
const COMMISSIONING = 4;
const COMMISSIONING_LINE = 5;
const installation = example("nodes_installation") as NodeList;
const redated = example("estimate_line_redated") as NodesWritten;

/** Serve the fake back, the line redated answering every write of a line. */
function serve(): FakeClient {
  const client = fakeClient({ [LINE]: "estimate_line_redated" });
  server.client = client;
  return client;
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

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("a write of the estimate that moves rows in time", () => {
  it("shows the amounts corrected for inflation the server answered for the rows it moved, their amounts at the year of reference as they were", async () => {
    const client = serve();
    render(
      <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
        <EstimateGrid
          nodes={installation}
          structure={STRUCTURE}
          structureVersion={1}
          reference={estimateReference()}
          editable
          tasksEditable
          query={{ sort: undefined, search: undefined }}
          filters={{}}
          preferences={undefined}
        />
      </NextIntlClientProvider>,
    );
    // Read in 2026, the year of reference: each amount is its own corrected.
    expect(cell(COMMISSIONING_LINE, "base_amount")).toHaveTextContent(/^6\s000,00$/);
    expect(cell(COMMISSIONING_LINE, "inflated_amount")).toHaveTextContent(/^6\s000,00$/);
    expect(cell(COMMISSIONING, "inflated_amount")).toHaveTextContent(/^6\s000,00$/);

    // The role of the wiring on site, chosen from its list.
    cell(ON_SITE, "resource_role").focus();
    await userEvent.keyboard("{Enter}Monteur");
    expect(screen.getByRole("combobox", { name: "Rôle" })).toHaveValue(CABLE_FITTER);
    await userEvent.keyboard("{Enter}");
    await vi.waitFor(() => {
      expect(cell(ON_SITE, "resource_role")).toHaveTextContent(/^Monteur câbleur$/);
    });
    expect(client.calls.map((call) => call.body)).toEqual([
      { resource_role_id: CABLE_FITTER, lock_version: 1 },
    ]);

    // The commissioning, consumed a year later, and its line: corrected anew at the inflation of
    // the witness, 3 %, as the server answered them (`reinflated`), never computed here.
    expect(redated.reinflated.map((each) => each.node_id)).toEqual(
      [COMMISSIONING, COMMISSIONING_LINE].map((row) => installation.items[row]?.node_id),
    );
    expect(cell(COMMISSIONING_LINE, "inflated_amount")).toHaveTextContent(/^6\s180,00$/);
    expect(cell(COMMISSIONING, "inflated_amount")).toHaveTextContent(/^6\s180,00$/);
    // The summary above, rendered whole (`ancestors`), sums them; the amounts at the year of
    // reference do not depend on the dates, and stay.
    expect(cell(SUMMARY, "inflated_amount")).toHaveTextContent(/^18\s780,00$/);
    expect(cell(SUMMARY, "base_amount")).toHaveTextContent(/^18\s600,00$/);
    expect(cell(COMMISSIONING_LINE, "base_amount")).toHaveTextContent(/^6\s000,00$/);
    expect(cell(COMMISSIONING, "base_amount")).toHaveTextContent(/^6\s000,00$/);
    // The mounting, still started in 2026, and its other line keep their year and amounts.
    expect(cell(MOUNTING, "inflated_amount")).toHaveTextContent(/^12\s600,00$/);
    expect(cell(TESTS, "inflated_amount")).toHaveTextContent(/^3\s000,00$/);
    expect(cell(ON_SITE, "inflated_amount")).toHaveTextContent(/^9\s600,00$/);
  });
});
