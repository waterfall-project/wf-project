// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createApiClient, Unreachable } from "@/api/client";
import type { Examples } from "@/api/generated/examples";
import { UnexpectedAnswer } from "@/api/problem";
import { SCREEN } from "@/components/shell/page-header";
import { SESSION_REQUIRED_DIGEST } from "@/components/system/failure";
import { ESTIMATE_FIELDS } from "@/components/grid/estimate";
import type { EstimateGridProps } from "@/components/grid/estimate-grid";
import {
  type AnyNodeFields,
  COMMON_FIELDS,
  type NodeList,
  nodeFieldNames,
} from "@/components/grid/nodes";
import { PLANNING_FIELDS } from "@/components/grid/planning";
import type { PlanningGridProps } from "@/components/grid/planning-grid";
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

const server = vi.hoisted(
  (): {
    answers: FakeAnswers;
    clients: FakeClient[];
    unreachable: boolean;
    undeclared: { readonly route: string; readonly answer: () => Response } | undefined;
    timing: FakeTiming;
  } => ({
    answers: {},
    clients: [],
    unreachable: false,
    undeclared: undefined,
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
    const undeclared = server.undeclared;
    if (undeclared !== undefined) {
      // An answer the contract does not declare for one read — a failure of the service, a
      // page of a gateway —; the other reads from their examples.
      return createApiClient({
        address: "http://api.invalid",
        fetch: (request) => {
          const path = new URL(request.url).pathname;
          if (path.endsWith(undeclared.route)) {
            return Promise.resolve(undeclared.answer());
          }
          const [, name] =
            Object.entries(EXAMPLE_BY_END).find(([end]) => path.endsWith(end))?.[1] ??
            (/\/revisions\/[^/]+$/.test(path) ? READ_REVISION : READ_PROJECT);
          return Promise.resolve(Response.json(example(name)));
        },
      });
    }
    const client = fakeClient(server.answers, server.timing);
    server.clients.push(client);
    return client;
  },
}));
// The grids render as they would, and keep what their page handed them.
const grids = vi.hoisted((): { estimate: EstimateGridProps[]; planning: PlanningGridProps[] } => ({
  estimate: [],
  planning: [],
}));

vi.mock("@/components/grid/estimate-grid", async (original) => {
  const actual = await original<typeof import("@/components/grid/estimate-grid")>();
  const { createElement } = await import("react");
  return {
    ...actual,
    EstimateGrid: (props: EstimateGridProps) => {
      grids.estimate.push(props);
      return createElement(actual.EstimateGrid, props);
    },
  };
});

vi.mock("@/components/grid/planning-grid", async (original) => {
  const actual = await original<typeof import("@/components/grid/planning-grid")>();
  const { createElement } = await import("react");
  return {
    ...actual,
    PlanningGrid: (props: PlanningGridProps) => {
      grids.planning.push(props);
      return createElement(actual.PlanningGrid, props);
    },
  };
});

vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/projects/01926f3a-7c00-7000-8000-000000000001",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const PROJECT = "01926f3a-7c00-7000-8000-000000000001";
// The project in pricing, without a revision (`project_pricing.json`).
const PRICING = "01926f3a-7c00-7000-8000-000000000002";
const REVISION = "01926f3a-7c00-7000-8000-000000000102";
/** The main structure of the revision, as `listCostStructures` names it. */
const STRUCTURE = {
  project_id: PROJECT,
  revision_id: REVISION,
  structure_id: "01926f3a-7c00-7000-8000-000000000201",
};
const NOT_FOUND = { problem: { code: "NOT_FOUND", status: 404 } } as const;
const NO_SEARCH = Promise.resolve({});
const BANNER = '<section aria-label="Reading context"';
const UNAUTHORIZED = { problem: { code: "SESSION_REQUIRED", status: 401 } } as const;

/** A read of the contract, with an example the contract cites for its answer. */
type CitedRead = {
  [R in keyof Examples]: readonly [R, Examples[R][keyof Examples[R]]];
}[keyof Examples];

/** The examples the reads of a revision answer, by the end of their path, the others aside. */
const EXAMPLE_BY_END = {
  "/session": ["GET /session", "session"],
  "/structures": ["GET /projects/{project_id}/revisions/{revision_id}/structures", "structures"],
  "/nodes": [
    "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes",
    "nodes",
  ],
  "/estimate-indicators": ["GET /projects/{project_id}/estimate-indicators", "estimate_indicators"],
  "/missing-rates": [
    "GET /projects/{project_id}/estimate-indicators/missing-rates",
    "missing_rates_none",
  ],
  "/cost-categories": ["GET /reference/cost-categories", "volume/cost_categories"],
  "/resource-roles": ["GET /reference/resource-roles", "resource_roles"],
} as const satisfies Readonly<Record<string, CitedRead>>;
const READ_REVISION = [
  "GET /projects/{project_id}/revisions/{revision_id}",
  "revision",
] as const satisfies CitedRead;
const READ_PROJECT = ["GET /projects/{project_id}", "project"] as const satisfies CitedRead;

/** The read of a revision, whose example a test may change. */
const REVISION_READ = "GET /projects/{project_id}/revisions/{revision_id}";

/** The estimate of the witness revision, some answers changed, and what its grid was handed. */
async function estimateWith(answers: FakeAnswers = {}) {
  server.answers = { ...server.answers, ...answers };
  const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
  const html = renderToStaticMarkup(
    inEnglish(await EstimatePage({ params, searchParams: NO_SEARCH })),
  );
  return { html, grid: grids.estimate[0] };
}

/** A failure of the service, in its envelope, with the correlation identifier of the request. */
function failure(correlation: string): Response {
  return Response.json(
    { code: "INTERNAL_ERROR", status: 500, correlation_id: correlation },
    { status: 500, headers: { "content-type": "application/problem+json" } },
  );
}

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

/** What the page asked of the nodes, besides the fields it reads of them. */
function nodesQuery(): Record<string, string> {
  const query = new URLSearchParams(nodesCall()?.query);
  query.delete("fields");
  return Object.fromEntries(query);
}

/** The fields of the nodes the page asked for, as `listNodes` names them. */
function nodesFields(): string[] | undefined {
  return nodesCall()?.query.get("fields")?.split(",");
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
  grids.estimate = [];
  grids.planning = [];
  server.clients = [];
  server.unreachable = false;
  server.undeclared = undefined;
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
    "GET /reference/cost-categories": "volume/cost_categories",
    "GET /reference/resource-roles": "resource_roles",
  };
});

/**
 * The screen of a grid, which fills the window (#163): the page bounded to its height, the grid
 * taking what the header and the indicators leave it.
 */
const FILLED_SCREEN = `<main data-fill="" class="${SCREEN.dense} min-h-0">`;

describe("the witness path", () => {
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
    const { html } = await estimateWith();
    expect(html).toContain(FILLED_SCREEN);
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
    expect(nodesQuery()).toEqual({
      sort_by: "budgeted_amount",
      sort_order: "desc",
      search: "revue",
      subproject_id: "unassigned",
    });
    expect(html).toMatch(/<th[^>]*aria-sort="descending"[^>]*>(?:(?!<\/th>).)*Budgeted/);
  });

  it("asks the plan order of the whole structure when the address holds no sort the grid offers, nor a search", async () => {
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const search = Promise.resolve({ sort_by: "start", sort_order: "desc", search: "" });
    await EstimatePage({ params, searchParams: search });
    expect(Object.keys(nodesQuery())).toEqual([]);
  });

  it("shows the totals the server gave for the request, in the language of the interface", async () => {
    const { html } = await estimateWith({
      "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes":
        "nodes_estimate",
    });
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
    expect(Object.keys(nodesQuery())).toEqual([]);
  });

  it("hands the grid the settings of the account the session read", async () => {
    const { html } = await estimateWith({ "GET /session": "session_grid_settings" });
    // The quantity hidden, the label widened.
    expect(html).not.toContain(">Qty<");
    expect(html).toContain('<col style="width:400px"/>');
  });

  it("names the category and the role of each line by the reference data, and opens the grid to entry when the revision allows it", async () => {
    const { html, grid } = await estimateWith();
    // Deactivated ones included, to name a line that bears one; the lists offer them no more.
    expect(callOf("/cost-categories")?.query.get("include_inactive")).toBe("true");
    expect(callOf("/resource-roles")?.query.get("include_inactive")).toBe("true");
    expect(
      grid?.reference.roles?.map(({ label, active }) => `${label}: ${String(active)}`),
    ).toEqual([
      "Ingénieur électricien: true",
      "Technicien de mise en service: true",
      "Automaticien: false",
    ]);
    expect(grid?.reference.categories).toHaveLength(200);
    // The revision lists the planning too: the label of a task is entered as well.
    expect([grid?.editable, grid?.tasksEditable]).toEqual([true, true]);
    // The line of the witness structure: subcontracting, and no role.
    expect(html).toMatch(/data-column="cost_category"[^>]*>Sous-traitance</);
  });

  it("lets an estimator enter the lines, and not the label of a task, which is the planning's", async () => {
    const { grid } = await estimateWith({ [REVISION_READ]: "revision_estimator" });
    expect([grid?.editable, grid?.tasksEditable]).toEqual([true, false]);
  });

  it("shows the grid without naming the roles when the API does not let the caller read them", async () => {
    const { html, grid } = await estimateWith({
      "GET /reference/resource-roles": { problem: { code: "NOT_FOUND", status: 404 } },
    });
    expect(grid?.reference.roles).toBeUndefined();
    expect(grid?.reference.categories).toHaveLength(200);
    expect(html).toMatch(/data-column="cost_category"[^>]*>Sous-traitance</);
  });

  it("keeps the grid of a marked revision read only", async () => {
    const { html, grid } = await estimateWith({ [REVISION_READ]: "revision_marked" });
    expect(grid?.editable).toBe(false);
    expect(html).not.toMatch(/<td(?![^>]*aria-readonly)[^>]*data-column=/);
  });

  it("sorts by the sort the account keeps for the grid when the address asks none, and by the address otherwise", async () => {
    const { html } = await estimateWith({ "GET /session": "session_grid_settings" });
    expect(nodesQuery()).toEqual({
      sort_by: "budgeted_amount",
      sort_order: "desc",
    });
    expect(html).toMatch(/<th[^>]*aria-sort="descending"[^>]*>(?:(?!<\/th>).)*Budgeted/);

    server.clients = [];
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    await EstimatePage({ params, searchParams: Promise.resolve({ sort_by: "label" }) });
    expect(nodesQuery()).toEqual({
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
    server.undeclared = { route: "/structures", answer: () => failure("req-7f3a") };
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    const page = EstimatePage({ params, searchParams: NO_SEARCH });
    await expect(page).rejects.toBeInstanceOf(UnexpectedAnswer);
    await expect(page).rejects.toMatchObject({
      operation: "listCostStructures",
      digest: "WATERFALL_CORRELATION;req-7f3a",
    });
  });

  it("never shows an empty grid when a gateway says the service is down: the API is out of reach", async () => {
    server.undeclared = {
      route: "/structures",
      answer: () => new Response("<html>Bad gateway</html>", { status: 502 }),
    };
    const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
    await expect(EstimatePage({ params, searchParams: NO_SEARCH })).rejects.toBeInstanceOf(
      Unreachable,
    );
  });

  it("never shows an empty grid for a revision without a main structure, which the contract rules out", async () => {
    const structures = example("structures") as { kind: string }[];
    server.undeclared = {
      route: "/structures",
      answer: () => Response.json(structures.filter((structure) => structure.kind !== "main")),
    };
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
    expect(nodesQuery()).toEqual({ kinds: "task" });
    // Of each task, the fields the grid reads alone (#166).
    expect(nodesFields()).toEqual(nodeFieldNames(PLANNING_FIELDS));
    expect(html.startsWith(BANNER)).toBe(true);
    expect(html).toContain(FILLED_SCREEN);
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
      sort_by: "total_float",
      sort_order: "desc",
      search: "revue",
      subproject_id: "unassigned",
    });
    const html = renderToStaticMarkup(
      inEnglish(await PlanningPage({ params, searchParams: search })),
    );
    expect(nodesQuery()).toEqual({
      kinds: "task",
      sort_by: "total_float",
      sort_order: "desc",
      search: "revue",
      subproject_id: "unassigned",
    });
    expect(html).toMatch(/<th[^>]*aria-sort="descending"[^>]*>(?:(?!<\/th>).)*Float/);
  });

  it("asks no sort the planning does not offer, such as an amount of the estimate", async () => {
    await PlanningPage({ params, searchParams: Promise.resolve({ sort_by: "budgeted_amount" }) });
    expect(nodesQuery()).toEqual({ kinds: "task" });
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

  it("names the categories whose hourly rate is missing, with the way to the reference, to enter them or to see them", async () => {
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
    // An estimator reads the rates, and may not enter them.
    expect(text(estimator)).toContain("Mise en service — 2026 See the hourly rates");
    expect(links(estimator)).toContain("/reference/costs");
  });

  it("says the indicators unavailable when the API refuses them, and still shows the missing rates and the grid", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/estimate-indicators": NOT_FOUND,
      "GET /projects/{project_id}/estimate-indicators/missing-rates": "missing_rates",
    };
    const html = renderToStaticMarkup(
      inEnglish(await EstimatePage({ params, searchParams: NO_SEARCH })),
    );
    expect(text(html)).toContain(
      "Mise en service — 2026 Enter the hourly rates Estimate indicators The estimate indicators are unavailable.",
    );
    expect(html).toMatch(/<table[^>]*role="grid"[^>]*aria-label="Estimate grid"/);
  });

  it("does not swallow a failure of the service reading the indicators: the screen of failure names it by its correlation identifier", async () => {
    server.undeclared = { route: "/estimate-indicators", answer: () => failure("req-9b1c") };
    const page = EstimatePage({ params, searchParams: NO_SEARCH });
    await expect(page).rejects.toBeInstanceOf(UnexpectedAnswer);
    await expect(page).rejects.toMatchObject({
      operation: "getEstimateIndicators",
      digest: "WATERFALL_CORRELATION;req-9b1c",
    });
  });

  it("leads to the sign-in when the API refuses the indicators for want of a session", async () => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/estimate-indicators": UNAUTHORIZED,
    };
    await expect(EstimatePage({ params, searchParams: NO_SEARCH })).rejects.toMatchObject({
      operation: "getEstimateIndicators",
      digest: SESSION_REQUIRED_DIGEST,
    });
  });

  it("says the API out of reach when a gateway answers for the indicators", async () => {
    server.undeclared = {
      route: "/estimate-indicators",
      answer: () => new Response("<html>Bad gateway</html>", { status: 502 }),
    };
    await expect(EstimatePage({ params, searchParams: NO_SEARCH })).rejects.toBeInstanceOf(
      Unreachable,
    );
  });

  it("says the indicators unavailable when the API refuses them for a missing hourly rate", async () => {
    server.undeclared = {
      route: "/estimate-indicators",
      answer: () =>
        Response.json(
          { code: "HOURLY_RATE_MISSING", status: 422 },
          { status: 422, headers: { "content-type": "application/problem+json" } },
        ),
    };
    const html = renderToStaticMarkup(
      inEnglish(await EstimatePage({ params, searchParams: NO_SEARCH })),
    );
    expect(text(html)).toContain("The estimate indicators are unavailable.");
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
      /^Project Modernisation du poste de commande Modernisation du poste de commande Code PRJ-001/,
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

/** The addresses the links of a page lead to. */
function links(markup: string): string[] {
  return [...markup.matchAll(/href="([^"]*)"/g)].map((match) => match[1] ?? "");
}

describe("the empty states of the shell", () => {
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
      "Revisions This project has no revision yet. Go to the revisions of the project",
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

  it("never says there is no revision when the API cannot be reached: it is announced", async () => {
    server.unreachable = true;
    const page = ProjectPage({
      params: Promise.resolve({ projectId: PROJECT }),
      searchParams: NO_SEARCH,
    });
    await expect(page).rejects.toBeInstanceOf(Unreachable);
  });
});

describe("the rows a page hands its grid", () => {
  const params = Promise.resolve({ projectId: PROJECT, revisionId: REVISION });
  const VOLUME = "volume/nodes_thousand";

  beforeEach(() => {
    server.answers = {
      ...server.answers,
      "GET /projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes": VOLUME,
    };
  });

  /**
   * Check that each row a grid was handed holds the fields of its list that its node has — the
   * fields every grid reads and those of its columns —, and those alone, its facets alike.
   */
  function projected(items: readonly object[], fields: AnyNodeFields) {
    const answer = example(VOLUME) as NodeList;
    const listed = {
      node: [...COMMON_FIELDS.node, ...fields.node, "task", "estimate_line"],
      task: [...COMMON_FIELDS.task, ...fields.task],
      line: [...COMMON_FIELDS.line, ...fields.line],
    };
    const kept = (source: object, keys: readonly string[]) =>
      keys.filter((key) => key in source).sort();
    expect(items).toHaveLength(answer.items.length);
    for (const [index, node] of answer.items.entries()) {
      const row = items[index] ?? {};
      expect(Object.keys(row).sort()).toEqual(kept(node, listed.node));
      for (const left of ["lineage_id", "parent_id", "position"]) {
        expect(row).not.toHaveProperty(left);
      }
      const facets = row as { task?: object | null; estimate_line?: object | null };
      expect(Object.keys(facets.task ?? {}).sort()).toEqual(kept(node.task ?? {}, listed.task));
      expect(Object.keys(facets.estimate_line ?? {}).sort()).toEqual(
        kept(node.estimate_line ?? {}, listed.line),
      );
    }
  }

  it("the estimate asks for and hands its grid the fields it shows of each node, and those alone", async () => {
    renderToStaticMarkup(inEnglish(await EstimatePage({ params, searchParams: NO_SEARCH })));
    expect(nodesFields()).toEqual(nodeFieldNames(ESTIMATE_FIELDS));
    expect(grids.estimate).toHaveLength(1);
    projected(grids.estimate[0]?.nodes.items ?? [], ESTIMATE_FIELDS);
    expect(grids.estimate[0]?.structure).toEqual(STRUCTURE);
  });

  it("the planning asks for and hands its grid the fields it shows of each node, and those alone", async () => {
    renderToStaticMarkup(inEnglish(await PlanningPage({ params, searchParams: NO_SEARCH })));
    expect(nodesFields()).toEqual(nodeFieldNames(PLANNING_FIELDS));
    expect(grids.planning).toHaveLength(1);
    projected(grids.planning[0]?.nodes.items ?? [], PLANNING_FIELDS);
    expect(grids.planning[0]?.structure).toEqual(STRUCTURE);
  });
});
