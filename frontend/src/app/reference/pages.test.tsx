// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { CostCategoryList, CostTypeList } from "@/components/reference/cost-lists";
import type { RateGridProps } from "@/components/reference/rate-grid";
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
import { queryOfCall } from "@/test/queries";

import CostSettingsPage, { generateMetadata as costsMetadata } from "./costs/page";
import IndicatorSettingsPage from "./indicators/page";
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
// The session of the contract, the sizes of pages its account keeps set for a test.
const kept = vi.hoisted((): { grids: Record<string, { page_size: number }> } => ({ grids: {} }));
vi.mock("@/session/request", async (original) => {
  const actual = await original<typeof import("@/session/request")>();
  return {
    ...actual,
    requestSession: async () => {
      const session = await actual.requestSession();
      return session === undefined
        ? undefined
        : {
            ...session,
            display_preferences: {
              ...session.display_preferences,
              grids: { ...session.display_preferences?.grids, ...kept.grids },
            },
          };
    },
  };
});
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

/** The labour nature of the witness. */
const LABOUR = "01926f3a-7c00-7000-8000-000000000461";

/** A list read whole as a list of choices is: every page, by the largest the contract takes. */
const WHOLE = { limit: "500", offset: "0" };

const NO_QUERY = { sort: undefined, search: undefined, size: undefined };

/** The roles of the witness, as the server pages them. */
const ROLE_PAGE = example("resource_roles") as { items: ResourceRole[]; meta: ListPage };

/** The reactivation available, as the server lists it on the deactivated automation engineer. */
const REACTIVATE =
  ROLE_PAGE.items.find((role) => role.label === "Automaticien")?.available_commands ?? [];

/** The queries the pages sent to an operation, each as its parameters. */
function queriesOf(route: string): Record<string, string>[] {
  return callsTo(route).map((call) => queryOfCall(call.query));
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
  kept.grids = {};
  grids.rates = [];
  server.clients = [];
  server.answers = {
    "GET /me": "me",
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
    expect(handed?.query).toEqual({ sort: undefined, search: undefined, size: 50 });
    // The page of the server's size: nothing asked but what the address asks.
    expect(queriesOf(RATES)).toEqual([{}]);
  });

  it("ask the server for the page, the sort and the search of the rates the address asks, by the names of the contract [WF-IHM-0060-A]", async () => {
    await costsAt({
      search: "Automatisme",
      sort_by: "rate.2026",
      sort_order: "desc",
      offset: "50",
      limit: "25",
      // The names of the other grids of the screen are not the rates'.
      type_sort_by: "label",
      type_limit: "100",
    });
    expect(queriesOf(RATES)).toEqual([
      {
        search: "Automatisme",
        sort_by: "rate.2026",
        sort_order: "desc",
        offset: "50",
        limit: "25",
      },
    ]);
    expect(grids.rates[0]?.query).toEqual({
      sort: { column: "rate.2026", order: "desc" },
      search: "Automatisme",
      size: 25,
    });
  });

  it("ask no sort of the rates the contract does not take, nor a page it would refuse", async () => {
    await costsAt({ sort_by: "rate.1999", offset: "-50" });
    expect(queriesOf(RATES)).toEqual([{}]);
  });

  it("offer no entry of a rate, nor a reactivation the server does not list, to a session that may only read the cost settings [WF-IHM-0090-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /me": "me_estimator",
      "GET /reference/cost-types": "cost_types_reader",
      "GET /reference/cost-categories": "volume/cost_categories_reader",
    };
    const page = await costsAt();
    expect(grids.rates[0]?.editable).toBe(false);
    // The natures and the categories read without the right to modify them carry no command.
    expect(rows(page, "Natures de coût")[1]).toBe("DEB Débours Hors main-d’œuvre Actif");
    expect(rows(page, "Catégories de coût")[1]).toBe("ACH-001 Sous-traitance Débours 604001 Actif");
    expect(page).not.toContain("Réactiver");
    expect(queriesOf("GET /reference/cost-types")).toEqual([{}, WHOLE]); // no category form
  });

  it("offer the creation and the modification of the natures and the categories to a session that may modify the cost settings, and say the fake back keeps nothing; neither to a session that may only read them [WF-IHM-0090-A]", async () => {
    const page = await costsAt();
    expect(text(page)).toContain("Nouvelle nature");
    expect(text(page)).toContain("Nouvelle catégorie");
    expect(page).toContain('aria-label="Modifier «\u00a0Débours\u00a0»"');
    expect(page).toMatch(/<p role="note"[^>]*>.*?Maquette\u00a0: le service simulé répond/);
    server.answers = {
      ...server.answers,
      "GET /me": "me_estimator",
      "GET /reference/cost-types": "cost_types_reader",
      "GET /reference/cost-categories": "volume/cost_categories_reader",
    };
    const read = await costsAt();
    for (const offered of ["Nouvelle", "Modifier", "Désactiver", "Maquette"]) {
      expect(read).not.toContain(offered);
    }
  });

  it("offer no command that deletes a nature or a category, which are deactivated [WF-REF-0010-A]", async () => {
    const page = await costsAt();
    // Aucun écran ne propose de supprimer un objet du référentiel.
    expect(text(page)).toContain("Désactiver");
    expect(text(page)).not.toMatch(/Supprimer|Effacer/);
  });

  it("present the natures of cost by their type, and each category by its nature and its accounting code, on dense grids sorted by each of their columns [WF-IHM-0060-A]", async () => {
    const page = await costsAt();
    // The session may modify the cost settings: each row offers its modification, and the
    // deactivation each object lists — the last nature of provision too since EP-14/L42p.
    expect(rows(page, "Natures de coût")).toEqual([
      "Code Libellé Type État Modifier",
      "DEB Débours Hors main-d’œuvre Actif Désactiver Modifier",
      "MO Main-d'œuvre Main-d’œuvre Actif Désactiver Modifier",
      "PRV Provision Provision pour risques Actif Désactiver Modifier",
      "3 natures",
    ]);
    expect(sortable(page, "Natures de coût")).toEqual(["Code", "Libellé", "Type", "État"]);
    const categories = rows(page, "Catégories de coût");
    expect(categories[0]).toBe("Code Libellé Nature Code comptable État Modifier");
    expect(categories[1]).toBe("ACH-001 Sous-traitance Débours 604001 Actif Désactiver Modifier");
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
      // For a session that writes, every nature, its type compared by the category form (#577).
      { include_inactive: "true", ...WHOLE },
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
    expect(queriesOf("GET /reference/cost-types")).toEqual([
      {},
      WHOLE,
      { include_inactive: "true", ...WHOLE },
    ]);
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
    const lists = (commands: components["schemas"]["ReferenceCommands"]) =>
      rendered(
        <>
          <CostTypeList
            rows={[{ ...labour, is_active: false, available_commands: commands }]}
            page={{ ...categories.meta, total: 1 }}
            query={NO_QUERY}
            preferences={undefined}
            state={undefined}
            readsInactive
            editable={false}
            kinds={[]}
          />
          <CostCategoryList
            rows={[{ ...category, is_active: false, available_commands: commands }]}
            page={{ ...categories.meta, total: 1 }}
            query={NO_QUERY}
            preferences={undefined}
            state={undefined}
            readsInactive
            editable={false}
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
          editable={false}
          kinds={[]}
        />
        <CostCategoryList
          rows={read.items}
          page={read.meta}
          query={NO_QUERY}
          preferences={undefined}
          state={undefined}
          readsInactive={false}
          editable={false}
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

describe("the settings of the costs, the size of the pages", () => {
  it.each([
    ["the rates", RATES, "limit"],
    ["the natures", "GET /reference/cost-types", "type_limit"],
    ["the categories", "GET /reference/cost-categories", "category_limit"],
  ])(
    "sends the limit of the reading of %s: 50 unasked, the page size asked [WF-IHM-0060-A]",
    async (_name, route, name) => {
      for (const [search, limit] of [
        [{}, "50"],
        [{ [name]: "25" }, "25"],
      ] as const) {
        server.clients = [];
        await costsAt(search);
        const [call] = callsTo(route);
        expect(Object.fromEntries(call?.query ?? []).limit).toBe(limit);
      }
    },
  );

  it.each([
    ["the rates", RATES, "hourly_rates"],
    ["the natures", "GET /reference/cost-types", "cost_types"],
    ["the categories", "GET /reference/cost-categories", "cost_categories"],
  ])(
    "reads the page size kept for %s when the address asks none [WF-IHM-0060-A]",
    async (_name, route, key) => {
      kept.grids = { [key]: { page_size: 25 } };
      await costsAt({});
      const call = callsTo(route);
      expect(Object.fromEntries(call[0]?.query ?? []).limit).toBe("25");
    },
  );
});
