// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";
import { APPLY, bodies, copied, PREVIEW, STRUCTURE } from "@/test/paste-grid";
import { estimateReference } from "@/test/reference";
import { SHOWN } from "@/test/grid-preferences";

import { EstimateGrid } from "./estimate-grid";
import type { NodeList } from "./nodes";

// The server of Next, as far as the grid needs it, as for the other tests of the paste.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/projects/p/revisions/r/estimate",
  useSearchParams: () => new URLSearchParams(),
}));

// The differential of the amendment 2 of the witness, which the example `nodes_amendment` reads:
// « Câblage sur site » (row 21), « Assistance aux essais de câblage » that the amendment removes
// (row 22), then « Essais sur site » that it adds (row 23).
const AMENDMENT = { ...STRUCTURE, structure_id: "01926f3a-7c00-7000-8000-000000000203" };
const amendment = example("nodes_amendment") as NodeList;
const WIRING = 2;
const REMOVED = 3;
const ADDED = 4;
// Two lines of one column, on the label of the wiring: the second one falls on the removed line,
// which the server skips (#1278).
const BLOCK = [["Câblage sur site"], ["Essais et reprise sur site"]];

/** Serve the fake back: the plan of the block that skips the removed line, and its confirmation. */
function serve(answers: FakeAnswers = {}): FakeClient {
  const client = fakeClient({
    [PREVIEW]: "paste_plan_amendment_skipping",
    [APPLY]: "paste_applied_amendment_skipping",
    ...answers,
  });
  server.client = client;
  return client;
}

/** The grid of the estimate on the differential, on the rows the reading answered. */
function renderDifferential(nodes: NodeList, search?: string) {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <EstimateGrid
        filters={search === undefined ? {} : { search }}
        nodes={nodes}
        structure={AMENDMENT}
        structureVersion={2}
        reference={estimateReference()}
        editable
        tasksEditable
        query={{ sort: undefined, search, size: undefined }}
        preferences={SHOWN}
        differential
      />
    </NextIntlClientProvider>,
  );
}

/** The label cell of a row, by its index among the rows of the answer. */
function labelOf(row: number): HTMLElement {
  const found = screen
    .getByRole("treegrid", { hidden: true })
    .querySelector<HTMLElement>(`td[data-row="${row.toString()}"][data-column="label"]`);
  if (found === null) {
    throw new Error(`no label in the row ${row.toString()}`);
  }
  return found;
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
  window.sessionStorage.clear();
});

describe("a block pasted on a differential", () => {
  it("skips the lines the amendment removes and writes the next ones, counting the lines of the block, never the nodes skipped [WF-IHM-0050-A]", async () => {
    const client = serve();
    renderDifferential(amendment);
    const removed = labelOf(REMOVED).textContent;
    labelOf(WIRING).focus();
    await userEvent.paste(copied(BLOCK));

    const dialog = await screen.findByRole("dialog", { name: "Coller depuis un tableur" });
    // The plan of the contract: two lines accepted, none refused, the removed node written by none.
    expect(bodies(client, PREVIEW)).toEqual([
      {
        target_node_id: amendment.items[WIRING]?.node_id,
        target_column: "label",
        rows: BLOCK,
      },
    ]);
    expect(await within(dialog).findByText("2 lignes seront écrites.")).toBeVisible();
    expect(within(dialog).queryByRole("list")).toBeNull();

    await userEvent.click(
      await within(dialog).findByRole("button", { name: "Appliquer le collage" }),
    );
    await vi.waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(bodies(client, APPLY)).toEqual([
      { paste_id: "01926f3a-7c00-7000-8000-000000000995", confirmed: true, lock_version: 2 },
    ]);
    // The task added is renamed by the second line; the removed line is untouched.
    expect(labelOf(ADDED)).toHaveTextContent("Essais et reprise sur site");
    expect(labelOf(REMOVED).textContent).toBe(removed);
    // Nothing refused: the grid says nothing more of it.
    expect(screen.queryByRole("region", { name: "Lignes refusées par le collage" })).toBeNull();
  });

  it("is refused when the node after the removed one is not shown, though the removed one is: it is that node the server would write [WF-IHM-0050-A]", async () => {
    const client = serve();
    // A search retained the rows but the task added, which the server would write.
    const retained: NodeList = {
      ...amendment,
      items: amendment.items.filter((_, index) => index !== ADDED),
    };
    renderDifferential(retained, "a");
    labelOf(WIRING).focus();
    await userEvent.paste(copied(BLOCK));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Le bloc collé écrirait dans des lignes du plan que la recherche ou le filtre cache",
    );
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(bodies(client, PREVIEW)).toEqual([]);
  });
});
