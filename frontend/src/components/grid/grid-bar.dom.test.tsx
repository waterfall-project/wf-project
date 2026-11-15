// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The bar of every grid, in one order (US-2080, decision of the author of 2026-11-14): the commands
 * of the screen, the search, « Filtres », « Colonnes », « Arbre », then undo and redo; no number of
 * rows in it, the totals row saying it alone (#3072); the chips of the filters on, each in the tint
 * of the primary, with its words and its cross (#3077).
 */
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { CATALOGUES } from "@/i18n/catalogues";
import { example, fakeClient } from "@/test/fixtures";
import { allShown } from "@/test/grid-preferences";

import type { GridConfig } from "./columns";
import { DenseGrid } from "./dense-grid";
import { ESTIMATE_GRID, type EstimateNode } from "./estimate";
import type { FilterChip } from "./filter-chips";
import { GridToolbar, type GridToolbarProps } from "./grid-toolbar";
import { type NodeList, type NodeSortColumn, type NodeTotals } from "./nodes";

const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/reference/costs",
  useSearchParams: () => new URLSearchParams(""),
}));

beforeEach(() => {
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
});

afterEach(() => {
  vi.restoreAllMocks();
});

/** Something rendered in French, as the screens are by default. */
function inFrench(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      {children}
    </NextIntlClientProvider>
  );
}

const ACTIVE: FilterChip = { key: "state", name: "État", value: "Actifs", params: ["is_active"] };
const KIND: FilterChip = { key: "kind", name: "Nature", value: "MO", params: ["kind"] };

/** A bar of a grid, with what every grid may hold besides `props`. */
function bar(props: Partial<GridToolbarProps>) {
  return render(
    inFrench(
      <GridToolbar
        columns={[]}
        search={undefined}
        onSearch={vi.fn()}
        undoable={undefined}
        commands={<button type="button">Insérer</button>}
        {...props}
      />,
    ),
  );
}

/** The line of the bar. */
function line(container: HTMLElement): HTMLElement {
  const found = container.querySelector<HTMLElement>("[data-grid-toolbar]");
  if (found === null) {
    throw new Error("no bar");
  }
  return found;
}

/** Each element after the one before it in the page, as the keyboard and the eye meet them. */
function expectInOrder(elements: readonly HTMLElement[]) {
  elements.slice(1).forEach((element, at) => {
    const before = elements[at];
    expect(
      before?.compareDocumentPosition(element),
      `${element.textContent} after ${before?.textContent ?? ""}`,
    ).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });
}

describe("the bar of a grid, in one order for every grid", () => {
  it("lays out a tree grid as the flat tables: its commands, the search, its filter, « Colonnes », « Arbre », then undo [WF-IHM-0060-A]", () => {
    const { container } = bar({
      treeFilters: <button type="button">Lot ou poste</button>,
      outline: { levels: 3, expandAll: vi.fn(), collapseTo: vi.fn() },
      undoable: true,
    });
    const inside = within(line(container));
    expectInOrder([
      inside.getByRole("button", { name: "Insérer" }),
      inside.getByRole("searchbox", { name: "Rechercher un libellé" }),
      inside.getByRole("button", { name: "Lot ou poste" }),
      inside.getByRole("button", { name: "Colonnes" }),
      inside.getByRole("button", { name: "Arbre" }),
      inside.getByRole("button", { name: "Annuler" }),
      inside.getByRole("button", { name: "Rétablir" }),
    ]);
  });

  it("lays out a flat table in the same order: its commands, the search, « Filtres », « Colonnes » [WF-IHM-0060-A]", () => {
    const { container } = bar({ filters: { panel: null, chips: [ACTIVE] }, onOpen: vi.fn() });
    const inside = within(line(container));
    expectInOrder([
      inside.getByRole("button", { name: "Insérer" }),
      inside.getByRole("searchbox", { name: "Rechercher un libellé" }),
      inside.getByRole("button", { name: "Filtres (1)" }),
      inside.getByRole("button", { name: "Colonnes" }),
    ]);
  });
});

const witness = example("nodes") as NodeList;
const FLAT: GridConfig<EstimateNode, NodeSortColumn, NodeTotals> = {
  key: "flat",
  name: "estimate",
  searched: true,
  rowKey: (node) => node.node_id,
  columns: ESTIMATE_GRID.columns.map((column) => ({ ...column, pinned: false })),
};

describe("the number of rows of a flat table, filtered", () => {
  it("is said by the totals row alone, never by the bar [WF-IHM-0130-A] [WF-IHM-0060-A]", () => {
    const { container } = render(
      inFrench(
        <DenseGrid
          config={FLAT}
          rows={witness.items}
          totals={witness.totals}
          totalsCaption={() => "4 natures"}
          query={{ sort: undefined, search: undefined, size: undefined }}
          preferences={allShown(ESTIMATE_GRID.columns)}
          filtering={{ panel: null, chips: [KIND] }}
        />,
      ),
    );
    expect(line(container)).not.toHaveTextContent("4 natures");
    expect(container.querySelector("tfoot")).toHaveTextContent("4 natures");
  });
});

describe("the chips of the filters on", () => {
  it("say each filter by its words and its cross, in the tint of the primary [WF-IHM-0060-A]", () => {
    bar({ filters: { panel: null, chips: [KIND, ACTIVE] }, onOpen: vi.fn() });
    const chips = within(screen.getByRole("list", { name: "Filtres actifs" })).getAllByRole(
      "listitem",
    );
    expect(chips.map((chip) => chip.textContent)).toEqual(["Nature : MO", "État : Actifs"]);
    const crosses = ["Retirer le filtre Nature : MO", "Retirer le filtre État : Actifs"];
    chips.forEach((chip, at) => {
      expect(within(chip).getByRole("button", { name: crosses[at] ?? "" })).toBeVisible();
      // The tint of the primary and its words in the primary, whose contrast contrast.test.ts
      // measures in both modes (`primary` on `accent`).
      expect(chip).toHaveClass("bg-accent", "text-primary");
    });
  });
});
