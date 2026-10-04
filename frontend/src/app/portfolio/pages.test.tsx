// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ProjectsGridProps } from "@/components/portfolio/projects-grid";
import { CATALOGUES } from "@/i18n/catalogues";
import type { PageSearchParams } from "@/navigation/context";
import { type FakeAnswers, type FakeClient, fakeClient } from "@/test/fixtures";

import ProjectsPage, { generateMetadata as projectsTitle } from "./projects/page";

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
  };
});

describe("the screens of the portfolio", () => {
  it("titles the tab with the function", async () => {
    expect((await projectsTitle()).title).toBe("Project portfolio — Waterfall");
  });

  it("offers the nodes of organisation, each named with its parent as the reference gives it", async () => {
    const markup = await render(ProjectsPage, { org_node_id: DESIGN_OFFICE });
    expect(markup).toContain(
      `<option value="${DESIGN_OFFICE}" selected="">Bureau d&#x27;études électricité (Direction technique)</option>`,
    );
    expect(markup).toContain(">Direction technique</option>");
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
    });
    const perimeter = {
      states: "in_progress,pricing",
      from: "2025-01-01",
      as_of: "2026-03-16",
      org_node_id: DESIGN_OFFICE,
    };
    expect(queryOf("GET /portfolio/projects")).toEqual({
      ...perimeter,
      offset: "50",
      search: "poste",
      sort_by: "cost_index",
      sort_order: "desc",
    });
    expect(queryOf("GET /portfolio/value")).toEqual(perimeter);
  });

  it("presents the value of the portfolio and its perimeter, the date it is computed at, and hands the list to the grid", async () => {
    const page = text(await render(ProjectsPage));
    expect(page).toContain("In progress and Pricing · 300 projects · calculated on 16 Mar 2026");
    expect(page).toMatch(
      /Order book .*2,597,289,500\.00 Gross pipeline .*317,939,400\.00 Weighted pipeline .*146,660,510\.00 Delivered .*0\.00 Conversion rate 40%/,
    );
    const [grid] = grids.projects;
    expect(grid?.projects).toHaveLength(300);
    expect(grid?.page.total).toBe(300);
  });

  it("says a list that retains no project empty", async () => {
    server.answers = { ...server.answers, "GET /portfolio/projects": "portfolio_projects_empty" };
    const page = text(await render(ProjectsPage, { states: "completed" }));
    expect(page).toContain("Completed · no project · calculated on 16 Mar 2026");
    expect(grids.projects[0]?.projects).toEqual([]);
  });
});
