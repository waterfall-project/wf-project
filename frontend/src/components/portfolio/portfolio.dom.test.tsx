// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { render, screen, waitFor, within } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api/generated/schema";
import type { ApiClient } from "@/api/client";
import { PendingAddress } from "@/components/grid/pending-address";
import { CATALOGUES } from "@/i18n/catalogues";
import type { Locale } from "@/i18n/locale";
import { example, fakeClient } from "@/test/fixtures";

import { type Perimeter, readPerimeter, type Takes } from "./address";

import { type NodeChoice, PerimeterBar, type ViewParameters } from "./perimeter";
import { CashOutChart, monthAfter, QuarterlyChart } from "./portfolio-charts";
import type { ProjectPage, ProjectRow } from "./portfolio-grid";
import { ProjectsGrid } from "./projects-grid";

// The server of Next, as far as the screen needs it: the preferences it writes, the address it
// reads.
const server = vi.hoisted((): { client: ApiClient | undefined } => ({ client: undefined }));
const router = vi.hoisted(() => ({ push: vi.fn(), refresh: vi.fn() }));
const page = vi.hoisted(() => ({ search: "" }));
const PATHNAME = "/portfolio/projects";

vi.mock("@/api/server", () => ({ serverClient: () => server.client }));
vi.mock("next/navigation", async (original) => ({
  ...(await original<typeof import("next/navigation")>()),
  useRouter: () => router,
  usePathname: () => PATHNAME,
  useSearchParams: () => new URLSearchParams(page.search),
}));

type Schemas = components["schemas"];

/** The projects of the portfolio the fake back serves: three hundred, in one page. */
const LIST = example("volume/portfolio_projects") as {
  readonly scope: Schemas["PortfolioScope"];
  readonly items: ProjectRow[];
  readonly meta: ProjectPage;
};
const NARROW = " ";

/** A part of the screen, in a language, under the address of the screen. */
function inLanguage(children: ReactNode, locale: Locale = "fr") {
  return (
    <NextIntlClientProvider locale={locale} messages={CATALOGUES[locale]} timeZone="UTC">
      <PendingAddress>{children}</PendingAddress>
    </NextIntlClientProvider>
  );
}

/** The grid of the projects, as the page hands it the list. */
function projectsGrid() {
  return inLanguage(
    <ProjectsGrid
      projects={LIST.items}
      page={LIST.meta}
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

/** Two nodes of organisation, the second under the first, as the reference names them. */
const NODES: readonly NodeChoice[] = [
  { id: "node-470", label: "Direction technique", parent: null },
  { id: "node-471", label: "Bureau d’études électricité", parent: "Direction technique" },
];

/** The perimeter bar of a view, the address at `search`. */
function perimeterBar(
  search: string,
  takes: Takes = { period: true, node: false },
  view?: ViewParameters,
) {
  page.search = search;
  const perimeter: Perimeter = readPerimeter(new URLSearchParams(search));
  return inLanguage(
    <PerimeterBar
      perimeter={perimeter}
      retained={["in_progress", "pricing"]}
      takes={takes}
      nodes={NODES}
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
    expect(witness[8]).toHaveTextContent("Non calculable");
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

  it("says in its totals row how many projects the server retained, never a count of the page", () => {
    render(projectsGrid());
    expect(within(grid()).getAllByRole("row").at(-1)).toHaveTextContent("300 projets retenus");
  });

  it("asks the server to sort by the cost index, and to search the labels", async () => {
    render(projectsGrid());
    const heading = within(grid()).getByRole("columnheader", { name: /Indice de coût/ });
    await userEvent.click(within(heading).getByRole("button"));
    expect(await lastAddress()).toBe(`${PATHNAME}?sort_by=cost_index&sort_order=asc`);
  });
});

describe("the perimeter of a view of the portfolio", () => {
  it("shows the states the server retained when the address asks none, and adds one to them", async () => {
    render(perimeterBar(""));
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

  it("restricts the labour to a node of organisation, named with its parent; the date alone where the view takes no period", async () => {
    render(perimeterBar("", { period: false, node: true }));
    expect(screen.queryByLabelText("Du")).toBeNull();
    const node = screen.getByLabelText("Nœud d’organisation");
    expect(
      within(node)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual([
      "Tous les nœuds",
      "Direction technique",
      "Bureau d’études électricité (Direction technique)",
    ]);
    await userEvent.selectOptions(node, "Bureau d’études électricité (Direction technique)");
    expect(await lastAddress()).toBe(`${PATHNAME}?org_node_id=node-471`);
  });

  it("offers the horizon and the threshold of a view", async () => {
    render(
      perimeterBar("", { period: false, node: false }, { horizon: undefined, threshold: "0.5" }),
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
});
