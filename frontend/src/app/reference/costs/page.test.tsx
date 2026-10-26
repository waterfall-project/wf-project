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

describe("the types of the natures the page hands the form of a category", () => {
  it("are every nature read with the deactivated ones, apart from the natures offered, for a session that writes", async () => {
    // The natures offered, then every one with the deactivated ones: the disbursements deactivated.
    server.answers = {
      ...server.answers,
      [TYPES]: ["cost_types", "cost_types", "cost_types_with_inactive"],
    };
    await costsAt();
    expect(queriesOf(TYPES)).toEqual([{}, WHOLE, { include_inactive: "true", ...WHOLE }]);
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

  it("are the natures offered when the address asks for the deactivated ones already, read once", async () => {
    server.answers = { ...server.answers, [TYPES]: "cost_types_with_inactive" };
    await costsAt({ include_inactive: "true" });
    expect(queriesOf(TYPES)).toEqual([
      { include_inactive: "true" },
      { include_inactive: "true", ...WHOLE },
    ]);
    const { every, natures } = handed();
    expect(every).toEqual(natures);
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

  it("are the natures offered for a session that writes without reading the deactivated ones, which the contract would refuse it, and the page keeps its commands", async () => {
    withdrawn.permissions = ["cost_settings.read"];
    const page = await costsAt();
    expect(queriesOf(TYPES)).toEqual([{}, WHOLE]);
    expect(handed().every).toEqual(handed().natures);
    expect(page).toContain("Nouvelle catégorie");
    expect(page).toContain("Modifier « Sous-traitance »");
  });
});

describe("the name of the company beside the currency", () => {
  it("is read with the command that modifies it by a session that holds cost_settings.write", async () => {
    const page = await costsAt();
    expect(page).toContain("Delmas Automatismes");
    expect(page).toContain("Modifier le nom de l’entreprise");
  });

  it("is read without any command to modify it by a session that does not hold cost_settings.write", async () => {
    server.answers = {
      ...server.answers,
      "GET /me": "me_estimator",
      [TYPES]: "cost_types_reader",
    };
    const page = await costsAt();
    expect(page).toContain("Delmas Automatismes");
    expect(page).not.toContain("Modifier le nom de l’entreprise");
  });
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
});
