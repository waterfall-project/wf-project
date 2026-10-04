// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The health of the steering of the portfolio (FBS-2.7, WF-PTF-0110), at the route of its function:
 * the signals of the projects in progress whose review is overdue, whose risks were not reviewed,
 * whose actual costs were not imported, or whose contractual milestone is passed, each with the zone
 * the server classes it in (WF-IHM-0070) and its project, which it opens.
 */
import type { Metadata } from "next";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { PendingAddress } from "@/components/grid/pending-address";
import { perimeterQuery, readPerimeter } from "@/components/portfolio/address";
import { PerimeterBar } from "@/components/portfolio/perimeter";
import { PilotHealthView } from "@/components/portfolio/portfolio-views";
import { PortfolioHeader, portfolioLabel } from "@/components/portfolio/portfolio-header";
import { Screen } from "@/components/shell/page-header";
import { FUNCTION_DENSITY } from "@/components/shell/function-display";
import { type PageSearchParams, pageSearch } from "@/navigation/context";

import { screenMetadata } from "../../title";

/** The health of the steering takes neither a period nor a node of organisation. */
const TAKES = { period: false, node: false } as const;

/** Title the tab with the function. */
export function generateMetadata(): Promise<Metadata> {
  return screenMetadata(portfolioLabel("portfolio_pilot_health"));
}

/** Render the health of the steering of the portfolio, on the perimeter the address asks. */
export default async function PortfolioPilotHealthPage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const perimeter = readPerimeter(pageSearch(await searchParams));
  const answer = await readOrFail("getPortfolioPilotHealth", () =>
    serverClient().GET("/portfolio/pilot-health", {
      params: { query: perimeterQuery(perimeter, TAKES) },
    }),
  );
  return (
    <PendingAddress>
      <Screen density={FUNCTION_DENSITY.portfolio_pilot_health}>
        <PortfolioHeader fn="portfolio_pilot_health" scope={answer.scope} />
        <PerimeterBar perimeter={perimeter} retained={answer.scope.states} takes={TAKES} />
        <PilotHealthView health={answer} />
      </Screen>
    </PendingAddress>
  );
}
