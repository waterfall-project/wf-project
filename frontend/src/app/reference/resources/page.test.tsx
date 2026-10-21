// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import { DAYS } from "@/components/reference/resource-grids";
import {
  CalendarList,
  type DayBounds,
  OrgNodeList,
  ResourceRoleList,
} from "@/components/reference/resource-lists";
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

import ResourceSettingsPage from "./page";

type ResourceRole = components["schemas"]["ResourceRole"];

// The settings of the resources, rendered as the server renders them (EP-02, EP-14/L43g, EP-14/L54):
// what the page asks of each list and shows of it — the categories each saying the type of its
// nature, and never the natures; the code of the roles it filters on; every role, which names those
// a refusal gives by their identifiers alone.
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

/** Every role, deactivated ones too, which a session that writes them reads (EP-14/L54). */
const EVERY_ROLE = { include_inactive: "true", ...WHOLE };

/** The node of the electrical design office, in the tree of the witness. */
const BUREAU = "01926f3a-7c00-7000-8000-000000000471";
/** The electrical engineering category and the standard week of the witness. */
const ELECTRICAL = "01926f3a-7c00-7000-8000-000000000402";
const STANDARD = "01926f3a-7c00-7000-8000-000000000481";

const NO_QUERY = { sort: undefined, search: undefined, size: undefined };

/** No bound on either side of a column. */
const NO_BOUNDS = { min: undefined, max: undefined };

/** No bound on the hours of any day. */
const NO_HOURS = Object.fromEntries(DAYS.map((day) => [day, NO_BOUNDS])) as DayBounds;

/** The roles of the witness, as the server pages them. */
const ROLE_PAGE = example("resource_roles") as { items: ResourceRole[]; meta: ListPage };

/** The three lists of the settings of the resources. */
const LISTS = [
  "GET /reference/org-nodes",
  "GET /reference/resource-roles",
  "GET /reference/calendars",
] as const;

/** Render a part of the screen, or the screen, in French. */
function rendered(page: unknown): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      {page as ReactNode}
    </NextIntlClientProvider>,
  );
}

/** Render the settings of the resources at the query given, in French. */
async function resourcesAt(search: PageSearchParams = {}): Promise<string> {
  return rendered(await ResourceSettingsPage({ searchParams: Promise.resolve(search) }));
}

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/&#x27;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
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

/** The texts of the rows of a table of a page, by its name. */
function rows(markup: string, table: string): string[] {
  const found = [...markup.matchAll(/<table[^>]*aria-label="([^"]*)"[^>]*>(.*?)<\/table>/g)].find(
    (match) => match[1] === table,
  );
  expect(found).toBeDefined();
  return [...(found?.[2] ?? "").matchAll(/<tr[^>]*>(.*?)<\/tr>/g)].map((row) => text(row[1] ?? ""));
}

/** The queries the page asked of a route of the fake back. */
function queriesOf(route: string): Record<string, string>[] {
  return server.clients
    .flatMap((client) => client.calls)
    .filter((call) => call.route === route)
    .map((call) => queryOfCall(call.query));
}

beforeEach(() => {
  server.clients = [];
  withdrawn.permissions = [];
  server.answers = {
    "GET /me": "me",
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

describe("the roles", () => {
  it("are asked of the server filtered on the code the address names, under the name of their grid", async () => {
    const page = await resourcesAt({ role_code: "AUT" });
    expect(queriesOf("GET /reference/resource-roles")[0]).toEqual({ code: "AUT" });
    // The filter shows the code asked, to be changed.
    expect(page).toMatch(/<form aria-label="Code du rôle".*?<input[^>]*value="AUT"/);
  });

  it("are read every one, the deactivated ones too, for a session that modifies them, and for none other", async () => {
    // What names the roles a refusal of a calendar gives by their identifiers alone (WF-PLA-0010).
    await resourcesAt();
    expect(queriesOf("GET /reference/resource-roles")).toEqual([
      {},
      { include_inactive: "true", ...WHOLE },
    ]);
    server.clients = [];
    withdrawn.permissions = ["resource_settings.write"];
    await resourcesAt();
    expect(queriesOf("GET /reference/resource-roles")).toEqual([{}]);
  });

  it("are shown all the same when the API refuses to read every one, their names done without", async () => {
    server.answers = {
      ...server.answers,
      "GET /reference/resource-roles": [
        "resource_roles",
        { problem: { code: "NOT_FOUND", status: 404 } },
      ],
    };
    const page = await resourcesAt();
    expect(queriesOf("GET /reference/resource-roles")).toEqual([{}, EVERY_ROLE]);
    expect(rows(page, "Rôles de ressources").at(-1)).toBe("5 rôles");
  });
});

describe("the settings of the resources", () => {
  it("offer the commands of the nodes, the roles and the calendars, none that deletes, to a session that may modify the settings of the resources, and say the fake back keeps nothing; none to a session that may only read them [WF-IHM-0090-A] [WF-REF-0010-A]", async () => {
    const page = text(await resourcesAt());
    expect(page).toMatch(/Maquette.*Nouveau nœud.*Nouveau rôle.*Nouveau calendrier.*Désigner/);
    expect(page).not.toMatch(/Supprimer|Effacer/);
    // The natures are not read: a category says if it is of labour (`cost_type_kind`).
    expect(queriesOf("GET /reference/cost-types")).toEqual([]);
    server.clients = [];
    server.answers = {
      ...server.answers,
      "GET /me": "me_estimator",
      "GET /reference/org-nodes": "org_nodes_reader",
      "GET /reference/resource-roles": "resource_roles_reader",
      "GET /reference/calendars": "calendars_reader",
    };
    expect(await resourcesAt()).not.toMatch(/Nouveau|Modifier|Désactiver|Désigner|Maquette/);
    expect(queriesOf("GET /reference/cost-types")).toEqual([]);
  });

  it("present the organisation as a tree grid in the order the server gives, each node by its label set in by its depth, its code and its depth, filtered by code, depth and state", async () => {
    const page = await resourcesAt();
    expect(rows(page, "Arbre d’organisation")).toEqual([
      "Libellé Code Niveau État Modifier",
      "Direction technique DT 1 Actif Désactiver Modifier",
      "Bureau d'études électricité BE-ELEC 2 Actif Désactiver Modifier",
      "Atelier de câblage AT-CABL 3 Actif Désactiver Modifier",
      "Service des achats ACHATS 2 Actif Désactiver Modifier",
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

  it("present each role with its code, its node, its category, its calendar and its capacity, named as the server resolves them, on a grid sorted by each of its columns, filtered by each and bounded on its figures [WF-IHM-0060-A]", async () => {
    const page = await resourcesAt({ include_inactive: "true" });
    expect(rows(page, "Rôles de ressources")).toEqual([
      "Libellé Code Nœud d’organisation Catégorie de coût Calendrier Heures par mois Effectif État Modifier",
      "Automaticien AUTOM Bureau d'études électricité Ingénierie électrique Semaine de trente-neuf heures 338,00 2 Désactivé Réactiver Modifier",
      "Ingénieur électricien ING-ELEC Bureau d'études électricité Ingénierie électrique Semaine standard 658 654,00 3 800 Actif Désactiver Modifier",
      "Monteur câbleur MONT-CAB Atelier de câblage Ingénierie électrique Semaine de quatre jours 216 662,50 1 250 Actif Désactiver Modifier",
      "Programmeur d'automates PROG-AUTO Bureau d'études automatismes Ingénierie électrique Semaine standard 519,99 3 Désactivé Réactiver Condition non remplie : nœud d’organisation actif. Modifier",
      "Technicien de mise en service TECH-MES Bureau d'études électricité Mise en service Semaine standard 485 324,00 2 800 Actif Désactiver Modifier",
      "5 rôles",
    ]);
    // The calendar of the deactivated role is not among those the page read: its name is the
    // answer's, never one the front would draw from another list.
    expect(rows(page, "Calendriers").join(" ")).not.toContain("trente-neuf");
    expect(sortable(page, "Rôles de ressources")).toEqual([
      "Libellé",
      "Code",
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
      "Libellé Lun. Mar. Mer. Jeu. Ven. Sam. Dim. Par défaut État Modifier",
      "Semaine de quatre jours 10 10 10 10 0 0 0 Désigner Actif Désactiver Modifier",
      "Semaine standard 8 8 8 8 8 0 0 Calendrier par défaut Actif Désactiver Condition non remplie : calendrier autre que celui par défaut. Modifier",
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
      EVERY_ROLE,
    ]);
    expect(queriesOf("GET /reference/calendars")).toEqual([
      {
        search: "Semaine",
        sort_by: "wednesday",
        sort_order: "asc",
        is_active: "true",
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
      "Libellé Code Niveau État Modifier",
      "Direction technique DT 1 Actif Désactiver Modifier",
      "Bureau d'études automatismes BE-AUTO 2 Désactivé Réactiver Modifier",
      "Cellule robotique CEL-ROBOT 3 Désactivé Réactiver Condition non remplie : nœud parent actif. Modifier",
      "Bureau d'études électricité BE-ELEC 2 Actif Désactiver Modifier",
      "Atelier de câblage AT-CABL 3 Actif Désactiver Modifier",
      "Service des achats ACHATS 2 Actif Désactiver Modifier",
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
      EVERY_ROLE,
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
      "GET /reference/resource-roles": [
        { problem: example("resource_roles_bounds_inverted") as Problem & { status: 422 } },
        "resource_roles",
      ],
    };
    const page = await resourcesAt({
      role_monthly_hours_min: "1000",
      role_monthly_hours_max: "500",
    });
    expect(queriesOf("GET /reference/resource-roles")).toEqual([
      { monthly_hours_min: "1000", monthly_hours_max: "500" },
      EVERY_ROLE,
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
    expect(queriesOf("GET /reference/resource-roles")).toEqual([{}, EVERY_ROLE]);
    expect(queriesOf("GET /reference/calendars")).toEqual([{}, WHOLE]);
  });

  it("keep the grid of a list a search or a filter narrows to nothing, the search shown to be changed, and say empty a list nothing narrows", () => {
    const query = { sort: undefined, search: "Personne", size: undefined };
    const none = { ...ROLE_PAGE.meta, total: 0 };
    const filters = {
      code: undefined,
      orgNode: undefined,
      category: undefined,
      calendar: undefined,
      state: undefined,
      monthlyHours: NO_BOUNDS,
      headcount: NO_BOUNDS,
    };
    // A list of roles a session that may only read them sees, nothing offered to choose.
    const roles = { rows: [], page: none, preferences: undefined, readsInactive: true } as const;
    const offered = { editable: false, nodes: [], labour: [], calendars: [] } as const;
    const narrowed = rendered(
      <ResourceRoleList {...roles} {...offered} query={query} categories={[]} filters={filters} />,
    );
    expect(rows(narrowed, "Rôles de ressources")).toContain("Aucune ligne ne répond à la demande.");
    expect(narrowed).toContain('value="Personne"');
    const filtered = rendered(
      <ResourceRoleList
        {...roles}
        {...offered}
        query={NO_QUERY}
        categories={undefined}
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
        editable={false}
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
        editable={false}
        filters={{ code: undefined, level: 4, state: undefined, levels: NO_BOUNDS }}
        levels={[]}
        nodes={[]}
      />,
    );
    expect(rows(tree, "Arbre d’organisation")).toContain("Aucune ligne ne répond à la demande.");
  });

  it("ask each list its active objects alone when the address does not ask for the deactivated ones, every role read besides, and offer to show them [WF-REF-0150-A]", async () => {
    const page = await resourcesAt();
    // The roles of the grid without the deactivated ones; every role besides, deactivated ones
    // too, read to name those a refusal gives by their identifiers alone (EP-14/L54).
    expect(queriesOf("GET /reference/resource-roles")[0]).not.toHaveProperty("include_inactive");
    expect(LISTS.flatMap(queriesOf).filter((query) => "include_inactive" in query)).toEqual([
      EVERY_ROLE,
    ]);
    expect(page).toMatch(
      /<a[^>]*href="\/reference\/resources\?include_inactive=true"[^>]*>.*?Afficher aussi les désactivés<\/a>/,
    );
    // The fake back answers its example whatever is asked: what the screen asks is proven.
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
      "GET /me": "me_estimator",
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

describe("the settings of the resources, the size of the pages", () => {
  it.each([
    ["the resource roles", "GET /reference/resource-roles", "role_limit"],
    ["the calendars", "GET /reference/calendars", "calendar_limit"],
  ])(
    "sends the limit of the reading of %s: 50 unasked, the page size asked [WF-IHM-0060-A]",
    async (_name, route, name) => {
      for (const [search, limit] of [
        [{}, "50"],
        [{ [name]: "25" }, "25"],
      ] as const) {
        server.clients = [];
        await resourcesAt(search);
        const [call] = server.clients
          .flatMap((client) => client.calls)
          .filter((each) => each.route === route);
        expect(Object.fromEntries(call?.query ?? []).limit).toBe(limit);
      }
    },
  );
});
