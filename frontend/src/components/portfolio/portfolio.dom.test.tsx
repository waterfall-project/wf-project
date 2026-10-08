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
import { ROW_REM } from "@/components/grid/dense-grid";
import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { expectAccessible } from "@/test/axe";
import { roomForCharts } from "@/test/chart-room";
import { example, fakeClient } from "@/test/fixtures";

import { type Perimeter, readPerimeter, type Takes } from "./address";

import { type NodeChoice, PerimeterBar, type ViewParameters } from "./perimeter";
import { CashOutChart, monthAfter, PortfolioCurveChart, QuarterlyChart } from "./portfolio-charts";
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
/** The height of a row of the grid, as the grid computes it on the default font of the browsers. */
const ROW_HEIGHT = ROW_REM * 16;
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
  code: node.code,
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

// Each drawing has the room a page gives it: ECharts measures it as it draws.
roomForCharts();

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
      "Écart à la référence",
      "Indice de coût",
      "Indice de délai",
      "Dernière révision marquée",
    ]);
    const witness = cellsOf("PRJ-001");
    expect(witness[2]).toHaveTextContent("En cours");
    // The indices of the witness, both nominal; the schedule index of another in alert, by its
    // shape.
    expect(within(witness[8] ?? document.body).getByRole("img", { name: "Nominal" })).toBeVisible();
    expect(within(witness[9] ?? document.body).getByRole("img", { name: "Nominal" })).toBeVisible();
    const lyon = cellsOf("PRJ-003");
    expect(within(lyon[9] ?? document.body).getByRole("img", { name: "Alerte" })).toBeVisible();
  });

  it("says an index the API cannot compute not computable, its reason seen once", () => {
    // The witness as its reference was marked, before any actual cost: its cost index not
    // computable (project_indicators_marked).
    const marked = example("project_indicators_marked") as Schemas["ProjectIndicators"];
    render(
      projectsGrid({
        ...LIST,
        items: LIST.items.map((project) =>
          project.code === "PRJ-001" ? { ...project, cost_index: marked.cost_index } : project,
        ),
      }),
    );
    const witness = cellsOf("PRJ-001");
    expect(witness[8]).toHaveTextContent("Non calculable — Aucun coût réel à la date de calcul.");
    // Its reason seen, in a secondary text, and read once: no title would describe it again.
    const reason = within(witness[8] ?? document.body).getByText(/Aucun coût réel/);
    expect(reason).not.toHaveClass("sr-only");
    expect(witness[8]?.querySelector("[title], [aria-describedby]")).toBeNull();
    expect(witness[8]?.textContent.match(/Aucun coût réel/g)).toHaveLength(1);
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

  it("says in its totals row how many projects the server retained, never a count of the page, and is accessible", async () => {
    // A window of two rows — some fourteen rendered, with the overscan of the grid —: the rules of
    // axe hold for each row alike, and a screenful took as long to check as to render — past its
    // time under load (#315).
    vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(2 * ROW_HEIGHT);
    const { container } = render(projectsGrid(PAGE));
    expect(PAGE.items).toHaveLength(50);
    expect(within(grid()).getAllByRole("row").at(-1)).toHaveTextContent("300 projets retenus");
    await expectAccessible(container);
  });

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
      "Réalisé et taux de transformation sur la période du 4 juin 2025 au 3 juin 2026",
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
      "DT · Direction technique",
      "\u2003BE-ELEC · Bureau d'études électricité",
      "\u2003\u2003AT-CABL · Atelier de câblage",
      "\u2003ACHATS · Service des achats",
    ]);
    await userEvent.selectOptions(node, "\u2003BE-ELEC · Bureau d'études électricité");
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
    render(
      inLanguage(
        <QuarterlyChart quarters={performance.quarterly} scope={performance.scope} />,
        "en",
      ),
    );
    const figure = screen.getByRole("figure", { name: "Quarterly evolution of the indices" });
    const rows = within(figure).getAllByRole("row");
    expect(rows.map((row) => row.textContent)).toEqual([
      "QuarterCost indexSchedule index",
      "Q3 2025Not computable — No actual cost at the calculation date.Not computable — No planned value at the calculation date.",
      "Q4 20250.940.93",
      expect.stringMatching(/^Q1 2026/),
      "Q2 20260.940.91",
    ]);
  });

  it("lists the points of the three curves of the S-curve, as the server summed them [WF-PTF-0100-A]", () => {
    const curves = example("portfolio_cost_curve") as Schemas["PortfolioCostCurve"];
    charts.props = [];
    render(inLanguage(<PortfolioCurveChart curves={curves} scope={curves.scope} />));
    const figure = screen.getByRole("figure", { name: "Coûts cumulés du portefeuille" });
    const rows = within(figure).getAllByRole("row");
    expect(rows[0]).toHaveTextContent("CourbeDateMontant");
    expect(rows[1]).toHaveTextContent(
      `Budget de référence31 déc. 2025210${NARROW}664${NARROW}042,15`,
    );
    expect(rows).toHaveLength(1 + 12 + 7 + 7);
    expect(rows.at(-1)).toHaveTextContent(
      `Projection du chef de projet30 nov. 20262${NARROW}130${NARROW}889${NARROW}768,69`,
    );
    // Three curves in the order of the API, the actual cost by steps, the others by lines; an axis
    // of amounts that reaches down to the lowest value drawn.
    const option = charts.props.at(-1)?.option(PALETTE);
    const series = [option?.series].flat() as { name: string; step?: string }[];
    expect(series.map((each) => [each.name, each.step])).toEqual([
      ["Budget de référence", undefined],
      ["Coût réel", "end"],
      ["Projection du chef de projet", undefined],
    ]);
    expect(option?.yAxis).not.toHaveProperty("min");
  });

  it("names the S-curve read as cash-out as the server says it is", () => {
    const curves = example("portfolio_cost_curve_payment_delays") as Schemas["PortfolioCostCurve"];
    render(inLanguage(<PortfolioCurveChart curves={curves} scope={curves.scope} />, "en"));
    expect(
      screen.getByRole("figure", { name: "Cumulative cash-out of the portfolio" }),
    ).toBeInTheDocument();
  });

  it("lists each month of cash-out, the past and the forecast", () => {
    const cashOut = example("portfolio_cost_curve_payment_delays") as Schemas["PortfolioCostCurve"];
    render(
      inLanguage(<CashOutChart months={cashOut.cash_out_by_month ?? []} scope={cashOut.scope} />),
    );
    const figure = screen.getByRole("figure", { name: "Décaissements par mois" });
    // The month of the calculation bears both: what was spent up to it, what is to come after.
    expect(within(figure).getByRole("row", { name: /juin 2026/ })).toHaveTextContent(
      `juin 202619${NARROW}586${NARROW}542,9530${NARROW}743${NARROW}434,03`,
    );
  });

  it("ends the step of the last month at the first of the next", () => {
    expect(monthAfter("2026-09")).toBe("2026-10");
    expect(monthAfter("2026-12")).toBe("2027-01");
  });

  it("draws the last month of each part to the first of the next, unmarked, on an axis that runs there", () => {
    const curves = example("portfolio_cost_curve_payment_delays") as Schemas["PortfolioCostCurve"];
    const months = curves.cash_out_by_month ?? [];
    charts.props = [];
    render(inLanguage(<CashOutChart months={months} scope={curves.scope} />));
    const option = charts.props.at(-1)?.option(PALETTE);
    const last = months.at(-1);
    const series = [option?.series].flat() as { data: unknown[] }[];
    expect(series.map((each) => each.data.at(-1))).toEqual([
      { value: ["2026-12-01T00:00:00Z", last?.past], symbol: "none" },
      { value: ["2026-12-01T00:00:00Z", last?.forecast], symbol: "none" },
    ]);
    // The axis is that of the months alone, whose ticks run past the first of the month after
    // the latest already: the end of the last step is not added to them.
    const ticks = monthTicks(
      months.map((month) => planningInstant(month.month)),
      true,
    );
    expect(option?.xAxis).toMatchObject({ min: ticks[0], max: ticks.at(-1) });
    expect(ticks.at(-1)).toBeGreaterThanOrEqual(Date.UTC(2026, 11, 1));
  });

  it("reaches down to a month of net negative cash-out, where the indices start from zero", () => {
    const credit = example("portfolio_cost_curve_credit") as Schemas["PortfolioCostCurve"];
    const performance = example("volume/portfolio_performance") as Schemas["PortfolioPerformance"];
    charts.props = [];
    render(
      inLanguage(<CashOutChart months={credit.cash_out_by_month ?? []} scope={credit.scope} />),
    );
    render(
      inLanguage(<QuarterlyChart quarters={performance.quarterly} scope={performance.scope} />),
    );
    const [cashOut, quarterly] = charts.props.map((props) => props.option(PALETTE));
    expect(cashOut?.yAxis).not.toHaveProperty("min");
    expect(quarterly?.yAxis).toMatchObject({ min: 0 });
    const figure = screen.getByRole("figure", { name: "Décaissements par mois" });
    expect(within(figure).getByRole("row", { name: /décembre 2025/ })).toHaveTextContent(
      `-2${NARROW}546${NARROW}166,40`,
    );
  });

  it("exports each chart as a PNG image that names the perimeter the server retained and its date of calculation (#312)", () => {
    const performance = example("volume/portfolio_performance") as Schemas["PortfolioPerformance"];
    const curves = example("portfolio_cost_curve_payment_delays") as Schemas["PortfolioCostCurve"];
    const value = example("volume/portfolio_value") as { scope: Schemas["PortfolioScope"] };
    const workload = example("portfolio_workload_org_node") as Schemas["PortfolioWorkload"];
    charts.props = [];
    render(inLanguage(<QuarterlyChart quarters={performance.quarterly} scope={value.scope} />));
    render(inLanguage(<PortfolioCurveChart curves={curves} scope={workload.scope} />));
    render(
      inLanguage(
        <CashOutChart months={curves.cash_out_by_month ?? []} scope={curves.scope} />,
        "en",
      ),
    );
    expect(charts.props.map((props) => props.exported?.())).toEqual([
      {
        title: "Évolution trimestrielle des indices du portefeuille",
        subtitle: `En cours et Chiffrage · 300${NARROW}projets · période du 4 juin 2025 au 3 juin 2026 · calculé au 3 juin 2026`,
        fileName: "evolution-des-indices-portefeuille-2026-06-03.png",
      },
      {
        title: "Décaissements cumulés du portefeuille",
        subtitle: `En cours et Chiffrage · 300${NARROW}projets · calculé au 3 juin 2026 · Main-d’œuvre de Direction technique et de ses descendants`,
        fileName: "decaissements-cumules-portefeuille-2026-06-03.png",
      },
      {
        title: "Cash-out of the portfolio by month",
        subtitle: "In progress and Pricing · 300 projects · calculated on 3 Jun 2026",
        fileName: "cash-out-by-month-portfolio-2026-06-03.png",
      },
    ]);
    expect(
      screen.getAllByRole("button", { name: /^(Exporter en PNG|Export as PNG)$/ }),
    ).toHaveLength(3);
  });
});
