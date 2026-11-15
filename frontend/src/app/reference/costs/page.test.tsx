// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { NatureChoice } from "@/components/reference/cost-kinds";
import { CATALOGUES } from "@/i18n/catalogues";
import type { PageSearchParams } from "@/navigation/context";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";
import { queryOfCall } from "@/test/queries";

import CostSettingsPage from "./page";

// What the page of the costs hands the form of a category (EP-02/L42g): the type of every nature,
// deactivated ones included, read apart for a session that writes and may read them.
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
// The session of the contract, some of its permissions withdrawn for a test: no account of the
// witness writes the cost settings without reading them (decision of the author, 2026-10-09).
const withdrawn = vi.hoisted(() => ({ permissions: [] as string[] }));
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
            permissions: session.permissions.filter(
              (permission) => !withdrawn.permissions.includes(permission),
            ),
          };
    },
  };
});
// The list of the categories renders as it would, and keeps what its page handed it.
const lists = vi.hoisted((): { categories: Record<string, unknown>[] } => ({ categories: [] }));
vi.mock("@/components/reference/cost-lists", async (original) => {
  const actual = await original<typeof import("@/components/reference/cost-lists")>();
  const { createElement } = await import("react");
  type Props = Parameters<typeof actual.CostCategoryList>[0];
  return {
    ...actual,
    CostCategoryList: (props: Props) => {
      lists.categories.push(props as unknown as Record<string, unknown>);
      return createElement(actual.CostCategoryList, props);
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

const TYPES = "GET /reference/cost-types";
/** A list read whole as a list of choices is: every page, by the largest the contract takes. */
const WHOLE = { limit: "500", offset: "0" };
/** The disbursements of the witness. */
const DISBURSEMENTS = "01926f3a-7c00-7000-8000-000000000462";

/** Render the settings of the costs at the query given, in French. */
async function costsAt(search: PageSearchParams = {}): Promise<string> {
  const page = await CostSettingsPage({ searchParams: Promise.resolve(search) });
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      {page as ReactNode}
    </NextIntlClientProvider>,
  );
}

/** The queries the page asked of a route of the fake back. */
function queriesOf(route: string): Record<string, string>[] {
  return server.clients
    .flatMap((client) => client.calls)
    .filter((call) => call.route === route)
    .map((call) => queryOfCall(call.query));
}

/** What the page handed the list of the categories: every nature, and the natures offered. */
function handed(): { every: unknown; natures: unknown } {
  const [props] = lists.categories;
  return { every: props?.every, natures: props?.natures };
}

/** The state of the disbursements among natures handed to the list, as their choices say it. */
function disbursements(natures: unknown): boolean | undefined {
  return (natures as NatureChoice[] | undefined)?.find((nature) => nature.id === DISBURSEMENTS)
    ?.active;
}

beforeEach(() => {
  lists.categories = [];
  server.clients = [];
  withdrawn.permissions = [];
  server.answers = {
    "GET /me": "me",
    "GET /reference/settings": "reference_settings",
    [TYPES]: "cost_types",
    "GET /reference/cost-categories": "volume/cost_categories",
    "GET /reference/hourly-rates": "volume/hourly_rate_grid",
  };
});

describe("the nature an address filters the categories by", () => {
  const CATEGORIES = "GET /reference/cost-categories";
  const NATURE = "01926f3a-7c00-7000-8000-000000000461";

  it("is sent to the read of the categories when it is a UUID [US-1770]", async () => {
    await costsAt({ category_cost_type_id: NATURE });
    const [query] = queriesOf(CATEGORIES);
    expect(query).toMatchObject({ cost_type_id: NATURE });
  });

  it("is not retained when it is not a UUID: the screen opens without this filter, and no read leaves with it [US-1770]", async () => {
    await costsAt({ category_cost_type_id: "abc" });
    const queries = queriesOf(CATEGORIES);
    expect(queries.length).toBeGreaterThan(0);
    expect(queries.every((query) => !("cost_type_id" in query))).toBe(true);
  });
});

describe("the types of the natures the page hands the form of a category", () => {
  it("are every nature read with the deactivated ones, apart from the natures offered, for a session that writes", async () => {
    // The natures offered, then every one with the deactivated ones: the disbursements deactivated.
    server.answers = {
      ...server.answers,
      [TYPES]: ["cost_types", "cost_types", "cost_types_with_inactive"],
    };
    await costsAt();
    expect(queriesOf(TYPES)).toEqual([
      { is_active: "true" },
      WHOLE,
      { include_inactive: "true", ...WHOLE },
    ]);
    const { every, natures } = handed();
    // The third read gives the types: the disbursements deactivated there, active among the offered.
    expect(disbursements(every)).toBe(false);
    expect(disbursements(natures)).toBe(true);
    expect((every as NatureChoice[]).map((nature) => [nature.code, nature.kind])).toEqual([
      ["DEB", "non_labor"],
      ["MO", "labor"],
      ["PRV", "provision"],
    ]);
  });

  it("are read apart from the natures offered, the active ones alone, whatever state the list of the natures shows [WF-REF-0150-A]", async () => {
    // The list of the natures shows every one; the natures offered stay the active ones.
    server.answers = {
      ...server.answers,
      [TYPES]: ["cost_types_with_inactive", "cost_types", "cost_types_with_inactive"],
    };
    await costsAt({ type_is_active: "all", include_inactive: "true" });
    expect(queriesOf(TYPES)).toEqual([
      { include_inactive: "true" },
      WHOLE,
      { include_inactive: "true", ...WHOLE },
    ]);
    const { every, natures } = handed();
    expect(disbursements(natures)).toBe(true);
    expect(disbursements(every)).toBe(false);
  });

  it("are none for a session that only reads, which has no form", async () => {
    server.answers = {
      ...server.answers,
      "GET /me": "me_estimator",
      [TYPES]: "cost_types_reader",
    };
    await costsAt();
    expect(queriesOf(TYPES)).toEqual([{}, WHOLE]);
    expect(handed().every).toBeUndefined();
  });

  it("never ask the deactivated objects of a session that only reads the cost settings, which the contract keeps for the permission to modify them, nor offer a filter of the state [WF-REF-0150-A]", async () => {
    // `cost_settings.read` without `cost_settings.write`: the fake back would answer the deactivated
    // ones whatever the permission, so the request of the page is what is proved.
    withdrawn.permissions = ["cost_settings.write"];
    const page = await costsAt({
      include_inactive: "true",
      type_is_active: "false",
      category_is_active: "all",
      is_active: "false",
    });
    for (const route of [TYPES, "GET /reference/cost-categories", "GET /reference/hourly-rates"]) {
      const queries = queriesOf(route);
      expect(queries.length).toBeGreaterThan(0);
      expect(
        queries.every((query) => !("include_inactive" in query) && !("is_active" in query)),
      ).toBe(true);
    }
    expect(page).not.toContain("désactivés");
    expect(page).not.toContain("Désactivés");
    expect(page).not.toContain("par défaut)");
    expect(page).not.toContain("Nouvelle catégorie");
  });
});

describe("the leaf of the correspondence of the actual costs", () => {
  it("is led to by a link of the header, to its route [WF-REF-0190-A]", async () => {
    const page = await costsAt();
    expect(page).toMatch(
      /<a [^>]*href="\/reference\/costs\/actual-cost-mapping"[^>]*>.*?Correspondance des coûts réels/,
    );
  });
});

describe("the name of the company", () => {
  it.each([
    ["a session that holds installation.write", "me"],
    ["a session that holds cost_settings.write alone", "me_manager"],
  ] as const)(
    "is no longer on the screen of the costs, which the card of the installation carries, for %s",
    async (_who, me) => {
      server.answers = { ...server.answers, "GET /me": me };
      const page = await costsAt();
      expect(page).toContain("Montants exprimés en");
      expect(page).not.toContain("Delmas Automatismes");
      expect(page).not.toContain("Modifier le nom de l’entreprise");
      expect(page).not.toContain("Nom de l’entreprise");
      expect(page).not.toContain('role="note"');
    },
  );
});

describe("the layout of the settings of the costs", () => {
  it("stacks the natures, the categories and the hourly rates in a page that scrolls, as the settings of the resources do", async () => {
    const page = await costsAt();
    const at = (title: string) => page.indexOf(`<section aria-label="${title}"`);
    const natures = at("Natures de coût");
    const categories = at("Catégories de coût");
    const rates = at("Taux horaires");
    expect(natures).toBeGreaterThan(0);
    expect(categories).toBeGreaterThan(natures);
    expect(rates).toBeGreaterThan(categories);
    // No side column, and a screen that does not fill the window at any width.
    expect(page).not.toContain("<aside");
    expect(page).not.toContain("data-fill");
    // The filters of the rates are inside the third section.
    expect(page.indexOf("Bornes de «\u00a0Grille des taux horaires\u00a0»")).toBeGreaterThan(rates);
  });

  it("sets each section in its card, the creation of a list in the header of its card before its table, the column of a year in the bar of the rates [WF-IHM-0060-A]", async () => {
    const page = await costsAt();
    for (const title of ["Natures de coût", "Catégories de coût", "Taux horaires"]) {
      expect(page).toContain(`<section aria-label="${title}" data-slot="section-card"`);
    }
    const header = (title: string) => {
      const start = page.indexOf(`<section aria-label="${title}"`);
      return page.slice(start, page.indexOf('data-slot="card-content"', start));
    };
    expect(header("Natures de coût")).toContain("Nouvelle nature");
    expect(header("Catégories de coût")).toContain("Nouvelle catégorie");
    // The card of the rates has no command at the right of its title: its column is added from
    // the bar of its grid.
    expect(header("Taux horaires")).not.toContain("<button");
    const rates = page.indexOf('<section aria-label="Taux horaires"');
    const bar = page.indexOf("data-grid-toolbar", rates);
    expect(page.indexOf("Ajouter la colonne", rates)).toBeGreaterThan(bar);
  });
});
