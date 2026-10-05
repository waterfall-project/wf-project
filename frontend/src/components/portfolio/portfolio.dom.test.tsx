// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import type { ApiClient } from "@/api/client";
import {
  type ChartPalette,
  type ChartProps,
  monthTicks,
  planningInstant,
} from "@/components/chart/chart";
import { ListPages } from "@/components/costs/cost-pages";
import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";
import { example, fakeClient } from "@/test/fixtures";

import { type Perimeter, readPerimeter, type Takes } from "./address";

import { type NodeChoice, PerimeterBar, type ViewParameters } from "./perimeter";
import { CashOutChart, monthAfter, QuarterlyChart } from "./portfolio-charts";
import type { ProjectPage, ProjectRow } from "./portfolio-grid";
import { PortfolioValueView } from "./portfolio-value";
import { ProjectsGrid } from "./projects-grid";

// The server of Next, as far as the screen needs it: the preferences it writes, the address it
// reads.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));
const PATHNAME = "/portfolio/projects";

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
// The charts render as they would, and keep what they were handed: their option among it.
const charts = vi.hoisted((): { props: ChartProps[] } => ({ props: [] }));
vi.mock("@/components/chart/chart", async (original) => {
  const actual = await original<typeof import("@/components/chart/chart")>();
  const { createElement } = await import("react");
  return {
    ...actual,
    Chart: (props: ChartProps) => {
      charts.props.push(props);
      return createElement(actual.Chart, props);
    },
  };
});
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => PATHNAME,
  useSearchParams: () => new URLSearchParams(page.search),
}));

type Schemas = components["schemas"];

/** A list of the projects of the portfolio, as the server answers it. */
interface ProjectList {
  readonly scope: Schemas["PortfolioScope"];
  readonly items: ProjectRow[];
  readonly meta: ProjectPage;
}

/** The projects of the portfolio the fake back serves: three hundred, in one page. */
const LIST = example("volume/portfolio_projects") as ProjectList;
/** Its second page of fifty, as the server pages it. */
const PAGE = example("volume/portfolio_projects_page") as ProjectList;
const NARROW = " ";
/** The colours and the font a chart is drawn in, as the probes would read them. */
const PALETTE: ChartPalette = {
  series: ["rgb(1, 1, 1)", "rgb(2, 2, 2)"],
  text: "rgb(3, 3, 3)",
  mark: "rgb(4, 4, 4)",
  axis: "rgb(5, 5, 5)",
  grid: "rgb(6, 6, 6)",
  background: "rgb(7, 7, 7)",
  font: "sans-serif",
};

/** A part of the screen, in a language, under the address of the screen. */
function inLanguage(children: ReactNode, locale: Locale = "fr") {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <PendingAddress>{children}</PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The grid of the projects, as the page hands it a list. */
function projectsGrid(list: ProjectList = LIST) {
  return inLanguage(
    <ProjectsGrid
      projects={list.items}
      page={list.meta}
      query={{ sort: undefined, search: undefined }}
      preferences={undefined}
    />,
  );
}

/** The grid of the projects. */
function grid(): HTMLElement {
  return screen.getByRole("grid", { name: "Projets du portefeuille" });
}

/** The cells of the row of a project, by its code. */
function cellsOf(code: string): HTMLElement[] {
  const row = within(grid())
    .getAllByRole("row")
    .find((candidate) =>
      [...candidate.querySelectorAll("td")].some((cell) => cell.textContent === code),
    );
  return [...(row?.querySelectorAll("td") ?? [])];
}

/** The nodes of organisation of the reference, as the page hands them to the perimeter. */
const NODES: readonly NodeChoice[] = (example("org_nodes") as Schemas["OrgNode"][]).map((node) => ({
  id: node.org_node_id,
  label: node.label,
  level: node.level,
}));
const DESIGN_OFFICE = "01926f3a-7c00-7000-8000-000000000471";

/** The perimeter bar of a view, the address at `search`. */
function perimeterBar(
  search: string,
  takes: Takes = { period: true, node: false },
  nodes: readonly NodeChoice[] = NODES,
  view?: ViewParameters,
) {
  page.search = search;
  const perimeter: Perimeter = readPerimeter(new URLSearchParams(search));
  return inLanguage(
    <PerimeterBar
      perimeter={perimeter}
      retained={LIST.scope.states}
      takes={takes}
      nodes={nodes}
      {...(view === undefined ? {} : { view })}
    />,
  );
}

/** The address the last navigation asked for. */
async function lastAddress(): Promise<string> {
  await waitFor(() => {
    expect(router.push).toHaveBeenCalled();
  });
  return String(router.push.mock.lastCall?.[0]);
}

beforeEach(() => {
  router.push.mockReset();
  page.search = "";
  server.client = fakeClient({ "PATCH /me/preferences": "preferences" });
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(560);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1400);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("the list of the projects of the portfolio", () => {
  it("presents each column the requirement names, the indices with their zone [WF-PTF-0040-A]", () => {
    render(projectsGrid());
    expect(
      within(grid())
        .getAllByRole("columnheader")
        .map((header) => header.textContent),
    ).toEqual([
      "Libellé",
      "Code",
      "État",
      "Budget de référence",
      "Devis courant",
      "Probabilité de gain",
      "Projection du chef de projet",
      "Écart au budget",
      "Indice de coût",
      "Indice de délai",
      "Dernière révision marquée",
    ]);
    const witness = cellsOf("PRJ-001");
    expect(witness[2]).toHaveTextContent("En cours");
    // The cost index of the witness is not computable, the schedule index in alert, by its shape.
    expect(witness[8]).toHaveTextContent("Non calculable — Aucun coût réel à la date de calcul.");
    expect(within(witness[9] ?? document.body).getByRole("img", { name: "Alerte" })).toBeVisible();
    expect(witness[9]).toHaveTextContent("0");
  });

  it("shows the estimate and the probability of an offer where a project in progress shows its budget [WF-PTF-0040-A]", () => {
    render(projectsGrid());
    const offer = cellsOf("PRJ-010");
    expect(offer[2]).toHaveTextContent("Chiffrage");
    expect(offer[3]?.textContent).toBe("");
    expect(offer[4]).toHaveTextContent(`4${NARROW}596${NARROW}900,00`);
    expect(offer[5]).toHaveTextContent("30 %");
    const progressing = cellsOf("PRJ-003");
    expect(progressing[3]).toHaveTextContent(`4${NARROW}570${NARROW}900,00`);
    expect(progressing[4]?.textContent).toBe("");
    expect(progressing[7]).toHaveTextContent(`502${NARROW}799,00`);
  });

  it("opens each project from its label [WF-PTF-0030-A]", () => {
    render(projectsGrid());
    expect(
      within(grid()).getByRole("link", { name: "Modernisation du poste de commande" }),
    ).toHaveAttribute("href", "/projects/01926f3a-7c00-7000-8000-000000000001");
  });

  it(
    "says in its totals row how many projects the server retained, never a count of the page, and is accessible",
    { timeout: 15_000 },
    async () => {
      const { container } = render(projectsGrid(PAGE));
      expect(PAGE.items).toHaveLength(50);
      expect(within(grid()).getAllByRole("row").at(-1)).toHaveTextContent("300 projets retenus");
      await expectAccessible(container);
    },
  );

  it("asks the server to sort by the cost index", async () => {
    render(projectsGrid());
    const heading = within(grid()).getByRole("columnheader", { name: /Indice de coût/ });
    await userEvent.click(within(heading).getByRole("button"));
    expect(await lastAddress()).toBe(`${PATHNAME}?sort_by=cost_index&sort_order=asc`);
  });

  it("asks the server to search the labels, back to the first page", async () => {
    page.search = "sort_by=label&offset=50";
    render(projectsGrid(PAGE));
    const search = screen.getByRole("search", { name: "Rechercher un libellé" });
    await userEvent.type(within(search).getByRole("searchbox"), "poste{Enter}");
    expect(await lastAddress()).toBe(`${PATHNAME}?sort_by=label&search=poste`);
  });

  it("leads to the pages before and after the one shown, from the address", () => {
    page.search = "states=in_progress&offset=50";
    render(inLanguage(<ListPages list="projects" page={PAGE.meta} shown={PAGE.items.length} />));
    const pages = screen.getByRole("navigation", { name: "Pages des projets" });
    expect(within(pages).getByRole("link", { name: /Projets précédents/ })).toHaveAttribute(
      "href",
      `${PATHNAME}?states=in_progress`,
    );
    expect(within(pages).getByRole("link", { name: /Projets suivants/ })).toHaveAttribute(
      "href",
      `${PATHNAME}?states=in_progress&offset=100`,
    );
  });
});

describe("the value of the portfolio", () => {
  it("says the period its statistics are computed on, and is accessible", async () => {
    const value = example("volume/portfolio_value") as Schemas["PortfolioValue"];
    const { container } = render(inLanguage(<PortfolioValueView value={value} />));
    const section = screen.getByRole("region", { name: "Valeur du portefeuille" });
    expect(section).toHaveTextContent(
      "Réalisé et taux de transformation sur la période du 17 mars 2025 au 16 mars 2026",
    );
    expect(section).toHaveTextContent("Taux de transformation40 %");
    await expectAccessible(container);
  });
});

describe("the perimeter of a view of the portfolio", () => {
  it("shows the states the server retained when the address asks none, and adds one to them", async () => {
    const { container } = render(perimeterBar("", { period: true, node: true }));
    await expectAccessible(container);
    const states = screen.getByRole("group", { name: "États retenus" });
    expect(within(states).getByRole("button", { name: "En cours" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(within(states).getByRole("button", { name: "Terminé" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    await userEvent.click(within(states).getByRole("button", { name: "Terminé" }));
    expect(await lastAddress()).toBe(`${PATHNAME}?states=in_progress%2Cpricing%2Ccompleted`);
  });

  it("keeps the last state retained, which cannot be released", async () => {
    render(perimeterBar("states=pricing"));
    const last = screen.getByRole("button", { name: "Chiffrage" });
    expect(last).toHaveAttribute("aria-pressed", "true");
    expect(last).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("button", { name: "En cours" })).not.toHaveAttribute("aria-disabled");
    await userEvent.click(last);
    expect(router.push).not.toHaveBeenCalled();
  });

  it("removes a state the address asks, back to the first page, the sort kept", async () => {
    render(perimeterBar("states=in_progress,pricing&sort_by=label&offset=50"));
    await userEvent.click(screen.getByRole("button", { name: "Chiffrage" }));
    expect(await lastAddress()).toBe(`${PATHNAME}?states=in_progress&sort_by=label`);
  });

  it("asks the period and the date of calculation together", async () => {
    render(perimeterBar("from=2025-01-01"));
    const form = screen.getByRole("form", { name: "Période et date de calcul" });
    expect(within(form).getByLabelText("Du")).toHaveValue("2025-01-01");
    await userEvent.type(within(form).getByLabelText("Calculé au"), "2026-03-16");
    await userEvent.click(within(form).getByRole("button", { name: "Appliquer" }));
    expect(await lastAddress()).toBe(`${PATHNAME}?from=2025-01-01&as_of=2026-03-16`);
  });

  it("never lets the period start after its end", () => {
    render(perimeterBar("from=2025-01-01&to=2025-12-31"));
    const form = screen.getByRole("form", { name: "Période et date de calcul" });
    expect(within(form).getByLabelText("Du")).toHaveAttribute("max", "2025-12-31");
    expect(within(form).getByLabelText("Au")).toHaveAttribute("min", "2025-01-01");
  });

  it("keeps shown a node the address filters on when no node can be read, to be cleared", async () => {
    render(perimeterBar(`org_node_id=${DESIGN_OFFICE}`, { period: false, node: true }, []));
    const node = screen.getByLabelText("Nœud d’organisation et ses descendants");
    expect(node).toHaveValue(DESIGN_OFFICE);
    await userEvent.selectOptions(node, "Tous les nœuds");
    expect(await lastAddress()).toBe(PATHNAME);
  });

  it("restricts the labour to a node of organisation and its descendants, offered as the tree; the date alone where the view takes no period", async () => {
    render(perimeterBar("", { period: false, node: true }));
    expect(screen.queryByLabelText("Du")).toBeNull();
    const node = screen.getByLabelText("Nœud d’organisation et ses descendants");
    expect(
      within(node)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual([
      "Tous les nœuds",
      "Direction technique",
      "\u2003Bureau d'études électricité",
      "\u2003\u2003Atelier de câblage",
      "\u2003Service des achats",
    ]);
    await userEvent.selectOptions(node, "\u2003Bureau d'études électricité");
    expect(await lastAddress()).toBe(`${PATHNAME}?org_node_id=${DESIGN_OFFICE}`);
  });

  it("offers the horizon and the threshold of a view", async () => {
    render(
      perimeterBar("", { period: false, node: false }, NODES, {
        horizon: undefined,
        threshold: "0.5",
      }),
    );
    expect(screen.getByLabelText("Seuil de sous-charge")).toHaveValue("0.5");
    await userEvent.selectOptions(screen.getByLabelText("Horizon"), "12 mois");
    expect(await lastAddress()).toBe(`${PATHNAME}?horizon_months=12`);
  });
});

describe("the charts of the portfolio", () => {
  it("lists the two indices of each quarter, as the server computes them", () => {
    const performance = example("volume/portfolio_performance") as Schemas["PortfolioPerformance"];
    render(inLanguage(<QuarterlyChart quarters={performance.quarterly} />, "en"));
    const figure = screen.getByRole("figure", { name: "Quarterly evolution of the indices" });
    const rows = within(figure).getAllByRole("row");
    expect(rows.map((row) => row.textContent)).toEqual([
      "QuarterCost indexSchedule index",
      "Q2 2025Not computable — No actual cost at the calculation date.Not computable — No planned value at the calculation date.",
      "Q3 20250.950.96",
      expect.stringMatching(/^Q4 2025/),
      "Q1 20260.940.91",
    ]);
  });

  it("lists each month of cash-out, the past and the forecast", () => {
    const cashOut = example("portfolio_cash_out") as Schemas["PortfolioCashOut"];
    render(inLanguage(<CashOutChart months={cashOut.months} />));
    const figure = screen.getByRole("figure", { name: "Décaissements par mois" });
    expect(within(figure).getByRole("row", { name: /mars 2026/ })).toHaveTextContent(
      `mars 202631${NARROW}864${NARROW}205,1038${NARROW}215${NARROW}760,00`,
    );
  });

  it("ends the step of the last month at the first of the next", () => {
    expect(monthAfter("2026-09")).toBe("2026-10");
    expect(monthAfter("2026-12")).toBe("2027-01");
  });

  it("draws the last month of each part to the first of the next, unmarked, on an axis that runs there", () => {
    const cashOut = example("portfolio_cash_out") as Schemas["PortfolioCashOut"];
    charts.props = [];
    render(inLanguage(<CashOutChart months={cashOut.months} />));
    const option = charts.props.at(-1)?.option(PALETTE);
    const last = cashOut.months.at(-1);
    const series = [option?.series].flat() as { data: unknown[] }[];
    expect(series.map((each) => each.data.at(-1))).toEqual([
      { value: ["2026-10-01T00:00:00Z", last?.past], symbol: "none" },
      { value: ["2026-10-01T00:00:00Z", last?.forecast], symbol: "none" },
    ]);
    // The axis is that of the months alone, whose ticks run past the first of the month after
    // the latest already: the end of the last step is not added to them.
    const ticks = monthTicks(
      cashOut.months.map((month) => planningInstant(month.month)),
      true,
    );
    expect(option?.xAxis).toMatchObject({ min: ticks[0], max: ticks.at(-1) });
    expect(ticks.at(-1)).toBeGreaterThanOrEqual(Date.UTC(2026, 9, 1));
  });

  it("reaches down to a month of net negative cash-out, where the indices start from zero", () => {
    const credit = example("portfolio_cash_out_credit") as Schemas["PortfolioCashOut"];
    const performance = example("volume/portfolio_performance") as Schemas["PortfolioPerformance"];
    charts.props = [];
    render(inLanguage(<CashOutChart months={credit.months} />));
    render(inLanguage(<QuarterlyChart quarters={performance.quarterly} />));
    const [cashOut, quarterly] = charts.props.map((props) => props.option(PALETTE));
    expect(cashOut?.yAxis).not.toHaveProperty("min");
    expect(quarterly?.yAxis).toMatchObject({ min: 0 });
    const figure = screen.getByRole("figure", { name: "Décaissements par mois" });
    expect(within(figure).getByRole("row", { name: /décembre 2025/ })).toHaveTextContent(
      `-1${NARROW}840${NARROW}250,00`,
    );
  });
});
