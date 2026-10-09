// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { PageSearchParams } from "@/navigation/context";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";

import AuditLogPage, { generateMetadata } from "./page";

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
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/admin/audit-log",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "fr-FR" })),
}));

const EVENTS = "GET /audit-events";
const FACETS = "GET /audit-events/facets";
const NEWEST = { sort_by: "occurred_at", sort_order: "desc" };
const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const CAMILLE = "01926f3a-7c00-7000-8000-000000000301";
const GRID = "Journal d’audit";

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/&#x27;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

/** Render the page in French. */
function rendered(page: unknown): string {
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="fr" messages={CATALOGUES.fr} timeZone="UTC">
      {page as ReactNode}
    </NextIntlClientProvider>,
  );
}

/** The page of the journal, as an address asks it. */
async function journal(search: PageSearchParams = {}): Promise<string> {
  return rendered(await AuditLogPage({ searchParams: Promise.resolve(search) }));
}

/** The queries of the calls the page made to an operation. */
function queriesOf(route: string) {
  return server.clients
    .flatMap((client) => client.calls)
    .filter((call) => call.route === route)
    .map((call) => Object.fromEntries(call.query));
}

/** The grid of the page, by its name. */
function gridOf(markup: string): string {
  const found = [...markup.matchAll(/<table[^>]*aria-label="([^"]*)"[^>]*>(.*?)<\/table>/g)].find(
    (match) => match[1] === GRID,
  );
  expect(found).toBeDefined();
  return found?.[2] ?? "";
}

/** The texts of the rows of the grid. */
function rows(markup: string): string[] {
  return [...gridOf(markup).matchAll(/<tr[^>]*>(.*?)<\/tr>/g)].map((row) => text(row[1] ?? ""));
}

/** The headers of the grid that sort, and how: those whose header holds a button. */
function sorted(markup: string): string[] {
  const head = /<thead[^>]*>(.*?)<\/thead>/.exec(gridOf(markup))?.[1] ?? "";
  return [...head.matchAll(/<th([^>]*)>(.*?)<\/th>/g)]
    .filter((header) => (header[2] ?? "").includes("<button"))
    .map(
      (header) =>
        `${text(header[2] ?? "")} ${/aria-sort="([^"]*)"/.exec(header[1] ?? "")?.[1] ?? ""}`,
    );
}

/** The addresses the links of the grid lead to, and what they say. */
function gridLinks(markup: string): string[] {
  return [...gridOf(markup).matchAll(/<a [^>]*href="([^"]*)"[^>]*>(.*?)<\/a>/g)].map(
    (match) => `${text(match[2] ?? "") || "∅"} → ${(match[1] ?? "").replace(/&amp;/g, "&")}`,
  );
}

beforeEach(() => {
  server.clients = [];
  server.answers = {
    "GET /me": "me",
    [EVENTS]: "audit_events",
    [FACETS]: "audit_facets",
    "GET /projects": "projects",
  };
});

describe("the journal of audit", () => {
  it("titles the tab with the function", async () => {
    expect((await generateMetadata()).title).toBe("Journal d’audit — Waterfall");
  });

  it("presents each inscription with its author, its action, its object and its project as it keeps them, and how many the server retained", async () => {
    const page = await journal();
    const shown = rows(page);
    expect(shown[0]).toBe("Date Auteur Action Nature de l’objet Objet Projet Corrélation");
    expect(shown[1]).toBe(
      "Camille Martin Application d’un import Import couts-reels-2026-05.xlsx PRJ-001 · Modernisation du poste de commande 01926f3a-7c00-7000-8000-000800000034",
    );
    // A backup of the platform: no label, named by its nature, never by its identifier; no project.
    expect(shown[2]).toBe(
      "La plateforme Sauvegarde Sauvegarde Sauvegarde Hors projet 01926f3a-7c00-7000-8000-000800000033",
    );
    expect(shown.at(-1)).toBe("36 inscriptions");
    expect(text(page)).toContain("Journal d’audit 36 inscriptions");
    // Each date, an instant the browser writes in its local time; the history, an icon named.
    expect(page).toContain('<time dateTime="2026-06-03T08:30:00Z">');
    expect(page).toContain('aria-label="Histoire de l’objet"');
  });

  it("asks the newest inscriptions first, and the other direction when the address asks it [WF-IHM-0060-A]", async () => {
    expect(sorted(await journal())).toContain("Date descending");
    expect(queriesOf(EVENTS)).toEqual([NEWEST]);
    server.clients = [];
    expect(sorted(await journal({ sort_by: "occurred_at", sort_order: "asc" }))).toContain(
      "Date ascending",
    );
    expect(queriesOf(EVENTS)).toEqual([{ sort_by: "occurred_at", sort_order: "asc" }]);
  });

  it("asks the server for the column of the contract the address sorts by, each both ways [WF-IHM-0060-A]", async () => {
    server.answers = { ...server.answers, [EVENTS]: "audit_events_by_actor" };
    const page = await journal({ sort_by: "actor", sort_order: "asc" });
    // Every column the contract sorts offers its sort, the one asked said sorted.
    expect(sorted(page).map((header) => header.trim())).toEqual([
      "Date",
      "Auteur ascending",
      "Action",
      "Nature de l’objet",
      "Objet",
      "Projet",
      "Corrélation",
    ]);
    expect(queriesOf(EVENTS)).toEqual([{ sort_by: "actor", sort_order: "asc" }]);
    server.clients = [];
    await journal({ sort_by: "project", sort_order: "desc" });
    await journal({ sort_by: "object_kind" });
    await journal({ sort_by: "correlation_id", sort_order: "desc" });
    expect(queriesOf(EVENTS)).toEqual([
      { sort_by: "project", sort_order: "desc" },
      { sort_by: "object_kind", sort_order: "asc" },
      { sort_by: "correlation_id", sort_order: "desc" },
    ]);
  });

  it("asks the server for the journal sorted by the label of the object, and shows it in the order it answers [WF-IHM-0060-A]", async () => {
    server.answers = { ...server.answers, [EVENTS]: "audit_events_by_object_label" };
    const page = await journal({ sort_by: "object_label", sort_order: "asc" });
    expect(sorted(page)).toContain("Objet ascending");
    expect(queriesOf(EVENTS)).toEqual([{ sort_by: "object_label", sort_order: "asc" }]);
    // The rows as the server ordered them: the backups, which have no label, last.
    const labels = rows(page).slice(1, -1);
    expect(labels.at(-1)).toContain("Sauvegarde Sauvegarde Sauvegarde");
    expect(
      labels.findIndex((row) => row.includes("Retard de livraison des armoires")),
    ).toBeLessThan(labels.findIndex((row) => row.includes(" Référence ")));
  });

  it("reads the hidden columns and the sort the account keeps for the grid, the address saying nothing of the sort", async () => {
    // An auditor contributes to no project: none he may open.
    server.answers = {
      ...server.answers,
      "GET /me": "me_auditor",
      "GET /projects": "projects_empty",
    };
    const page = await journal();
    expect(sorted(page)[0]).toBe("Date ascending");
    expect(queriesOf(EVENTS)).toEqual([{ sort_by: "occurred_at", sort_order: "asc" }]);
    expect(rows(page)[0]).toBe("Date Auteur Action Nature de l’objet Objet Projet");
    // The address is the truth: a sort it asks wins over the one kept.
    server.clients = [];
    await journal({ sort_by: "occurred_at", sort_order: "desc" });
    expect(queriesOf(EVENTS)).toEqual([NEWEST]);
  });

  it("offers an auditor who may not read the accounts nor open any project the authors and the projects of the whole journal to filter by", async () => {
    // An auditor contributes to no project: none he may open; the consultation of the journal
    // alone reads its facets.
    server.answers = {
      ...server.answers,
      "GET /me": "me_auditor",
      "GET /projects": "projects_empty",
    };
    const page = await journal();
    expect(rows(page).at(-1)).toBe("36 inscriptions");
    expect(queriesOf(FACETS)).toEqual([{}]);
    expect(queriesOf("GET /users")).toEqual([]);
    expect(text(page)).toContain("Auteur Tous les comptes Camille Martin");
    expect(text(page)).toContain(
      "Projet Tous les projets PRJ-001 · Modernisation du poste de commande",
    );
  });

  it("asks the server for the filters and the page the address names, under the names of the contract", async () => {
    await journal({
      from: "2026-05-01T00:00:00.000Z",
      to: "2026-06-01T00:00:00Z",
      user_id: CAMILLE,
      actor_kind: "user",
      actions: "backup,import_apply,nothing",
      project_id: PROJECT,
      object_kind: "import",
      object_id: "01926f3a-7c00-7000-8000-000000000a14",
      correlation_id: "01926f3a-7c00-7000-8000-000800000034",
      search: "couts",
      sort_by: "action",
      sort_order: "desc",
      offset: "50",
    });
    expect(queriesOf(EVENTS)).toEqual([
      {
        offset: "50",
        search: "couts",
        from: "2026-05-01T00:00:00.000Z",
        to: "2026-06-01T00:00:00Z",
        user_id: CAMILLE,
        actor_kind: "user",
        actions: "import_apply,backup",
        project_id: PROJECT,
        object_kind: "import",
        object_id: "01926f3a-7c00-7000-8000-000000000a14",
        correlation_id: "01926f3a-7c00-7000-8000-000800000034",
        sort_by: "action",
        sort_order: "desc",
      },
    ]);
  });

  it("asks nothing of an address whose values no server could take, and both kinds of author as none", async () => {
    await journal({
      from: "yesterday",
      to: "2026-13-45T25:00Z",
      user_id: "camille",
      actor_kind: "user,platform",
      actions: "erase",
      project_id: "a.b",
      object_kind: "planet",
      object_id: "-",
      correlation_id: "a request",
      sort_by: "label",
      offset: "-3",
    });
    expect(queriesOf(EVENTS)).toEqual([NEWEST]);
  });

  it("offers the authors and the projects the whole journal names, and reads the projects the session may open in every state for its links", async () => {
    const page = text(await journal());
    expect(page).toContain("Auteur Tous les comptes Camille Martin Toutes les actions");
    expect(page).toContain("Projet Tous les projets PRJ-001 · Modernisation du poste de commande");
    expect(queriesOf(FACETS)).toEqual([{}]);
    expect(queriesOf("GET /users")).toEqual([]);
    expect(queriesOf("GET /projects")).toEqual([
      {
        limit: "500",
        offset: "0",
        states: "created,pricing,in_progress,completed,lost,abandoned",
        sort_by: "code",
      },
    ]);
  });

  it("names the object and the project with a link where the session may open the project, its revision and the revision an object lives in too", async () => {
    const links = gridLinks(await journal());
    expect(links).toContain(`PRJ-001 · Modernisation du poste de commande → /projects/${PROJECT}`);
    expect(links).toContain(
      `Référence → /projects/${PROJECT}/revisions/01926f3a-7c00-7000-8000-000000000101`,
    );
    expect(links).toContain(
      `Retard de livraison des armoires → /projects/${PROJECT}/revisions/01926f3a-7c00-7000-8000-000000000102/risks?risk=01926f3a-7c00-7000-8000-000000000752`,
    );
    // An import of actual costs, a backup, an account live in no revision: their names alone.
    expect(links.filter((link) => link.startsWith("couts-reels"))).toEqual([]);
  });

  it("names the project and its objects without a link where the session may not open the project", async () => {
    server.answers = { ...server.answers, "GET /projects": "projects_empty" };
    const page = await journal();
    // Only the links of the journal itself remain: the correlations.
    expect(
      gridLinks(page).filter((link) => !link.startsWith("∅") && !link.includes("correlation_id=")),
    ).toEqual([]);
    expect(text(gridOf(page))).toContain("PRJ-001 · Modernisation du poste de commande");
  });

  it("reads the journal of a project after its exit from the lifecycle as before it [WF-SEC-0030-A]", async () => {
    server.answers = { ...server.answers, [EVENTS]: "audit_events_exited" };
    const page = await journal({ project_id: PROJECT });
    expect(rows(page)[1]).toContain(
      "Camille Martin Sortie du cycle de vie Projet Modernisation du poste de commande",
    );
    expect(rows(page).at(-1)).toBe("13 inscriptions");
    expect(queriesOf(EVENTS)).toEqual([{ project_id: PROJECT, ...NEWEST }]);
  });

  it("offers no command: nothing modifies nor deletes an inscription [WF-SEC-0030-A]", async () => {
    const page = text(await journal());
    for (const command of ["Modifier", "Supprimer", "Créer", "Effacer"]) {
      expect(page).not.toContain(command);
    }
  });

  it("is not found by a session that may not consult the journal, as an address that leads nowhere [WF-ADM-0110-A]", async () => {
    server.answers = { ...server.answers, "GET /me": "me_estimator" };
    await expect(journal()).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
    // The session alone is read: nothing of the journal, its facets or the projects.
    expect(server.clients.flatMap((client) => client.calls).map((call) => call.route)).toEqual([
      "GET /me",
    ]);
  });

  it("is not found when the API does not find the journal", async () => {
    server.answers = {
      ...server.answers,
      [EVENTS]: { problem: { code: "NOT_FOUND", status: 404 } },
    };
    await expect(journal()).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
  });

  it("says a period the API refuses in place of the inscriptions, and at the field of its end, the filters kept to be changed", async () => {
    server.answers = {
      ...server.answers,
      [EVENTS]: {
        problem: example("audit_events_period_inverted") as Problem & { status: 422 },
      },
    };
    const page = await journal({ from: "2026-06-03T14:00:00Z", to: "2026-06-01T00:00:00Z" });
    expect(text(page)).toContain("La période finit avant de commencer");
    expect(page).not.toContain("<table");
    expect(page).toContain('aria-label="Filtres du journal"');
    // The end refused, said at its field; the start the API names is said in the local time once
    // hydrated, which only the browser knows (`audit.dom.test.tsx`).
    const fields = page.match(/<input[^>]*type="datetime-local"[^>]*>/g) ?? [];
    expect(fields.map((field) => field.includes('aria-invalid="true"'))).toEqual([false, true]);
    expect(text(page)).toContain("La fin de la période ne peut précéder son début.");
  });

  it("says another refusal of the filters by its envelope, never as a period inverted", async () => {
    server.answers = {
      ...server.answers,
      [EVENTS]: {
        problem: {
          code: "VALIDATION_FAILED",
          status: 422,
          fields: [{ pointer: "/query/object_id", code: "VALUE_OUT_OF_RANGE" }],
        },
      },
    };
    const page = text(await journal({ object_id: "01926f3a-7c00-7000-8000-000000000a14" }));
    expect(page).not.toContain("La période finit avant de commencer");
    expect(page).toContain(CATALOGUES.fr.errors.VALIDATION_FAILED);
  });

  it("asks no instant whose fields are out of their bounds", async () => {
    await journal({
      from: "2026-02-30T08:00:00Z",
      to: "2026-05-01T24:00:00Z",
    });
    await journal({ from: "2026-13-01T08:00:00Z", to: "2026-05-01T08:60:00+01:00" });
    await journal({ from: "2028-02-29T23:59:59.5+02:00", to: "2026-05-01T08:00:00Z" });
    expect(queriesOf(EVENTS)).toEqual([
      NEWEST,
      NEWEST,
      { from: "2028-02-29T23:59:59.5+02:00", to: "2026-05-01T08:00:00Z", ...NEWEST },
    ]);
  });

  it("says the journal holds nothing only when nothing narrows it", async () => {
    server.answers = { ...server.answers, [EVENTS]: "audit_events_empty" };
    expect(text(await journal())).toContain("Le journal ne tient aucune inscription.");
    for (const narrowing of [
      { actions: "restore" },
      { search: "avenant 9" },
      { correlation_id: "r-1" },
    ]) {
      const narrowed = await journal(narrowing);
      expect(text(narrowed)).not.toContain("Le journal ne tient aucune inscription.");
      expect(rows(narrowed).at(-1)).toBe("Aucune inscription");
    }
  });

  it("offers a project the address asks that the session may not open, and names an object by what the inscriptions say", async () => {
    server.answers = { ...server.answers, "GET /projects": "projects_empty" };
    const page = await journal({
      project_id: PROJECT,
      object_id: "01926f3a-7c00-7000-8000-000000000a14",
    });
    expect(page).toContain(
      `<option value="${PROJECT}" selected="">PRJ-001 · Modernisation du poste de commande</option>`,
    );
    expect(text(page)).toContain("Objet : couts-reels-2026-05.xlsx Lever");
  });

  it("names a backup whose history the address asks by its nature, never by its identifier", async () => {
    const backup = "01926f3a-7c00-7000-8000-000000000907";
    const page = text(await journal({ object_kind: "backup", object_id: backup }));
    expect(page).toContain("Objet : Sauvegarde Lever");
    expect(page).not.toContain(`Objet : ${backup}`);
  });
});
