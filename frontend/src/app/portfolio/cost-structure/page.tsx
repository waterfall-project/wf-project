// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The structure of the costs of the portfolio (FBS-2.4, WF-PTF-0080), at the route of its function:
 * the breakdown by nature of the aggregated reference budget and remaining to commit, in amount and
 * in share, and the labour by node of organisation, as the server computes them at the date the
 * address asks; never a breakdown of the actual cost by nature, which the ERP does not give.
 */
import type { Metadata } from "next";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { PendingAddress } from "@/components/grid/pending-address";
import { perimeterQuery, readPerimeter } from "@/components/portfolio/address";
import { PerimeterBar } from "@/components/portfolio/perimeter";
import { CostStructureView } from "@/components/portfolio/portfolio-views";
import { PortfolioHeader, portfolioLabel } from "@/components/portfolio/portfolio-header";
import { Screen } from "@/components/shell/page-header";
import { FUNCTION_DENSITY } from "@/components/shell/function-display";
import { type PageSearchParams, pageSearch } from "@/navigation/context";

import { screenMetadata } from "../../title";
import { readNodes } from "../nodes";

/** The structure of the costs takes no period, and a node of organisation. */
const TAKES = { period: false, node: true } as const;

/** Title the tab with the function. */
export function generateMetadata(): Promise<Metadata> {
  return screenMetadata(portfolioLabel("portfolio_cost_structure"));
}

/** Render the structure of the costs of the portfolio, on the perimeter the address asks. */
export default async function PortfolioCostStructurePage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const perimeter = readPerimeter(pageSearch(await searchParams));
  const [answer, nodes] = await Promise.all([
    readOrFail("getPortfolioCostStructure", () =>
      serverClient().GET("/portfolio/cost-structure", {
        params: { query: perimeterQuery(perimeter, TAKES) },
      }),
    ),
    readNodes(),
  ]);
  return (
    <PendingAddress>
      <Screen density={FUNCTION_DENSITY.portfolio_cost_structure}>
        <PortfolioHeader fn="portfolio_cost_structure" scope={answer.scope} />
        <PerimeterBar
          perimeter={perimeter}
          retained={answer.scope.states}
          takes={TAKES}
          nodes={nodes}
        />
        <CostStructureView structure={answer} />
      </Screen>
    </PendingAddress>
  );
}
