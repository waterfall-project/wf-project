// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { cleanup, render, screen, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ApiClient } from "@/api/client";
import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import { expectAccessible } from "@/test/axe";
import { example, fakeClient } from "@/test/fixtures";

import { type Contributor, type Subproject, type WorkBreakdown } from "./settings-grids";
import { ContributorList, SubprojectList, WorkBreakdownList } from "./settings-lists";

// The server of Next, as far as the screen needs it: the fake back, which keeps the settings of
// the grids, the address it reads and the navigations it asks.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));
const PATH = "/projects/01926f3a-7c00-7000-8000-000000000001/settings";

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => PATH,
  useSearchParams: () => new URLSearchParams(page.search),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const breakdown = example("work_breakdown") as WorkBreakdown;
const subprojects = example("subprojects") as Subproject[];
const contributors = (example("contributors") as { items: Contributor[] }).items;

/** The settings of a project, in French, sharing the address last asked as the page does. */
function settings(children: ReactNode = <AllLists />) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>{children}</PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The three lists of the settings, as the page shows them. */
function AllLists() {
  return (
    <>
      <WorkBreakdownList breakdown={breakdown} project={PROJECT} />
      <SubprojectList subprojects={subprojects} />
      <ContributorList contributors={contributors} />
    </>
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
  page.search = "";
  sessionStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
  router.push.mockClear();
});

describe("the grids of the settings of a project", () => {
  it("are three dense grids, each named after its list, its menu of the columns too, and break no rule of accessibility", async () => {
    const { container } = render(settings());
    expect(screen.getByRole("treegrid", { name: "Lotissement" })).toBeInTheDocument();
    expect(screen.getByRole("grid", { name: "Sous-projets" })).toBeInTheDocument();
    expect(screen.getByRole("grid", { name: "Contributeurs" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Colonnes de «\u00a0Contributeurs\u00a0»" }),
    ).toBeInTheDocument();
    // The work breakdown sorts nothing, in the order entered; the two flat tables sort on each of
    // their three columns.
    const sorting = (name: string) =>
      screen
        .getByRole(name === "Lotissement" ? "treegrid" : "grid", { name })
        .querySelectorAll("thead button");
    expect(sorting("Lotissement")).toHaveLength(0);
    expect(sorting("Sous-projets")).toHaveLength(3);
    expect(sorting("Contributeurs")).toHaveLength(3);
    await expectAccessible(container);
  });

  it("fold the work breakdown, a work package over its deliverables, the order of the tree kept", async () => {
    render(settings());
    const tree = screen.getByRole("treegrid", { name: "Lotissement" });
    expect(within(tree).getAllByRole("row")).toHaveLength(5);
    const item = within(tree).getByRole("row", { name: /Fourniture et montage des armoires/ });
    await userEvent.click(within(item).getByRole("button", { name: "Plier" }));
    // The header, the order item, the totals.
    expect(within(tree).getAllByRole("row")).toHaveLength(3);
    await userEvent.click(within(item).getByRole("button", { name: "Déplier" }));
    expect(within(tree).getAllByRole("row")).toHaveLength(5);
  });

  it("ask the server for the search of the sub-projects under the names of their grid, the rest of the address kept", async () => {
    page.search = "contributor_kinds=contributor";
    render(settings());
    await userEvent.type(
      screen.getByRole("searchbox", { name: "Rechercher dans «\u00a0Sous-projets\u00a0»" }),
      "SP-C",
    );
    await userEvent.keyboard("{Enter}");
    expect(lastAddress()).toBe(`${PATH}?contributor_kinds=contributor&subproject_search=SP-C`);
  });

  it.each([
    ["Code ERP", "code"],
    ["Libellé", "label"],
    ["Coûts réels", "has_actual_costs"],
  ] as const)(
    "ask the server for the sort of the sub-projects by « %s », both ways, under the names of their grid, the rest of the address kept [WF-IHM-0060-A]",
    async (heading, column) => {
      // Chaque colonne d'une table plate se trie dans les deux sens.
      page.search = "contributor_kinds=contributor";
      const { rerender } = render(settings());
      const header = () =>
        within(screen.getByRole("grid", { name: "Sous-projets" })).getByRole("button", {
          name: heading,
        });
      await userEvent.click(header());
      const sorted = `subproject_sort_by=${column}&subproject_sort_order`;
      expect(lastAddress()).toBe(`${PATH}?contributor_kinds=contributor&${sorted}=asc`);
      page.search = `contributor_kinds=contributor&${sorted}=asc`;
      const query = { sort: { column, order: "asc" }, search: undefined } as const;
      rerender(
        settings(
          <SubprojectList subprojects={subprojects} shown={{ query, preferences: undefined }} />,
        ),
      );
      await userEvent.click(header());
      expect(lastAddress()).toBe(`${PATH}?contributor_kinds=contributor&${sorted}=desc`);
    },
  );

  it.each([
    ["Nom", "display_name"],
    ["Qualité", "kind"],
    ["Compte", "is_active"],
  ] as const)(
    "ask the server for the sort of the contributors by « %s », both ways, under the names of their grid, the rest of the address kept [WF-IHM-0060-A]",
    async (heading, column) => {
      // Chaque colonne d'une table plate se trie dans les deux sens.
      page.search = "subproject_search=SP";
      const { rerender } = render(settings());
      const header = () =>
        within(screen.getByRole("grid", { name: "Contributeurs" })).getByRole("button", {
          name: heading,
        });
      await userEvent.click(header());
      const sorted = `contributor_sort_by=${column}&contributor_sort_order`;
      expect(lastAddress()).toBe(`${PATH}?subproject_search=SP&${sorted}=asc`);
      page.search = `subproject_search=SP&${sorted}=asc`;
      const query = { sort: { column, order: "asc" }, search: undefined } as const;
      rerender(
        settings(
          <ContributorList contributors={contributors} shown={{ query, preferences: undefined }} />,
        ),
      );
      await userEvent.click(header());
      expect(lastAddress()).toBe(`${PATH}?subproject_search=SP&${sorted}=desc`);
    },
  );

  it("ask the server for the search of the contributors on their names, under the names of their grid", async () => {
    page.search = "subproject_search=SP";
    render(settings());
    await userEvent.type(
      screen.getByRole("searchbox", { name: "Rechercher dans «\u00a0Contributeurs\u00a0»" }),
      "Mar{Enter}",
    );
    expect(lastAddress()).toBe(`${PATH}?subproject_search=SP&contributor_search=Mar`);
  });

  it("filter the sub-projects on their actual costs and the contributors on the state of their account, under the names of their grid", async () => {
    page.search = "subproject_search=SP";
    render(settings());
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Coûts réels" }),
      "Sans coût réel imputé",
    );
    expect(lastAddress()).toBe(`${PATH}?subproject_search=SP&subproject_has_actual_costs=false`);
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "État du compte" }),
      "Comptes désactivés",
    );
    expect(lastAddress()).toBe(
      `${PATH}?subproject_search=SP&subproject_has_actual_costs=false&contributor_is_active=false`,
    );
    // Every one chosen again lifts the filter.
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "État du compte" }),
      "Tous les comptes",
    );
    expect(lastAddress()).toBe(`${PATH}?subproject_search=SP&subproject_has_actual_costs=false`);
  });

  it("filter the contributors by capacity under the names of their grid, the capacities in the order of the contract [WF-IHM-0130-A]", async () => {
    page.search = "subproject_search=SP";
    const { rerender } = render(settings());
    const filter = screen.getByRole("group", { name: "Filtrer par qualité" });
    await userEvent.click(within(filter).getByRole("button", { name: "Contributeur" }));
    expect(lastAddress()).toBe(`${PATH}?subproject_search=SP&contributor_kinds=contributor`);
    page.search = "subproject_search=SP&contributor_kinds=contributor";
    rerender(
      settings(
        <ContributorList
          contributors={contributors.filter((each) => each.kind === "contributor")}
          kinds={["contributor"]}
        />,
      ),
    );
    expect(
      screen.getByRole("grid", { name: "Contributeurs" }).querySelector("tfoot tr")?.textContent,
    ).toBe("3 contributeurs");
    await userEvent.click(
      within(screen.getByRole("group", { name: "Filtrer par qualité" })).getByRole("button", {
        name: "Chef de projet",
      }),
    );
    // Every capacity retained is no filter: it is lifted, and « every capacity » is pressed.
    expect(lastAddress()).toBe(`${PATH}?subproject_search=SP`);
  });

  it("keep the folds of the work breakdown for each project: folded in one, unfolded in another, folded again back in the first", async () => {
    const other = "01926f3a-7c00-7000-8000-000000000002";
    const tree = (project: string) =>
      settings(<WorkBreakdownList breakdown={breakdown} project={project} />);
    const rows = () =>
      within(screen.getByRole("treegrid", { name: "Lotissement" })).getAllByRole("row");
    const { unmount } = render(tree(PROJECT));
    const item = within(screen.getByRole("treegrid", { name: "Lotissement" })).getByRole("row", {
      name: /Fourniture et montage des armoires/,
    });
    await userEvent.click(within(item).getByRole("button", { name: "Plier" }));
    expect(rows()).toHaveLength(3);
    unmount();
    render(tree(other));
    expect(rows()).toHaveLength(5);
    cleanup();
    render(tree(PROJECT));
    expect(rows()).toHaveLength(3);
  });
});
