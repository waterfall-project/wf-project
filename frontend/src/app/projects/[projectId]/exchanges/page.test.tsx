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
  usePathname: () => `/projects/${PROJECT}/exchanges`,
  useSearchParams: () => new URLSearchParams(),
}));
// The tracker of the shell, which a screen hands its tasks over to, is above the page.
vi.mock("@/components/tasks/task-tracker", () => ({ useTrackTask: () => () => undefined }));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
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

/** Render the screen of the exchanges in a language, at the query given. */
async function exchangesAt(search: PageSearchParams = {}, locale: Locale = "en") {
  const page = await ExchangesPage({
    params: Promise.resolve({ projectId: PROJECT }),
    searchParams: Promise.resolve(search),
  });
  return renderToStaticMarkup(
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]}>
      {page as ReactNode}
    </NextIntlClientProvider>,
  );
}

/** The calls the page made, by route and path. */
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

describe("the screen of the exchanges", () => {
  it("titles the tab with the exchanges and the project", async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ projectId: PROJECT }),
      searchParams: Promise.resolve({}),
    });
    expect(metadata.title).toBe("File exchanges · Modernisation du poste de commande — Waterfall");
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
    // The current revision says which imports into it are offered.
    expect(calls(GET_REVISION)).toEqual([`/projects/${PROJECT}/revisions/${REVISION}?`]);
    expect(calls(IMPORTS)).toEqual([`/projects/${PROJECT}/imports?limit=20`]);
    expect(text(page)).toContain(
      "Imports of the project File Kind Status Opened on devis-poste-de-commande.xlsx Estimate Analysed",
    );
    expect(page).toContain(`href="/projects/${PROJECT}/exchanges?import=${IMPORT}"`);
    expect(text(page)).toContain("planning-poste-de-commande.xml MS Project schedule Abandoned");
  });

  it("shows the report of the import the address names, its context kept, the import marked in the list", async () => {
    const page = await exchangesAt({ revision_id: REVISION, import: IMPORT });
    expect(calls(GET_IMPORT)).toEqual([`/projects/${PROJECT}/imports/${IMPORT}?`]);
    // The revision the screen reads in is the current one: it is not read twice.
    expect(calls(GET_REVISION)).toHaveLength(1);
    expect(page).toContain(
      '<section aria-label="Report of the import “devis-poste-de-commande.xlsx”"',
    );
    expect(text(page)).toContain("24 lines read.");
    expect(text(page)).toContain(
      "2 lines rejected Line Reason 7 Unknown task. 12 Unknown resource role.",
    );
    expect(text(page)).toContain(
      "3 differences with the existing data Change Object Label Added Estimate line Essais de continuité Updated Estimate line Raccordement des borniers Removed Estimate line Borniers",
    );
    expect(buttons(page).slice(0, 2)).toEqual(["Apply the import", "Abandon the import"]);
    const current = [...page.matchAll(/<a aria-current="page"[^>]*href="([^"]*)"/g)];
    expect(current.map((match) => match[1])).toEqual([
      `/projects/${PROJECT}/exchanges?revision_id=${REVISION}&amp;import=${IMPORT}`,
    ]);
  });

  it("renders the report from its codes in the language of its reader, whoever made the import [WF-ARC-0110-A]", async () => {
    const french = text(await exchangesAt({ import: IMPORT }, "fr"));
    const english = text(await exchangesAt({ import: IMPORT }, "en"));
    expect(french).toContain(
      "2 lignes rejetées Ligne Motif 7 Tâche inconnue. 12 Rôle de ressource inconnu.",
    );
    expect(english).toContain(
      "2 lines rejected Line Reason 7 Unknown task. 12 Unknown resource role.",
    );
  });

  it("names the reasons a report asks an explicit confirmation for", async () => {
    server.answers = {
      ...server.answers,
      [GET_IMPORT]: { example: "import_planning_mismatch", status: 200 },
    };
    const page = text(await exchangesAt({ import: IMPORT }));
    expect(page).toContain(
      "Explicit confirmation required Dates or durations differ from those Waterfall recalculates",
    );
    expect(page).toContain("No line rejected");
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

  it("offers no import into a revision to a project without a current revision, and reads none", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": { example: "project_pricing", status: 200 },
      [IMPORTS]: { example: "imports_empty", status: 200 },
    };
    const page = await exchangesAt();
    expect(buttons(page)).toEqual(["Import actual costs", "Request the export"]);
    expect(calls(GET_REVISION)).toEqual([]);
    expect(text(page)).toContain("No import has been opened on this project yet.");
  });

  it("is not found when the import the address names is not", async () => {
    server.answers = {
      ...server.answers,
      [GET_IMPORT]: { problem: { code: "NOT_FOUND", status: 404 } },
    };
    await expect(exchangesAt({ import: IMPORT })).rejects.toThrow("NEXT_HTTP_ERROR_FALLBACK;404");
  });
});
