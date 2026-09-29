// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createApiClient, Unreachable } from "@/api/client";
import { SignedOut, UnexpectedAnswer } from "@/api/problem";
import { SCREEN } from "@/components/shell/page-header";
import { SESSION_REQUIRED_DIGEST } from "@/components/system/failure";
import { CATALOGUES } from "@/i18n/catalogues";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type FakeTiming,
} from "@/test/fixtures";

import ProjectPage, { generateMetadata as projectMetadata } from "./[projectId]/page";
import EstimatePage, {
  generateMetadata as estimateMetadata,
} from "./[projectId]/revisions/[revisionId]/estimate/page";
import RevisionPage from "./[projectId]/revisions/[revisionId]/page";
import PlanningPage, {
  generateMetadata as planningMetadata,
} from "./[projectId]/revisions/[revisionId]/planning/page";
import ProjectsPage, { generateMetadata as projectsMetadata } from "./page";

const server = vi.hoisted(
  (): {
    answers: FakeAnswers;
    clients: FakeClient[];
    unreachable: boolean;
    structures: (() => Response) | undefined;
    timing: FakeTiming;
  } => ({
    answers: {},
    clients: [],
    unreachable: false,
    structures: undefined,
    timing: {},
  }),
);

vi.mock("@/api/server", () => ({
  serverClient: () => {
    if (server.unreachable) {
      return createApiClient({
        address: "http://unreachable.invalid",
        fetch: () => Promise.reject(new TypeError("fetch failed")),
      });
    }
    const structures = server.structures;
    if (structures !== undefined) {
      // An answer the contract does not declare for the structures — a failure of the
      // service, a page of a gateway —; the session, the project and the revision from their
      // examples.
      return createApiClient({
        address: "http://api.invalid",
        fetch: (request) => {
          const path = new URL(request.url).pathname;
          if (path.endsWith("/structures")) {
            return Promise.resolve(structures());
          }
          if (path.endsWith("/session")) {
            return Promise.resolve(Response.json(example("session")));
          }
          const name = /\/revisions\/[^/]+$/.test(path) ? "revision" : "project";
          return Promise.resolve(Response.json(example(name)));
        },
      });
    }
    const client = fakeClient(server.answers, server.timing);
    server.clients.push(client);
    return client;
  },
}));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/projects",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
// The project in pricing, without a revision (`project_pricing.json`).
const PRICING = "01926f3a-7c00-7000-8000-000000000002";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
const NOT_FOUND = { problem: { code: "NOT_FOUND", status: 404 } } as const;
const NO_SEARCH = Promise.resolve({});
const BANNER = '<section aria-label="Reading context"';
const UNAUTHORIZED = { problem: { code: "SESSION_REQUIRED", status: 401 } } as const;

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** The call that read the nodes of the structure. */
function nodesCall() {
  return callOf("/nodes");
}

/** The call to the API whose route ends as given. */
function callOf(end: string) {
  return server.clients.flatMap((client) => client.calls).find((call) => call.route.endsWith(end));
}

/** A page in English, as the shell hands it its texts. */
function inEnglish(page: ReactNode) {
  return (
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en}>
      {page}
    </NextIntlClientProvider>
  );
}

beforeEach(() => {
  server.clients = [];
  server.unreachable = false;
  server.structures = undefined;
  server.timing = {};
  server.answers = {
    "GET /session": "session",
    "GET /projects": "projects",
    "GET /reference/readiness": "reference_readiness",
    "GET /projects/{project_id}": "project",
    "GET /projects/{project_id}/revisions": "revisions",
    "GET /projects/{project_id}/revisions/{revision_id}": "revision",
    "GET /projects/{project_id}/revisions/{revision_id}/structures": "structures",
    "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes": "nodes",
    "GET /projects/{project_id}/estimate-indicators": "estimate_indicators",
    "GET /projects/{project_id}/estimate-indicators/missing-rates": "missing_rates_none",
  };
});

describe("the witness path", () => {
  it("lists the projects, each a link to its page", async () => {
    const html = renderToStaticMarkup(inEnglish(await ProjectsPage({ searchParams: NO_SEARCH })));
    expect(html.startsWith(`<main class="${SCREEN.dense}">`)).toBe(true);
    expect(html).toMatch(/<h1[^>]*><svg[^>]*aria-hidden="true"[^>]*>.*?<\/svg>Projects<\/h1>/);
    expect(html).toContain(`<a href="/projects/${PROJECT}">Modernisation du poste de commande</a>`);
    expect(html).toContain("Extension de la ligne d&#x27;essais");
  });

  it("shows a project and links to its revisions", async () => {
    const page = await ProjectPage({
      params: Promise.resolve({ projectId: PROJECT }),
      searchParams: NO_SEARCH,
    });
    const html = renderToStaticMarkup(inEnglish(page));
    expect(html).toContain(`<main class="${SCREEN.dense}">`);
    expect(html).toMatch(/<h1[^>]*><svg[^>]*>.*?<\/svg>Modernisation du poste de commande<\/h1>/);
    expect(html).toContain(`href="/projects/${PROJECT}/revisions/${REVISION}"`);
    expect(html).toContain(">Référence</a>");
  });

  it("shows the grid of the estimate on the main structure, a row for each node, in the order of the answer", async () => {
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const html = renderToStaticMarkup(
      inEnglish(await EstimatePage({ params, searchParams: NO_SEARCH })),
    );
    expect(html).toContain(`<main class="${SCREEN.dense}">`);
    expect(html).toMatch(
      /<h1[^>]*><svg[^>]*aria-hidden="true"[^>]*>.*?<\/svg>Costing and estimate<\/h1>/,
    );
    expect(text(html)).toContain("Structure principale · 3 tasks, 1 line");
    expect(html).toMatch(
      /<table[^>]*role="grid"[^>]*aria-label="Estimate grid"[^>]*aria-rowcount="6"/,
    );
    // Each row shows the icon of its nature, named for it: a summary task, a task, a line.
    const natures = [...html.matchAll(/<svg[^>]*role="img"[^>]*aria-label="([^"]*)"/g)]
      .map((match) => match[1])
      .filter((name) => name !== "Computed");
    expect(natures).toEqual(["Summary task", "Task", "Disbursement line", "Task"]);
    const labels = [...html.matchAll(/<span class="truncate">([^<]*)<\/span>/g)].map(
      (match) => match[1],
    );
    expect(labels).toEqual(
      expect.arrayContaining(["Études", "Études de détail", "Ingénierie de détail"]),
    );
    expect(text(html)).toContain("Total — 3 tasks, 1 line");
  });

  it("asks the server for the sort, the search and the filtered sub-project the address holds, by the parameters of the contract", async () => {
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const search = Promise.resolve({
      sort_by: "budgeted_amount",
      sort_order: "desc",
      search: "revue",
      subproject_id: "unassigned",
    });
    const html = renderToStaticMarkup(
      inEnglish(await EstimatePage({ params, searchParams: search })),
    );
    const call = nodesCall();
    expect(Object.fromEntries(call?.query ?? [])).toEqual({
      sort_by: "budgeted_amount",
      sort_order: "desc",
      search: "revue",
      subproject_id: "unassigned",
    });
    expect(html).toMatch(/<th[^>]*aria-sort="descending"[^>]*>(?:(?!<\/th>).)*Budgeted/);
  });

  it("asks the plan order of the whole structure when the address holds no sort the grid offers, nor a search", async () => {
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const search = Promise.resolve({ sort_by: "start_date", sort_order: "desc", search: "" });
    await EstimatePage({ params, searchParams: search });
    expect([...(nodesCall()?.query.keys() ?? [])]).toEqual([]);
  });

  it("shows the totals the server gave for the request, in the language of the interface", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes":
        "nodes_estimate",
    };
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const html = renderToStaticMarkup(
      inEnglish(await EstimatePage({ params, searchParams: NO_SEARCH })),
    );
    expect(text(html)).toContain("Total — 3 tasks, 3 lines 12.5 2,734.56 2,734.56");
  });

  it("reads the session, the structures and the reading context together, and waits for the session only to read the nodes", async () => {
    let answer: () => void = () => undefined;
    const held = new Promise<void>((resolve) => {
      answer = resolve;
    });
    server.timing = { hold: (route) => (route === "GET /session" ? held : undefined) };
    const routes = () => server.clients.flatMap((client) => client.calls).map((call) => call.route);
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const page = EstimatePage({ params, searchParams: NO_SEARCH });
    await vi.waitFor(() => {
      expect(routes()).toEqual(
        expect.arrayContaining([
          "GET /session",
          "GET /projects/{project_id}/revisions/{revision_id}/structures",
          "GET /projects/{project_id}",
          "GET /projects/{project_id}/revisions/{revision_id}",
        ]),
      );
    });
    expect(nodesCall()).toBeUndefined();
    answer();
    await page;
    expect(nodesCall()).toBeDefined();
  });

  it("asks no sort when the address lifted it, whatever the account keeps", async () => {
    server.answers = { ...server.answers, "GET /session": "session_grid_settings" };
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    await EstimatePage({ params, searchParams: Promise.resolve({ sort_by: "" }) });
    expect([...(nodesCall()?.query.keys() ?? [])]).toEqual([]);
  });

  it("hands the grid the settings of the account the session read", async () => {
    server.answers = { ...server.answers, "GET /session": "session_grid_settings" };
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const html = renderToStaticMarkup(
      inEnglish(await EstimatePage({ params, searchParams: NO_SEARCH })),
    );
    // The quantity hidden, the label widened.
    expect(html).not.toContain(">Qty<");
    expect(html).toContain('<col style="width:400px"/>');
  });

  it("sorts by the sort the account keeps for the grid when the address asks none, and by the address otherwise", async () => {
    server.answers = { ...server.answers, "GET /session": "session_grid_settings" };
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const html = renderToStaticMarkup(
      inEnglish(await EstimatePage({ params, searchParams: NO_SEARCH })),
    );
    expect(Object.fromEntries(nodesCall()?.query ?? [])).toEqual({
      sort_by: "budgeted_amount",
      sort_order: "desc",
    });
    expect(html).toMatch(/<th[^>]*aria-sort="descending"[^>]*>(?:(?!<\/th>).)*Budgeted/);

    server.clients = [];
    await EstimatePage({ params, searchParams: Promise.resolve({ sort_by: "label" }) });
    expect(Object.fromEntries(nodesCall()?.query ?? [])).toEqual({
      sort_by: "label",
      sort_order: "asc",
    });
  });

  it("leads from a revision to its planning, the first function of a revision in the order of the FBS and of the sidebar, the reading context carried on", async () => {
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const search = Promise.resolve({ subproject_id: "unassigned", as_of: ["2026-05-31", "x"] });
    await expect(RevisionPage({ params, searchParams: search })).rejects.toMatchObject({
      digest: expect.stringContaining(
        `;/projects/${PROJECT}/revisions/${REVISION}/planning?subproject_id=unassigned&as_of=2026-05-31&as_of=x;`,
      ) as unknown,
    });
    await expect(RevisionPage({ params, searchParams: NO_SEARCH })).rejects.toMatchObject({
      digest: expect.stringContaining(
        `;/projects/${PROJECT}/revisions/${REVISION}/planning;`,
      ) as unknown,
    });
    // The session alone is read, to know what it may read; nothing of the revision yet.
    const routes = server.clients.flatMap((client) => client.calls).map((call) => call.route);
    expect(new Set(routes)).toEqual(new Set(["GET /session"]));
  });

  it("leads an estimator who may not read the planning from a revision to its estimate", async () => {
    server.answers = { ...server.answers, "GET /session": "session_estimator" };
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    await expect(RevisionPage({ params, searchParams: NO_SEARCH })).rejects.toMatchObject({
      digest: expect.stringContaining(
        `;/projects/${PROJECT}/revisions/${REVISION}/estimate;`,
      ) as unknown,
    });
  });

  it("leads from a revision to its planning without a session, whose page leads to the sign-in", async () => {
    server.answers = { ...server.answers, "GET /session": UNAUTHORIZED };
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    await expect(RevisionPage({ params, searchParams: NO_SEARCH })).rejects.toMatchObject({
      digest: expect.stringContaining(
        `;/projects/${PROJECT}/revisions/${REVISION}/planning;`,
      ) as unknown,
    });
  });

  it("is not found at a revision the address names by no identifier, before leading anywhere", async () => {
    const params = Promise.resolve({ projectId: PROJECT, revisionId: "a.b" });
    await expect(RevisionPage({ params, searchParams: NO_SEARCH })).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
  });

  it("is not found when the API does not find the structures of the revision", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}/structures": NOT_FOUND,
    };
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    await expect(EstimatePage({ params, searchParams: NO_SEARCH })).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
  });

  it("never shows an empty grid on a failure of the service: the screen of failure names it by its correlation identifier", async () => {
    server.structures = () =>
      Response.json(
        { code: "INTERNAL_ERROR", status: 500, correlation_id: "req-7f3a" },
        { status: 500, headers: { "content-type": "application/problem+json" } },
      );
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const page = EstimatePage({ params, searchParams: NO_SEARCH });
    await expect(page).rejects.toBeInstanceOf(UnexpectedAnswer);
    await expect(page).rejects.toMatchObject({
      operation: "listCostStructures",
      digest: "WATERFALL_CORRELATION;req-7f3a",
    });
  });

  it("never shows an empty grid when a gateway says the service is down: the API is out of reach", async () => {
    server.structures = () => new Response("<html>Bad gateway</html>", { status: 502 });
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    await expect(EstimatePage({ params, searchParams: NO_SEARCH })).rejects.toBeInstanceOf(
      Unreachable,
    );
  });

  it("never shows an empty grid for a revision without a main structure, which the contract rules out", async () => {
    const structures = example("structures") as { kind: string }[];
    server.structures = () =>
      Response.json(structures.filter((structure) => structure.kind !== "main"));
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    await expect(EstimatePage({ params, searchParams: NO_SEARCH })).rejects.toMatchObject({
      name: "UnexpectedAnswer",
      operation: "listCostStructures",
    });
  });

  it("is not found at an address that names no revision, before the API is asked", async () => {
    const params = Promise.resolve({ projectId: PROJECT, revisionId: "a.b" });
    await expect(EstimatePage({ params, searchParams: NO_SEARCH })).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
    expect(server.clients.flatMap((client) => client.calls)).toEqual([]);
  });

  it("is not found for a project the API does not find, as the other screens of a project", async () => {
    server.answers = {
      "GET /session": "session",
      "GET /projects/{project_id}": NOT_FOUND,
      "GET /projects/{project_id}/revisions": NOT_FOUND,
    };
    const page = ProjectPage({
      params: Promise.resolve({ projectId: PROJECT }),
      searchParams: NO_SEARCH,
    });
    await expect(page).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
  });

  it("titles the tab with the screen, and with the project read", async () => {
    expect((await projectsMetadata()).title).toBe("Projects — Waterfall");
    const params = Promise.resolve({ projectId: PROJECT });
    expect((await projectMetadata({ params })).title).toBe(
      "Projects · Modernisation du poste de commande — Waterfall",
    );
  });
});

describe("the grid of the planning", () => {
  const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });

  beforeEach(() => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes":
        "nodes_planning",
    };
  });

  it("shows the tasks of the main structure, asking the server for the tasks alone, the same grid as the estimate", async () => {
    const html = renderToStaticMarkup(
      inEnglish(await PlanningPage({ params, searchParams: NO_SEARCH })),
    );
    expect(Object.fromEntries(nodesCall()?.query ?? [])).toEqual({ kinds: "task" });
    expect(html.startsWith(BANNER)).toBe(true);
    expect(html).toContain(`<main class="${SCREEN.dense}">`);
    expect(html).toMatch(/<h1[^>]*><svg[^>]*aria-hidden="true"[^>]*>.*?<\/svg>Planning<\/h1>/);
    expect(text(html)).toContain("Structure principale · 6 tasks");
    expect(html).toMatch(
      /<table[^>]*role="grid"[^>]*aria-label="Planning grid"[^>]*aria-rowcount="8"/,
    );
    expect(text(html)).toContain("Total — 6 tasks");
    // The totals the server gave, which `kinds` leaves as they are, are not the planning's to
    // show: it has no column of hours nor of amounts.
    expect(text(html)).not.toContain("100,000.00");
  });

  it("asks the server for the sort, the search and the filtered sub-project the address holds, besides the tasks", async () => {
    const search = Promise.resolve({
      sort_by: "total_float_days",
      sort_order: "desc",
      search: "revue",
      subproject_id: "unassigned",
    });
    const html = renderToStaticMarkup(
      inEnglish(await PlanningPage({ params, searchParams: search })),
    );
    expect(Object.fromEntries(nodesCall()?.query ?? [])).toEqual({
      kinds: "task",
      sort_by: "total_float_days",
      sort_order: "desc",
      search: "revue",
      subproject_id: "unassigned",
    });
    expect(html).toMatch(/<th[^>]*aria-sort="descending"[^>]*>(?:(?!<\/th>).)*Float/);
  });

  it("asks no sort the planning does not offer, such as an amount of the estimate", async () => {
    await PlanningPage({ params, searchParams: Promise.resolve({ sort_by: "budgeted_amount" }) });
    expect(Object.fromEntries(nodesCall()?.query ?? [])).toEqual({ kinds: "task" });
  });

  it("is not found for a revision the API does not find", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": NOT_FOUND,
    };
    await expect(PlanningPage({ params, searchParams: NO_SEARCH })).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
  });

  it("titles the tabs of the planning and of the estimate with the function and the project", async () => {
    const project = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    expect((await planningMetadata({ params: project })).title).toBe(
      "Planning · Modernisation du poste de commande — Waterfall",
    );
    expect((await estimateMetadata({ params: project })).title).toBe(
      "Costing and estimate · Modernisation du poste de commande — Waterfall",
    );
  });
});

describe("the indicators and the missing rates of the estimate", () => {
  const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });

  it("shows the indicators of the revision above its grid, with the date they are computed at", async () => {
    const html = renderToStaticMarkup(
      inEnglish(await EstimatePage({ params, searchParams: NO_SEARCH })),
    );
    expect(text(html)).toMatch(
      /Costing and estimate Structure principale · 3 tasks, 1 line Estimate indicators Computed on Estimate total 100,000.00 .*No\. Label/,
    );
    expect(html).toContain('<time dateTime="2026-03-16T14:05:00Z"');
    expect(Object.fromEntries(callOf("/estimate-indicators")?.query ?? [])).toEqual({
      revision_id: REVISION,
    });
    expect(Object.fromEntries(callOf("/missing-rates")?.query ?? [])).toEqual({
      revision_id: REVISION,
    });
    expect(text(html)).not.toContain("Missing hourly rates");
  });

  it("reads the indicators for the sub-project the address filters", async () => {
    await EstimatePage({ params, searchParams: Promise.resolve({ subproject_id: "unassigned" }) });
    expect(Object.fromEntries(callOf("/estimate-indicators")?.query ?? [])).toEqual({
      revision_id: REVISION,
      scope: "unassigned",
    });
  });

  it("names the categories whose hourly rate is missing, with the way to the reference for a session that may read it", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/estimate-indicators/missing-rates": "missing_rates",
    };
    const html = renderToStaticMarkup(
      inEnglish(await EstimatePage({ params, searchParams: NO_SEARCH })),
    );
    expect(text(html)).toContain(
      "Missing hourly rates The estimate cannot be calculated until these cost categories have an hourly rate for its reference year: Ingénierie électrique — 2026 Mise en service — 2026 Enter the hourly rates",
    );
    expect(links(html)).toContain("/reference/costs");

    server.answers = { ...server.answers, "GET /session": "session_estimator" };
    const estimator = renderToStaticMarkup(
      inEnglish(await EstimatePage({ params, searchParams: NO_SEARCH })),
    );
    expect(text(estimator)).toContain("Ingénierie électrique — 2026");
    expect(links(estimator)).not.toContain("/reference/costs");
  });

  it("never shows figures it did not read: indicators the API does not find leave the screen not found", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/estimate-indicators": NOT_FOUND,
    };
    await expect(EstimatePage({ params, searchParams: NO_SEARCH })).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
  });
});

describe("the banner of the reading context on the witness path", () => {
  it("names the project on the page of a project [WF-IHM-0020-A]", async () => {
    const page = await ProjectPage({
      params: Promise.resolve({ projectId: PROJECT }),
      searchParams: NO_SEARCH,
    });
    const html = renderToStaticMarkup(inEnglish(page));
    expect(html.startsWith(BANNER)).toBe(true);
    expect(text(html)).toMatch(
      /^Project Modernisation du poste de commande Modernisation du poste de commande Référence/,
    );
  });

  it("names the project and the revision on the grid of a revision [WF-IHM-0020-A]", async () => {
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const search = Promise.resolve({ subproject_id: "unassigned" });
    const html = renderToStaticMarkup(
      inEnglish(await EstimatePage({ params, searchParams: search })),
    );
    expect(html.startsWith(BANNER)).toBe(true);
    expect(text(html)).toMatch(
      /^Project Modernisation du poste de commande Revision Current revision Draft Subproject: No subproject Costing and estimate /,
    );
    expect(html).toContain(`href="/projects/${PROJECT}/revisions/${REVISION}/estimate"`);
  });

  it("is not found for a revision the API does not find, as the other screens of a project", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": NOT_FOUND,
    };
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    await expect(EstimatePage({ params, searchParams: NO_SEARCH })).rejects.toMatchObject({
      digest: "NEXT_HTTP_ERROR_FALLBACK;404",
    });
  });

  it("does not swallow an answer other than not found, and leaves it to the screen of failure", async () => {
    server.answers = { ...server.answers, "GET /projects/{project_id}": UNAUTHORIZED };
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    await expect(EstimatePage({ params, searchParams: NO_SEARCH })).rejects.toMatchObject({
      operation: "getProject",
      digest: SESSION_REQUIRED_DIGEST,
    });
  });
});

/** The list of projects in English, at an address whose query is given. */
async function projectsPage(search: Record<string, string> = {}): Promise<string> {
  const page = await ProjectsPage({ searchParams: Promise.resolve(search) });
  return renderToStaticMarkup(inEnglish(page));
}

/** The addresses the links of a page lead to. */
function links(markup: string): string[] {
  return [...markup.matchAll(/href="([^"]*)"/g)].map((match) => match[1] ?? "");
}

describe("the empty states of the shell", () => {
  it("says there is no project, on the example of an empty list", async () => {
    server.answers = { ...server.answers, "GET /projects": "projects_empty" };
    const html = await projectsPage();
    expect(text(html)).toBe("Projects No project.");
    expect(html).not.toContain("<ul");
  });

  it("lifts the contributor filter when it is what empties the list", async () => {
    server.answers = { ...server.answers, "GET /projects": "projects_empty" };
    const html = await projectsPage({ is_contributor: "true" });
    expect(text(html)).toBe("Projects You contribute to no project. Show all projects");
    expect(links(html)).toEqual(["/projects"]);
    const list = server.clients
      .flatMap((client) => client.calls)
      .find((call) => call.route === "GET /projects");
    expect(list?.query.get("is_contributor")).toBe("true");
  });

  it("asks the whole list when the address holds no filter", async () => {
    await projectsPage();
    const list = server.clients
      .flatMap((client) => client.calls)
      .find((call) => call.route === "GET /projects");
    expect(list?.query.has("is_contributor")).toBe(false);
  });

  it("names each prerequisite an incomplete reference lacks, and leads to where it is provided", async () => {
    server.answers = {
      ...server.answers,
      "GET /reference/readiness": "reference_readiness_incomplete",
    };
    const html = await projectsPage();
    expect(text(html)).toMatch(
      /^Projects Incomplete reference data No project can be created until the common reference data has: a default calendar with working hours an active cost category Modernisation/,
    );
    expect(links(html).slice(0, 2)).toEqual(["/reference/resources", "/reference/costs"]);
  });

  it("names the prerequisites without a link to a function the session may not read", async () => {
    server.answers = {
      ...server.answers,
      "GET /session": UNAUTHORIZED,
      "GET /reference/readiness": "reference_readiness_incomplete",
    };
    const html = await projectsPage();
    expect(text(html)).toContain("a default calendar with working hours an active cost category");
    expect(links(html)).not.toContain("/reference/costs");
  });

  it("says nothing of a complete reference", async () => {
    expect(text(await projectsPage())).not.toContain("reference data");
  });

  it("says a project has no revision yet, on the example of an empty history, and leads to its revisions", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}": "project_pricing",
      "GET /projects/{project_id}/revisions": "revisions_empty",
    };
    const page = await ProjectPage({
      params: Promise.resolve({ projectId: PRICING }),
      searchParams: NO_SEARCH,
    });
    const html = renderToStaticMarkup(inEnglish(page));
    expect(text(html)).toContain(
      "Extension de la ligne d&#x27;essais This project has no revision yet. Go to the revisions of the project",
    );
    expect(links(html)).toContain(`/projects/${PRICING}/revisions`);
    expect(html).not.toContain("<ul");
  });

  it("does not offer the way to the revisions to a session that may not read them", async () => {
    server.answers = {
      ...server.answers,
      "GET /session": UNAUTHORIZED,
      "GET /projects/{project_id}": "project_pricing",
      "GET /projects/{project_id}/revisions": "revisions_empty",
    };
    const page = await ProjectPage({
      params: Promise.resolve({ projectId: PRICING }),
      searchParams: NO_SEARCH,
    });
    const html = renderToStaticMarkup(inEnglish(page));
    expect(text(html)).toContain("This project has no revision yet.");
    expect(text(html)).not.toContain("Go to the revisions of the project");
    expect(links(html)).not.toContain(`/projects/${PRICING}/revisions`);
  });

  it("guides a new installation to its reference before saying there is no project", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects": "projects_empty",
      "GET /reference/readiness": "reference_readiness_incomplete",
    };
    const html = await projectsPage();
    expect(html).toMatch(
      new RegExp(`^<main class="${SCREEN.dense}">.*?</h1>.*?<section aria-labelledby="[^"]+"`),
    );
    expect(text(html)).toBe(
      "Projects Incomplete reference data No project can be created until the common reference data has: " +
        "a default calendar with working hours an active cost category No project.",
    );
    expect(links(html)).toEqual(["/reference/resources", "/reference/costs"]);
  });

  it("is not found for a revision its address carries that the API does not find", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}": NOT_FOUND,
    };
    const page = ProjectPage({
      params: Promise.resolve({ projectId: PROJECT }),
      searchParams: Promise.resolve({ revision_id: REVISION }),
    });
    await expect(page).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
  });

  it("is not found at an address that names no project, before the API is asked", async () => {
    const page = ProjectPage({
      params: Promise.resolve({ projectId: "a.b" }),
      searchParams: NO_SEARCH,
    });
    await expect(page).rejects.toMatchObject({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" });
    expect(server.clients.flatMap((client) => client.calls)).toEqual([]);
  });

  it("never says the list is empty when the API refuses it for want of a session: it leads to the sign-in page", async () => {
    server.answers = { ...server.answers, "GET /projects": UNAUTHORIZED };
    await expect(ProjectsPage({ searchParams: NO_SEARCH })).rejects.toBeInstanceOf(SignedOut);
  });

  it("never says there is no project or no revision when the API cannot be reached: it is announced", async () => {
    server.unreachable = true;
    await expect(ProjectsPage({ searchParams: NO_SEARCH })).rejects.toBeInstanceOf(Unreachable);
    const page = ProjectPage({
      params: Promise.resolve({ projectId: PROJECT }),
      searchParams: NO_SEARCH,
    });
    await expect(page).rejects.toBeInstanceOf(Unreachable);
  });
});
