// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The header of a view of the portfolio: the title of its function, and under it the perimeter
 * the server retained for it (WF-PTF-0010) — the states, the number of projects, the period when
 * there is one, the node of organisation, named by the server, whose labour it retains — and the
 * date it is computed at, which every figure of the view carries
 * (WF-IHM-0020): a view of the portfolio is computed at a date, `scope.as_of`, as the server gives
 * it, a date of planning shown without time zone. Nothing of it is deduced from the address.
 */
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader } from "@/components/shell/page-header";
import { formatPlanningDate } from "@/i18n/format";
import type { NavigationFunction } from "@/navigation/functions";

import type { PortfolioScope } from "./address";

/** The functions of the portfolio, by their permission. */
export type PortfolioFunction = Extract<NavigationFunction["permission"], `portfolio_${string}`>;

/** The key of the label of each function of the portfolio, by its permission. */
const LABELS = {
  portfolio_projects: "functions.portfolioProjects",
  portfolio_workload: "functions.portfolioWorkload",
  portfolio_performance: "functions.portfolioPerformance",
  portfolio_cost_structure: "functions.portfolioCostStructure",
  portfolio_risks: "functions.portfolioRisks",
  portfolio_cash_out: "functions.portfolioCashOut",
  portfolio_pilot_health: "functions.portfolioPilotHealth",
} as const satisfies Readonly<Record<PortfolioFunction, NavigationFunction["label"]>>;

/** The label of a function of the portfolio, which titles its screen and its tab. */
export function portfolioLabel(fn: PortfolioFunction) {
  return LABELS[fn];
}

/**
 * The perimeter the server retained, in a sentence: states, projects, period, date of calculation.
 */
function ScopeLine({ scope }: { readonly scope: PortfolioScope }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const date = (value: string) => formatPlanningDate(value, locale);
  const states = format.list(scope.states.map((state) => t(`enums.ProjectState.${state}`)));
  const asOf = date(scope.as_of);
  const from = scope.from ?? null;
  const to = scope.to ?? null;
  const count = scope.project_count;
  if (from !== null && to !== null) {
    return t("portfolio.scope.period", { states, count, asOf, from: date(from), to: date(to) });
  }
  if (from !== null) {
    return t("portfolio.scope.since", { states, count, asOf, from: date(from) });
  }
  if (to !== null) {
    return t("portfolio.scope.until", { states, count, asOf, to: date(to) });
  }
  return t("portfolio.scope.noPeriod", { states, count, asOf });
}

/** The node of organisation the server retained, by the label it gives; nothing without one. */
function NodeLine({ scope }: { readonly scope: PortfolioScope }) {
  const t = useTranslations("portfolio.scope");
  return scope.org_node_label === null ? null : (
    <span className="block">{t("node", { node: scope.org_node_label })}</span>
  );
}

/** Render the header of a view of the portfolio, the perimeter and the date under its title. */
export function PortfolioHeader({
  fn,
  scope,
}: {
  readonly fn: PortfolioFunction;
  readonly scope: PortfolioScope;
}) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t(LABELS[fn])}
      icon={FUNCTION_ICONS[fn]}
      density={FUNCTION_DENSITY[fn]}
      subtitle={
        <>
          <ScopeLine scope={scope} />
          <NodeLine scope={scope} />
        </>
      }
    />
  );
}
