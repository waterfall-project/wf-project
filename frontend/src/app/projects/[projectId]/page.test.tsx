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
const MAPPING_READ = "GET /reference/actual-cost-mapping";
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

  it("says on the import of actual costs unavailable the columns without a label, with the way to the correspondence, reading it once [WF-REF-0190-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_actual_cost_mapping_incomplete",
      "GET /reference/actual-cost-mapping": "actual_cost_mapping_empty",
    };
    const page = await projectAt();
    expect(text(page)).toContain("Required columns without a label in the mapping:");
    expect(page).toContain('href="/reference/costs/actual-cost-mapping"');
    expect(routes().filter((route) => route === MAPPING_READ)).toHaveLength(1);
  });

  it("keeps the condition and the way to the correspondence when the correspondence cannot be read [WF-REF-0190-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_actual_cost_mapping_incomplete",
      [MAPPING_READ]: { problem: { code: "NOT_FOUND", status: 404 } },
    };
    const page = await projectAt();
    expect(text(page)).toContain("Unmet condition: actual-cost extraction mapping complete");
    expect(page).toContain('href="/reference/costs/actual-cost-mapping"');
    expect(text(page)).not.toContain("Required columns without a label");
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

/** Where the page leads, from the redirect it throws; `undefined` when it renders. */
async function leadsTo(search: PageSearchParams = {}): Promise<string | undefined> {
  try {
    await projectAt(search);
  } catch (error) {
    const digest = (error as { digest?: unknown }).digest;
    if (typeof digest === "string" && digest.startsWith("NEXT_REDIRECT;")) {
      return digest.split(";")[2];
    }
    throw error;
  }
  return undefined;
}

describe("the screen of a project that has a revision leads to it", () => {
  const WITNESS = `/projects/${PRICING}`;
  const CURRENT = "01926f3a-7c00-7000-8000-000000000102";
  const REFERENCE = "01926f3a-7c00-7000-8000-000000000101";
  const SUBPROJECT = "01926f3a-7c00-7000-8000-000000000301";

  beforeEach(() => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project",
      "GET /projects/{project_id}/revisions": "revisions",
      "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    };
  });

  it("to the revision in progress, the reading context of the address and its filters kept [WF-IHM-0010-A]", async () => {
    expect(await leadsTo()).toBe(`${WITNESS}/revisions/${CURRENT}`);
    expect(await leadsTo({ subproject_id: SUBPROJECT })).toBe(
      `${WITNESS}/revisions/${CURRENT}?subproject_id=${SUBPROJECT}`,
    );
  });

  it("to the reference when the project has none in progress [WF-IHM-0010-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_without_current_revision",
    };
    expect(await leadsTo()).toBe(`${WITNESS}/revisions/${REFERENCE}`);
  });

  it("to the last revision marked when it has neither in progress nor reference [WF-IHM-0010-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_pricing",
      "GET /projects/{project_id}/revisions": "revisions_marked",
    };
    expect(await leadsTo()).toBe(`${WITNESS}/revisions/${REFERENCE}`);
  });

  it("to the revisions when the revision chosen cannot be read by the session [WF-IHM-0010-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": {
        problem: { code: "NOT_FOUND", status: 404 },
      },
    };
    expect(await leadsTo()).toBe(`${WITNESS}/revisions`);
  });

  it("to the revisions when the project has some but none in progress, of reference or marked, the filters of the address kept [WF-IHM-0010-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_pricing",
      "GET /projects/{project_id}/revisions": "revisions_project_created",
    };
    expect(await leadsTo()).toBe(`${WITNESS}/revisions`);
    expect(await leadsTo({ subproject_id: SUBPROJECT })).toBe(
      `${WITNESS}/revisions?subproject_id=${SUBPROJECT}`,
    );
  });

  it("to the revision in progress, not to the one the address names, which the path replaces [WF-IHM-0010-A]", async () => {
    expect(await leadsTo({ revision_id: REFERENCE })).toBe(`${WITNESS}/revisions/${CURRENT}`);
  });

  it("sends the report of an import its address names to the exchanges of the revision, which shows it [WF-IHM-0010-A]", async () => {
    expect(await leadsTo({ import: IMPORT })).toBe(
      `${WITNESS}/revisions/${CURRENT}/exchanges?import=${IMPORT}`,
    );
    expect(await leadsTo({ import: IMPORT, subproject_id: SUBPROJECT })).toBe(
      `${WITNESS}/revisions/${CURRENT}/exchanges?subproject_id=${SUBPROJECT}&import=${IMPORT}`,
    );
  });

  it("keeps the screen, its encart and its imports, of a project without a revision, and no list of revisions [WF-IHM-0010-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_pricing",
      "GET /projects/{project_id}/revisions": "revisions_empty",
    };
    expect(await leadsTo()).toBeUndefined();
    const page = await projectAt();
    expect(page).toContain('aria-label="Start the project"');
    expect(page).toContain('aria-label="Import a file"');
    expect(page).not.toContain('aria-label="Revisions"');
  });
});
