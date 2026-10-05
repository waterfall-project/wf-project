// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CostsGridProps } from "@/components/costs/costs-grid";
import { CATALOGUES } from "@/i18n/catalogues";
import type { PageSearchParams } from "@/navigation/context";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";

import ActualCostsPage, { generateMetadata } from "./page";

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
// The grid renders as it would, and keeps what its page handed it.
const grids = vi.hoisted((): { costs: CostsGridProps[] } => ({ costs: [] }));
vi.mock("@/components/costs/costs-grid", async (original) => {
  const actual = await original<typeof import("@/components/costs/costs-grid")>();
  const { createElement } = await import("react");
  return {
    ...actual,
    CostsGrid: (props: CostsGridProps) => {
      grids.costs.push(props);
      return createElement(actual.CostsGrid, props);
    },
  };
});
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => PATHNAME,
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const PATHNAME = `/projects/${PROJECT}/revisions/${REVISION}/actual-costs`;
const COMMAND = "01926f3a-7c00-7000-8000-000000000801";
const NOT_FOUND = { problem: { code: "NOT_FOUND", status: 404 } } as const;
const BANNER = '<section aria-label="Reading context"';
const COSTS = "GET /projects/{project_id}/actual-costs";
const IMPORTS = "GET /projects/{project_id}/cost-imports";

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/&#x27;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

/** Render the screen of the actual costs in English, at the query given. */
async function costsAt(search: PageSearchParams = {}) {
  const page = await ActualCostsPage({
    params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
    searchParams: Promise.resolve(search),
  });
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
      {page as ReactNode}
    </NextIntlClientProvider>,
  );
}

/** The query of the one call the page made to an operation. */
function queryOf(route: string): Record<string, string> {
  const calls = server.clients.flatMap((client) => client.calls);
  const [call, ...more] = calls.filter((each) => each.route === route);
  expect(more).toEqual([]);
  return Object.fromEntries(call?.query ?? []);
}

beforeEach(() => {
  grids.costs = [];
  server.clients = [];
  server.answers = {
    "GET /session": "session",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/revisions": "revisions",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    "GET /projects/{project_id}/subprojects": "subprojects",
    [COSTS]: "actual_costs",
    [IMPORTS]: "cost_imports",
  };
});

describe("the screen of the actual costs", () => {
  it("titles the tab with the function and the project", async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ projectId: PROJECT, revisionId: REVISION }),
    });
    expect(metadata.title).toMatch(/^Actual costs · /);
  });

  it("reads the first page of the actual costs of the project, and of the journal of its imports, under the banner [WF-CRE-0040-A]", async () => {
    const page = await costsAt();
    expect(page.startsWith(BANNER)).toBe(true);
    expect(queryOf(COSTS)).toEqual({});
    expect(queryOf(IMPORTS)).toEqual({ limit: "12" });
    expect(text(page)).toContain("Actual costs 4 lines retained");
  });

  it("leads from its head to the imports and exports of the project, where the actual costs are imported, in the same context", async () => {
    const page = await costsAt({ subproject_id: "unassigned", as_of: "2026-05-31" });
    expect(page).toMatch(
      new RegExp(
        `<a [^>]*href="/projects/${PROJECT}/revisions/${REVISION}/exchanges\\?subproject_id=unassigned&amp;as_of=2026-05-31"[^>]*>.*?Imports and exports</a>`,
      ),
    );
  });

  it("presents the three totals and the date of the last import the server gives [WF-CRE-0040-A] [WF-CRE-0050-A]", async () => {
    const page = await costsAt();
    expect(text(page)).toContain(
      "Tracked scope 3,000.00 Excluded from the tracked scope 650.00 General total 3,650.00 Last import",
    );
    expect(page).toContain('<time dateTime="2026-05-04T08:30:00Z">');
  });

  it("hands the grid the lines of the page in the order of the answer, of each the fields it reads alone", async () => {
    await costsAt();
    const [handed] = grids.costs;
    expect(handed?.costs.items.map((line) => line.document_number)).toEqual([
      "FA-2026-0412",
      "AV-2026-0388",
      "FA-2026-0301",
      "FA-2026-0295",
    ]);
    expect(Object.keys(handed?.costs.items[0] ?? {})).toEqual([
      "cost_line_id",
      "document_number",
      "document_date",
      "amount",
      "subproject_code",
      "subproject_label",
      "is_in_tracked_scope",
      "excluded_reason",
      "passthrough",
    ]);
    expect(handed?.costs.totals).toEqual({
      tracked: "3000.00",
      excluded: "650.00",
      overall: "3650.00",
    });
  });

  it("asks the server for the sort, the filters and the pages the address names, by the names of the contract [WF-CRE-0040-A]", async () => {
    await costsAt({
      sort_by: "amount",
      sort_order: "desc",
      in_tracked_scope: "false",
      subproject_id: COMMAND,
      from: "2026-04-01",
      to: "2026-04-30",
      offset: "50",
      imports_offset: "12",
      search: "câbles",
    });
    expect(queryOf(COSTS)).toEqual({
      offset: "50",
      subproject_id: COMMAND,
      from: "2026-04-01",
      to: "2026-04-30",
      in_tracked_scope: "false",
      sort_by: "amount",
      sort_order: "desc",
    });
    expect(queryOf(IMPORTS)).toEqual({ limit: "12", offset: "12" });
    expect(grids.costs[0]?.query.sort).toEqual({ column: "amount", order: "desc" });
  });

  it("asks the server to sort by a column kept from the file, by its name in the file [WF-IHM-0060-A]", async () => {
    await costsAt({ sort_by: "passthrough.Fournisseur", sort_order: "desc" });
    expect(queryOf(COSTS)).toEqual({ sort_by: "passthrough.Fournisseur", sort_order: "desc" });
    expect(grids.costs[0]?.query.sort).toEqual({
      column: "passthrough.Fournisseur",
      order: "desc",
    });
  });

  it("asks nothing the contract would refuse: a sort by a column it does not sort by, a page that is no place", async () => {
    await costsAt({ sort_by: "passthrough.", offset: "-3", in_tracked_scope: "maybe" });
    expect(queryOf(COSTS)).toEqual({});
  });

  it("offers the sub-projects of the project to filter on, the one the address names chosen", async () => {
    const page = await costsAt({ subproject_id: COMMAND });
    expect(page).toMatch(
      new RegExp(`<option value="${COMMAND}" selected="">SP-CMD — Poste de commande</option>`),
    );
    expect(page).toContain('<option value="unassigned">No subproject</option>');
  });

  it("shows the way to the next page when the server holds more lines than the page [WF-CRE-0040-A]", async () => {
    server.answers = { ...server.answers, [COSTS]: { example: "actual_costs_page", status: 200 } };
    const page = await costsAt({ offset: "1" });
    expect(text(page)).toContain("Actual costs 4 lines retained");
    expect(page).toContain('aria-label="Pages of the actual costs"');
    expect(page).toContain(`href="${PATHNAME}?offset=2"`);
  });

  it("says nothing has been imported yet: no line, null totals, no import [WF-CRE-0050-A]", async () => {
    server.answers = {
      ...server.answers,
      [COSTS]: { example: "actual_costs_empty", status: 200 },
      [IMPORTS]: { example: "cost_imports_empty", status: 200 },
    };
    const said = text(await costsAt());
    expect(said).toContain("Actual costs no line retained");
    expect(said).toContain("General total 0.00 Last import No import");
    expect(said).toContain("No row matches the request.");
    expect(said).toContain("Journal of the imports No actual cost has been imported yet.");
  });

  it.each([
    [
      "actual_costs_period_inverted",
      "The actual costs cannot be read over this period: its end precedes its start.",
    ],
    [
      "actual_costs_subproject_unknown",
      "The actual costs cannot be read: the sub-project asked for does not exist.",
    ],
  ])(
    "says filters the API refuses in place of the lines, the filters kept to be changed: %s",
    async (refusal, sentence) => {
      server.answers = {
        ...server.answers,
        [COSTS]: { problem: example(refusal) as Problem & { status: 422 } },
      };
      const markup = await costsAt({ from: "2026-04-30", to: "2026-03-01" });
      const said = text(markup);
      expect(said).toContain(sentence);
      // The period refused stays in the bar, to be changed.
      expect(markup).toMatch(/<input[^>]*type="date"[^>]*value="2026-04-30"/);
      expect(markup).toMatch(/<input[^>]*type="date"[^>]*value="2026-03-01"/);
      expect(said).not.toContain("General total");
      expect(said).toContain("Journal of the imports");
      expect(grids.costs).toEqual([]);
    },
  );

  it.each([
    [
      "two parameters at once",
      [
        { pointer: "/query/to", code: "VALUE_OUT_OF_RANGE" as const },
        { pointer: "/query/subproject_id", code: "UNKNOWN_SUBPROJECT" as const },
      ],
    ],
    [
      "a parameter it does not know",
      [{ pointer: "/query/in_tracked_scope", code: "VALUE_OUT_OF_RANGE" as const }],
    ],
  ])(
    "says the filters refused without naming one, when the envelope points at %s",
    async (_, fields) => {
      server.answers = {
        ...server.answers,
        [COSTS]: {
          problem: {
            code: "VALIDATION_FAILED",
            status: 422,
            fields,
          },
        },
      };
      expect(text(await costsAt())).toContain(
        "The actual costs cannot be read: the API refuses the filters asked for.",
      );
    },
  );

  it("is not found when the API does not find the project", async () => {
    server.answers = { ...server.answers, "GET /projects/{project_id}": NOT_FOUND };
    await expect(costsAt()).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
  });
});
