// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { CostCategoryList, CostTypeList } from "@/components/reference/cost-lists";
import type { RateGridProps } from "@/components/reference/rate-grid";
import {
  CalendarList,
  type DayBounds,
  OrgNodeList,
  ResourceRoleList,
} from "@/components/reference/resource-lists";
import { DAYS } from "@/components/reference/resource-grids";
import { RiskZonesTable } from "@/components/reference/setting-tables";
import { CATALOGUES } from "@/i18n/catalogues";
import type { PageSearchParams } from "@/navigation/context";
import type { ListPage } from "@/navigation/pages";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";

import CostSettingsPage, { generateMetadata as costsMetadata } from "./costs/page";
import IndicatorSettingsPage from "./indicators/page";
import ResourceSettingsPage from "./resources/page";
import RiskSettingsPage from "./risks/page";

type CostType = components["schemas"]["CostType"];
type CostCategory = components["schemas"]["CostCategory"];
type ResourceRole = components["schemas"]["ResourceRole"];

const server = vi.hoisted((): { answers: FakeAnswers; clients: FakeClient[] } => ({
  answers: {},
  clients: [],
}));

vi.mock("@/api/server", () => ({
  serverClient: () => {
    const client = fakeClient(server.answers);
    server.clients.push(client);
    return client;
  },
}));
// The grid renders as it would, and keeps what its page handed it.
const grids = vi.hoisted((): { rates: RateGridProps[] } => ({ rates: [] }));
vi.mock("@/components/reference/rate-grid", async (original) => {
  const actual = await original<typeof import("@/components/reference/rate-grid")>();
  const { createElement } = await import("react");
  return {
    ...actual,
    RateGrid: (props: RateGridProps) => {
      grids.rates.push(props);
      return createElement(actual.RateGrid, props);
    },
  };
});
const navigation = vi.hoisted(() => ({ pathname: "/reference/costs" }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => navigation.pathname,
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "fr-FR" })),
}));

const RATES = "GET /reference/hourly-rates";
const NOT_FOUND = { problem: { code: "NOT_FOUND", status: 404 } } as const;

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/&#x27;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

/** Render a page of the reference data in French. */
function rendered(page: unknown): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      {page as ReactNode}
    </NextIntlClientProvider>,
  );
}

/** Render the settings of the costs at the query given. */
async function costsAt(search: PageSearchParams = {}) {
  navigation.pathname = "/reference/costs";
  return rendered(await CostSettingsPage({ searchParams: Promise.resolve(search) }));
}

/** Render the settings of the resources at the query given. */
async function resourcesAt(search: PageSearchParams = {}) {
  navigation.pathname = "/reference/resources";
  return rendered(await ResourceSettingsPage({ searchParams: Promise.resolve(search) }));
}

/** The node of the electrical design office, in the tree of the witness. */
const BUREAU = "01926f3a-7c00-7000-8000-000000000471";
/** The labour nature, the electrical engineering category and the standard week of the witness. */
const LABOUR = "01926f3a-7c00-7000-8000-000000000461";
const ELECTRICAL = "01926f3a-7c00-7000-8000-000000000402";
const STANDARD = "01926f3a-7c00-7000-8000-000000000481";

/** A list read whole as a list of choices is: every page, by the largest the contract takes. */
const WHOLE = { limit: "500", offset: "0" };

const NO_QUERY = { sort: undefined, search: undefined };

/** No bound on either side of a column. */
const NO_BOUNDS = { min: undefined, max: undefined };

/** No bound on the hours of any day. */
const NO_HOURS = Object.fromEntries(DAYS.map((day) => [day, NO_BOUNDS])) as DayBounds;

/** The roles of the witness, as the server pages them. */
const ROLE_PAGE = example("resource_roles") as { items: ResourceRole[]; meta: ListPage };

/** The reactivation available, as the server lists it on the deactivated automation engineer. */
const REACTIVATE =
  ROLE_PAGE.items.find((role) => role.label === "Automaticien")?.available_commands ?? [];

/** The three lists of the settings of the resources. */
const LISTS = [
  "GET /reference/org-nodes",
  "GET /reference/resource-roles",
  "GET /reference/calendars",
] as const;

/** The queries the pages sent to an operation, each as its parameters. */
function queriesOf(route: string): Record<string, string>[] {
  return callsTo(route).map((call) => Object.fromEntries(call.query));
}

/** The headings of the columns a grid of a page sorts: those whose header holds a button. */
function sortable(markup: string, table: string): string[] {
  const found = [...markup.matchAll(/<table[^>]*aria-label="([^"]*)"[^>]*>(.*?)<\/table>/g)].find(
    (match) => match[1] === table,
  );
  const head = /<thead[^>]*>(.*?)<\/thead>/.exec(found?.[2] ?? "")?.[1] ?? "";
  return [...head.matchAll(/<th[^>]*>(.*?)<\/th>/g)]
    .filter((header) => (header[1] ?? "").includes("<button"))
    .map((header) => text(header[1] ?? ""));
}

/** The choices of the list of a page a label names, each by its value and its text as written. */
function optionsOf(markup: string, label: string): (string | undefined)[][] {
  const id = new RegExp(`<label[^>]*for="([^"]+)"[^>]*>${label}</label>`).exec(markup)?.[1];
  const select = new RegExp(`<select[^>]*id="${id ?? ""}"[^>]*>(.*?)</select>`).exec(markup)?.[1];
  return [...(select ?? "").matchAll(/<option value="([^"]+)">([^<]*)<\/option>/g)].map(
    (option) => [option[1], option[2]?.replace(/&#x27;/g, "'")],
  );
}

/** The calls the pages made to an operation. */
function callsTo(route: string) {
  return server.clients.flatMap((client) => client.calls).filter((call) => call.route === route);
}

/** The texts of the rows of a table of a page, by its name. */
function rows(markup: string, table: string): string[] {
  const found = [...markup.matchAll(/<table[^>]*aria-label="([^"]*)"[^>]*>(.*?)<\/table>/g)].find(
    (match) => match[1] === table,
  );
  expect(found).toBeDefined();
  return [...(found?.[2] ?? "").matchAll(/<tr[^>]*>(.*?)<\/tr>/g)].map((row) => text(row[1] ?? ""));
}

beforeEach(() => {
  grids.rates = [];
  server.clients = [];
  server.answers = {
    "GET /session": "session",
    "GET /reference/settings": "reference_settings",
    "GET /reference/cost-types": "cost_types",
    "GET /reference/cost-categories": "volume/cost_categories",
    [RATES]: "volume/hourly_rate_grid",
    "GET /reference/org-nodes": "org_nodes",
    "GET /reference/resource-roles": "resource_roles",
    "GET /reference/calendars": "calendars",
    "GET /reference/duration-units": "duration_units",
  };
});

describe("the settings of the costs", () => {
  it("title the tab with the function", async () => {
    expect((await costsMetadata()).title).toBe("Paramètres de coûts — Waterfall");
  });

  it("hand the grid of the hourly rates the page the server answers, its currency, and its entry to a session that may modify the cost settings", async () => {
    const page = await costsAt();
    expect(text(page)).toContain(
      "Paramètres de coûts Montants exprimés en EUR, devise unique de l’installation.",
    );
    const [handed] = grids.rates;
    expect(handed?.grid.rows).toHaveLength(150);
    expect(handed?.grid.years).toHaveLength(15);
    expect(handed?.grid.meta.total).toBe(150);
    expect(handed?.currency).toBe("EUR");
    expect(handed?.editable).toBe(true);
    expect(handed?.query).toEqual({ sort: undefined, search: undefined });
    // The page of the server's size: nothing asked but what the address asks.
    expect(queriesOf(RATES)).toEqual([{}]);
  });

  it("ask the server for the page, the sort and the search of the rates the address asks, by the names of the contract [WF-IHM-0060-A]", async () => {
    await costsAt({
      search: "Automatisme",
      sort_by: "rate.2026",
      sort_order: "desc",
      offset: "50",
      // The names of the other grids of the screen are not the rates'.
      type_sort_by: "label",
    });
    expect(queriesOf(RATES)).toEqual([
      { search: "Automatisme", sort_by: "rate.2026", sort_order: "desc", offset: "50" },
    ]);
    expect(grids.rates[0]?.query).toEqual({
      sort: { column: "rate.2026", order: "desc" },
      search: "Automatisme",
    });
  });

  it("ask no sort of the rates the contract does not take, nor a page it would refuse", async () => {
    await costsAt({ sort_by: "rate.1999", offset: "-50" });
    expect(queriesOf(RATES)).toEqual([{}]);
  });

  it("offer no entry of a rate, nor a reactivation the server does not list, to a session that may only read the cost settings [WF-IHM-0090-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /session": "session_estimator",
      "GET /reference/cost-types": "cost_types_reader",
      "GET /reference/cost-categories": "volume/cost_categories_reader",
    };
    const page = await costsAt();
    expect(grids.rates[0]?.editable).toBe(false);
    // The natures and the categories read without the right to modify them carry no command.
    expect(rows(page, "Natures de coût")[1]).toBe("DEB Débours Hors main-d’œuvre Actif");
    expect(rows(page, "Catégories de coût")[1]).toBe("ACH-001 Sous-traitance Débours 604001 Actif");
    expect(page).not.toContain("Réactiver");
  });

  it("present the natures of cost by their type, and each category by its nature and its accounting code, on dense grids sorted by each of their columns [WF-IHM-0060-A]", async () => {
    const page = await costsAt();
    expect(rows(page, "Natures de coût")).toEqual([
      "Code Libellé Type État",
      "DEB Débours Hors main-d’œuvre Actif",
      "MO Main-d'œuvre Main-d’œuvre Actif",
      "PRV Provision Provision Actif",
      "3 natures",
    ]);
    expect(sortable(page, "Natures de coût")).toEqual(["Code", "Libellé", "Type", "État"]);
    const categories = rows(page, "Catégories de coût");
    expect(categories[0]).toBe("Code Libellé Nature Code comptable État");
    expect(categories[1]).toBe("ACH-001 Sous-traitance Débours 604001 Actif");
    // The totals row says how many the server retained, whatever the rows of the page.
    expect(categories.at(-1)).toBe("200 catégories");
    expect(sortable(page, "Catégories de coût")).toEqual([
      "Code",
      "Libellé",
      "Nature",
      "Code comptable",
      "État",
    ]);
    // The categories are filtered by nature, offered as the server gives every one.
    expect(optionsOf(page, "Nature")).toEqual([
      ["01926f3a-7c00-7000-8000-000000000462", "DEB · Débours"],
      [LABOUR, "MO · Main-d'œuvre"],
      ["01926f3a-7c00-7000-8000-000000000463", "PRV · Provision"],
    ]);
    expect(page).toContain('aria-label="Types de nature"');
    expect(text(page)).toContain("Tous les types Main-d’œuvre Hors main-d’œuvre Provision");
  });

  it("ask each list of the server by the names of the contract, as the address asks it under the names of its grid [WF-IHM-0130-A]", async () => {
    await costsAt({
      type_search: "MO",
      type_sort_by: "kind",
      type_sort_order: "desc",
      type_kinds: "provision,labor,unknown",
      type_is_active: "false",
      type_offset: "50",
      category_search: "641",
      category_sort_by: "accounting_code",
      category_cost_type_id: LABOUR,
      category_is_active: "true",
      category_offset: "50",
    });
    expect(queriesOf("GET /reference/cost-types")).toEqual([
      {
        search: "MO",
        sort_by: "kind",
        sort_order: "desc",
        offset: "50",
        kinds: "labor,provision",
        is_active: "false",
      },
      // Every nature, which the filter of the categories offers.
      WHOLE,
    ]);
    expect(queriesOf("GET /reference/cost-categories")).toEqual([
      {
        search: "641",
        sort_by: "accounting_code",
        sort_order: "asc",
        offset: "50",
        cost_type_id: LABOUR,
        is_active: "true",
      },
    ]);
    expect(queriesOf(RATES)).toEqual([{}]);
  });

  it("ask the active natures, categories and rates alone by default, the deactivated ones too when the address asks for them, and offer to show and hide them back to the first page of each list [WF-REF-0150-A]", async () => {
    const shown = await costsAt();
    expect(queriesOf("GET /reference/cost-types")).toEqual([{}, WHOLE]);
    expect(queriesOf("GET /reference/cost-categories")).toEqual([{}]);
    expect(queriesOf(RATES)).toEqual([{}]);
    expect(shown).toMatch(
      /<a[^>]*href="\/reference\/costs\?include_inactive=true"[^>]*>.*?Afficher aussi les désactivés<\/a>/,
    );
    server.clients = [];
    const hidden = await costsAt({ include_inactive: "true", search: "Automatisme" });
    expect(queriesOf("GET /reference/cost-types")).toEqual([
      { include_inactive: "true" },
      { include_inactive: "true", ...WHOLE },
    ]);
    expect(queriesOf("GET /reference/cost-categories")).toEqual([{ include_inactive: "true" }]);
    expect(queriesOf(RATES)).toEqual([{ include_inactive: "true", search: "Automatisme" }]);
    expect(hidden).toMatch(/<a[^>]*href="\/reference\/costs"[^>]*>.*?Masquer les désactivés<\/a>/);
  });

  it("offer the reactivation of a deactivated nature or category as the server lists it, and none it does not list [WF-REF-0150-A] [WF-IHM-0090-A]", () => {
    const labour = (example("cost_types") as { items: CostType[] }).items.find(
      (nature) => nature.code === "MO",
    );
    const categories = example("volume/cost_categories") as {
      items: CostCategory[];
      meta: ListPage;
    };
    const [category] = categories.items;
    if (labour === undefined || category === undefined) {
      throw new Error("the examples hold a nature and a category");
    }
    const lists = (commands: CostType["available_commands"]) =>
      rendered(
        <>
          <CostTypeList
            rows={[{ ...labour, is_active: false, available_commands: commands }]}
            page={{ ...categories.meta, total: 1 }}
            query={NO_QUERY}
            preferences={undefined}
            state={undefined}
            readsInactive
            kinds={[]}
          />
          <CostCategoryList
            rows={[{ ...category, is_active: false, available_commands: commands }]}
            page={{ ...categories.meta, total: 1 }}
            query={NO_QUERY}
            preferences={undefined}
            state={undefined}
            readsInactive
            natures={[]}
            nature={undefined}
          />
        </>,
      );
    const offered = lists(REACTIVATE);
    expect(rows(offered, "Natures de coût")[1]).toBe(
      "MO Main-d'œuvre Main-d’œuvre Désactivé Réactiver",
    );
    expect(offered).toContain('aria-label="Réactiver «\u00a0Main-d&#x27;œuvre\u00a0»"');
    expect(offered).toContain('aria-label="Réactiver «\u00a0Sous-traitance\u00a0»"');
    // Read without the right to modify them, as the server lists them: no command.
    const types = example("cost_types_reader") as { items: CostType[]; meta: ListPage };
    const read = example("volume/cost_categories_reader") as {
      items: CostCategory[];
      meta: ListPage;
    };
    const unlisted = rendered(
      <>
        <CostTypeList
          rows={types.items}
          page={types.meta}
          query={NO_QUERY}
          preferences={undefined}
          state={undefined}
          readsInactive={false}
          kinds={[]}
        />
        <CostCategoryList
          rows={read.items}
          page={read.meta}
          query={NO_QUERY}
          preferences={undefined}
          state={undefined}
          readsInactive={false}
          natures={[]}
          nature={undefined}
        />
      </>,
    );
    expect(rows(unlisted, "Catégories de coût")[1]).toBe(
      "ACH-001 Sous-traitance Débours 604001 Actif",
    );
    expect(unlisted).not.toContain("Réactiver");
  });

  it("ask the server for the rates of a year between the bounds the address names, with the state, and count in the totals the categories it retains [WF-IHM-0130-A]", async () => {
    server.answers = { ...server.answers, [RATES]: "volume/hourly_rate_grid_bounded" };
    const bounded = example("volume/hourly_rate_grid_bounded") as { meta: ListPage };
    const page = await costsAt({
      rate_year: "2026",
      rate_min: "99.12",
      rate_max: "150.5",
      is_active: "true",
      // A bound of another grid of the screen is not the rates'.
      category_rate_min: "1",
    });
    expect(queriesOf(RATES)).toEqual([
      { is_active: "true", rate_year: "2026", rate_min: "99.12", rate_max: "150.5" },
    ]);
    const [handed] = grids.rates;
    expect(handed?.grid.meta.total).toBe(bounded.meta.total);
    expect(handed?.grid.years).toHaveLength(15);
    // The year chosen among those of the grid, the bounds shown as French writes them.
    expect(optionsOf(page, "Année du taux")).toHaveLength(14);
    expect(page).toContain('<option value="2026" selected="">2026</option>');
    expect(page).toContain('value="150,5"');
    expect(page).toContain('aria-label="Bornes de «\u00a0Grille des taux horaires\u00a0»"');
  });

  it("ask no bound of the rate without its year, nor one that is no amount of the contract", async () => {
    await costsAt({ rate_min: "110" });
    await costsAt({ rate_year: "2026", rate_min: "110.555", rate_max: "abc" });
    await costsAt({ rate_year: "1999", rate_min: "110" });
    expect(queriesOf(RATES)).toEqual([{}, {}, {}]);
  });

  it("present no bound of the rate without its year, nor offer to lift it", async () => {
    const page = await costsAt({ rate_min: "110" });
    expect(page).not.toContain('value="110"');
    expect(text(page)).not.toContain("Lever les bornes");
  });

  it("say at its field the upper bound of the rate the server refuses, the grid unread", async () => {
    server.answers = {
      ...server.answers,
      [RATES]: {
        problem: example("hourly_rate_grid_bounds_inverted") as Problem & { status: 422 },
      },
    };
    const page = await costsAt({ rate_year: "2026", rate_min: "100", rate_max: "90" });
    expect(grids.rates).toEqual([]);
    expect(text(page)).toContain("La borne supérieure ne peut précéder la borne inférieure, 100.");
    expect(text(page)).toContain("La liste n’est pas lue");
    expect(page).toMatch(/aria-label="Taux horaire, max."[^>]*aria-invalid="true"/);
    // The year asked stays chosen, the grid that would name the others unread.
    expect(optionsOf(page, "Année du taux")).toEqual([]);
    expect(page).toContain('<option value="2026" selected="">2026</option>');
  });

  it("say at the choice of the year that the server requires it with a bound of the rate, the grid unread", async () => {
    server.answers = {
      ...server.answers,
      [RATES]: {
        problem: example("hourly_rate_grid_rate_year_missing") as Problem & { status: 422 },
      },
    };
    const page = await costsAt({ rate_year: "2026", rate_min: "100" });
    expect(grids.rates).toEqual([]);
    expect(text(page)).toContain("Année du taux 2026 Une valeur est requise.");
    expect(page).toMatch(/<select[^>]*aria-invalid="true"/);
  });

  it("are not found when the API refuses or does not find the grid", async () => {
    server.answers = { ...server.answers, [RATES]: NOT_FOUND };
    await expect(costsAt()).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
  });
});

describe("the settings of the resources", () => {
  it("present the organisation as a tree grid in the order the server gives, each node by its label set in by its depth, its code and its depth, filtered by code, depth and state", async () => {
    const page = await resourcesAt();
    expect(rows(page, "Arbre d’organisation")).toEqual([
      "Libellé Code Niveau État",
      "Direction technique DT 1 Actif",
      "Bureau d'études électricité BE-ELEC 2 Actif",
      "Atelier de câblage AT-CABL 3 Actif",
      "Service des achats ACHATS 2 Actif",
      "4 nœuds",
    ]);
    // A tree that folds, each node at its level; no header sorts it.
    expect(page).toMatch(/<table[^>]*role="treegrid"[^>]*aria-label="Arbre d’organisation"/);
    expect(page).toContain('aria-level="3"');
    expect(sortable(page, "Arbre d’organisation")).toEqual([]);
    // Its depths are those of the whole tree.
    expect(optionsOf(page, "Niveau")).toEqual([
      ["1", "1"],
      ["2", "2"],
      ["3", "3"],
    ]);
    expect(page).toContain('aria-label="Code du nœud"');
    expect(page).toContain('aria-label="État des objets de «\u00a0Arbre d’organisation\u00a0»"');
  });

  it("present each role with its node, its category, its calendar and its capacity, named as the server resolves them, on a grid sorted by each of its columns, filtered by each and bounded on its figures [WF-IHM-0060-A]", async () => {
    const page = await resourcesAt({ include_inactive: "true" });
    expect(rows(page, "Rôles de ressources")).toEqual([
      "Libellé Nœud d’organisation Catégorie de coût Calendrier Heures par mois Effectif État",
      "Automaticien Bureau d'études électricité Ingénierie électrique Semaine de trente-neuf heures 338,00 2 Désactivé Réactiver",
      "Ingénieur électricien Bureau d'études électricité Ingénierie électrique Semaine standard 658 654,00 3 800 Actif",
      "Monteur câbleur Atelier de câblage Ingénierie électrique Semaine de quatre jours 216 662,50 1 250 Actif",
      "Programmeur d'automates Bureau d'études automatismes Ingénierie électrique Semaine standard 519,99 3 Désactivé Réactiver Condition non remplie : nœud d’organisation actif.",
      "Technicien de mise en service Bureau d'études électricité Mise en service Semaine standard 485 324,00 2 800 Actif",
      "5 rôles",
    ]);
    // The calendar of the deactivated role is not among those the page read: its name is the
    // answer's, never one the front would draw from another list.
    expect(rows(page, "Calendriers").join(" ")).not.toContain("trente-neuf");
    expect(sortable(page, "Rôles de ressources")).toEqual([
      "Libellé",
      "Nœud d’organisation",
      "Catégorie de coût",
      "Calendrier",
      "Heures par mois",
      "Effectif",
      "État",
    ]);
    // The roles are filtered by node, offered in the order of the tree, each set in by its depth;
    // by category and by calendar, each one the session reads offered.
    expect(text(page)).toContain("Nœud d’organisation Tous les nœuds");
    expect(optionsOf(page, "Nœud d’organisation")).toEqual([
      ["01926f3a-7c00-7000-8000-000000000470", "DT · Direction technique"],
      [BUREAU, "\u2003BE-ELEC · Bureau d'études électricité"],
      ["01926f3a-7c00-7000-8000-000000000472", "\u2003\u2003AT-CABL · Atelier de câblage"],
      ["01926f3a-7c00-7000-8000-000000000473", "\u2003ACHATS · Service des achats"],
    ]);
    const categories = optionsOf(page, "Catégorie de coût");
    expect(categories).toHaveLength(200);
    expect(categories[0]).toEqual([
      "01926f3a-7c00-7000-8000-000000000401",
      "ACH-001 · Sous-traitance",
    ]);
    expect(optionsOf(page, "Calendrier")).toEqual([
      ["01926f3a-7c00-7000-8000-000000000482", "Semaine de quatre jours"],
      [STANDARD, "Semaine standard"],
    ]);
    // Its figures are bounded, the least and the most of each.
    expect(page).toContain('aria-label="Bornes de «\u00a0Rôles de ressources\u00a0»"');
    expect(page).toContain('aria-label="Heures par mois, min."');
    expect(page).toContain('aria-label="Effectif, max."');
  });

  it("present each calendar by its seven values of hours, the default one marked, sorted by each of its columns, and the units of duration [WF-IHM-0060-A]", async () => {
    const page = await resourcesAt();
    expect(rows(page, "Calendriers")).toEqual([
      "Libellé Lun. Mar. Mer. Jeu. Ven. Sam. Dim. Par défaut État",
      "Semaine de quatre jours 10 10 10 10 0 0 0 Actif",
      "Semaine standard 8 8 8 8 8 0 0 Calendrier par défaut Actif",
      "2 calendriers",
    ]);
    expect(sortable(page, "Calendriers")).toEqual([
      "Libellé",
      "Lun.",
      "Mar.",
      "Mer.",
      "Jeu.",
      "Ven.",
      "Sam.",
      "Dim.",
      "Par défaut",
      "État",
    ]);
    expect(text(page)).toContain(
      "Unités de durée Heures par jour 8 Heures par semaine 40 Jours par mois 20",
    );
  });

  it("ask each list of the server by the names of the contract, as the address asks it under the names of its grid [WF-IHM-0060-A] [WF-IHM-0130-A]", async () => {
    await resourcesAt({
      org_search: "BE",
      org_code: "ELEC",
      org_level: "2",
      org_is_active: "true",
      role_search: "Ingé",
      role_sort_by: "monthly_hours",
      role_sort_order: "desc",
      role_org_node_id: BUREAU,
      role_cost_category_id: ELECTRICAL,
      role_calendar_id: STANDARD,
      role_is_active: "false",
      role_monthly_hours_min: "300000",
      role_monthly_hours_max: "700000.5",
      role_headcount_min: "2",
      role_offset: "50",
      calendar_search: "Semaine",
      calendar_sort_by: "wednesday",
      calendar_is_active: "true",
      calendar_friday_max: "0",
      calendar_monday_min: "8",
      calendar_offset: "50",
      // The names of the contract alone belong to no grid of this screen.
      search: "ignored",
      sort_by: "label",
    });
    // The tree narrowed, and the tree whole, which the filters of the roles offer.
    expect(queriesOf("GET /reference/org-nodes")).toEqual([
      { search: "BE", code: "ELEC", level: "2", is_active: "true" },
      {},
    ]);
    expect(queriesOf("GET /reference/resource-roles")).toEqual([
      {
        search: "Ingé",
        sort_by: "monthly_hours",
        sort_order: "desc",
        org_node_id: BUREAU,
        cost_category_id: ELECTRICAL,
        calendar_id: STANDARD,
        is_active: "false",
        monthly_hours_min: "300000",
        monthly_hours_max: "700000.5",
        headcount_min: "2",
        offset: "50",
      },
    ]);
    expect(queriesOf("GET /reference/calendars")).toEqual([
      {
        search: "Semaine",
        sort_by: "wednesday",
        sort_order: "asc",
        is_active: "true",
        monday_min: "8",
        friday_max: "0",
        offset: "50",
      },
      // Every calendar, which the filter of the roles offers.
      WHOLE,
    ]);
    expect(queriesOf("GET /reference/cost-categories")).toEqual([WHOLE]);
  });

  it("present the reactivation of a node under a deactivated parent unavailable, with its condition, and that of the parent available [WF-IHM-0090-A] [WF-REF-0080-A]", async () => {
    server.answers = { ...server.answers, "GET /reference/org-nodes": "org_nodes_with_inactive" };
    const page = await resourcesAt({ include_inactive: "true" });
    expect(rows(page, "Arbre d’organisation")).toEqual([
      "Libellé Code Niveau État",
      "Direction technique DT 1 Actif",
      "Bureau d'études automatismes BE-AUTO 2 Désactivé Réactiver",
      "Cellule robotique CEL-ROBOT 3 Désactivé Réactiver Condition non remplie : nœud parent actif.",
      "Bureau d'études électricité BE-ELEC 2 Actif",
      "Atelier de câblage AT-CABL 3 Actif",
      "Service des achats ACHATS 2 Actif",
      "6 nœuds",
    ]);
    const command = (name: string) =>
      new RegExp(`<button[^>]*aria-label="Réactiver «\u00a0${name}\u00a0»"[^>]*>`).exec(page)?.[0];
    expect(command("Cellule robotique")).toContain('aria-disabled="true"');
    expect(command("Bureau d&#x27;études automatismes")).toBeDefined();
    expect(command("Bureau d&#x27;études automatismes")).not.toContain("aria-disabled");
  });

  it("ask the roles between the bounds of their figures, and count in the totals those the server retains [WF-IHM-0130-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /reference/resource-roles": "resource_roles_bounded",
    };
    const page = await resourcesAt({
      include_inactive: "true",
      role_monthly_hours_min: "485324.00",
    });
    expect(queriesOf("GET /reference/resource-roles")).toEqual([
      { include_inactive: "true", monthly_hours_min: "485324.00" },
    ]);
    const shown = rows(page, "Rôles de ressources");
    expect(shown).toHaveLength(4);
    expect(shown.at(-1)).toBe("2 rôles");
    // The bound shown as French writes a number to enter it.
    expect(page).toContain('value="485324,00"');
  });

  it("say at its field the upper bound the server refuses for preceding the lower one, the roles unread and the rest of the screen read", async () => {
    server.answers = {
      ...server.answers,
      "GET /reference/resource-roles": {
        problem: example("resource_roles_bounds_inverted") as Problem & { status: 422 },
      },
    };
    const page = await resourcesAt({
      role_monthly_hours_min: "1000",
      role_monthly_hours_max: "500",
    });
    expect(queriesOf("GET /reference/resource-roles")).toEqual([
      { monthly_hours_min: "1000", monthly_hours_max: "500" },
    ]);
    expect(text(page)).toContain(
      "La borne supérieure ne peut précéder la borne inférieure, 1 000. Effectif",
    );
    expect(text(page)).toContain(
      "La liste n’est pas lue : le serveur refuse les bornes demandées.",
    );
    expect(page).toMatch(/aria-label="Heures par mois, max."[^>]*aria-invalid="true"/);
    expect(page).not.toContain('aria-label="Rôles de ressources" role="grid"');
    expect(page).not.toMatch(/<table[^>]*aria-label="Rôles de ressources"/);
    // The calendars and the tree, read as the address asks them.
    expect(rows(page, "Calendriers").at(-1)).toBe("2 calendriers");
  });

  it("say at its field the upper bound of the hours of a day the server refuses, the calendars unread", async () => {
    server.answers = {
      ...server.answers,
      // The page refused; every calendar, which the filter of the roles offers, read.
      "GET /reference/calendars": [
        { problem: example("calendars_bounds_inverted") as Problem & { status: 422 } },
        "calendars",
      ],
    };
    const page = await resourcesAt({ calendar_friday_min: "10", calendar_friday_max: "8" });
    expect(queriesOf("GET /reference/calendars")).toEqual([
      { friday_min: "10", friday_max: "8" },
      WHOLE,
    ]);
    expect(page).toMatch(/aria-label="Ven., max."[^>]*aria-invalid="true"/);
    expect(text(page)).toContain("La borne supérieure ne peut précéder la borne inférieure, 10.");
    expect(page).not.toMatch(/<table[^>]*aria-label="Calendriers"/);
  });

  it("ask the tree between the bounds of the depth, and say at its field the upper bound the server refuses", async () => {
    await resourcesAt({ org_level_min: "2", org_level_max: "3", org_level: "0" });
    expect(queriesOf("GET /reference/org-nodes")).toEqual([{ level_min: "2", level_max: "3" }, {}]);
    server.clients = [];
    // The tree narrowed refused; the whole tree, which the filters of the roles offer, read.
    server.answers = {
      ...server.answers,
      "GET /reference/org-nodes": [
        {
          problem: {
            code: "VALIDATION_FAILED",
            status: 422,
            fields: [
              { pointer: "/query/level_max", code: "VALUE_OUT_OF_RANGE", params: { minimum: "3" } },
            ],
          },
        },
        "org_nodes",
      ],
    };
    const page = await resourcesAt({ org_level_min: "3", org_level_max: "2" });
    expect(queriesOf("GET /reference/org-nodes")).toEqual([{ level_min: "3", level_max: "2" }, {}]);
    expect(page).toMatch(/aria-label="Niveau, max."[^>]*aria-invalid="true"/);
    expect(text(page)).toContain("La borne supérieure ne peut précéder la borne inférieure, 3.");
    expect(page).not.toMatch(/<table[^>]*aria-label="Arbre d’organisation"/);
    expect(optionsOf(page, "Nœud d’organisation")).toHaveLength(4);
  });

  it("read the tree once, and ask no sort, search, filter, bound nor page, when the address asks none the contract takes", async () => {
    await resourcesAt({
      role_sort_by: "capacity",
      role_org_node_id: "not an identifier",
      role_offset: "-1",
      role_monthly_hours_min: "1 000",
      role_headcount_max: "2,5",
      calendar_monday_min: "huit",
      org_level: "0",
      org_level_min: "0",
      org_level_max: "1,5",
      org_code: "x".repeat(21),
    });
    expect(queriesOf("GET /reference/org-nodes")).toEqual([{}]);
    expect(queriesOf("GET /reference/resource-roles")).toEqual([{}]);
    expect(queriesOf("GET /reference/calendars")).toEqual([{}, WHOLE]);
  });

  it("keep the grid of a list a search or a filter narrows to nothing, the search shown to be changed, and say empty a list nothing narrows", () => {
    const query = { sort: undefined, search: "Personne" };
    const none = { ...ROLE_PAGE.meta, total: 0 };
    const filters = {
      orgNode: undefined,
      category: undefined,
      calendar: undefined,
      state: undefined,
      monthlyHours: NO_BOUNDS,
      headcount: NO_BOUNDS,
    };
    const narrowed = rendered(
      <ResourceRoleList
        rows={[]}
        page={none}
        query={query}
        preferences={undefined}
        readsInactive
        nodes={[]}
        categories={[]}
        calendars={[]}
        filters={filters}
      />,
    );
    expect(rows(narrowed, "Rôles de ressources")).toContain("Aucune ligne ne répond à la demande.");
    expect(narrowed).toContain('value="Personne"');
    const filtered = rendered(
      <ResourceRoleList
        rows={[]}
        page={none}
        query={NO_QUERY}
        preferences={undefined}
        readsInactive
        nodes={[]}
        categories={undefined}
        calendars={[]}
        filters={{ ...filters, calendar: STANDARD }}
      />,
    );
    expect(filtered).toContain('aria-label="Rôles de ressources"');
    // The categories the API refused offer no filter.
    expect(filtered).not.toContain("Toutes les catégories");
    const empty = rendered(
      <CalendarList
        rows={[]}
        page={none}
        query={NO_QUERY}
        preferences={undefined}
        readsInactive={false}
        state={undefined}
        hours={NO_HOURS}
      />,
    );
    expect(text(empty)).toBe("Calendriers Aucun calendrier.");
    const tree = rendered(
      <OrgNodeList
        rows={[]}
        query={NO_QUERY}
        preferences={undefined}
        readsInactive
        filters={{ code: undefined, level: 4, state: undefined, levels: NO_BOUNDS }}
        levels={[]}
      />,
    );
    expect(rows(tree, "Arbre d’organisation")).toContain("Aucune ligne ne répond à la demande.");
  });

  it("ask the active objects alone when the address does not ask for the deactivated ones, and offer to show them [WF-REF-0150-A]", async () => {
    const page = await resourcesAt();
    for (const route of LISTS) {
      expect(queriesOf(route).every((query) => !("include_inactive" in query))).toBe(true);
    }
    expect(page).toMatch(
      /<a[^>]*href="\/reference\/resources\?include_inactive=true"[^>]*>.*?Afficher aussi les désactivés<\/a>/,
    );
    // The fake back answers its example whatever is asked — the deactivated role among them —:
    // what the screen asks is what this proves.
  });

  it("ask the deactivated objects too when the address asks for them, each said deactivated and offered to be reactivated as the server lists it, and offer to hide them [WF-REF-0150-A]", async () => {
    const page = await resourcesAt({ include_inactive: "true", role_offset: "50" });
    for (const route of LISTS) {
      expect(queriesOf(route).map((query) => query.include_inactive)).not.toContain(undefined);
    }
    expect(page).toContain('aria-label="Réactiver «\u00a0Automaticien\u00a0»"');
    // Hidden again back to the first page of the roles.
    expect(page).toMatch(
      /<a[^>]*href="\/reference\/resources"[^>]*>.*?Masquer les désactivés<\/a>/,
    );
  });

  it("never ask the deactivated objects of a session that may not read the settings of the resources, which the contract refuses, nor offer to show them, to filter on them or to reactivate them [WF-IHM-0090-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /session": "session_estimator",
      "GET /reference/org-nodes": "org_nodes_reader",
      "GET /reference/resource-roles": "resource_roles_reader",
      "GET /reference/calendars": "calendars_reader",
    };
    const page = await resourcesAt({
      include_inactive: "true",
      role_is_active: "false",
      calendar_is_active: "false",
    });
    for (const route of LISTS) {
      expect(
        queriesOf(route).every(
          (query) => !("include_inactive" in query) && !("is_active" in query),
        ),
      ).toBe(true);
    }
    expect(text(page)).not.toContain("désactivés");
    expect(page).not.toContain("État des objets");
    // The roles read without the right to modify them, as the server lists them: no command.
    expect(rows(page, "Rôles de ressources")).toHaveLength(5);
    expect(page).not.toContain("Réactiver");
    // The categories, which it may read with the deactivated ones, are offered as it may read them.
    expect(queriesOf("GET /reference/cost-categories")).toEqual([
      { include_inactive: "true", ...WHOLE },
    ]);
  });
});

describe("the settings of the risks and of the indicators", () => {
  it("present the three bounds of each axis of the risk matrix, the severity in percentage of the reference budget", async () => {
    const page = rendered(await RiskSettingsPage());
    expect(rows(page, "Bornes de la matrice de risques")).toEqual([
      "Axe Première borne Deuxième borne Troisième borne",
      "Probabilité 10 % 30 % 60 %",
      "Gravité, en pourcentage du budget de référence 1 % 5 % 10 %",
    ]);
  });

  it("present the zone of each cell of the risk matrix, the highest probability at the top", async () => {
    const page = rendered(await RiskSettingsPage());
    expect(rows(page, "Zones de la matrice de risques")).toEqual([
      "Probabilité, puis gravité Gravité, niveau 1 Gravité, niveau 2 Gravité, niveau 3 Gravité, niveau 4",
      "Probabilité, niveau 4 Vigilance Vigilance Alerte Alerte",
      "Probabilité, niveau 3 Nominal Vigilance Vigilance Alerte",
      "Probabilité, niveau 2 Nominal Nominal Vigilance Vigilance",
      "Probabilité, niveau 1 Nominal Nominal Nominal Vigilance",
    ]);
  });

  it("place each zone by probability then severity, never the transposed cell", () => {
    // The matrix of the example is symmetric: one zone changed, at the rank of the lowest
    // probability and the highest severity, tells the order from its transposition.
    const settings = example("reference_settings") as components["schemas"]["ReferenceSettings"];
    const matrix = { ...settings.risk_matrix, zones: settings.risk_matrix.zones.with(3, "alert") };
    const page = rendered(<RiskZonesTable matrix={matrix} />);
    const [, highest, , , lowest] = rows(page, "Zones de la matrice de risques");
    expect(lowest).toBe("Probabilité, niveau 1 Nominal Nominal Nominal Alerte");
    expect(highest).toBe("Probabilité, niveau 4 Vigilance Vigilance Alerte Alerte");
  });

  it("present the thresholds of the two indices and the delay between two reviews", async () => {
    const page = rendered(await IndicatorSettingsPage());
    expect(rows(page, "Seuils d’alerte des indices")).toEqual([
      "Indice Seuil de vigilance Seuil d’alerte",
      "Indice de coût 0,9 0,8",
      "Indice de délai 0,9 0,8",
    ]);
    expect(text(page)).toContain(
      "Délai maximal entre deux révisions marquées d’un projet en cours : 8 semaines.",
    );
  });
});
