// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { PendingAddress } from "@/components/grid/pending-address";
import type { GridQuery } from "@/components/grid/query";
import { CATALOGUES } from "@/i18n/catalogues";
import type { ListPage } from "@/navigation/pages";
import { expectAccessible } from "@/test/axe";
import { example, fakeClient } from "@/test/fixtures";

import { CostGrid } from "./cost-grid";
import {
  COST_CATEGORY_SORTS,
  COST_TYPE_SORTS,
  type CostCategory,
  type CostCategorySort,
  costCategoryGrid,
  type CostType,
  type CostTypeSort,
  costTypeGrid,
} from "./cost-grids";

// The server of Next, as far as the grids need it: the preferences a sort writes, the address they
// read and the navigations they ask.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/reference/costs",
  useSearchParams: () => new URLSearchParams(page.search),
}));

const NO_QUERY = { sort: undefined, search: undefined };
const types = example("cost_types") as { items: CostType[]; meta: ListPage };
// The second page of fifty categories of the two hundred of the volumes.
const categories = example("volume/cost_categories_page") as {
  items: CostCategory[];
  meta: ListPage;
};

/** A part of the screen, in French, sharing the address last asked as the page does. */
function inFrench(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>{children}</PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The address of the last navigation the screen asked. */
function lastAddress(): unknown {
  return router.push.mock.calls.at(-1)?.[0];
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
  page.search = "category_offset=50";
  sessionStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
  router.push.mockClear();
});

describe("the grid of the natures of cost", () => {
  /** The grid of the natures, as the address asks it. */
  const typeGrid = (query: GridQuery<CostTypeSort> = NO_QUERY) =>
    inFrench(
      <CostGrid
        kind="costTypes"
        rows={types.items}
        page={types.meta}
        query={query}
        preferences={undefined}
        editable={false}
      />,
    );

  it.each(COST_TYPE_SORTS)(
    "asks the server for the sort by %s under the names of its grid, both ways [WF-IHM-0060-A]",
    async (column) => {
      const { rerender } = render(typeGrid());
      const label = costTypeGrid().columns.find((each) => each.contract === column)?.label;
      const heading = label === undefined ? "" : CATALOGUES.fr.grid.columns[label];
      const header = () =>
        within(screen.getByRole("grid", { name: "Natures de coût" })).getByRole("button", {
          name: heading,
        });
      await userEvent.click(header());
      const ascending = `/reference/costs?category_offset=50&type_sort_by=${column}&type_sort_order=asc`;
      expect(lastAddress()).toBe(ascending);
      // The page answers the sort asked: a second click asks the other way.
      page.search = ascending.split("?")[1] ?? "";
      rerender(typeGrid({ sort: { column, order: "asc" }, search: undefined }));
      await userEvent.click(header());
      expect(lastAddress()).toBe(
        `/reference/costs?category_offset=50&type_sort_by=${column}&type_sort_order=desc`,
      );
    },
  );

  it("says each nature by its type in words, and in its totals how many the server retains", () => {
    render(
      inFrench(
        <CostGrid
          kind="costTypes"
          rows={types.items}
          page={types.meta}
          query={NO_QUERY}
          preferences={undefined}
          editable={false}
        />,
      ),
    );
    const grid = screen.getByRole("grid", { name: "Natures de coût" });
    // The natures by code, as the list without sort gives them: the disbursements first.
    expect(grid.querySelector('td[data-row="0"][data-column="kind"]')).toHaveTextContent(
      "Hors main-d’œuvre",
    );
    expect(grid.querySelector("tfoot tr")?.textContent).toBe("3 natures");
  });
});

describe("the grid of the categories of cost", () => {
  /** The grid of the second page of the categories, as the address asks it. */
  const categoryGrid = (query: GridQuery<CostCategorySort> = NO_QUERY) =>
    inFrench(
      <CostGrid
        kind="costCategories"
        rows={categories.items}
        page={categories.meta}
        query={query}
        preferences={undefined}
        editable={false}
      />,
    );

  it.each(COST_CATEGORY_SORTS)(
    "asks the server for the sort by %s under the names of its grid, both ways, back to its first page [WF-IHM-0060-A]",
    async (column) => {
      const { rerender } = render(categoryGrid());
      const label = costCategoryGrid().columns.find((each) => each.contract === column)?.label;
      const heading = label === undefined ? "" : CATALOGUES.fr.grid.columns[label];
      const header = () =>
        within(screen.getByRole("grid", { name: "Catégories de coût" })).getByRole("button", {
          name: heading,
        });
      await userEvent.click(header());
      const ascending = `/reference/costs?category_sort_by=${column}&category_sort_order=asc`;
      expect(lastAddress()).toBe(ascending);
      // The page answers the sort asked, from its first page: a second click asks the other way.
      page.search = ascending.split("?")[1] ?? "";
      rerender(categoryGrid({ sort: { column, order: "asc" }, search: undefined }));
      await userEvent.click(header());
      expect(lastAddress()).toBe(
        `/reference/costs?category_sort_by=${column}&category_sort_order=desc`,
      );
    },
  );

  it("says in its totals how many categories the server retains, never the rows of the page [WF-IHM-0130-A]", async () => {
    const { container } = render(
      inFrench(
        <CostGrid
          kind="costCategories"
          rows={categories.items}
          page={categories.meta}
          query={NO_QUERY}
          preferences={undefined}
          editable={false}
        />,
      ),
    );
    const grid = screen.getByRole("grid", { name: "Catégories de coût" });
    expect(grid.querySelector("tfoot tr")?.textContent).toBe("200 catégories");
    expect(
      screen.getByRole("searchbox", { name: "Rechercher dans « Catégories de coût »" }),
    ).toBeInTheDocument();
    await expectAccessible(container);
  });
});
