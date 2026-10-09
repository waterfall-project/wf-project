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
import { useTranslations } from "next-intl";

import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader } from "@/components/shell/page-header";
import type { NavigationFunction } from "@/navigation/functions";

import type { PortfolioScope } from "./address";
import { useScopeSentence } from "./provenance";

/** The functions of the portfolio, by their permission. */
export type PortfolioFunction = Extract<NavigationFunction["permission"], `portfolio_${string}`>;

/** The key of the label of each function of the portfolio, by its permission. */
const LABELS = {
  portfolio_projects: "functions.portfolioProjects",
  portfolio_workload: "functions.portfolioWorkload",
  portfolio_performance: "functions.portfolioPerformance",
  portfolio_cost_structure: "functions.portfolioCostStructure",
  portfolio_risks: "functions.portfolioRisks",
  portfolio_cost_curve: "functions.portfolioCostCurve",
  portfolio_pilot_health: "functions.portfolioPilotHealth",
} as const satisfies Readonly<Record<PortfolioFunction, NavigationFunction["label"]>>;

/** The label of a function of the portfolio, which titles its screen and its tab. */
export function portfolioLabel(fn: PortfolioFunction) {
  return LABELS[fn];
}

/** The perimeter the server retained, in a sentence: states, projects, period, date of calculation. */
function ScopeLine({ scope }: { readonly scope: PortfolioScope }) {
  return useScopeSentence()(scope);
}

/** The node of organisation the server retained, by the label it gives; nothing without one. */
function NodeLine({ scope }: { readonly scope: PortfolioScope }) {
  const t = useTranslations("portfolio.scope");
  return scope.org_node_label === null ? null : (
    <span className="block">{t("node", { node: scope.org_node_label })}</span>
  );
}

/**
 * Render the header of a view of the portfolio, the perimeter and the date under its title; the
 * title alone for a view the server did not read — its period refused —, of which no perimeter was
 * retained.
 */
export function PortfolioHeader({
  fn,
  scope,
}: {
  readonly fn: PortfolioFunction;
  readonly scope: PortfolioScope | undefined;
}) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t(LABELS[fn])}
      icon={FUNCTION_ICONS[fn]}
      density={FUNCTION_DENSITY[fn]}
      subtitle={
        scope === undefined ? undefined : (
          <>
            <ScopeLine scope={scope} />
            <NodeLine scope={scope} />
          </>
        )
      }
    />
  );
}
