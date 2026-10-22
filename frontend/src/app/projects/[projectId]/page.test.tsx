// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CATALOGUES } from "@/i18n/catalogues";
import type { PageSearchParams } from "@/navigation/context";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import ProjectPage from "./page";

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
  usePathname: () => `/projects/${PRICING}`,
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

// The project in pricing, without a revision (`project_pricing.json`).
const PRICING = "01926f3a-7c00-7000-8000-000000000002";
const IMPORT = "01926f3a-7c00-7000-8000-000000000a11";
const IMPORT_READ = "GET /projects/{project_id}/imports/{import_id}";

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/&#x27;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

/** Render the screen of the project in English, at the query given. */
async function projectAt(search: PageSearchParams = {}) {
  const page = await ProjectPage({
    params: Promise.resolve({ projectId: PRICING }),
    searchParams: Promise.resolve(search),
  });
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
      {page as ReactNode}
    </NextIntlClientProvider>,
  );
}

/** The routes of the calls the page made. */
function routes(): string[] {
  return server.clients.flatMap((client) => client.calls).map((call) => call.route);
}

beforeEach(() => {
  server.clients = [];
  server.answers = {
    "GET /me": "me",
    "GET /projects/{project_id}": "project_pricing",
    "GET /projects/{project_id}/revisions": "revisions_empty",
    [IMPORT_READ]: "import_analysed",
  };
});

describe("the imports on the screen of a project without revision", () => {
  it("offers each import as the project lists it, an import creating the revision it applies to (#332)", async () => {
    const page = await projectAt();
    const imports = /<section aria-label="Import a file"[\s\S]*?<\/section>/.exec(page)?.[0];
    expect(imports).toBeDefined();
    // In pricing, the planning, the estimate and the remaining are offered; the actual costs
    // wait for the project to be in progress, which the command says.
    const commands = text(imports ?? "");
    expect(commands).toContain("Import an MS Project schedule");
    expect(commands).toContain("Import an estimate");
    expect(imports).toMatch(
      /aria-disabled="true"[^>]*>(<svg[^>]*>.*?<\/svg>)?Import actual costs</,
    );
    expect(routes()).not.toContain(IMPORT_READ);
  });

  it("shows the report of the import its address names, above the imports", async () => {
    const page = await projectAt({ import: IMPORT });
    expect(routes()).toContain(IMPORT_READ);
    const report = page.indexOf('aria-label="Report of the import');
    expect(report).toBeGreaterThan(-1);
    expect(report).toBeLessThan(page.indexOf('aria-label="Import a file"'));
  });

  it("offers no import on the screen of a project that has revisions: the screen of the imports does", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project",
      "GET /projects/{project_id}/revisions": "revisions",
      "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    };
    const page = await projectAt();
    expect(page).not.toContain('aria-label="Import a file"');
  });

  it("offers an estimator the import of an estimate unavailable, lacking the permission to create the revision it would create", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_pricing_estimator",
    };
    const page = await projectAt();
    expect(page).toMatch(/aria-disabled="true"[^>]*>(<svg[^>]*>.*?<\/svg>)?Import an estimate</);
    expect(text(page)).toContain(
      "Import an estimate Unmet condition: holding the permission to create a revision.",
    );
    expect(text(page)).not.toContain("Import an MS Project schedule");
  });
});

describe("the encart « Démarrer le projet »", () => {
  const REVISION_READ = "GET /projects/{project_id}/revisions/{revision_id}";

  /** The page of a project that has a revision in progress, which the server reads as given. */
  async function withRevision(revision: "revision" | "revision_without_tasks" | "revision_reader") {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project",
      "GET /projects/{project_id}/revisions": "revisions",
      [REVISION_READ]: revision,
    };
    return projectAt();
  }

  it("is shown while the revision in progress lists the skeleton and its main structure has no task, the choices as the server lists them [WF-PRJ-0030-A]", async () => {
    const page = await withRevision("revision_without_tasks");
    const encart = /<section aria-label="Start the project"[\s\S]*?<\/section>/.exec(page)?.[0];
    expect(encart).toBeDefined();
    expect(text(encart ?? "")).toContain("Automatic planning from the work breakdown");
    expect(text(encart ?? "")).toContain("Import an MS Project file");
    expect(text(encart ?? "")).toContain("Later");
    expect(encart).toContain(`href="/projects/${PRICING}/settings?start=skeleton"`);
    expect(routes()).toContain(REVISION_READ);
  });

  it("is no longer shown once the main structure bears a task: the server names main_structure_without_tasks as missing [WF-PRJ-0030-A]", async () => {
    const page = await withRevision("revision");
    expect(page).not.toContain('aria-label="Start the project"');
  });

  it("is not shown to a session that may not modify the planning: the revision does not list the skeleton", async () => {
    const page = await withRevision("revision_reader");
    expect(page).not.toContain('aria-label="Start the project"');
  });

  it("is not shown on a project without a revision in progress, and reads no revision", async () => {
    const page = await projectAt();
    expect(page).not.toContain('aria-label="Start the project"');
    expect(routes()).not.toContain(REVISION_READ);
  });
});
