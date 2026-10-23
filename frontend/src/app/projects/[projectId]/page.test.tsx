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

  /**
   * The page of the witness project, whose revision in progress (102) the list of its revisions
   * carries whole. No example of the contract lists a revision in progress that offers the skeleton
   * for a project that has it in progress: the encart shown is tested on the components, against
   * `revision_without_tasks` (project-start.dom.test.tsx), and the fake back serves the witness.
   */
  async function withRevisions(list: "revisions" | "revisions_designation_open") {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project",
      "GET /projects/{project_id}/revisions": list,
    };
    return projectAt();
  }

  it("is no longer shown once the main structure bears a task: the list names main_structure_without_tasks as missing, and no revision is read besides it [WF-PRJ-0030-A]", async () => {
    const page = await withRevisions("revisions");
    expect(page).not.toContain('aria-label="Start the project"');
    expect(routes()).not.toContain(REVISION_READ);
  });

  it("is not shown when the revision in progress is not among the revisions listed, and reads no revision either", async () => {
    const page = await withRevisions("revisions_designation_open");
    expect(page).not.toContain('aria-label="Start the project"');
    expect(routes()).not.toContain(REVISION_READ);
  });

  it("is shown from the creation on a project without a revision, as the project lists the skeleton, and reads no revision [WF-PRJ-0030-A]", async () => {
    const page = await projectAt();
    expect(page).toContain('aria-label="Start the project"');
    expect(text(page)).toContain("Automatic planning from the work breakdown");
    expect(routes()).not.toContain(REVISION_READ);
  });

  it("is not shown on a project without a revision whose skeleton the project lists unavailable, the last marked revision bearing tasks [WF-PRJ-0030-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_without_current_revision",
    };
    const page = await projectAt();
    expect(page).not.toContain('aria-label="Start the project"');
  });

  it("is not shown to an estimator, whom the project does not list the skeleton to [WF-PRJ-0030-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_pricing_estimator",
    };
    const page = await projectAt();
    expect(page).not.toContain('aria-label="Start the project"');
  });
});
