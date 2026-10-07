// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import type { PageSearchParams } from "@/navigation/context";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import ExchangesPage, { generateMetadata } from "./page";

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
  usePathname: () => PATHNAME,
  useSearchParams: () => new URLSearchParams(),
}));
// The tracker of the shell, which a screen hands its tasks over to, is above the page.
vi.mock("@/components/tasks/task-tracker", () => ({ useTrackTask: () => () => undefined }));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const MARKED = "01926f3a-7c00-7000-8000-000000000101";
const PATHNAME = `/projects/${PROJECT}/revisions/${REVISION}/exchanges`;
const IMPORT = "01926f3a-7c00-7000-8000-000000000a11";
const GET_IMPORT = "GET /projects/{project_id}/imports/{import_id}";
const GET_REVISION = "GET /projects/{project_id}/revisions/{revision_id}";
const IMPORTS = "GET /projects/{project_id}/imports";

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/&quot;/g, '"')
    .replace(/&#x27;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

/** The names of the buttons of a page. */
function buttons(markup: string): string[] {
  return [...markup.matchAll(/<button[^>]*>(.*?)<\/button>/g)].map((match) => text(match[1] ?? ""));
}

/** The addresses the links of a page lead to. */
function links(markup: string): string[] {
  return [...markup.matchAll(/<a [^>]*href="([^"]*)"/g)].map((match) => match[1] ?? "");
}

/** Render the screen of the imports and exports in a language, at the query given. */
async function exchangesAt(
  search: PageSearchParams = {},
  locale: Locale = "en",
  revisionId = REVISION,
) {
  const page = await ExchangesPage({
    params: Promise.resolve({ projectId: PROJECT, revisionId }),
    searchParams: Promise.resolve(search),
  });
  return renderToStaticMarkup(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]}>
      {page as ReactNode}
    </NextIntlClientProvider>,
  );
}

/** The calls the page made to a route, by path and query. */
function calls(route: string): string[] {
  return server.clients
    .flatMap((client) => client.calls)
    .filter((call) => call.route === route)
    .map((call) => `${call.path}?${call.query.toString()}`);
}

beforeEach(() => {
  server.clients = [];
  server.answers = {
    "GET /session": "session",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/revisions": "revisions",
    [GET_REVISION]: "revision",
    "GET /projects/{project_id}/subprojects": "subprojects",
    [IMPORTS]: "imports",
    [GET_IMPORT]: "import_analysed",
  };
});

describe("the screen of the imports and exports", () => {
  it("titles the tab with the leaf and the project", async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
    });
    expect(metadata.title).toBe(
      "Imports and exports · Modernisation du poste de commande — Waterfall",
    );
  });

  it("starts with the imports the server offers, the imports of the project and the export, and reads no report", async () => {
    const page = await exchangesAt();
    expect(page.startsWith('<section aria-label="Reading context"')).toBe(true);
    expect(buttons(page)).toEqual([
      "Import an MS Project schedule",
      "Import an estimate",
      "Import an estimate to complete",
      "Import actual costs",
      "Request the export",
    ]);
    expect(calls(GET_IMPORT)).toEqual([]);
    // The revision read says which exports it offers, read once; the project, which imports.
    expect(calls(GET_REVISION)).toEqual([`/projects/${PROJECT}/revisions/${REVISION}?`]);
    expect(calls(IMPORTS)).toEqual([`/projects/${PROJECT}/imports?limit=20`]);
    expect(text(page)).toContain(
      "Imports of the project File Kind Status Opened on devis-poste-de-commande.xlsx Estimate Analysed couts-reels-2026-05.xlsx Actual costs Applied couts-reels-2026-04-correction.xlsx Actual costs Expired",
    );
    expect(links(page)).toContain(`${PATHNAME}?import=${IMPORT}`);
    expect(text(page)).toContain("planning-poste-de-commande.xml MS Project schedule Abandoned");
  });

  it("reads no revision but the one of its route, whose exports it offers, the imports being the project's", async () => {
    server.answers = { ...server.answers, [GET_REVISION]: "revision_marked" };
    const page = await exchangesAt({}, "en", MARKED);
    expect(calls(GET_REVISION)).toEqual([`/projects/${PROJECT}/revisions/${MARKED}?`]);
    expect(buttons(page)).toEqual([
      "Import an MS Project schedule",
      "Import an estimate",
      "Import an estimate to complete",
      "Import actual costs",
      "Request the export",
    ]);
  });

  it("offers a reader who modifies nothing the exports of what it reads", async () => {
    server.answers = { ...server.answers, [GET_REVISION]: "revision_reader" };
    const page = await exchangesAt();
    expect(buttons(page)).toContain("Request the export");
    expect(text(page)).not.toContain("No export is offered to you on this revision.");
  });

  it("shows the report of the import the address names, its context kept, the import marked in the list", async () => {
    const page = await exchangesAt({ import: IMPORT, as_of: "2026-05-31" });
    expect(calls(GET_IMPORT)).toEqual([`/projects/${PROJECT}/imports/${IMPORT}?`]);
    expect(page).toContain(
      '<section aria-label="Report of the import “devis-poste-de-commande.xlsx”"',
    );
    expect(text(page)).toContain("5 lines read.");
    expect(text(page)).toContain(
      "2 lines rejected Line Reason 3 Unknown task. 5 Unknown resource role.",
    );
    expect(text(page)).toContain(
      "3 differences with the existing data Change Object Label Fields Added Estimate line Essais de continuité Updated Estimate line Raccordement des borniers Hours Removed Estimate line Borniers",
    );
    expect(buttons(page).slice(0, 2)).toEqual(["Apply the import", "Abandon the import"]);
    const current = [...page.matchAll(/<a aria-current="page"[^>]*href="([^"]*)"/g)];
    expect(current.map((match) => match[1])).toEqual([
      `${PATHNAME}?as_of=2026-05-31&amp;import=${IMPORT}`,
    ]);
  });

  it("asks nothing of an import the address names by what no identifier can be", async () => {
    const page = await exchangesAt({ import: ".." });
    expect(calls(GET_IMPORT)).toEqual([]);
    expect(page).not.toContain("Report of the import");
  });

  it("renders the report from its codes in the language of its reader, whoever made the import [WF-ARC-0110-A]", async () => {
    const french = text(await exchangesAt({ import: IMPORT }, "fr"));
    const english = text(await exchangesAt({ import: IMPORT }, "en"));
    expect(french).toContain(
      "2 lignes rejetées Ligne Motif 3 Tâche inconnue. 5 Rôle de ressource inconnu.",
    );
    expect(english).toContain(
      "2 lines rejected Line Reason 3 Unknown task. 5 Unknown resource role.",
    );
  });

  it("names the reasons a report asks an explicit confirmation for", async () => {
    server.answers = {
      ...server.answers,
      [GET_IMPORT]: { example: "import_actual_costs_analysed", status: 200 },
    };
    const page = text(await exchangesAt({ import: IMPORT }));
    expect(page).toContain("Explicit confirmation required Unknown subproject");
    expect(page).toContain("No line rejected");
  });

  it("names the fields a difference changes by the columns of its object, in the language of its reader [WF-ARC-0110-A]", async () => {
    const french = text(await exchangesAt({ import: IMPORT }, "fr"));
    expect(french).toContain("Modifié Ligne de devis Raccordement des borniers Charge");
    server.answers = {
      ...server.answers,
      [GET_IMPORT]: { example: "import_actual_costs_analysed", status: 200 },
    };
    // Two lines of actual cost already imported: a credit note whose OTP element changed,
    // charged anew on its sub-project; an invoice whose amount changed in the ERP.
    const english = text(await exchangesAt({ import: IMPORT }));
    expect(english).toContain(
      "2 differences with the existing data Change Object Label Fields Updated Actual cost line AV-2026-0388 Subproject Updated Actual cost line FA-2026-0412 Amount",
    );
    server.answers = {
      ...server.answers,
      [GET_IMPORT]: { example: "import_planning_mismatch", status: 200 },
    };
    // A round trip: a task lengthened in the file, a started task the file no longer holds, kept.
    const planning = text(await exchangesAt({ import: IMPORT }));
    expect(planning).toContain("Updated Task Revue de conception Duration");
    expect(planning).toContain("Kept Task Études de détail");
  });

  it("says the analysis under way, without a report, still abandonable but not applicable", async () => {
    server.answers = {
      ...server.answers,
      [GET_IMPORT]: { example: "import_analysing", status: 200 },
    };
    const page = await exchangesAt({ import: IMPORT });
    expect(text(page)).toContain("The file is being analysed.");
    expect(buttons(page).slice(0, 1)).toEqual(["Abandon the import"]);
  });

  it("asks the page of the imports the address names, and leads to the pages around it", async () => {
    server.answers = { ...server.answers, [IMPORTS]: { example: "imports_page", status: 200 } };
    const page = await exchangesAt({ offset: "2", import: IMPORT });
    expect(calls(IMPORTS)).toEqual([`/projects/${PROJECT}/imports?limit=20&offset=2`]);
    expect(page).toContain('aria-label="Pages of the imports of the project"');
    // The pages turn from the address the browser shows, here without a query.
    expect(links(page)).toEqual(expect.arrayContaining([PATHNAME, `${PATHNAME}?offset=4`]));
    // The imports of the page lead to their report, on the same page of the list.
    expect(links(page)).toContain(
      `${PATHNAME}?offset=2&amp;import=01926f3a-7c00-7000-8000-000000000a10`,
    );
  });

  it("offers the imports of a project without a current revision, which the import creates", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": { example: "project_pricing", status: 200 },
      [IMPORTS]: { example: "imports_empty", status: 200 },
    };
    const page = await exchangesAt();
    expect(buttons(page)).toEqual([
      "Import an MS Project schedule",
      "Import an estimate",
      "Import an estimate to complete",
      "Import actual costs",
      "Request the export",
    ]);
    expect(text(page)).toContain("No import has been opened on this project yet.");
  });

  it("names the permission to create the revision an import would create, when the caller lacks it", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": { example: "project_pricing_estimator", status: 200 },
      [GET_REVISION]: "revision_estimator",
    };
    const page = await exchangesAt();
    expect(buttons(page)).toEqual(["Import an estimate", "Request the export"]);
    expect(text(page)).toContain("holding the permission to create a revision");
    expect(text(page)).toContain("Estimate Estimate to complete");
  });

  it("is not found when the import the address names is not", async () => {
    server.answers = {
      ...server.answers,
      [GET_IMPORT]: { problem: { code: "NOT_FOUND", status: 404 } },
    };
    await expect(exchangesAt({ import: IMPORT })).rejects.toThrow("NEXT_HTTP_ERROR_FALLBACK;404");
  });
});
