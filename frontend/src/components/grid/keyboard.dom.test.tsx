// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { createEvent, fireEvent, render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";

import { EstimateGrid } from "./estimate-grid";
import { triesEntry } from "./grid-keyboard";
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
const DEPENDENCIES =
  "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/dependencies";
// The main structure of the current revision of the witness project, as the examples name it.
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
// The rows of the estimate, by their index: the summary, the task « Câblage des armoires », its
// line of labour, its disbursement, its provision — whose quantity and unit disbursement the
// server computes —, the milestone.
const TASK = 1;
const LABOUR = 2;
const DISBURSEMENT = 3;
const PROVISION = 4;
const MILESTONE = 5;
const estimate = example("nodes_estimate") as NodeList;

/** Serve the fake back, and give it back to read its calls. */
function serve(): FakeClient {
  const client = fakeClient({ [DEPENDENCIES]: "dependencies_provision" });
  server.client = client;
  return client;
}

/** Render the grid of the estimate, in French. */
function renderGrid() {
  return render(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <EstimateGrid
        nodes={estimate}
        structure={STRUCTURE}
        query={NO_QUERY}
        preferences={undefined}
      />
    </NextIntlClientProvider>,
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

/** The refusal of an entry on a computed value. */
function refusal() {
  return screen.queryByRole("dialog", { name: "Valeur calculée" });
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1000);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the keyboard of a grid", () => {
  it("is one stop of the tabulation, the active cell, which the arrows move", async () => {
    serve();
    renderGrid();
    const stops = screen.getByRole("grid").querySelectorAll('td[tabindex="0"]');
    expect([...stops]).toEqual([cell(0, "label")]);
    cell(0, "label").focus();
    await userEvent.keyboard("{ArrowDown}{ArrowRight}{ArrowRight}");
    expect(cell(1, "hours")).toHaveFocus();
    expect(cell(1, "hours")).toHaveAttribute("tabindex", "0");
    expect(cell(0, "label")).toHaveAttribute("tabindex", "-1");
    await userEvent.keyboard("{End}");
    expect(cell(1, "reestimated_amount")).toHaveFocus();
    await userEvent.keyboard("{Home}");
    expect(cell(1, "row_number")).toHaveFocus();
    await userEvent.keyboard("{Control>}{End}{/Control}");
    expect(cell(MILESTONE, "reestimated_amount")).toHaveFocus();
    await userEvent.keyboard("{Control>}{Home}{/Control}{PageDown}");
    expect(cell(MILESTONE, "row_number")).toHaveFocus();
    await userEvent.keyboard("{ArrowDown}{PageUp}{ArrowUp}{ArrowLeft}");
    expect(cell(0, "row_number")).toHaveFocus();
    // The cell clicked is the active one: the one stop of the tabulation.
    await userEvent.click(cell(DISBURSEMENT, "quantity"));
    expect(cell(DISBURSEMENT, "quantity")).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("grid").querySelectorAll('td[tabindex="0"]')).toHaveLength(1);
    // Tab leaves the grid.
    await userEvent.tab();
    expect(screen.getByRole("grid")).not.toContainElement(document.activeElement as HTMLElement);
  });

  it("stops on the computed cells without entering them, and refuses a try", async () => {
    serve();
    renderGrid();
    cell(PROVISION, "label").focus();
    // The arrows stop on the quantity of the provision, which the server computes: read only,
    // it opens nothing to type, and the arrows go on past it.
    await userEvent.keyboard("{ArrowRight}");
    const quantity = cell(PROVISION, "quantity");
    expect(quantity).toHaveFocus();
    expect(quantity).toHaveAttribute("aria-readonly", "true");
    await userEvent.keyboard("{ArrowRight}{ArrowRight}");
    expect(cell(PROVISION, "unit_disbursement")).toHaveFocus();
    expect(screen.queryByRole("textbox")).toBeNull();
    // A character typed on it is refused, naming what it depends on; Escape gives the focus back.
    await userEvent.keyboard("5");
    expect(refusal()).toHaveTextContent(/Débours unit\. ne se saisit pas/);
    expect(screen.queryByRole("textbox")).toBeNull();
    await expectAccessible(document.body);
    await userEvent.keyboard("{Escape}");
    expect(refusal()).toBeNull();
    expect(cell(PROVISION, "unit_disbursement")).toHaveFocus();
    expect(cell(PROVISION, "unit_disbursement")).toHaveAttribute("aria-expanded", "false");
    // F2 on another computed cell refuses it too.
    await userEvent.keyboard("{ArrowRight}{F2}");
    expect(refusal()).toHaveTextContent(/Budgété ne se saisit pas/);
  });

  it("opens nothing on a cell that takes no entry, nor computed: the quantity of a task", async () => {
    serve();
    renderGrid();
    cell(TASK, "quantity").focus();
    await userEvent.keyboard("{Enter}7{F2}");
    expect(refusal()).toBeNull();
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(cell(TASK, "quantity")).toHaveAttribute("aria-readonly", "true");
    expect(cell(TASK, "quantity")).not.toHaveAttribute("aria-haspopup");
    expect(cell(TASK, "quantity")).toHaveFocus();
    // The effort of a line takes one.
    expect(cell(LABOUR, "hours")).not.toHaveAttribute("aria-readonly");
  });

  it("scrolls nothing on Space, whatever the cell", () => {
    serve();
    renderGrid();
    for (const target of [cell(LABOUR, "hours"), cell(LABOUR, "budgeted_amount")]) {
      const space = createEvent.keyDown(target, { key: " " });
      fireEvent(target, space);
      expect(space.defaultPrevented).toBe(true);
    }
  });

  it("closes a refusal on a click elsewhere, without scrolling back to its cell, the cell clicked active", async () => {
    serve();
    renderGrid();
    cell(PROVISION, "budgeted_amount").focus();
    await userEvent.keyboard("{Enter}");
    expect(refusal()).not.toBeNull();
    const scroller = screen.getByRole("grid").parentElement;
    const scrolled = scroller?.scrollTop;
    await userEvent.click(cell(LABOUR, "label"));
    expect(refusal()).toBeNull();
    expect(scroller?.scrollTop).toBe(scrolled);
    expect(cell(LABOUR, "label")).toHaveFocus();
    expect(cell(LABOUR, "label")).toHaveAttribute("tabindex", "0");
    expect(cell(PROVISION, "budgeted_amount")).toHaveAttribute("aria-expanded", "false");
  });

  it("closes a refusal on a click on its own cell, rather than opening it again", async () => {
    serve();
    renderGrid();
    await userEvent.click(cell(PROVISION, "budgeted_amount"));
    expect(refusal()).not.toBeNull();
    await userEvent.click(cell(PROVISION, "budgeted_amount"));
    expect(refusal()).toBeNull();
    expect(cell(PROVISION, "budgeted_amount")).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(cell(PROVISION, "budgeted_amount"));
    expect(refusal()).not.toBeNull();
  });
});

describe("a key that tries an entry", () => {
  /** A key pressed, with its modifiers. */
  function key(name: string, { ctrl = false, alt = false, meta = false, altGraph = false } = {}) {
    return {
      key: name,
      ctrlKey: ctrl,
      altKey: alt,
      metaKey: meta,
      getModifierState: () => altGraph,
    };
  }

  it("is Enter, F2, or a character typed, a shortcut aside", () => {
    expect(triesEntry(key("Enter"))).toBe(true);
    expect(triesEntry(key("F2"))).toBe(true);
    expect(triesEntry(key("7"))).toBe(true);
    expect(triesEntry(key("é"))).toBe(true);
    expect(triesEntry(key("Tab"))).toBe(false);
    expect(triesEntry(key("c", { ctrl: true }))).toBe(false);
    expect(triesEntry(key("c", { meta: true }))).toBe(false);
    expect(triesEntry(key("c", { alt: true }))).toBe(false);
  });

  it("is a character typed by AltGr, which Windows reports as Ctrl and Alt together", () => {
    expect(triesEntry(key("€", { ctrl: true, alt: true, altGraph: true }))).toBe(true);
    expect(triesEntry(key("@", { ctrl: true, alt: true, altGraph: true }))).toBe(true);
  });
});
