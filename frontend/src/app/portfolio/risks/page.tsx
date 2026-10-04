// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The risks of the portfolio (FBS-2.5, WF-PTF-0090), at the route of its function: on the perimeter
 * the address asks, the total of the provisions of the risks identified, the heaviest of them with
 * their project, which they open, the matrix the portfolio fills, and the provisions of the risks
 * that occurred against those dismissed over the period — as the server computes them.
 */
import type { Metadata } from "next";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { PendingAddress } from "@/components/grid/pending-address";
import { perimeterQuery, readPerimeter } from "@/components/portfolio/address";
import { PerimeterBar } from "@/components/portfolio/perimeter";
import { PortfolioRisksView } from "@/components/portfolio/portfolio-views";
import { PortfolioHeader, portfolioLabel } from "@/components/portfolio/portfolio-header";
import { Screen } from "@/components/shell/page-header";
import { FUNCTION_DENSITY } from "@/components/shell/function-display";
import { type PageSearchParams, pageSearch } from "@/navigation/context";

import { screenMetadata } from "../../title";

/** Title the tab with the function. */
export function generateMetadata(): Promise<Metadata> {
  return screenMetadata(portfolioLabel("portfolio_risks"));
}

/** Render the risks of the portfolio, on the perimeter the address asks. */
export default async function PortfolioRisksPage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const perimeter = readPerimeter(pageSearch(await searchParams));
  const answer = await readOrFail("getPortfolioRisks", () =>
    serverClient().GET("/portfolio/risks", { params: { query: perimeterQuery(perimeter) } }),
  );
  return (
    <PendingAddress>
      <Screen density={FUNCTION_DENSITY.portfolio_risks}>
        <PortfolioHeader fn="portfolio_risks" scope={answer.scope} />
        <PerimeterBar perimeter={perimeter} retained={answer.scope.states} />
        <PortfolioRisksView risks={answer} />
      </Screen>
    </PendingAddress>
  );
}
