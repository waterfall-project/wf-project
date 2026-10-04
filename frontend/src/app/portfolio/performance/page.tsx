// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The performance of the portfolio (FBS-2.3, WF-PTF-0070), at the route of its function: on the
 * projects in progress of the perimeter the address asks (WF-PTF-0010), the aggregated indices with
 * their zone, the cumulated variances, the three projections against the aggregated reference
 * budget, the distribution of the projects by zone of each index, and the evolution of the two
 * indices quarter by quarter — every figure as the server computes it, a ratio of sums
 * (WF-PTF-0020); the front computes nothing.
 */
import type { Metadata } from "next";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { PendingAddress } from "@/components/grid/pending-address";
import { perimeterQuery, readPerimeter } from "@/components/portfolio/address";
import { PerimeterBar } from "@/components/portfolio/perimeter";
import { QuarterlyChart } from "@/components/portfolio/portfolio-charts";
import { PerformanceView } from "@/components/portfolio/portfolio-views";
import { PortfolioHeader, portfolioLabel } from "@/components/portfolio/portfolio-header";
import { Screen } from "@/components/shell/page-header";
import { FUNCTION_DENSITY } from "@/components/shell/function-display";
import { type PageSearchParams, pageSearch } from "@/navigation/context";

import { screenMetadata } from "../../title";

/** Title the tab with the function. */
export function generateMetadata(): Promise<Metadata> {
  return screenMetadata(portfolioLabel("portfolio_performance"));
}

/** Render the performance of the portfolio, on the perimeter the address asks. */
export default async function PortfolioPerformancePage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const perimeter = readPerimeter(pageSearch(await searchParams));
  const answer = await readOrFail("getPortfolioPerformance", () =>
    serverClient().GET("/portfolio/performance", { params: { query: perimeterQuery(perimeter) } }),
  );
  return (
    <PendingAddress>
      <Screen density={FUNCTION_DENSITY.portfolio_performance}>
        <PortfolioHeader fn="portfolio_performance" scope={answer.scope} />
        <PerimeterBar perimeter={perimeter} retained={answer.scope.states} />
        <PerformanceView performance={answer} />
        <QuarterlyChart quarters={answer.quarterly} />
      </Screen>
    </PendingAddress>
  );
}
