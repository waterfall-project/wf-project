// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { OwnEstimateEntry } from "@/components/revisions/own-estimate-entry";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient } from "@/test/fixtures";
import { estimateReference } from "@/test/reference";
import { SHOWN } from "@/test/grid-preferences";

import { EstimateGrid } from "./estimate-grid";
import type { NodeList, NodeSortColumn } from "./nodes";
import type { GridQuery } from "./query";

// The server of Next, as far as the grid needs it, as for the other tests of the grid.
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
const LINE = `PATCH ${STRUCTURE_PATH}/nodes/{node_id}/estimate-line` as const;
const REPORT = `GET ${STRUCTURE_PATH}/rebase` as const;
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000206",
};
const LABOUR = 4;
const estimate = example("nodes_risk_estimate") as NodeList;

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

describe("the entry into the grid of an own estimate in arrears", () => {
  it("reads the report of the update before the first entry, presents what it keeps, and writes nothing until it is confirmed [US-3140] [WF-RIS-0070-A]", async () => {
    const client = fakeClient({
      [REPORT]: "structure_rebase_report_risk",
      [LINE]: "estimate_line_updated",
    });
    server.client = client;
    render(
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
          <EstimateGrid
            nodes={estimate}
            structure={STRUCTURE}
            structureVersion={1}
            reference={estimateReference()}
            editable
            tasksEditable
            differential
            query={NO_QUERY}
            filters={{}}
            preferences={SHOWN}
          />
        </OwnEstimateEntry>
      </NextIntlClientProvider>,
    );
    cell(LABOUR, "resource_role").focus();
    await userEvent.keyboard("{Enter}");
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Rôle" }),
      "Monteur câbleur",
    );
    await userEvent.keyboard("{Tab}");
    expect(
      await screen.findByRole("region", { name: "Mise à jour du devis propre" }),
    ).toHaveTextContent("garde une valeur contre le projet");
    await waitFor(() => {
      expect(client.calls.map((call) => call.route)).toEqual([REPORT]);
    });
    expect(client.calls.some((call) => call.route === LINE)).toBe(false);
  });
});
