// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PerimeterBarProps } from "@/components/portfolio/perimeter";
import type { ProjectsGridProps } from "@/components/portfolio/projects-grid";
import { CATALOGUES } from "@/i18n/catalogues";
import type { PageSearchParams } from "@/navigation/context";
import {
  example,
  type FakeAnswers,
  type FakeClient,
  fakeClient,
  type Problem,
} from "@/test/fixtures";
import { queryOfCall } from "@/test/queries";

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
// The perimeter bar renders as it would, and keeps what its page handed it.
const bars = vi.hoisted((): { props: PerimeterBarProps[] } => ({ props: [] }));
vi.mock("@/components/portfolio/perimeter", async (original) => {
  const actual = await original<typeof import("@/components/portfolio/perimeter")>();
  const { createElement } = await import("react");
  return {
    ...actual,
    PerimeterBar: (props: PerimeterBarProps) => {
      bars.props.push(props);
      return createElement(actual.PerimeterBar, props);
    },
  };
});
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => ({ push: () => undefined, refresh: () => undefined }),
  usePathname: () => "/portfolio/projects",
  useSearchParams: () => new URLSearchParams(),
}));
// The session of the contract, the sizes of pages its account keeps set for a test.
const kept = vi.hoisted(
  (): { grids: Record<string, { page_size?: number; filters?: Record<string, string> }> } => ({
    grids: {},
  }),
);
vi.mock("@/session/request", async (original) => {
  const actual = await original<typeof import("@/session/request")>();
  return {
    ...actual,
    requestSession: async () => {
      const session = await actual.requestSession();
      return session === undefined
        ? undefined
        : {
            ...session,
            display_preferences: {
              ...session.display_preferences,
              grids: { ...session.display_preferences?.grids, ...kept.grids },
            },
          };
    },
  };
});
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
  return queryOfCall(call?.query ?? []);
}

beforeEach(() => {
  kept.grids = {};
  grids.projects = [];
  bars.props = [];
  server.clients = [];
  server.answers = {
    "GET /me": "me",
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
      /Order book .*2,665,431,068\.05 Gross pipeline .*317,939,400\.00 Weighted pipeline .*146,660,510\.00 Delivered .*0\.00 Conversion rate 40%/,
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
    expect(page).toContain(
      "In progress · 269 projects · period from 4 Jun 2025 to 3 Jun 2026 · calculated on 3 Jun 2026",
    );
    expect(page).toMatch(/Cost index 0\.941 Nominal Schedule index 0\.9088 Nominal/);
    expect(page).toMatch(/At the observed rate .*2,832,594,354\.58 .*167,163,286\.53/);
    expect(page).toContain(
      "Cost index Nominal 169 Cost index Watch 47 Cost index Alert 53 Schedule index Nominal 152",
    );
    expect(page).toContain(
      "Q2 2025 Not computable — No actual cost at the calculation date. Not computable — No planned value at the calculation date. Q3 2025 Not computable — No actual cost at the calculation date. Not computable — No planned value at the calculation date.",
    );
  });

  it("presents the structure of the costs by nature and the labour by node, and no breakdown of the actual cost, over the period of the projects completed [WF-PTF-0010-A]", async () => {
    const page = text(await render(CostStructurePage, { from: "2025-01-01" }));
    expect(queryOf("GET /portfolio/cost-structure")).toEqual({ from: "2025-01-01" });
    expect(page).toContain("The actual cost is not broken down by nature");
    expect(page).toMatch(/Reference budget by nature .*Main-d'œuvre .*1,465,987,087\.43 55%/);
    expect(page).toMatch(/Labour by organisation node .*Bureau d'études électricité .*100%/);
  });

  it("opens the project of each of the heaviest risks, and fills the matrix [WF-PTF-0030-A]", async () => {
    const markup = await render(RisksPage);
    const page = text(markup);
    expect(page).toMatch(/Provisions of the identified risks .*104,325,697\.03/);
    expect(markup.match(/href="\/projects\/[\w-]+"/g)).toHaveLength(10);
    expect(markup).toContain(
      'href="/projects/01926f3a-7c00-7000-8000-000300000119">Extension de la sous-station — Grenoble</a>',
    );
    expect(page).toContain("Risk matrix");
    expect(markup).toContain("Export as PNG");
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
    expect(markup).toMatch(/733,321\.89 h.*?aria-label="Alert".*?111\.34%/);
    expect(text(markup)).toContain("Ingénieur électricien 658,654 h");
  });

  it("leads an address that names none of the horizon, the threshold and the node to those the account kept, the perimeter carried over [WF-PTF-0060-A]", async () => {
    kept.grids = {
      portfolio_workload: {
        filters: {
          horizon_months: "12",
          under_load_threshold: "0.5",
          org_node_id: TECHNICAL_DIRECTION,
        },
      },
    };
    const refusal = await render(WorkloadPage, { states: "completed" }).catch(
      (error: unknown) => error,
    );
    const { digest } = refusal as { digest: string };
    expect(digest).toContain("NEXT_REDIRECT");
    const target = digest.split(";")[2] ?? "";
    expect(target.split("?")[0]).toBe("/portfolio/workload");
    expect(Object.fromEntries(new URLSearchParams(target.split("?")[1]))).toEqual({
      horizon_months: "12",
      under_load_threshold: "0.5",
      org_node_id: TECHNICAL_DIRECTION,
      states: "completed",
    });
  });

  it("restores the settings the address leaves out, and keeps the one it names [WF-PTF-0060-A]", async () => {
    kept.grids = {
      portfolio_workload: { filters: { horizon_months: "12", under_load_threshold: "0.5" } },
    };
    const refusal = await render(WorkloadPage, { org_node_id: TECHNICAL_DIRECTION }).catch(
      (error: unknown) => error,
    );
    const target = (refusal as { digest: string }).digest.split(";")[2] ?? "";
    expect(Object.fromEntries(new URLSearchParams(target.split("?")[1]))).toEqual({
      horizon_months: "12",
      under_load_threshold: "0.5",
      org_node_id: TECHNICAL_DIRECTION,
    });
  });

  it("reads the address as it is when it names every setting, whatever the account kept [WF-PTF-0060-A]", async () => {
    kept.grids = { portfolio_workload: { filters: { horizon_months: "12" } } };
    await render(WorkloadPage, { horizon_months: "24", under_load_threshold: "0.3" });
    expect(queryOf("GET /portfolio/workload")).toEqual({
      horizon_months: "24",
      under_load_threshold: "0.3",
    });
  });

  it("asks no horizon, and restores none, for a horizon written empty, the default [WF-PTF-0060-A]", async () => {
    kept.grids = { portfolio_workload: { filters: { horizon_months: "12" } } };
    await render(WorkloadPage, { horizon_months: "" });
    expect(queryOf("GET /portfolio/workload")).toEqual({});
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

  it("asks the period of the projects completed for the S-curve, whatever its horizon, and keeps the horizon when the period is refused [WF-PTF-0010-A] [WF-PTF-0100-A]", async () => {
    await render(CostCurvePage, { states: "completed", from: "2025-01-01", horizon_months: "12" });
    expect(queryOf("GET /portfolio/cost-curve")).toEqual({
      states: "completed",
      from: "2025-01-01",
      horizon_months: "12",
    });
    server.answers = {
      ...server.answers,
      "GET /portfolio/cost-curve": {
        problem: example("portfolio_period_inverted") as Problem & { status: 422 },
      },
    };
    const markup = await render(CostCurvePage, {
      from: "2026-03-31",
      to: "2026-01-01",
      horizon_months: "12",
    });
    expect(text(markup)).toContain("The view is not read: the server refuses the period asked.");
    expect(markup).toContain('<option value="12" selected="">12 months</option>');
  });

  it("sends the horizon of the S-curve, lists the points of its three curves, and offers to read it as cash-out [WF-PTF-0100-A]", async () => {
    const markup = await render(CostCurvePage, { horizon_months: "24" });
    expect(queryOf("GET /portfolio/cost-curve")).toEqual({ horizon_months: "24" });
    const page = text(markup);
    expect(page).toContain("Cumulative costs of the portfolio");
    expect(page).toContain("Reference budget 31 Dec 2025 210,664,042.15");
    expect(page).toContain("Actual cost 3 Jun 2026 1,285,133,439.68");
    expect(page).toContain("Project manager’s projection 30 Nov 2026 2,143,620,318.36");
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
    expect(page).toContain("June 2026 19,713,579.42 31,417,246.57");
    expect(markup).toContain('href="/portfolio/cost-curve?horizon_months=24"');
    expect(page).toContain("Back to the cumulative costs");
  });

  it("presents the coverage of the risks of the portfolio, each sum as the server made it, the variance signed [WF-PTF-0090-A]", async () => {
    const page = text(await render(RisksPage));
    expect(page).toContain(
      "Risk coverage Reference reserve 103,703,525.80 Remaining provisions 104,325,697.03 Cost of the occurred risks 4,605,324.00 Coverage variance -5,227,495.23",
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
    [
      "cost structure",
      CostStructurePage,
      "GET /portfolio/cost-structure",
      { ...DATE, ...PERIOD, ...NODE },
    ],
    ["risks", RisksPage, "GET /portfolio/risks", { ...DATE, ...PERIOD }],
    [
      "workload",
      WorkloadPage,
      "GET /portfolio/workload",
      { ...DATE, ...NODE, horizon_months: "12", under_load_threshold: "0.4" },
    ],
    [
      "S-curve",
      CostCurvePage,
      "GET /portfolio/cost-curve",
      { ...DATE, ...PERIOD, horizon_months: "12" },
    ],
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

describe("the notice that a project completed has no effect", () => {
  it.each([
    ["the aggregated workload", WorkloadPage, "workload", ["in_progress", "pricing"]],
    ["the project control health", PilotHealthPage, "pilotHealth", ["in_progress"]],
  ] as const)(
    "is asked of the perimeter of %s on the states the server retained, none said while it retains no completed project [WF-PTF-0060-A] [WF-PTF-0110-A]",
    async (_view, page, view, states) => {
      const markup = await render(page);
      const [bar, ...more] = bars.props;
      expect(more).toEqual([]);
      expect(bar?.completedWithoutEffect).toBe(view);
      expect(bar?.retained).toEqual(states);
      expect(markup).not.toContain(CATALOGUES.en.portfolio.perimeter.completedWithoutEffect[view]);
    },
  );

  it.each([
    ["the projects", ProjectsPage],
    ["the performance", PerformancePage],
    ["the structure of the costs", CostStructurePage],
    ["the risks", RisksPage],
    ["the S-curve", CostCurvePage],
  ])("is not asked of the perimeter of %s [WF-PTF-0010-A]", async (_view, page) => {
    await render(page);
    expect(bars.props.map((bar) => bar.completedWithoutEffect)).toEqual([undefined]);
  });
});

describe("a period of the portfolio the server refuses", () => {
  const inverted = { problem: example("portfolio_period_inverted") as Problem & { status: 422 } };
  const period = { from: "2026-03-31", to: "2026-01-01" };

  /** The field of a side of the period, and what describes it. */
  function field(markup: string, value: string): { readonly tag: string; readonly said: string } {
    const tag = new RegExp(`<input[^>]*value="${value}"[^>]*>`).exec(markup)?.[0] ?? "";
    const described = /aria-describedby="([^"]+)"/.exec(tag)?.[1];
    const said =
      described === undefined
        ? ""
        : (new RegExp(`<p id="${described}"[^>]*>([^<]*)</p>`).exec(markup)?.[1] ?? "");
    return { tag, said };
  }

  it.each([
    ["the projects", ProjectsPage, "GET /portfolio/projects" as const],
    ["the value", ProjectsPage, "GET /portfolio/value" as const],
    ["the performance", PerformancePage, "GET /portfolio/performance" as const],
    ["the risks", RisksPage, "GET /portfolio/risks" as const],
    ["the structure of the costs", CostStructurePage, "GET /portfolio/cost-structure" as const],
    ["the S-curve", CostCurvePage, "GET /portfolio/cost-curve" as const],
  ])(
    "says at the field of its end the period %s are refused for, the start named, the view unread and the perimeter kept",
    async (_view, page, route) => {
      server.answers = { ...server.answers, [route]: inverted };
      const markup = await render(page, period);
      const end = field(markup, "2026-01-01");
      expect(end.tag).toContain('aria-invalid="true"');
      expect(end.said).toBe("The end of the period may not precede its start, 31 Mar 2026.");
      expect(field(markup, "2026-03-31").tag).not.toContain("aria-invalid");
      expect(text(markup)).toContain("The view is not read: the server refuses the period asked.");
      expect(markup).not.toContain('role="grid"');
      // No state named, nothing says what is retained: the filter by state is not offered, which
      // would restrict the perimeter to one state in silence.
      expect(markup).not.toContain('aria-label="States retained"');
    },
  );

  it("presses in the filter by state of a view refused the states the address names, as it asks them", async () => {
    server.answers = { ...server.answers, "GET /portfolio/performance": inverted };
    const markup = await render(PerformancePage, { ...period, states: "in_progress,completed" });
    const group = markup.slice(markup.indexOf('aria-label="States retained"'));
    const pressed = [
      ...group.matchAll(/<button[^>]*aria-pressed="(true|false)"[^>]*>(.*?)<\/button>/g),
    ]
      .slice(0, 3)
      .map((match) => [text(match[2] ?? ""), match[1]]);
    expect(pressed).toEqual([
      ["In progress", "true"],
      ["Pricing", "false"],
      ["Completed", "true"],
    ]);
  });

  it("says at the field of its start a start the server refuses for following the end it completed the period with, the end named", async () => {
    server.answers = {
      ...server.answers,
      "GET /portfolio/performance": {
        problem: example("portfolio_open_period_inverted") as Problem & { status: 422 },
      },
    };
    const markup = await render(PerformancePage, { from: "2026-09-01" });
    const start = field(markup, "2026-09-01");
    expect(start.tag).toContain('aria-invalid="true"');
    expect(start.said).toBe(
      "The start of the period may not follow its default end, the date of calculation, 3 Jun 2026.",
    );
    expect(text(markup)).toContain("The view is not read: the server refuses the period asked.");
  });
});

describe("the portfolio, the size of the pages of the list of projects", () => {
  it.each([
    ["no preference", {}, "50"],
    ["a page size of 25", { limit: "25" }, "25"],
  ])("sends %s as the limit of its reading [WF-IHM-0060-A]", async (_name, search, limit) => {
    await render(ProjectsPage, search);
    const call = server.clients
      .flatMap((client) => client.calls)
      .find((each) => each.route === "GET /portfolio/projects");
    expect(Object.fromEntries(call?.query ?? []).limit).toBe(limit);
  });

  it("reads the page size kept by the account when the address asks none [WF-IHM-0060-A]", async () => {
    kept.grids = { portfolio_projects: { page_size: 25 } };
    await render(ProjectsPage, {});
    const call = server.clients
      .flatMap((client) => client.calls)
      .find((each) => each.route === "GET /portfolio/projects");
    expect(Object.fromEntries(call?.query ?? []).limit).toBe("25");
  });
});
