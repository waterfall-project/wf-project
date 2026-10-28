// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The aggregated workload of the portfolio (FBS-2.2, WF-PTF-0060), at the route of its function: by
 * role and by month, the load of the projects of the perimeter, the capacity of each role and the
 * rate of load, each month with the zone the server classes it in — overload and under-load alike
 * (WF-IHM-0070). The horizon and the threshold of under-load are parameters of the view, in the
 * address (`horizon_months`, `under_load_threshold`), as the node of organisation of its perimeter
 * (`org_node_id`): the three are display preferences kept from one consultation to the next, as the
 * settings of a grid are (WF-PTF-0060-A, WF-IHM-0060) — a setting the address leaves out is
 * restored, by the address that names it (`restoredWorkload`) —; the server reads them, the front
 * computes nothing.
 * A threshold the address does not name shows as the server retained it.
 */
import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { PendingAddress } from "@/components/grid/pending-address";
import {
  perimeterQuery,
  readHorizon,
  readPerimeter,
  readThreshold,
} from "@/components/portfolio/address";
import { KeptWorkload } from "@/components/portfolio/kept-workload";
import {
  restoredWorkload,
  WORKLOAD_KEPT,
  WORKLOAD_KEY,
} from "@/components/portfolio/kept-workload-address";
import { PerimeterBar } from "@/components/portfolio/perimeter";
import { PortfolioHeader, portfolioLabel } from "@/components/portfolio/portfolio-header";
import { WorkloadView } from "@/components/portfolio/portfolio-views";
import { FUNCTION_DENSITY } from "@/components/shell/function-display";
import { Screen } from "@/components/shell/page-header";
import { type PageSearchParams, pageSearch } from "@/navigation/context";
import { requestSession } from "@/session/request";

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
  const [search, session] = await Promise.all([
    searchParams.then((asked) => pageSearch(asked)),
    requestSession(),
  ]);
  const preferences = session?.display_preferences?.grids?.[WORKLOAD_KEY] ?? undefined;
  // A setting the address leaves out, and that is kept: restored before anything is read.
  const restored = restoredWorkload(search, preferences?.filters);
  if (restored !== undefined) {
    redirect(restored);
  }
  const perimeter = readPerimeter(search);
  const horizon = readHorizon(search);
  const threshold = readThreshold(search);
  const [answer, nodes] = await Promise.all([
    readOrFail("getPortfolioWorkload", () =>
      serverClient().GET("/portfolio/workload", {
        params: {
          query: {
            ...perimeterQuery(perimeter, TAKES),
            ...(horizon === undefined ? {} : { horizon_months: Number(horizon) }),
            ...(threshold === undefined ? {} : { under_load_threshold: threshold }),
          },
        },
      }),
    ),
    readNodes(),
  ]);
  return (
    <PendingAddress kept={WORKLOAD_KEPT}>
      <KeptWorkload preferences={preferences} />
      <Screen density={FUNCTION_DENSITY.portfolio_workload}>
        <PortfolioHeader fn="portfolio_workload" scope={answer.scope} />
        <PerimeterBar
          perimeter={perimeter}
          retained={answer.scope.states}
          takes={TAKES}
          nodes={nodes}
          view={{ horizon, threshold: threshold ?? answer.under_load_threshold }}
        />
        <WorkloadView workload={answer} />
      </Screen>
    </PendingAddress>
  );
}
