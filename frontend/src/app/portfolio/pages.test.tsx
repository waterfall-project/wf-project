// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ProjectsGridProps } from "@/components/portfolio/projects-grid";
import { CATALOGUES } from "@/i18n/catalogues";
import type { PageSearchParams } from "@/navigation/context";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import CostCurvePage, { generateMetadata as costCurveTitle } from "./cost-curve/page";
import CostStructurePage, { generateMetadata as costStructureTitle } from "./cost-structure/page";
import PerformancePage, { generateMetadata as performanceTitle } from "./performance/page";
import PilotHealthPage, { generateMetadata as pilotHealthTitle } from "./pilot-health/page";
import ProjectsPage, { generateMetadata as projectsTitle } from "./projects/page";
import RisksPage, { generateMetadata as risksTitle } from "./risks/page";
import WorkloadPage, { generateMetadata as workloadTitle } from "./workload/page";

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
const grids = vi.hoisted((): { projects: ProjectsGridProps[] } => ({ projects: [] }));
vi.mock("@/components/portfolio/projects-grid", async (original) => {
  const actual = await original<typeof import("@/components/portfolio/projects-grid")>();
  const { createElement } = await import("react");
  return {
    ...actual,
    ProjectsGrid: (props: ProjectsGridProps) => {
      grids.projects.push(props);
      return createElement(actual.ProjectsGrid, props);
    },
  };
});
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/portfolio/projects",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/headers", () => ({
  headers: () => Promise.resolve(new Headers({ "accept-language": "en-GB" })),
}));

const DESIGN_OFFICE = "01926f3a-7c00-7000-8000-000000000471";
const TECHNICAL_DIRECTION = "01926f3a-7c00-7000-8000-000000000470";
const WITNESS = "/projects/01926f3a-7c00-7000-8000-000000000001";

/** A page of the portfolio, as Next renders it with the query of its address. */
type PortfolioPage = (props: { searchParams: Promise<PageSearchParams> }) => Promise<unknown>;

/** What a page says, its tags left out: the texts a reader reads, one space apart. */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, " ")
    .replace(/&#x27;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

/** Render a page of the portfolio in English, at the query given. */
async function render(page: PortfolioPage, search: PageSearchParams = {}) {
  const element = await page({ searchParams: Promise.resolve(search) });
  return renderToStaticMarkup(
    <NextIntlClientProvider locale="en" messages={CATALOGUES.en} timeZone="UTC">
      {element as ReactNode}
    </NextIntlClientProvider>,
  );
}

/** The query of the one call the pages made to an operation. */
function queryOf(route: string): Record<string, string> {
  const calls = server.clients.flatMap((client) => client.calls);
  const [call, ...more] = calls.filter((each) => each.route === route);
  expect(more).toEqual([]);
  return Object.fromEntries(call?.query ?? []);
}

beforeEach(() => {
  grids.projects = [];
  server.clients = [];
  server.answers = {
    "GET /session": "session",
    "GET /portfolio/projects": "volume/portfolio_projects",
    "GET /portfolio/value": "volume/portfolio_value",
    "GET /reference/org-nodes": "org_nodes",
    "GET /portfolio/performance": "volume/portfolio_performance",
    "GET /portfolio/cost-structure": "volume/portfolio_cost_structure",
    "GET /portfolio/risks": "volume/portfolio_risks",
    "GET /portfolio/workload": "portfolio_workload",
    "GET /portfolio/cost-curve": "portfolio_cost_curve",
    "GET /portfolio/pilot-health": "pilot_health",
  };
});

describe("the screens of the portfolio", () => {
  it.each([
    [projectsTitle, "Project portfolio"],
    [workloadTitle, "Aggregated workload"],
    [performanceTitle, "Portfolio performance"],
    [costStructureTitle, "Portfolio cost structure"],
    [risksTitle, "Portfolio risks"],
    [costCurveTitle, "Portfolio S-curve"],
    [pilotHealthTitle, "Project control health"],
  ])("titles the tab with the function", async (title: () => Promise<Metadata>, name) => {
    expect((await title()).title).toBe(`${name} — Waterfall`);
  });

  it("offers the nodes of organisation as the tree the reference orders, a node retaining its descendants", async () => {
    const markup = await render(ProjectsPage, { org_node_id: DESIGN_OFFICE });
    expect(markup).toContain(
      `<option value="${DESIGN_OFFICE}" selected="">\u2003BE-ELEC · Bureau d&#x27;études électricité</option>`,
    );
    expect(markup).toContain(">DT · Direction technique</option>");
    expect(markup).toContain(">\u2003\u2003AT-CABL · Atelier de câblage</option>");
    expect(text(markup)).toContain("Organisation node and its descendants");
  });

  it("asks the list and the value on the perimeter, the sort, the search and the page of the address", async () => {
    await render(ProjectsPage, {
      states: "in_progress,pricing,lost",
      from: "2025-01-01",
      to: "2025-02-30",
      as_of: "2026-03-16",
      sort_by: "cost_index",
      sort_order: "desc",
      search: "poste",
      offset: "50",
      org_node_id: DESIGN_OFFICE,
      zones: "alert,nominal,unknown",
    });
    const perimeter = {
      states: "in_progress,pricing",
      from: "2025-01-01",
      as_of: "2026-03-16",
      org_node_id: DESIGN_OFFICE,
    };
    expect(queryOf("GET /portfolio/projects")).toEqual({
      ...perimeter,
      zones: "nominal,alert",
      offset: "50",
      search: "poste",
      sort_by: "cost_index",
      sort_order: "desc",
    });
    expect(queryOf("GET /portfolio/value")).toEqual(perimeter);
  });

  it("presents the value of the portfolio and its perimeter, the date it is computed at, and hands the list to the grid", async () => {
    const page = text(await render(ProjectsPage));
    expect(page).toContain("In progress and Pricing · 300 projects · calculated on 3 Jun 2026");
    expect(page).toMatch(
      /Order book .*2,597,310,034\.56 Gross pipeline .*317,939,400\.00 Weighted pipeline .*146,660,510\.00 Delivered .*0\.00 Conversion rate 40%/,
    );
    const [grid] = grids.projects;
    expect(grid?.projects).toHaveLength(300);
    expect(grid?.page.total).toBe(300);
  });

  it("says a list that retains no project empty", async () => {
    server.answers = { ...server.answers, "GET /portfolio/projects": "portfolio_projects_empty" };
    const page = text(await render(ProjectsPage, { states: "completed" }));
    expect(page).toContain("Completed · no project · calculated on 3 Jun 2026");
    expect(grids.projects[0]?.projects).toEqual([]);
  });
  it("presents the aggregated indices with their zone, the projections, and the projects by zone [WF-IHM-0070-A]", async () => {
    const markup = await render(PerformancePage, { as_of: "2026-06-03" });
    expect(queryOf("GET /portfolio/performance")).toEqual({ as_of: "2026-06-03" });
    const page = text(markup);
    expect(page).toContain("In progress · 269 projects · calculated on 3 Jun 2026");
    expect(page).toMatch(/Cost index 0\.94 Nominal Schedule index 0\.91 Nominal/);
    expect(page).toMatch(/At the observed rate .*2,760,474,046\.69 .*163,164,012\.13/);
    expect(page).toContain(
      "Cost index Nominal 169 Cost index Watch 47 Cost index Alert 53 Schedule index Nominal 153",
    );
    expect(page).toContain(
      "Q3 2025 Not computable — No actual cost at the calculation date. Not computable — No planned value at the calculation date.",
    );
  });

  it("presents the structure of the costs by nature and the labour by node, and no breakdown of the actual cost", async () => {
    const page = text(await render(CostStructurePage, { from: "2025-01-01" }));
    expect(queryOf("GET /portfolio/cost-structure")).toEqual({});
    expect(page).toContain("The actual cost is not broken down by nature");
    expect(page).toMatch(/Reference budget by nature .*Main-d'œuvre .*1,428,520,519\.01 55%/);
    expect(page).toMatch(/Labour by organisation node .*Bureau d'études électricité .*100%/);
  });

  it("opens the project of each of the heaviest risks, and fills the matrix [WF-PTF-0030-A]", async () => {
    const markup = await render(RisksPage);
    const page = text(markup);
    expect(page).toMatch(/Provisions of the identified risks .*103,826,197\.03/);
    expect(markup.match(/href="\/projects\/[\w-]+"/g)).toHaveLength(10);
    expect(markup).toContain(
      'href="/projects/01926f3a-7c00-7000-8000-000300000119">Extension de la sous-station — Grenoble</a>',
    );
    expect(page).toContain("Risk matrix");
    // The cell of the highest probability and severity, by its signal and its count.
    expect(markup).toMatch(/aria-label="Alert"(?:(?!<\/td>)[\s\S])*?<\/span>32<\/span>/);
  });

  it("signals a month of a role over its capacity, and sends the horizon and the threshold chosen [WF-PTF-0060-A]", async () => {
    const markup = await render(WorkloadPage, {
      horizon_months: "12",
      under_load_threshold: "0.5",
      from: "2025-01-01",
    });
    expect(queryOf("GET /portfolio/workload")).toEqual({
      horizon_months: "12",
      under_load_threshold: "0.5",
    });
    expect(markup).toMatch(/730,721\.95 h.*?aria-label="Alert".*?110\.94%/);
    expect(text(markup)).toContain("Ingénieur électricien 658,654 h");
  });

  it("heads its columns with the months of the horizon, and names the node the server retained", async () => {
    server.answers = {
      ...server.answers,
      "GET /portfolio/workload": "portfolio_workload_org_node",
    };
    const page = text(await render(WorkloadPage, { org_node_id: TECHNICAL_DIRECTION }));
    expect(page).toContain("Labour of Direction technique and of its descendants");
    expect(page).toContain(
      "Role Monthly capacity June 2026 July 2026 August 2026 September 2026 October 2026 November 2026 Ingénieur",
    );
  });

  it("shows the threshold of under-load the server retained when the address names none", async () => {
    const markup = await render(WorkloadPage);
    expect(queryOf("GET /portfolio/workload")).toEqual({});
    expect(markup).toContain('<option value="0.5" selected="">50%</option>');
  });

  it("asks any horizon the contract takes, and shows it chosen", async () => {
    const markup = await render(CostCurvePage, { horizon_months: "36" });
    expect(queryOf("GET /portfolio/cost-curve")).toEqual({ horizon_months: "36" });
    expect(markup).toContain('<option value="36" selected="">36 months</option>');
  });

  it("stands without a node to choose when the API does not find the nodes of organisation", async () => {
    server.answers = {
      ...server.answers,
      "GET /reference/org-nodes": { problem: { code: "NOT_FOUND", status: 404 } },
    };
    const markup = await render(ProjectsPage);
    expect(text(markup)).toMatch(/Order book .*2,597,310,034\.56/);
    expect(grids.projects[0]?.projects).toHaveLength(300);
    expect(markup).not.toContain("Organisation node");
  });

  it("stands without a node to choose on a view that takes one, when the API does not find the nodes", async () => {
    server.answers = {
      ...server.answers,
      "GET /reference/org-nodes": { problem: { code: "NOT_FOUND", status: 404 } },
    };
    const markup = await render(PerformancePage);
    expect(text(markup)).toMatch(/Cost index 0\.94 Nominal/);
    expect(markup).not.toContain("Organisation node");
  });

  it("sends the horizon of the S-curve, lists the points of its three curves, and offers to read it as cash-out [WF-PTF-0100-A]", async () => {
    const markup = await render(CostCurvePage, { horizon_months: "24" });
    expect(queryOf("GET /portfolio/cost-curve")).toEqual({ horizon_months: "24" });
    const page = text(markup);
    expect(page).toContain("Cumulative costs of the portfolio");
    expect(page).toContain("Reference budget 31 Dec 2025 210,664,042.15");
    expect(page).toContain("Actual cost 3 Jun 2026 1,283,825,869.48");
    expect(page).toContain("Project manager’s projection 30 Nov 2026 2,130,889,768.69");
    // Without the payment delays, the server details no cash-out: no second chart.
    expect(page).not.toContain("Cash-out by month");
    expect(markup).toContain(
      'href="/portfolio/cost-curve?horizon_months=24&amp;payment_delays=true"',
    );
    expect(page).toContain("Read as cash-out");
  });

  it("asks the S-curve as cash-out when the address says so, and lists the cash-out by month the server details [WF-PTF-0100-A]", async () => {
    server.answers = {
      ...server.answers,
      "GET /portfolio/cost-curve": "portfolio_cost_curve_payment_delays",
    };
    const markup = await render(CostCurvePage, { horizon_months: "24", payment_delays: "true" });
    expect(queryOf("GET /portfolio/cost-curve")).toEqual({
      horizon_months: "24",
      payment_delays: "true",
    });
    const page = text(markup);
    expect(page).toContain("Cumulative cash-out of the portfolio");
    expect(page).toContain("Cash-out by month");
    expect(page).toContain("June 2026 19,586,542.95 30,743,434.03");
    expect(markup).toContain('href="/portfolio/cost-curve?horizon_months=24"');
    expect(page).toContain("Back to the cumulative costs");
  });

  it("presents the coverage of the risks of the portfolio, each sum as the server made it, the variance signed [WF-PTF-0090-A]", async () => {
    const page = text(await render(RisksPage));
    expect(page).toContain(
      "Risk coverage Reference reserve 102,854,375.80 Remaining provisions 103,826,197.03 Cost of the occurred risks 4,605,324.00 Coverage variance -5,577,145.23",
    );
  });

  it("opens the project of each signal of the health of the steering, by its zone [WF-PTF-0030-A] [WF-IHM-0070-A]", async () => {
    const markup = await render(PilotHealthPage);
    // The witness is signalled its review overdue alone; a milestone overdue is another's.
    expect(markup.match(new RegExp(`href="${WITNESS}"`, "g"))).toHaveLength(1);
    const page = text(markup);
    expect(page).toMatch(/Periodic review overdue .*Watch/);
    expect(page).toMatch(/Contractual milestone overdue .*Alert/);
  });

  it("says what each signal of the health of the steering names, as the server gives it", async () => {
    const page = text(await render(PilotHealthPage));
    expect(page).toContain("Periodic review overdue 17 weeks since the last marked revision Watch");
    expect(page).toContain(
      "Contractual milestone overdue Réception usine, reference date 30 Apr 2026 Alert",
    );
  });
  // The whole perimeter asked, and what each view sends of it, as its operation takes it.
  const ASKED = {
    states: "in_progress,pricing",
    from: "2025-01-01",
    to: "2025-12-31",
    as_of: "2026-06-03",
    org_node_id: DESIGN_OFFICE,
    horizon_months: "12",
    under_load_threshold: "0.4",
  };
  const DATE = { states: ASKED.states, as_of: ASKED.as_of };
  const PERIOD = { from: ASKED.from, to: ASKED.to };
  const NODE = { org_node_id: DESIGN_OFFICE };
  it.each([
    ["performance", PerformancePage, "GET /portfolio/performance", { ...DATE, ...PERIOD, ...NODE }],
    ["cost structure", CostStructurePage, "GET /portfolio/cost-structure", { ...DATE, ...NODE }],
    ["risks", RisksPage, "GET /portfolio/risks", { ...DATE, ...PERIOD }],
    [
      "workload",
      WorkloadPage,
      "GET /portfolio/workload",
      { ...DATE, ...NODE, horizon_months: "12", under_load_threshold: "0.4" },
    ],
    ["S-curve", CostCurvePage, "GET /portfolio/cost-curve", { ...DATE, horizon_months: "12" }],
    ["health of the steering", PilotHealthPage, "GET /portfolio/pilot-health", DATE],
  ] as const)(
    "sends of the perimeter what the %s takes, and that alone",
    async (_view, page: PortfolioPage, route, expected) => {
      await render(page, ASKED);
      expect(queryOf(route)).toEqual(expected);
    },
  );

  it("says the period of the statistics of the value, as the server retained it", async () => {
    const page = text(await render(ProjectsPage));
    expect(page).toContain(
      "Delivered and conversion rate over the period from 4 Jun 2025 to 3 Jun 2026",
    );
  });
});
