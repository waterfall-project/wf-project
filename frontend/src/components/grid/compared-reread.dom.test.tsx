// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, render, renderHook, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeClient, fakeClient, held } from "@/test/fixtures";
import { SHOWN } from "@/test/grid-preferences";
import { estimateReference } from "@/test/reference";

import { type CellReading, type CellRules, useCellWrites } from "./cell-writes";
import type { CellEntry, RowsWritten } from "./columns";
import { ESTIMATE_FIELDS, type EstimateNode } from "./estimate";
import { EstimateGrid } from "./estimate-grid";
import {
  type NodeList,
  nodeFresher,
  nodeKey,
  type NodeSortColumn,
  type NodesWritten,
  type NodeTotals,
  nodesWritten,
  projectNodes,
} from "./nodes";
import type { GridQuery } from "./query";

// The entry of a grid compared to a base (WF-IHM-0150, US-2340): the answer of a write takes the
// place of the rows it wrote, as anywhere, and the grid reads its comparison anew once its writes
// answered — no write answers the marks, the values of the base nor the differences. The server of
// Next, as far as the grid needs it, as for the other tests of the grid.
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

// The current revision of the witness compared to its reference, on the installation on site: the
// summary « Installation sur site » differs by its amounts, and « Câblage sur site » by its review
// of the remaining to commit. The write of that line answers it, and the tasks above it whole, at
// the version they had: without the marks of the comparison, which no write answers.
const comparison = example("comparison_current") as NodeList;
const REDATED = example("estimate_line_redated") as NodesWritten;
const indexOf = (label: string) =>
  comparison.items.findIndex((node) => (node.task?.label ?? node.estimate_line?.label) === label);
const SUMMARY = indexOf("Installation sur site");
const WIRING = indexOf("Câblage sur site");
const ASSISTANCE = indexOf("Assistance aux essais de câblage");

/** Serve the fake back, a write of a line held until let go when asked, and give it back. */
function serve(hold?: Promise<void>): FakeClient {
  const client = fakeClient(
    { [LINE]: "estimate_line_redated" },
    { hold: (route, index) => (route === LINE && index === 0 ? hold : undefined) },
  );
  server.client = client;
  return client;
}

/** The grid of the estimate on a reading, compared to a base or not, open to entry. */
function grid(nodes: NodeList, comparing: boolean): ReactNode {
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
        comparing={comparing}
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

/** The writes of a line the fake back was asked. */
function lineWrites(client: FakeClient): number {
  return client.calls.filter((call) => call.route === LINE).length;
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  router.refresh.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("a grid compared to a base, entered", () => {
  it("takes the answer of a write in place of the rows it wrote, then reads the comparison anew once, the marks and the values of the base following [WF-IHM-0150-A]", async () => {
    serve();
    const { rerender } = render(grid(comparison, true));
    expect(within(cell(SUMMARY, "base_amount")).getByText("Δ")).toBeInTheDocument();
    cell(WIRING, "hours").focus();
    await userEvent.keyboard("121{Enter}");
    await vi.waitFor(() => {
      expect(router.refresh).toHaveBeenCalledTimes(1);
    });
    // The rows written as the server answered them: the line re-estimated, the summary above it
    // whole, at its version, without the marks no write answers.
    expect(cell(WIRING, "reestimated_amount")).toHaveTextContent(/9\s639,40/);
    expect(within(cell(SUMMARY, "base_amount")).queryByText("Δ")).toBeNull();
    // The comparison read anew — served as the fake back serves it, which keeps nothing — takes
    // their place: the summary marked again, the value of its base given.
    rerender(grid(structuredClone(comparison), true));
    expect(within(cell(SUMMARY, "base_amount")).getByText("Δ")).toBeInTheDocument();
    expect(cell(SUMMARY, "base_amount")).toHaveTextContent(/Base : 618\s600,00/);
    expect(cell(WIRING, "reestimated_amount")).toHaveTextContent(/9\s600,00/);
    expect(router.refresh).toHaveBeenCalledTimes(1);
  });

  it("keeps the cursor and a cell being entered through the reading anew [WF-IHM-0150-A]", async () => {
    serve();
    const { rerender } = render(grid(comparison, true));
    cell(WIRING, "hours").focus();
    await userEvent.keyboard("121{Enter}");
    await vi.waitFor(() => {
      expect(router.refresh).toHaveBeenCalledTimes(1);
    });
    // Another cell entered while the comparison is read anew, its entry not validated.
    cell(ASSISTANCE, "hours").focus();
    await userEvent.keyboard("45");
    const editor = screen.getByRole("textbox");
    expect(editor).toHaveValue("45");
    rerender(grid(structuredClone(comparison), true));
    expect(screen.getByRole("textbox")).toHaveValue("45");
    expect(screen.getByRole("textbox")).toHaveFocus();
    await userEvent.keyboard("{Escape}");
    expect(cell(ASSISTANCE, "hours")).toHaveFocus();
  });

  it("waits for every write under way, and reads the comparison anew once [WF-IHM-0150-A]", async () => {
    const answer = held();
    const client = serve(answer.until);
    render(grid(comparison, true));
    cell(WIRING, "hours").focus();
    await userEvent.keyboard("121{Enter}");
    cell(WIRING, "quantity").focus();
    await userEvent.keyboard("2{Enter}");
    // The first write held: the second waits behind it, and nothing is read anew.
    expect(lineWrites(client)).toBe(1);
    expect(router.refresh).not.toHaveBeenCalled();
    await act(async () => {
      answer.release();
      await answer.until;
    });
    await vi.waitFor(() => {
      expect(lineWrites(client)).toBe(2);
    });
    await vi.waitFor(() => {
      expect(router.refresh).toHaveBeenCalledTimes(1);
    });
  });

  it("reads nothing anew out of a comparison: the answers alone, as the rule of EP-02 says", async () => {
    serve();
    render(grid(comparison, false));
    cell(WIRING, "hours").focus();
    await userEvent.keyboard("121{Enter}");
    await vi.waitFor(() => {
      expect(cell(WIRING, "reestimated_amount")).toHaveTextContent(/9\s639,40/);
    });
    expect(router.refresh).not.toHaveBeenCalled();
  });
});

describe("the answers laid over the comparison read anew", () => {
  const rows = projectNodes(comparison, ESTIMATE_FIELDS);
  const first: CellReading<EstimateNode, NodeTotals> = {
    address: "/projects/p/revisions/r/estimate?base_revision_id=b",
    rows: rows.items,
    totals: rows.totals,
  };
  const redated = nodesWritten(REDATED, ESTIMATE_FIELDS, true);

  /** A write that answers at once what it is given, from the row it left from. */
  function answering(
    written: (from: EstimateNode) => RowsWritten<EstimateNode, NodeTotals>,
  ): CellEntry<EstimateNode, NodeTotals> {
    return {
      kind: { type: "decimal", nullable: true },
      in: () => true,
      value: () => undefined,
      write: (from) => Promise.resolve({ kind: "done", data: written(from) }),
    };
  }

  /** The line answered anew by a later write: its effort, a version and a place more. */
  function later(from: EstimateNode): RowsWritten<EstimateNode, NodeTotals> {
    const { estimate_line: line } = from;
    if (line === null || line === undefined) {
      throw new Error("the row written is a line");
    }
    const entered = { ...line, hours: "130" };
    return {
      rows: [{ ...from, lock_version: from.lock_version + 1, estimate_line: entered }],
      changed: [],
      parts: [],
      totals: undefined,
      order: redated.order + 1,
    };
  }

  it("lets the answers taken before the reading was asked give way to it, and keeps over it the one given since [WF-IHM-0150-A]", async () => {
    const reread = vi.fn();
    const rules: CellRules<EstimateNode, NodeTotals> = {
      rowKey: nodeKey,
      fresher: nodeFresher,
      reread,
    };
    const { result, rerender } = renderHook(
      (reading: CellReading<EstimateNode, NodeTotals>) => useCellWrites(reading, rules),
      {
        initialProps: first,
        wrapper: ({ children }: { readonly children: ReactNode }) => (
          <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr}>
            {children}
          </NextIntlClientProvider>
        ),
      },
    );
    const write = async (entry: CellEntry<EstimateNode, NodeTotals>, value: string) => {
      const row = result.current.rows[WIRING];
      if (row === undefined) {
        throw new Error("the comparison holds the wiring on site");
      }
      await act(async () => {
        result.current.write({ row, column: "hours", entry, value, shown: value });
        await new Promise((resolve) => setTimeout(resolve, 0));
      });
    };
    const earlier = answering(() => redated);
    await write(earlier, "121");
    expect(reread).toHaveBeenCalledTimes(1);
    // The summary as the write answered it, at the version read: no mark of the comparison.
    expect(result.current.rows[SUMMARY]?.base).toBeUndefined();
    // A write answered after the reading was asked, before the reading arrives.
    await write(answering(later), "130");
    expect(reread).toHaveBeenCalledTimes(2);
    rerender({ ...first, rows: structuredClone(rows.items) });
    // The reading asked first takes the place of what was answered before it was asked — the
    // summary, whose version says nothing — and the answer given since stays laid over it.
    expect(result.current.rows[SUMMARY]?.base).toEqual(rows.items[SUMMARY]?.base);
    expect(rows.items[SUMMARY]?.base).toBeTruthy();
    expect(result.current.rows[SUMMARY]?.difference).toBe("modified");
    expect(result.current.rows[WIRING]?.estimate_line?.hours).toBe("130");
  });
});
