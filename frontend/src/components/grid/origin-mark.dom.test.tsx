// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import { example } from "@/test/fixtures";

import { EstimateGrid } from "./estimate-grid";
import type { NodeList, NodeSortColumn } from "./nodes";
import { PlanningGrid } from "./planning-grid";
import type { GridQuery } from "./query";
import { estimateReference } from "@/test/reference";

vi.mock("@/api/server", () => ({ serverClient: () => undefined }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
  usePathname: () => "/projects/p/revisions/r/planning",
  useSearchParams: () => new URLSearchParams(),
}));

const NO_QUERY: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined, size: undefined };
const STRUCTURE = {
  project_id: "01926f3a-7c00-7000-8000-000000000001",
  revision_id: "01926f3a-7c00-7000-8000-000000000102",
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const RISK = "01926f3a-7c00-7000-8000-000000000752";
const NAMES = { [RISK]: "Retard de livraison des armoires" };
// The nodes the occurrence of the risk merged, and their ancestor, which bears no origin.
const FROM_RISK = example("nodes_from_risk") as NodeList;
const MARKED = FROM_RISK.items.filter((node) => node.origin_risk_id != null).length;
const NAMED = "Came of the occurrence of the risk “Retard de livraison des armoires”";

/** The grid of the planning on the nodes of a risk, the labels of the risks given or not. */
function renderPlanning(origins: Readonly<Record<string, string>> | undefined) {
  return render(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      <PlanningGrid
        nodes={FROM_RISK}
        structure={STRUCTURE}
        structureVersion={1}
        filters={{}}
        query={NO_QUERY}
        preferences={undefined}
        origins={origins}
      />
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1000);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the mark of a row a risk occurred merged", () => {
  it("marks each row of the grid of the planning that bears an origin, naming the risk, and no other [WF-RIS-0060-A]", () => {
    renderPlanning(NAMES);
    expect(MARKED).toBeGreaterThan(0);
    expect(MARKED).toBeLessThan(FROM_RISK.items.length);
    expect(screen.getAllByRole("img", { name: NAMED })).toHaveLength(MARKED);
    // The ancestor, which the server renders for the tree and which bears no origin, has no mark.
    const ancestor = screen.getByText("Poste de commande").closest("tr");
    expect(ancestor?.querySelector('[aria-label^="Came of"]')).toBeNull();
  });

  it("says a risk without its name when the project lists none to it [WF-RIS-0060-A]", () => {
    renderPlanning(undefined);
    expect(screen.queryByRole("img", { name: NAMED })).toBeNull();
    expect(screen.getAllByRole("img", { name: "Came of the occurrence of a risk" }).length).toBe(
      MARKED,
    );
  });

  it("marks the lines of the estimate too [WF-RIS-0060-A]", () => {
    render(
      <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
        <EstimateGrid
          nodes={FROM_RISK}
          structure={STRUCTURE}
          structureVersion={1}
          filters={{}}
          reference={estimateReference()}
          editable={false}
          tasksEditable={false}
          query={NO_QUERY}
          preferences={undefined}
          origins={NAMES}
        />
      </NextIntlClientProvider>,
    );
    expect(screen.getAllByRole("img", { name: NAMED })).toHaveLength(MARKED);
  });
});
