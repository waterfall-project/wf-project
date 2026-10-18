// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";
import { estimateReference } from "@/test/reference";

import { EstimateGrid } from "./estimate-grid";
import type { NodeFilters, NodeList, NodeSortColumn, NodesWritten } from "./nodes";
import type { GridQuery } from "./query";

// The totals and the summaries a write of the estimate answers, apart from the entry itself
// (`entry.dom.test.tsx`), whose file they made too long. The server of Next, as far as the grid
// needs it, as for the other tests of the grid.
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
// The main structure of the current revision of the witness project, as the examples name it.
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const NODES_ROUTE =
  "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes";
// The rows of the estimate: the task « Câblage des armoires » and its line of labour.
const estimate = example("nodes_estimate") as NodeList;
/** The index of a row of the estimate, found by its label in the example (#400). */
function rowOf(label: string): number {
  return estimate.items.findIndex(
    (node) => (node.task?.label ?? node.estimate_line?.label) === label,
  );
}
const TASK_ROW = rowOf("Câblage des armoires");
const LABOUR = rowOf("Raccordement des borniers");
const LINE_ANSWER = example("estimate_line_updated") as NodesWritten;
// The whole structure of the witness, read without a filter, its core first (#376), whose totals
// the writes of the core answer: the line of labour the write answers, its task and the lot of
// the control station above it, found by their identifiers in the examples (#400).
const core = example("volume/nodes_thousand") as NodeList;
const indexOf = (id: string | null | undefined) =>
  core.items.findIndex((node) => node.node_id === id);
const CORE_LABOUR = indexOf(LINE_ANSWER.nodes[0]?.node_id);
const CORE_TASK = indexOf(core.items[CORE_LABOUR]?.parent_id);
const CORE_LOT = indexOf(core.items[CORE_TASK]?.parent_id);
// The lots of the core down to that of the line written, the totals still those of the whole
// structure: the server's, which the grid sums nothing to show. The six thousand rows made each
// key take a quarter of a second under happy-dom, past the time of the test under load (EP-02/L46).
const coreLots: NodeList = {
  ...core,
  items: core.items.slice(
    0,
    core.items.findIndex((node, index) => index > CORE_LOT && (node.parent_id ?? null) === null),
  ),
};

/** Serve the fake back, and give it back to read its calls. */
function serve(answers: FakeAnswers = {}): FakeClient {
  const client = fakeClient({ [LINE]: "estimate_line_updated", ...answers });
  server.client = client;
  return client;
}

/** The grid of the estimate on an answer, in French, open to entry, as the address asked. */
function grid(
  nodes: NodeList = estimate,
  query: GridQuery<NodeSortColumn> = NO_QUERY,
  filters: NodeFilters = {},
) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <EstimateGrid
        nodes={nodes}
        structure={STRUCTURE}
        structureVersion={1}
        reference={estimateReference()}
        editable
        tasksEditable
        query={query}
        filters={filters}
        preferences={undefined}
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

/** The texts of the totals row, at the foot of the grid. */
function totals(): (string | null)[] {
  const row = screen.getByRole("treegrid").querySelector("tfoot tr");
  return [...(row?.querySelectorAll("td") ?? [])].map((cell) => cell.textContent);
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("what a write answers besides the row written", () => {
  it("shows the amounts the server recalculated on the tasks above it, and the totals of the structure, summing nothing [WF-DEV-0050-A]", async () => {
    serve();
    render(grid(coreLots));
    expect(totals().slice(1)).toEqual([
      "Total — 1\u202f000 tâches, 5\u202f000 lignes",
      "",
      "",
      "",
      "116\u202f270",
      "",
      "",
      "",
      "",
      "66\u202f105\u202f223,89",
      "68\u202f923\u202f691,06",
    ]);
    cell(CORE_LABOUR, "hours").focus();
    await userEvent.keyboard("14{Enter}");
    // The amounts of each summary follow those of its subordinates, as the server answers them,
    // at the year of reference and corrected for inflation.
    await vi.waitFor(() => {
      expect(cell(CORE_LOT, "base_amount")).toHaveTextContent(/502\s554,56$/);
    });
    expect(cell(CORE_TASK, "base_amount")).toHaveTextContent(/502\s354,56$/);
    expect(cell(CORE_LOT, "inflated_amount")).toHaveTextContent(/502\s554,56$/);
    expect(cell(CORE_TASK, "inflated_amount")).toHaveTextContent(/502\s354,56$/);
    expect(totals().slice(1)).toEqual([
      "Total — 1\u202f000 tâches, 5\u202f000 lignes",
      "",
      "",
      "",
      "116\u202f271,5",
      "",
      "",
      "",
      "",
      "66\u202f105\u202f343,89",
      "68\u202f923\u202f811,06",
    ]);
  });

  it("reads anew the totals of a reading a search narrowed, by its own request, once its writes answered, never taking those of the structure [WF-ARC-0020-A]", async () => {
    // The reading anew answers other totals than the reading: the example of another subtree.
    const client = serve({ [NODES_ROUTE]: "nodes" });
    const search = { sort: undefined, search: "borniers" };
    render(grid(estimate, search, { search: "borniers" }));
    cell(LABOUR, "hours").focus();
    await userEvent.keyboard("14{Enter}");
    // The tasks above it as the write answered them; the totals as the reading anew gave them.
    await vi.waitFor(() => {
      expect(totals()[1]).toBe("Total — 6 tâches, 1 ligne");
    });
    expect(cell(TASK_ROW, "base_amount")).toHaveTextContent(/502\s354,56$/);
    expect(totals()[5]).toBe("0");
    expect(totals()[10]).toBe("100\u202f000,00");
    // The same search, after the write, each node asked by its identifier alone.
    const reads = client.calls.filter((call) => call.route === NODES_ROUTE);
    expect(reads.map((call) => Object.fromEntries(call.query))).toEqual([
      { search: "borniers", fields: "node_id" },
    ]);
    expect(client.calls.map((call) => call.route)).toEqual([LINE, NODES_ROUTE]);
  });

  it("takes the totals read anew after the last write alone, dropping a reading under way when another write left", async () => {
    // The first reading anew is held until the second has answered, which answers other totals.
    let release: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    const client = fakeClient(
      { [LINE]: "estimate_line_updated", [NODES_ROUTE]: ["nodes", "nodes_risk_occurred"] },
      { hold: (route, index) => (route === NODES_ROUTE && index === 0 ? held : undefined) },
    );
    server.client = client;
    const search = { sort: undefined, search: "borniers" };
    render(grid(estimate, search, { search: "borniers" }));
    cell(LABOUR, "hours").focus();
    await userEvent.keyboard("14{Enter}");
    await vi.waitFor(() => {
      expect(client.calls.filter((call) => call.route === NODES_ROUTE)).toHaveLength(1);
    });
    // Another write leaves while the totals are read anew: its own reading anew answers.
    cell(LABOUR, "quantity").focus();
    await userEvent.keyboard("3{Enter}");
    await vi.waitFor(() => {
      expect(totals()[1]).toBe("Total — 3 tâches, 2 lignes");
    });
    // The first reading answers last: dropped, the totals of the second stay.
    await act(async () => {
      release();
      await new Promise((resolve) => setTimeout(resolve, 20));
    });
    expect(totals()[1]).toBe("Total — 3 tâches, 2 lignes");
    expect(client.calls.map((call) => call.route)).toEqual([LINE, NODES_ROUTE, LINE, NODES_ROUTE]);
  });

  it("tells a reading anew of the totals the server refuses, the totals of the reading left as they were", async () => {
    const lost = { problem: { code: "SESSION_REQUIRED", status: 401 } } as const;
    serve({ [NODES_ROUTE]: lost });
    const search = { sort: undefined, search: "borniers" };
    render(grid(estimate, search, { search: "borniers" }));
    cell(LABOUR, "hours").focus();
    await userEvent.keyboard("14{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent("Vous devez vous connecter.");
    expect(cell(TASK_ROW, "base_amount")).toHaveTextContent(/502\s354,56$/);
    expect(totals()[5]).toBe("12,5");
  });

  it("reads nothing anew for a reading of the whole structure, whose totals the writes answer", async () => {
    const client = serve();
    render(grid(coreLots));
    cell(CORE_LABOUR, "hours").focus();
    await userEvent.keyboard("14{Enter}");
    await vi.waitFor(() => {
      expect(totals()[5]).toBe("116\u202f271,5");
    });
    expect(client.calls.map((call) => call.route)).toEqual([LINE]);
  });
});
