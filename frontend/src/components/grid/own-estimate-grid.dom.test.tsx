// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { OwnEstimateEntry } from "@/components/revisions/own-estimate-entry";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient } from "@/test/fixtures";
import { copied, pasteOn } from "@/test/paste-grid";
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
const REBASE = `POST ${STRUCTURE_PATH}/rebase` as const;
const PREVIEW = `POST ${STRUCTURE_PATH}/nodes/paste-preview` as const;
const APPLY = `POST ${STRUCTURE_PATH}/nodes/paste` as const;
// The counter of the own estimate once the update is applied (`structure_rebased_risk`).
const UPDATED = 6;
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

/** The grid of the own estimate in arrears, under its guard, on the structure read at a counter. */
function tree(version: number) {
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
        <EstimateGrid
          nodes={estimate}
          structure={STRUCTURE}
          structureVersion={version}
          reference={estimateReference()}
          editable
          tasksEditable
          differential
          query={NO_QUERY}
          filters={{}}
          preferences={SHOWN}
        />
      </OwnEstimateEntry>
    </NextIntlClientProvider>
  );
}

/** Enter another role into the labour line: the cell is edited, and left. */
async function enterRole(): Promise<void> {
  cell(LABOUR, "resource_role").focus();
  await userEvent.keyboard("{Enter}");
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "Rôle" }),
    "Monteur câbleur",
  );
  await userEvent.keyboard("{Tab}");
}

/** Paste a cell on the label of the labour line, and confirm the plan. */
async function pasteLabel(): Promise<void> {
  await pasteOn(cell(LABOUR, "label"), copied([["Raccordement revu"]]));
  const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
  await userEvent.click(
    await within(dialog).findByRole("button", { name: "Appliquer le collage" }),
  );
}

describe("the entry into the grid of an own estimate in arrears", () => {
  it("reads the report of the update before the first entry, presents what it keeps, and writes nothing until it is confirmed [US-3140] [WF-RIS-0070-A]", async () => {
    const client = fakeClient({
      [REPORT]: "structure_rebase_report_risk",
      [LINE]: "estimate_line_updated",
    });
    server.client = client;
    render(tree(1));
    await enterRole();
    expect(
      await screen.findByRole("region", { name: "Mise à jour du devis propre" }),
    ).toHaveTextContent("garde une valeur contre le projet");
    await waitFor(() => {
      expect(client.calls.map((call) => call.route)).toEqual([REPORT]);
    });
    expect(client.calls.some((call) => call.route === LINE)).toBe(false);
  });

  it("updates a cell entry without a question, sends nothing from the rows before the update, and writes the next one without reading the report again [US-3140] [WF-RIS-0070-A]", async () => {
    const client = fakeClient({
      [REPORT]: "structure_rebase_report_risk_clean",
      [REBASE]: "structure_rebased_risk",
      [LINE]: "estimate_line_updated",
    });
    server.client = client;
    const { rerender } = render(tree(5));
    await enterRole();
    expect(await screen.findByText(/est à jour\. Saisissez de nouveau/)).toBeVisible();
    expect(client.calls.map((call) => call.route)).toEqual([REPORT, REBASE]);
    // The page read anew by the update: the next entry carries what it read, and reads no report.
    rerender(tree(UPDATED));
    await enterRole();
    await waitFor(() => {
      expect(client.calls.map((call) => call.route)).toEqual([REPORT, REBASE, LINE]);
    });
    expect(client.calls[2]?.body).toMatchObject({ lock_version: 1 });
  });

  it("updates a paste without a question, applies nothing from the version before the update, and applies the next one with the counter read after it [US-3140] [WF-RIS-0070-A]", async () => {
    const client = fakeClient({
      [REPORT]: "structure_rebase_report_risk_clean",
      [REBASE]: "structure_rebased_risk",
      [PREVIEW]: "paste_plan",
      [APPLY]: "paste_applied",
    });
    server.client = client;
    const { rerender } = render(tree(5));
    await pasteLabel();
    expect(await screen.findByText(/est à jour\. Saisissez de nouveau/)).toBeVisible();
    expect(client.calls.map((call) => call.route)).toEqual([PREVIEW, REPORT, REBASE]);
    rerender(tree(UPDATED));
    await userEvent.keyboard("{Escape}");
    await pasteLabel();
    await waitFor(() => {
      expect(client.calls.map((call) => call.route)).toEqual([
        PREVIEW,
        REPORT,
        REBASE,
        PREVIEW,
        APPLY,
      ]);
    });
    expect(client.calls[4]?.body).toMatchObject({ confirmed: true, lock_version: UPDATED });
  });

  it("asks nothing of the report to undo on an own estimate in arrears [US-3140]", async () => {
    const client = fakeClient({
      [REPORT]: "structure_rebase_report_risk_clean",
      "POST /projects/{project_id}/revisions/{revision_id}/undo": "undo_task_renamed",
    });
    server.client = client;
    render(tree(5));
    await userEvent.click(screen.getByRole("button", { name: "Annuler" }));
    await waitFor(() => {
      expect(client.calls.map((call) => call.route)).toEqual([
        "POST /projects/{project_id}/revisions/{revision_id}/undo",
      ]);
    });
  });
});
