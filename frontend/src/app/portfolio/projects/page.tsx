// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The portfolio of projects (FBS-2.1), at the route of its function (`functions.json`): the value
 * of the portfolio (WF-PTF-0050) and the list of its projects (WF-PTF-0040), on the perimeter the
 * address asks (WF-PTF-0010) — the states, the period, the date of calculation, the node of
 * organisation, under the names of the contract, the nodes offered as the reference gives them —;
 * the list is a page of the projects the server retained, sorted, searched and paged as the
 * address asks (`sort_by`, `sort_order`, `search`, `offset`), and filtered on the zones of their
 * indices it names (`zones`, #313). Every figure as the API gives it: the
 * front computes, sorts, filters and pages nothing. A read the API refuses, or cannot answer, is
 * thrown for the pages of the shell to say.
 */
import type { Metadata } from "next";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { readPage } from "@/components/costs/address";
import { ListPages } from "@/components/costs/cost-pages";
import { PendingAddress } from "@/components/grid/pending-address";
import { OFFSET, readGridQuery } from "@/components/grid/query";
import {
  type Perimeter,
  perimeterQuery,
  readPerimeter,
  readZones,
} from "@/components/portfolio/address";
import { PerimeterBar } from "@/components/portfolio/perimeter";
import { PortfolioHeader, portfolioLabel } from "@/components/portfolio/portfolio-header";
import { PROJECT_GRID, PROJECT_SORT_COLUMNS } from "@/components/portfolio/portfolio-grid";
import { PortfolioValueView } from "@/components/portfolio/portfolio-value";
import { ProjectsGrid } from "@/components/portfolio/projects-grid";
import { ZoneFilter } from "@/components/portfolio/zone-filter";
import { Screen } from "@/components/shell/page-header";
import { type PageSearchParams, pageSearch } from "@/navigation/context";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../title";
import { readNodes } from "../nodes";

/** Title the tab with the function. */
export function generateMetadata(): Promise<Metadata> {
  return screenMetadata(portfolioLabel("portfolio_projects"));
}

/** The value of the portfolio on the perimeter asked. */
function readValue(perimeter: Perimeter) {
  return readOrFail("getPortfolioValue", () =>
    serverClient().GET("/portfolio/value", { params: { query: perimeterQuery(perimeter) } }),
  );
}

/** Render the value of the portfolio and the list of its projects. */
export default async function PortfolioProjectsPage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const search = pageSearch(await searchParams);
  const perimeter = readPerimeter(search);
  const offset = readPage(search, OFFSET);
  const zones = readZones(search);
  const settings = requestSession().then(
    (session) => session?.user.display_preferences?.grids?.[PROJECT_GRID.key] ?? undefined,
  );
  const query = await settings.then((kept) =>
    readGridQuery(search, PROJECT_SORT_COLUMNS, kept?.sort),
  );
  const [projects, value, nodes, preferences] = await Promise.all([
    readOrFail("getPortfolioProjects", () =>
      serverClient().GET("/portfolio/projects", {
        params: {
          query: {
            ...perimeterQuery(perimeter),
            ...(zones.length === 0 ? {} : { zones: [...zones] }),
            ...(offset === 0 ? {} : { offset }),
            ...(query.search === undefined ? {} : { search: query.search }),
            ...(query.sort === undefined
              ? {}
              : { sort_by: query.sort.column, sort_order: query.sort.order }),
          },
        },
      }),
    ),
    readValue(perimeter),
    readNodes(),
    settings,
  ]);
  return (
    // The perimeter, the grid and the pages compose the changes they make to the address.
    <PendingAddress>
      <Screen density="dense" fill>
        <PortfolioHeader fn="portfolio_projects" scope={projects.scope} />
        <PerimeterBar perimeter={perimeter} retained={projects.scope.states} nodes={nodes} />
        <PortfolioValueView value={value} />
        <div className="flex min-h-0 flex-1 flex-col gap-2">
          <ZoneFilter zones={zones} />
          <ProjectsGrid
            projects={projects.items}
            page={projects.meta}
            query={query}
            preferences={preferences}
          />
          <ListPages list="projects" page={projects.meta} shown={projects.items.length} />
        </div>
      </Screen>
    </PendingAddress>
  );
}
