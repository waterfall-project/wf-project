// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The aggregated workload of the portfolio (FBS-2.2, WF-PTF-0060), at the route of its function: by
 * role and by month, the load of the projects of the perimeter, the capacity of each role and the
 * rate of load, each month with the zone the server classes it in — overload and under-load alike
 * (WF-IHM-0070). The horizon and the threshold of under-load are parameters of the view, in the
 * address (`horizon_months`, `under_load_threshold`), never preferences kept from one consultation
 * to the next; the server reads them, the front computes nothing.
 */
import type { Metadata } from "next";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { PendingAddress } from "@/components/grid/pending-address";
import {
  HORIZON,
  HORIZONS,
  perimeterQuery,
  readChoice,
  readPerimeter,
  THRESHOLD,
  THRESHOLDS,
} from "@/components/portfolio/address";
import { PerimeterBar } from "@/components/portfolio/perimeter";
import { PortfolioHeader, portfolioLabel } from "@/components/portfolio/portfolio-header";
import { WorkloadView } from "@/components/portfolio/portfolio-views";
import { FUNCTION_DENSITY } from "@/components/shell/function-display";
import { Screen } from "@/components/shell/page-header";
import { type PageSearchParams, pageSearch } from "@/navigation/context";

import { screenMetadata } from "../../title";
import { readNodes } from "../nodes";

/** The aggregated workload takes no period, and a node of organisation. */
const TAKES = { period: false, node: true } as const;

/** Title the tab with the function. */
export function generateMetadata(): Promise<Metadata> {
  return screenMetadata(portfolioLabel("portfolio_workload"));
}

/** Render the aggregated workload of the portfolio, on the perimeter and the horizon asked. */
export default async function PortfolioWorkloadPage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const search = pageSearch(await searchParams);
  const perimeter = readPerimeter(search);
  const horizon = readChoice(search, HORIZON, HORIZONS);
  const threshold = readChoice(search, THRESHOLD, THRESHOLDS);
  const nodes = readNodes();
  const answer = await readOrFail("getPortfolioWorkload", () =>
    serverClient().GET("/portfolio/workload", {
      params: {
        query: {
          ...perimeterQuery(perimeter, TAKES),
          ...(horizon === undefined ? {} : { horizon_months: Number(horizon) }),
          ...(threshold === undefined ? {} : { under_load_threshold: threshold }),
        },
      },
    }),
  );
  return (
    <PendingAddress>
      <Screen density={FUNCTION_DENSITY.portfolio_workload}>
        <PortfolioHeader fn="portfolio_workload" scope={answer.scope} />
        <PerimeterBar
          perimeter={perimeter}
          retained={answer.scope.states}
          takes={TAKES}
          nodes={await nodes}
          view={{ horizon, threshold }}
        />
        <WorkloadView workload={answer} />
      </Screen>
    </PendingAddress>
  );
}
