// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cash-out of the portfolio (FBS-2.6, WF-PTF-0100), at the route of its function: month by
 * month over the horizon the address asks (`horizon_months`), the sum of the projections of
 * cash-out of the projects of the perimeter — the past by month of document date, the forecast
 * from the date of calculation —, as the server sums them; nothing is computed here.
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
} from "@/components/portfolio/address";
import { PerimeterBar } from "@/components/portfolio/perimeter";
import { CashOutChart } from "@/components/portfolio/portfolio-charts";
import { PortfolioHeader, portfolioLabel } from "@/components/portfolio/portfolio-header";
import { FUNCTION_DENSITY } from "@/components/shell/function-display";
import { Screen } from "@/components/shell/page-header";
import { type PageSearchParams, pageSearch } from "@/navigation/context";

import { screenMetadata } from "../../title";

/** The cash-out takes neither a period nor a node of organisation. */
const TAKES = { period: false, node: false } as const;

/** Title the tab with the function. */
export function generateMetadata(): Promise<Metadata> {
  return screenMetadata(portfolioLabel("portfolio_cash_out"));
}

/** Render the cash-out of the portfolio, on the perimeter and the horizon asked. */
export default async function PortfolioCashOutPage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const search = pageSearch(await searchParams);
  const perimeter = readPerimeter(search);
  const horizon = readChoice(search, HORIZON, HORIZONS);
  const answer = await readOrFail("getPortfolioCashOut", () =>
    serverClient().GET("/portfolio/cash-out", {
      params: {
        query: {
          ...perimeterQuery(perimeter, TAKES),
          ...(horizon === undefined ? {} : { horizon_months: Number(horizon) }),
        },
      },
    }),
  );
  return (
    <PendingAddress>
      <Screen density={FUNCTION_DENSITY.portfolio_cash_out}>
        <PortfolioHeader fn="portfolio_cash_out" scope={answer.scope} />
        <PerimeterBar
          perimeter={perimeter}
          retained={answer.scope.states}
          takes={TAKES}
          view={{ horizon }}
        />
        <CashOutChart months={answer.months} />
      </Screen>
    </PendingAddress>
  );
}
