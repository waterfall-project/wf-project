// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { forgetMessages } from "@/components/notices/message-history";
import { OwnEstimateEntry } from "@/components/revisions/own-estimate-entry";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient } from "@/test/fixtures";

import type { NodeList, NodeSortColumn } from "./nodes";
import { PLANNING_GRID } from "./planning";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";

// The planning of an own estimate in arrears (US-3140): its cells are entries as those of the estimate
// are, the predecessors among them, written after an update that signals nothing without a question.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/projects/p/revisions/r/planning",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined, size: undefined };
const STRUCTURE_PATH = "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}";
const REPORT = `GET ${STRUCTURE_PATH}/rebase` as const;
const REBASE = `POST ${STRUCTURE_PATH}/rebase` as const;
const NODES = `GET ${STRUCTURE_PATH}/nodes` as const;
const PREDECESSORS = `PUT ${STRUCTURE_PATH}/nodes/{node_id}/predecessors` as const;
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000206",
};
// The nodes as the structure lists them once updated, and as the page read them before: the mounting
// of the cabinets at a counter the update moved on.
const read = example("nodes_nested") as NodeList;
const MOUNTING = read.items.findIndex(
  (node) => node.task?.label === "Montage des armoires sur site",
);
const BEFORE = 0;
const before: NodeList = {
  ...read,
  items: read.items.map((node, row) =>
    row === MOUNTING ? { ...node, lock_version: BEFORE } : node,
  ),
};
// The columns but the Gantt, which no entry here needs.
const PREFERENCES = {
  hidden_columns: [
    ...PLANNING_GRID.columns.filter((column) => column.hidden === true).map((column) => column.key),
    "gantt",
  ],
};

/** The cell of a row, by its index, and of a column, by its key. */
function cellAt(row: number, column: string): HTMLElement {
  const found = screen
    .getByRole("treegrid")
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="${column}"]`);
  if (found === null) {
    throw new Error(`no cell ${column} in the row ${row.toString()}`);
  }
  return found;
}

beforeEach(() => {
  window.sessionStorage.clear();
  forgetMessages();
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the predecessors entered into the planning of an own estimate in arrears", () => {
  it("updates without a question, and writes the links once, with the counter of the node read after the update [US-3140] [WF-RIS-0070-A]", async () => {
    const client = fakeClient({
      [REPORT]: "structure_rebase_report_risk_clean",
      [REBASE]: "structure_rebased_risk",
      [NODES]: "nodes_nested",
      [PREDECESSORS]: "predecessor_set",
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
          <PlanningGrid
            nodes={before}
            structure={STRUCTURE}
            structureVersion={5}
            filters={{ kinds: ["task"] }}
            query={NO_QUERY}
            preferences={PREFERENCES}
            undoable
            editable
          />
        </OwnEstimateEntry>
      </NextIntlClientProvider>,
    );
    // The links emptied: a blank text, which names no row to resolve.
    await act(async () => {
      cellAt(MOUNTING, "predecessors").focus();
      await Promise.resolve();
    });
    await userEvent.keyboard("{F2}");
    await userEvent.clear(within(screen.getByRole("treegrid")).getByRole("textbox"));
    await userEvent.keyboard("{Enter}");
    await waitFor(() => {
      expect(client.calls.map((call) => call.route)).toEqual([REPORT, REBASE, NODES, PREDECESSORS]);
    });
    const node = read.items[MOUNTING];
    expect(node?.lock_version).not.toBe(BEFORE);
    expect(client.calls[3]?.path).toContain(node?.node_id);
    expect(client.calls[3]?.body).toEqual({ predecessors: [], lock_version: node?.lock_version });
    expect(await screen.findByText(/a été mis à jour\./)).toBeVisible();
    expect(screen.queryByText(/Saisissez de nouveau/)).toBeNull();
  });

  it("tells the refusal of the predecessors a node no longer accepts once updated, on their cell, and writes nothing [US-3140] [WF-RIS-0070-A] (#4820)", async () => {
    // The nodes as the update left them are the example `nodes_risk_estimate`, whose second row no
    // longer lists `task.predecessors` among the fields it accepts (`entry-guard.ts`, `notAccepted`,
    // VALIDATION_FAILED on FIELD_NOT_ACCEPTED); the page read it before, still accepting them.
    const left = example("nodes_risk_estimate") as NodeList;
    const ROW = 1;
    const page: NodeList = {
      ...left,
      items: left.items.map((node, row) =>
        row === ROW
          ? { ...node, editable_fields: [...node.editable_fields, "task.predecessors"] }
          : node,
      ),
    };
    const client = fakeClient({
      [REPORT]: "structure_rebase_report_risk_clean",
      [REBASE]: "structure_rebased_risk",
      [NODES]: "nodes_risk_estimate",
      [PREDECESSORS]: "predecessor_set",
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
          <PlanningGrid
            nodes={page}
            structure={STRUCTURE}
            structureVersion={5}
            filters={{ kinds: ["task"] }}
            query={NO_QUERY}
            preferences={PREFERENCES}
            undoable
            editable
          />
        </OwnEstimateEntry>
      </NextIntlClientProvider>,
    );
    await act(async () => {
      cellAt(ROW, "predecessors").focus();
      await Promise.resolve();
    });
    await userEvent.keyboard("{F2}");
    await userEvent.clear(within(screen.getByRole("treegrid")).getByRole("textbox"));
    await userEvent.keyboard("{Enter}");
    expect(await screen.findByText("Ce champ ne se saisit pas sur cette ligne.")).toBeVisible();
    expect(client.calls.map((call) => call.route)).toEqual([REPORT, REBASE, NODES]);
  });
});
