// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { example, type FakeClient, fakeClient } from "@/test/fixtures";

import { FOLD_STORAGE_PREFIX } from "./fold";
import type { NodeList, NodeSortColumn } from "./nodes";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";

// The server of Next, as far as the grid needs it, as for the other tests of the grid.
const server = vi.hoisted((): { client: FakeClient | undefined } => ({ client: undefined }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/projects/p/revisions/r/planning",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined, size: undefined };
// The main structure of the current revision of the witness project, as the examples name it.
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
// The witness planning of four levels of tasks: « Relance du fournisseur » is under « Retard de
// livraison des armoires », under « Poste de commande », under « Installation sur site ».
const nested = example("nodes_nested") as NodeList;
const KEPT = `${FOLD_STORAGE_PREFIX}planning:${STRUCTURE.revision_id}`;

/** The identifier of the node of a label. */
function nodeOf(label: string): string {
  const node = nested.items.find((each) => each.task?.label === label);
  if (node === undefined) {
    throw new Error(`no node of ${label}`);
  }
  return node.node_id;
}

/** The grid of the planning, the task the address targets given. */
function planning(target: string | undefined) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PlanningGrid
        nodes={nested}
        structure={STRUCTURE}
        structureVersion={1}
        filters={{ kinds: ["task"] }}
        query={NO_QUERY}
        preferences={undefined}
        target={target}
      />
    </NextIntlClientProvider>
  );
}

/** The labels of the rows the grid renders, in their order. */
function labels(): string[] {
  return [...document.querySelectorAll('tbody td[data-column="label"]')].map(
    (cell) => cell.textContent,
  );
}

/** The cell of the label of a row. */
function labelCell(label: string): HTMLElement {
  const cell = [...document.querySelectorAll<HTMLElement>('tbody td[data-column="label"]')].find(
    (each) => each.textContent === label,
  );
  if (cell === undefined) {
    throw new Error(`no row of ${label}`);
  }
  return cell;
}

beforeEach(() => {
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
});

afterEach(() => {
  vi.restoreAllMocks();
  window.sessionStorage.clear();
});

describe("the task the address of the planning targets", () => {
  it("unfolds the rows above the task, as the session had folded them, and sets the cursor on it, the focus with it [WF-DEV-0090-A]", () => {
    // Depuis une tâche du détail, l'utilisateur atteint cette tâche dans la grille de planning.
    // The tree folded down to its first level in the session, as the menu « Arbre » leaves it, and
    // another branch folded besides: only the rows above the task unfold.
    const folded = [
      "Installation sur site",
      "Poste de commande",
      "Retard de livraison des armoires",
    ].map(nodeOf);
    window.sessionStorage.setItem(KEPT, JSON.stringify({ collapsed: folded, revealed: "" }));
    render(planning(nodeOf("Relance du fournisseur")));
    expect(labels()).toContain("Relance du fournisseur");
    expect(labelCell("Relance du fournisseur")).toHaveFocus();
    expect(labelCell("Relance du fournisseur")).toHaveAttribute("tabindex", "0");
    // The unfolding is kept: the session finds the tree as the link left it, and the folding of
    // the rows without difference (US-2360) as it was, off.
    expect(JSON.parse(window.sessionStorage.getItem(KEPT) ?? "{}")).toEqual({
      collapsed: [],
      revealed: "",
      differences: { on: false, opened: [] },
    });
  });

  it("leaves folded what is not above the task", () => {
    const folded = ["Retard de livraison des armoires"].map(nodeOf);
    window.sessionStorage.setItem(KEPT, JSON.stringify({ collapsed: folded, revealed: "" }));
    render(planning(nodeOf("Mise en service")));
    expect(labels()).not.toContain("Relance du fournisseur");
    expect(labelCell("Mise en service")).toHaveFocus();
  });

  it("aims at the task once: a fold made afterwards stays, the cursor where the user put it", async () => {
    const { rerender } = render(planning(nodeOf("Relance du fournisseur")));
    const above = within(labelCell("Retard de livraison des armoires")).getByRole("button");
    await userEvent.click(above);
    expect(labels()).not.toContain("Relance du fournisseur");
    // A reading anew of the same address — a sort, a refresh of the page — does not aim again.
    rerender(planning(nodeOf("Relance du fournisseur")));
    expect(labels()).not.toContain("Relance du fournisseur");
    expect(labelCell("Retard de livraison des armoires")).toHaveFocus();
  });

  it("opens as it would without a target when the reading does not hold the task", () => {
    render(planning("01926f3a-7c00-7000-8000-000000000999"));
    expect(labels()).toHaveLength(nested.items.length);
    expect(labelCell("Installation sur site")).toHaveAttribute("tabindex", "0");
    expect(document.activeElement).toBe(document.body);
    expect(screen.getByRole("treegrid")).toBeInTheDocument();
  });
});
