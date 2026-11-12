// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import type { ListPage } from "@/navigation/pages";
import { example } from "@/test/fixtures";

import type { CostCategory, CostType } from "./cost-grids";
import { natureChoice } from "./cost-kinds";
import { CostCategoryList, CostTypeList } from "./cost-lists";
import type { Calendar, OrgNode, ResourceRole } from "./resource-grids";
import { type HourlyRateGrid, RateGrid } from "./rate-grid";
import { CalendarList, OrgNodeList, ResourceRoleList, type RoleFilters } from "./resource-lists";

// The filters of the lists of the reference data folded into the bar of their table (#2916,
// WF-IHM-0130, WF-IHM-0060): the chips told from the address, each lifted by the parameters it says,
// and the panel, closed until « Filtres » opens it.
const router = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));

vi.mock("next/cache", () => ({ refresh: vi.fn() }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => "/reference/resources",
  useSearchParams: () => new URLSearchParams(page.search),
}));

const roles = example("resource_roles") as { items: ResourceRole[]; meta: ListPage };
const nodes = example("org_nodes") as OrgNode[] | { items: OrgNode[] };
const calendars = example("calendars") as { items: Calendar[]; meta: ListPage };
const types = example("cost_types") as { items: CostType[]; meta: ListPage };
const categories = example("volume/cost_categories_page") as {
  items: CostCategory[];
  meta: ListPage;
};

const QUERY = { sort: undefined, search: undefined, size: undefined } as const;
const NONE = { min: undefined, max: undefined };
const OFFSET = "role_offset=50";

const nodeRows = Array.isArray(nodes) ? nodes : nodes.items;
const NODE = nodeRows[0];
const ROLE_NODES = nodeRows.map((node) => ({
  id: node.org_node_id,
  code: node.code,
  label: node.label,
  level: node.level,
  active: node.is_active,
}));
const CALENDARS = calendars.items.map((calendar) => ({
  id: calendar.calendar_id,
  label: calendar.label,
  active: calendar.is_active,
}));
const NATURES = types.items.map(natureChoice);

function inFrench(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      <PendingAddress>{children}</PendingAddress>
    </NextIntlClientProvider>
  );
}

const noRoleFilters: RoleFilters = {
  code: undefined,
  orgNode: undefined,
  category: undefined,
  calendar: undefined,
  state: undefined,
  monthlyHours: NONE,
  headcount: NONE,
};

function roleList(filters: Partial<RoleFilters>) {
  return inFrench(
    <ResourceRoleList
      rows={roles.items}
      page={roles.meta}
      query={QUERY}
      preferences={undefined}
      editable
      nodes={ROLE_NODES}
      categories={[]}
      labour={undefined}
      calendars={CALENDARS}
      filters={{ ...noRoleFilters, ...filters }}
    />,
  );
}

beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1600);
  page.search = "";
});
afterEach(() => {
  vi.restoreAllMocks();
  router.push.mockClear();
});

const lastAddress = (): unknown => router.push.mock.calls.at(-1)?.[0];
const named = (text: string) => (name: string) => name.replace(/\s/g, " ") === text;

describe("the chips of the filters of the resource roles", () => {
  const CASES = [
    {
      name: "the code",
      search: "role_code=AUT",
      filters: { code: "AUT" },
      chip: "Code : AUT",
      lifts: ["role_code"],
    },
    {
      name: "a node of organisation the screen does not offer, by its identifier",
      search: "role_org_node_id=unknown",
      filters: { orgNode: "unknown" },
      chip: "Nœud d’organisation : unknown",
      lifts: ["role_org_node_id"],
    },
    {
      name: "the state",
      search: "role_is_active=false",
      filters: { state: false },
      chip: "État : Désactivés",
      lifts: ["role_is_active"],
    },
    {
      name: "the bounds of the monthly hours",
      search: "role_monthly_hours_min=100&role_monthly_hours_max=160",
      filters: { monthlyHours: { min: "100", max: "160" } },
      chip: "Heures par mois : de 100 à 160",
      lifts: ["role_monthly_hours_min", "role_monthly_hours_max"],
    },
    {
      name: "the least headcount",
      search: "role_headcount_min=2",
      filters: { headcount: { min: "2", max: undefined } },
      chip: "Effectif : 2 au moins",
      lifts: ["role_headcount_min"],
    },
  ] as const;

  it.each(CASES)(
    "tell $name, and lift it by the parameters of the address that say it [WF-IHM-0130-A]",
    async ({ search, filters, chip, lifts }) => {
      page.search = `role_sort_by=code&${OFFSET}&${search}`;
      render(roleList(filters));
      await userEvent.click(
        screen.getByRole("button", { name: named(`Retirer le filtre ${chip}`) }),
      );
      const rest = new URLSearchParams(page.search);
      for (const name of [...lifts, "role_offset"]) {
        rest.delete(name);
      }
      expect(lastAddress()).toBe(`/reference/resources?${rest.toString()}`);
    },
  );

  it("tell a node of organisation by its code and its label [WF-IHM-0130-A]", () => {
    page.search = `role_org_node_id=${NODE?.org_node_id ?? ""}`;
    render(roleList({ orgNode: NODE?.org_node_id }));
    const chips = screen.getByRole("list", { name: "Filtres actifs" });
    expect(chips).toHaveTextContent(`Nœud d’organisation : ${NODE?.code ?? ""}`);
    expect(chips).toHaveTextContent(NODE?.label ?? "");
  });

  it("fold the filters into a panel closed until « Filtres » opens it [WF-IHM-0130-A]", async () => {
    render(roleList({}));
    const toggle = screen.getByRole("button", { name: /^Filtres/ });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(toggle);
    expect(screen.getByRole("group", { name: "Filtres" })).toBeVisible();
    expect(screen.getByRole("searchbox", { name: "Code du rôle" })).toBeVisible();
  });

  it("clear every filter at once, the sort kept [WF-IHM-0130-A]", async () => {
    page.search = "role_sort_by=code&role_code=AUT&role_is_active=true&role_offset=50";
    render(roleList({ code: "AUT", state: true }));
    await userEvent.click(screen.getByRole("button", { name: "Effacer les filtres" }));
    expect(lastAddress()).toBe("/reference/resources?role_sort_by=code");
  });
});

describe("the chips of the filters of the other lists of the reference data", () => {
  it("tell the code, the depth and the bounds of the depth of the tree, which are lifted by their own parameters [WF-IHM-0130-A]", async () => {
    page.search = "org_code=A&org_level=2&org_level_min=1&org_level_max=3";
    render(
      inFrench(
        <OrgNodeList
          rows={nodeRows}
          query={QUERY}
          preferences={undefined}
          editable
          filters={{
            code: "A",
            level: 2,
            state: undefined,
            levels: { min: "1", max: "3" },
          }}
          levels={[1, 2, 3]}
          nodes={ROLE_NODES}
        />,
      ),
    );
    const chips = screen.getByRole("list", { name: "Filtres actifs" });
    expect(chips.children).toHaveLength(3);
    await userEvent.click(screen.getByRole("button", { name: "Retirer le filtre Niveau : 2" }));
    expect(lastAddress()).toBe("/reference/resources?org_code=A&org_level_min=1&org_level_max=3");
    await userEvent.click(
      screen.getByRole("button", { name: "Retirer le filtre Niveau : de 1 à 3" }),
    );
    expect(lastAddress()).toBe("/reference/resources?org_code=A");
  });

  it("tell the state of the calendars, and offer no panel to a session that cannot read the deactivated ones [WF-IHM-0130-A]", async () => {
    page.search = "calendar_is_active=true";
    const list = (editable: boolean) =>
      inFrench(
        <CalendarList
          rows={calendars.items}
          page={calendars.meta}
          query={QUERY}
          preferences={undefined}
          editable={editable}
          state={editable ? true : undefined}
        />,
      );
    const { unmount } = render(list(true));
    await userEvent.click(screen.getByRole("button", { name: "Retirer le filtre État : Actifs" }));
    expect(lastAddress()).toBe("/reference/resources");
    unmount();
    render(list(false));
    expect(screen.queryByRole("button", { name: /^Filtres/ })).toBeNull();
  });

  it("tell the types of the natures of cost and their state [WF-IHM-0130-A]", async () => {
    page.search = "type_kinds=labor%2Cprovision&type_is_active=false";
    render(
      inFrench(
        <CostTypeList
          rows={types.items}
          page={types.meta}
          query={QUERY}
          preferences={undefined}
          editable
          state={false}
          kinds={["labor", "provision"]}
        />,
      ),
    );
    const chips = screen.getByRole("list", { name: "Filtres actifs" });
    expect(chips.children).toHaveLength(2);
    await userEvent.click(screen.getByRole("button", { name: "Effacer les filtres" }));
    expect(lastAddress()).toBe("/reference/resources");
  });

  it("tell the nature of the categories of cost by its code and its label [WF-IHM-0130-A]", async () => {
    const nature = NATURES[0];
    page.search = `category_cost_type_id=${nature?.id ?? ""}`;
    render(
      inFrench(
        <CostCategoryList
          rows={categories.items}
          page={categories.meta}
          query={QUERY}
          preferences={undefined}
          editable
          state={undefined}
          natures={NATURES}
          nature={nature?.id}
        />,
      ),
    );
    expect(screen.getByRole("list", { name: "Filtres actifs" })).toHaveTextContent(
      `Nature : ${nature?.code ?? ""}`,
    );
  });
});

describe("the chips of the filters of the grid of the hourly rates", () => {
  const grid = example("volume/hourly_rate_grid") as HourlyRateGrid;
  const years = grid.years;
  const last = years.at(-1)?.toString() ?? "";

  it("tell the state and the bounds of the rate of the year the address names, lifted with that year [WF-IHM-0130-A]", async () => {
    page.search = `is_active=true&rate_year=${last}&rate_min=10&rate_max=20.5`;
    render(
      inFrench(
        <RateGrid
          grid={{ ...grid, rows: grid.rows.slice(0, 3) }}
          currency="EUR"
          editable
          query={QUERY}
          preferences={undefined}
          filters={{
            state: true,
            year: Number(last),
            rate: { min: "10", max: "20.5" },
          }}
          panel={<p>filters</p>}
        />,
      ),
    );
    const chips = screen.getByRole("list", { name: "Filtres actifs" });
    expect(chips.children).toHaveLength(2);
    await userEvent.click(
      screen.getByRole("button", {
        name: named(`Retirer le filtre Taux horaire ${last} : de 10,00 à 20,50`),
      }),
    );
    expect(lastAddress()).toBe("/reference/resources?is_active=true");
  });
});
