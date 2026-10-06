// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The S-curve of the portfolio (FBS-2.6, WF-PTF-0100), at the route of its function: over the
 * horizon the address asks (`horizon_months`), the three cumulative curves of the projects of the
 * perimeter — the reference budget, the actual cost to the date of calculation, the project
 * managers' projection beyond — summed month by month by the server (WF-IND-0100). Read as
 * cash-out when the address asks it (`payment_delays`, the convention of the indicators of a
 * project), the server shifts the curves of each project by its payment delays and details the
 * cash-out month by month, the past and the forecast, which a second chart shows. Nothing is
 * summed nor shifted here; the command only changes the address, the rest of it kept.
 */
import { Banknote } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { PendingAddress } from "@/components/grid/pending-address";
import { PAYMENT_DELAYS } from "@/components/indicators/indicator-sections";
import {
  parametersHref,
  perimeterQuery,
  readHorizon,
  readPerimeter,
} from "@/components/portfolio/address";
import { PerimeterBar } from "@/components/portfolio/perimeter";
import { CashOutChart, PortfolioCurveChart } from "@/components/portfolio/portfolio-charts";
import { PortfolioHeader, portfolioLabel } from "@/components/portfolio/portfolio-header";
import { FUNCTION_DENSITY } from "@/components/shell/function-display";
import { Screen } from "@/components/shell/page-header";
import { buttonVariants } from "@/components/ui/button";
import { type PageSearchParams, pageSearch } from "@/navigation/context";

import { screenMetadata } from "../../title";

/** The S-curve takes neither a period nor a node of organisation. */
const TAKES = { period: false, node: false } as const;

/** The route of the screen. */
const ROUTE = "/portfolio/cost-curve";

/** Title the tab with the function. */
export function generateMetadata(): Promise<Metadata> {
  return screenMetadata(portfolioLabel("portfolio_cost_curve"));
}

/** The query of the address as Next hands it, the first value of each parameter. */
function queryOf(search: PageSearchParams): URLSearchParams {
  const query = new URLSearchParams();
  for (const [name, value] of Object.entries(search)) {
    const first = typeof value === "string" ? value : value?.[0];
    if (first !== undefined) {
      query.set(name, first);
    }
  }
  return query;
}

/**
 * The command that reads the S-curve as cash-out, or comes back to the cumulative costs: as the
 * server says the curves are — shifted or not —, not as asked.
 */
function PaymentDelaysToggle({
  shifted,
  query,
}: {
  readonly shifted: boolean;
  readonly query: URLSearchParams;
}) {
  const t = useTranslations("portfolio.costCurve");
  return (
    <Link
      href={parametersHref(ROUTE, query, { [PAYMENT_DELAYS]: shifted ? undefined : "true" })}
      scroll={false}
      className={buttonVariants({ variant: "outline", size: "sm" })}
    >
      <Banknote aria-hidden="true" />
      {shifted ? t("undelay") : t("delay")}
    </Link>
  );
}

/** Render the S-curve of the portfolio, on the perimeter and the horizon asked. */
export default async function PortfolioCostCurvePage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const asked = await searchParams;
  const search = pageSearch(asked);
  const perimeter = readPerimeter(search);
  const horizon = readHorizon(search);
  const delays = search.get(PAYMENT_DELAYS) === "true";
  const answer = await readOrFail("getPortfolioCostCurve", () =>
    serverClient().GET("/portfolio/cost-curve", {
      params: {
        query: {
          ...perimeterQuery(perimeter, TAKES),
          ...(horizon === undefined ? {} : { horizon_months: Number(horizon) }),
          ...(delays ? { payment_delays: true } : {}),
        },
      },
    }),
  );
  return (
    <PendingAddress>
      <Screen density={FUNCTION_DENSITY.portfolio_cost_curve}>
        <PortfolioHeader fn="portfolio_cost_curve" scope={answer.scope} />
        <PerimeterBar
          perimeter={perimeter}
          retained={answer.scope.states}
          takes={TAKES}
          view={{ horizon }}
        />
        <PaymentDelaysToggle shifted={answer.payment_delays} query={queryOf(asked)} />
        <PortfolioCurveChart curves={answer} />
        {answer.cash_out_by_month === null ? null : (
          <CashOutChart months={answer.cash_out_by_month} />
        )}
      </Screen>
    </PendingAddress>
  );
}
