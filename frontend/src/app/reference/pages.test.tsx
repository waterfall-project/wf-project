// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { CostCategoryList, CostTypeList } from "@/components/reference/cost-lists";
import type { RateGridProps } from "@/components/reference/rate-grid";
import { CalendarList, OrgNodeList, ResourceRoleList } from "@/components/reference/resource-lists";
import { RiskZonesTable } from "@/components/reference/setting-tables";
import { CATALOGUES } from "@/i18n/catalogues";
import type { PageSearchParams } from "@/navigation/context";
import { example, type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import CostSettingsPage, { generateMetadata as costsMetadata } from "./costs/page";
import IndicatorSettingsPage from "./indicators/page";
import ResourceSettingsPage from "./resources/page";
import RiskSettingsPage from "./risks/page";

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

/** The choices of the lists of a page, each by its value and its text as written. */
function options(markup: string): (string | undefined)[][] {
  return [...markup.matchAll(/<option value="([^"]+)">([^<]*)<\/option>/g)].map((option) => [
    option[1],
    option[2]?.replace(/&#x27;/g, "'"),
  ]);
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

  it("hand the grid of the hourly rates the answer whole, its currency, and its entry to a session that may modify the cost settings", async () => {
    const page = await costsAt();
    expect(text(page)).toContain(
      "Paramètres de coûts Montants exprimés en EUR, devise unique de l’installation.",
    );
    const [handed] = grids.rates;
    expect(handed?.grid.rows).toHaveLength(150);
    expect(handed?.grid.years).toHaveLength(15);
    expect(handed?.currency).toBe("EUR");
    expect(handed?.editable).toBe(true);
    expect(handed?.query).toEqual({ sort: undefined, search: undefined });
    expect(callsTo(RATES).map((call) => call.query.toString())).toEqual([""]);
  });

  it("ask the server for the categories a search retains, by the name of the contract", async () => {
    await costsAt({ search: "Automatisme", sort_by: "label" });
    expect(callsTo(RATES).map((call) => Object.fromEntries(call.query))).toEqual([
      { search: "Automatisme" },
    ]);
    expect(grids.rates[0]?.query).toEqual({ sort: undefined, search: "Automatisme" });
  });

  it("offer no entry of a rate to a session that may only read the cost settings", async () => {
    server.answers = { ...server.answers, "GET /session": "session_estimator" };
    await costsAt();
    expect(grids.rates[0]?.editable).toBe(false);
  });

  it("present the natures of cost by their type, and each category by its nature and its accounting code", async () => {
    const page = await costsAt();
    expect(rows(page, "Natures de coût")).toEqual([
      "Code Libellé Type État",
      "MO Main-d'œuvre Main-d’œuvre Actif",
      "DEB Débours Hors main-d’œuvre Actif",
      "PRV Provision Provision Actif",
    ]);
    const categories = rows(page, "Catégories de coût");
    expect(categories).toHaveLength(201);
    expect(categories[1]).toBe("MO-001 Ingénierie électrique Main-d'œuvre 641001 Actif");
    expect(categories).toContain("ACH-001 Sous-traitance Débours 604001 Actif");
  });

  it("ask the active natures, categories and rates alone by default, the deactivated ones too when the address asks for them, and offer to show and hide them [WF-REF-0150-A]", async () => {
    const reads = ["GET /reference/cost-types", "GET /reference/cost-categories", RATES] as const;
    const shown = await costsAt();
    for (const route of reads) {
      expect(queriesOf(route)).toEqual([{}]);
    }
    expect(shown).toMatch(
      /<a[^>]*href="\/reference\/costs\?include_inactive=true"[^>]*>.*?Afficher aussi les désactivés<\/a>/,
    );
    server.clients = [];
    const hidden = await costsAt({ include_inactive: "true", search: "Automatisme" });
    expect(queriesOf("GET /reference/cost-types")).toEqual([{ include_inactive: "true" }]);
    expect(queriesOf("GET /reference/cost-categories")).toEqual([{ include_inactive: "true" }]);
    expect(queriesOf(RATES)).toEqual([{ include_inactive: "true", search: "Automatisme" }]);
    expect(hidden).toMatch(/<a[^>]*href="\/reference\/costs"[^>]*>.*?Masquer les désactivés<\/a>/);
  });

  it("offer the reactivation of a deactivated nature or category to a session that may modify the cost settings, and to no other [WF-REF-0150-A]", () => {
    const [labour] = example("cost_types") as components["schemas"]["CostType"][];
    const [category] = example("volume/cost_categories") as components["schemas"]["CostCategory"][];
    if (labour === undefined || category === undefined) {
      throw new Error("the examples hold a nature and a category");
    }
    const lists = (reactivable: boolean) =>
      rendered(
        <>
          <CostTypeList types={[{ ...labour, is_active: false }]} reactivable={reactivable} />
          <CostCategoryList
            categories={[{ ...category, is_active: false }]}
            reactivable={reactivable}
          />
        </>,
      );
    const offered = lists(true);
    expect(rows(offered, "Natures de coût")[1]).toBe(
      "MO Main-d'œuvre Main-d’œuvre Désactivé Réactiver",
    );
    expect(offered).toContain('aria-label="Réactiver «\u00a0Main-d&#x27;œuvre\u00a0»"');
    expect(offered).toContain('aria-label="Réactiver «\u00a0Ingénierie électrique\u00a0»"');
    const read = lists(false);
    expect(rows(read, "Catégories de coût")[1]).toBe(
      "MO-001 Ingénierie électrique Main-d'œuvre 641001 Désactivé",
    );
  });

  it("are not found when the API refuses or does not find the grid", async () => {
    server.answers = { ...server.answers, [RATES]: NOT_FOUND };
    await expect(costsAt()).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
  });
});

describe("the settings of the resources", () => {
  it("present the organisation as a tree grid in the order the server gives, each node by its label set in by its depth, its code and its depth", async () => {
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
  });

  it("present each role with its node, its category, its calendar and its capacity, named as the server resolves them, on a grid sorted by each of its columns [WF-IHM-0060-A]", async () => {
    const page = await resourcesAt({ include_inactive: "true" });
    expect(rows(page, "Rôles de ressources")).toEqual([
      "Libellé Nœud d’organisation Catégorie de coût Calendrier Heures par mois Effectif État",
      "Ingénieur électricien Bureau d'études électricité Ingénierie électrique Semaine standard 658 654,00 3 800 Actif",
      "Technicien de mise en service Bureau d'études électricité Mise en service Semaine standard 485 324,00 2 800 Actif",
      "Monteur câbleur Atelier de câblage Ingénierie électrique Semaine de quatre jours 216 662,50 1 250 Actif",
      "Automaticien Bureau d'études électricité Ingénierie électrique Semaine de trente-neuf heures 338,00 2 Désactivé Réactiver",
      "4 rôles",
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
    // The roles are filtered by node, offered in the order of the tree, each set in by its depth.
    expect(text(page)).toContain("Nœud d’organisation Tous les nœuds");
    expect(options(page)).toEqual([
      ["01926f3a-7c00-7000-8000-000000000470", "DT · Direction technique"],
      [BUREAU, "\u2003BE-ELEC · Bureau d'études électricité"],
      ["01926f3a-7c00-7000-8000-000000000472", "\u2003\u2003AT-CABL · Atelier de câblage"],
      ["01926f3a-7c00-7000-8000-000000000473", "\u2003ACHATS · Service des achats"],
    ]);
  });

  it("present each calendar by its seven values of hours, the default one marked, sorted by its label, its mark and its state, and the units of duration", async () => {
    const page = await resourcesAt();
    expect(rows(page, "Calendriers")).toEqual([
      "Libellé Lun. Mar. Mer. Jeu. Ven. Sam. Dim. Par défaut État",
      "Semaine standard 8 8 8 8 8 0 0 Calendrier par défaut Actif",
      "Semaine de quatre jours 10 10 10 10 0 0 0 Actif",
      "2 calendriers",
    ]);
    expect(sortable(page, "Calendriers")).toEqual(["Libellé", "Par défaut", "État"]);
    expect(text(page)).toContain(
      "Unités de durée Heures par jour 8 Heures par semaine 40 Jours par mois 20",
    );
  });

  it("ask each list of the server by the names of the contract, as the address asks it under the names of its grid [WF-IHM-0060-A]", async () => {
    await resourcesAt({
      org_search: "BE",
      role_search: "Ingé",
      role_sort_by: "monthly_hours",
      role_sort_order: "desc",
      role_org_node_id: BUREAU,
      calendar_search: "Semaine",
      calendar_sort_by: "is_default",
      // The names of the contract alone belong to no grid of this screen.
      search: "ignored",
      sort_by: "label",
    });
    // The tree searched, and the tree whole, which the filter of the roles offers.
    expect(queriesOf("GET /reference/org-nodes")).toEqual([{ search: "BE" }, {}]);
    expect(queriesOf("GET /reference/resource-roles")).toEqual([
      { search: "Ingé", sort_by: "monthly_hours", sort_order: "desc", org_node_id: BUREAU },
    ]);
    expect(queriesOf("GET /reference/calendars")).toEqual([
      { search: "Semaine", sort_by: "is_default", sort_order: "asc" },
    ]);
  });

  it("read the tree once, and ask no sort nor search, when the address asks none", async () => {
    await resourcesAt({ role_sort_by: "capacity", role_org_node_id: "not an identifier" });
    expect(queriesOf("GET /reference/org-nodes")).toEqual([{}]);
    expect(queriesOf("GET /reference/resource-roles")).toEqual([{}]);
    expect(queriesOf("GET /reference/calendars")).toEqual([{}]);
  });

  it("keep the grid of a list a search or a filter narrows to nothing, the search shown to be changed, and say empty a list nothing narrows", () => {
    const query = { sort: undefined, search: "Personne" };
    const narrowed = rendered(
      <ResourceRoleList
        rows={[]}
        query={query}
        preferences={undefined}
        reactivable
        nodes={[]}
        orgNode={undefined}
      />,
    );
    expect(rows(narrowed, "Rôles de ressources")).toContain("Aucune ligne ne répond à la demande.");
    expect(narrowed).toContain('value="Personne"');
    const filtered = rendered(
      <ResourceRoleList
        rows={[]}
        query={{ sort: undefined, search: undefined }}
        preferences={undefined}
        reactivable
        nodes={[]}
        orgNode={BUREAU}
      />,
    );
    expect(filtered).toContain('aria-label="Rôles de ressources"');
    const none = rendered(
      <CalendarList
        rows={[]}
        query={{ sort: undefined, search: undefined }}
        preferences={undefined}
        reactivable
      />,
    );
    expect(text(none)).toBe("Calendriers Aucun calendrier.");
    const tree = rendered(
      <OrgNodeList rows={[]} query={query} preferences={undefined} reactivable={false} />,
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

  it("ask the deactivated objects too when the address asks for them, each said deactivated and offered to be reactivated, and offer to hide them [WF-REF-0150-A]", async () => {
    const page = await resourcesAt({ include_inactive: "true" });
    for (const route of LISTS) {
      expect(queriesOf(route).map((query) => query.include_inactive)).not.toContain(undefined);
    }
    expect(page).toContain('aria-label="Réactiver «\u00a0Automaticien\u00a0»"');
    expect(page).toMatch(
      /<a[^>]*href="\/reference\/resources"[^>]*>.*?Masquer les désactivés<\/a>/,
    );
  });

  it("never ask the deactivated objects of a session that may not read the settings of the resources, which the contract refuses, nor offer to show or reactivate them", async () => {
    server.answers = { ...server.answers, "GET /session": "session_estimator" };
    const page = await resourcesAt({ include_inactive: "true" });
    for (const route of LISTS) {
      expect(queriesOf(route).every((query) => !("include_inactive" in query))).toBe(true);
    }
    expect(text(page)).not.toContain("désactivés");
    expect(text(page)).not.toContain("Réactiver");
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
