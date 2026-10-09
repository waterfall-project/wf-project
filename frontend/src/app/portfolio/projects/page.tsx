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
 * front computes, sorts, filters and pages nothing. A period the API refuses — an end before the
 * start — is said at its field, the view unread (`RefusedView`); any other read the API refuses, or
 * cannot answer, is thrown for the pages of the shell to say.
 */
import type { Metadata } from "next";

import { serverClient } from "@/api/server";
import { readPage } from "@/components/costs/address";
import { ListPages } from "@/components/grid/list-pages";
import { PendingAddress } from "@/components/grid/pending-address";
import { OFFSET, readGridQuery } from "@/components/grid/query";
import {
  type Perimeter,
  perimeterQuery,
  portfolioProjectsQuery,
  PROJECTS_LIST,
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
import { readView, RefusedView } from "../refused";

/** Title the tab with the function. */
export function generateMetadata(): Promise<Metadata> {
  return screenMetadata(portfolioLabel("portfolio_projects"));
}

/** The value of the portfolio on the perimeter asked. */
function readValue(perimeter: Perimeter) {
  return readView("getPortfolioValue", () =>
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
    readView("getPortfolioProjects", () =>
      serverClient().GET("/portfolio/projects", {
        params: {
          query: portfolioProjectsQuery({ perimeter, zones, offset, query }),
        },
      }),
    ),
    readValue(perimeter),
    readNodes(),
    settings,
  ]);
  // Both read on the same period: refused by either, the view is not read.
  if (projects.kind === "refused" || value.kind === "refused") {
    const refused = projects.kind === "refused" ? projects.refused : undefined;
    return (
      <PendingAddress>
        <RefusedView
          fn="portfolio_projects"
          perimeter={perimeter}
          refused={refused ?? (value.kind === "refused" ? value.refused : undefined)}
          nodes={nodes}
        />
      </PendingAddress>
    );
  }
  return (
    // The perimeter, the grid and the pages compose the changes they make to the address.
    <PendingAddress>
      <Screen density="dense" fill>
        <PortfolioHeader fn="portfolio_projects" scope={projects.data.scope} />
        <PerimeterBar perimeter={perimeter} retained={projects.data.scope.states} nodes={nodes} />
        <PortfolioValueView value={value.data} />
        <div className="flex min-h-0 flex-1 flex-col gap-2">
          <ZoneFilter zones={zones} />
          <ProjectsGrid
            projects={projects.data.items}
            page={projects.data.meta}
            query={query}
            preferences={preferences}
          />
          <ListPages
            list={PROJECTS_LIST}
            texts="portfolio.pages"
            page={projects.data.meta}
            shown={projects.data.items.length}
          />
        </div>
      </Screen>
    </PendingAddress>
  );
}
