// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { PageSearchParams } from "@/navigation/context";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import ResourceSettingsPage from "./page";

// What the page of the resources reads to offer the creation of a role (EP-14/L43g): the categories,
// each saying the type of its nature, and never the natures.
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
// witness modifies the settings of the resources without reading those of the costs.
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
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/reference/resources",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "fr-FR" })),
}));

/** A list read whole as a list of choices is: every page, by the largest the contract takes. */
const WHOLE = { limit: "500", offset: "0" };

/** Render the settings of the resources at the query given, in French. */
async function resourcesAt(search: PageSearchParams = {}): Promise<string> {
  const page = await ResourceSettingsPage({ searchParams: Promise.resolve(search) });
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
    .map((call) => Object.fromEntries(call.query));
}

beforeEach(() => {
  server.clients = [];
  withdrawn.permissions = [];
  server.answers = {
    "GET /session": "session",
    "GET /reference/org-nodes": "org_nodes",
    "GET /reference/resource-roles": "resource_roles",
    "GET /reference/calendars": "calendars",
    "GET /reference/duration-units": "duration_units",
    "GET /reference/cost-categories": "volume/cost_categories",
  };
});

describe("the creation of a role", () => {
  it("is offered to a session that modifies the resources without reading the settings of the costs, from the active categories alone, the natures unread", async () => {
    withdrawn.permissions = ["cost_settings.read", "cost_settings.write"];
    const page = await resourcesAt({ include_inactive: "true" });
    expect(page).toContain("Nouveau rôle");
    // The deactivated categories, which the contract would refuse it (403), are not asked.
    expect(queriesOf("GET /reference/cost-categories")).toEqual([WHOLE]);
    expect(queriesOf("GET /reference/cost-types")).toEqual([]);
  });
});
