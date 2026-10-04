// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { RateGridProps } from "@/components/reference/rate-grid";
import { CATALOGUES } from "@/i18n/catalogues";
import type { PageSearchParams } from "@/navigation/context";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

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
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/reference/costs",
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
  return rendered(await CostSettingsPage({ searchParams: Promise.resolve(search) }));
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

  it("are not found when the API refuses or does not find the grid", async () => {
    server.answers = { ...server.answers, [RATES]: NOT_FOUND };
    await expect(costsAt()).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
  });
});

describe("the settings of the resources", () => {
  it("present the organisation, each node with the one it is attached to", async () => {
    const page = rendered(await ResourceSettingsPage());
    expect(rows(page, "Arbre d’organisation")).toEqual([
      "Libellé Rattaché à État",
      "Direction technique Racine de l’arbre Actif",
      "Bureau d'études électricité Direction technique Actif",
      "Atelier de câblage Bureau d'études électricité Actif",
      "Service de mise en service Direction technique Actif",
    ]);
  });

  it("present each role with its node, its category, its calendar and its capacity, a deactivated one said so", async () => {
    const page = rendered(await ResourceSettingsPage());
    expect(rows(page, "Rôles de ressources")).toEqual([
      "Libellé Nœud d’organisation Catégorie de coût Calendrier Heures par mois Effectif État",
      "Ingénieur électricien Bureau d'études électricité Ingénierie électrique Semaine standard 151,67 6 Actif",
      "Technicien de mise en service Bureau d'études électricité Mise en service Semaine standard 151,67 4 Actif",
      "Automaticien Bureau d'études électricité Ingénierie électrique Semaine standard 151,67 2 Désactivé",
    ]);
  });

  it("present each calendar by its seven values of hours, the default one marked, and the units of duration", async () => {
    const page = rendered(await ResourceSettingsPage());
    expect(rows(page, "Calendriers")).toEqual([
      "Libellé Lun. Mar. Mer. Jeu. Ven. Sam. Dim. Par défaut État",
      "Semaine standard 8 8 8 8 8 0 0 Calendrier par défaut Actif",
      "Semaine de quatre jours 10 10 10 10 0 0 0 Actif",
    ]);
    expect(text(page)).toContain(
      "Unités de durée Heures par jour 8 Heures par semaine 40 Jours par mois 20",
    );
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
