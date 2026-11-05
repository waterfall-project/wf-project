// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The coverage of the risks of a project (WF-RIS-0050, WF-RAE-0020), on the screen of the risks as
 * on that of the remaining to commit: the risk reserve of the reference revision, against the
 * provisions of the risks still identified in the revision read and the costs at the occurrence of
 * the risks occurred (`Risk.occurrence_cost`), which neither a reestimate nor the completion of the
 * tasks merged changes, and the coverage variance, signed — each as the server computes it
 * (`getProjectRiskCoverage`), never a difference made here (WF-ARC-0020). Computed: each bears the
 * one mark of a computed value, Σ, named. They lie in a card of figures (`FiguresCard`, US-0550).
 *
 * The reestimated cost of the occurred risks (`occurred_reestimated`, #1763) stands in regard of
 * their cost, as an information the variance does not count (WF-RIS-0050): beside it on its row,
 * in the muted type of what is not a term of the variance, named in full to a reader of the screen.
 * A row of its own made the card the tallest of the screen of the remaining to commit, and pushed
 * the totals of its grid out of the window (US-1020/L2).
 */
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import type { CalculationContext } from "@/components/context/indicator";
import { ComputedAmount, ComputedTotal } from "@/components/computed-amount";
import { FigureTerm, FiguresCard, FiguresList } from "@/components/figures-card";

/** The coverage of the risks of a project, as the server computes it. */
export type RiskCoverage = components["schemas"]["RiskCoverage"];

/**
 * Its amounts, which the indicators of the remaining to commit repeat
 * (`RemainingIndicators.coverage`, WF-RAE-0020).
 */
type RiskCoverageTotals = components["schemas"]["RiskCoverageTotals"];

/**
 * The amounts of the coverage, as the contract names them, in its order; the reestimated cost of the
 * occurred risks is not one of its rows, but stands beside their cost.
 */
const AMOUNTS = [
  ["reserve", "reserve"],
  ["remaining_provisions", "remainingProvisions"],
  ["occurred_cost", "occurredCost"],
  ["coverage_variance", "coverageVariance"],
] as const satisfies readonly (readonly [keyof RiskCoverageTotals, string])[];

/**
 * The cost of the occurred risks, and in regard of it their reestimated cost, an information: a
 * short word on the screen, its full name and its mention of an information for a reader of it.
 * The portfolio presents them the same way (`PortfolioRisksView`, #1953).
 */
export function OccurredCost({ coverage }: { readonly coverage: RiskCoverageTotals }) {
  const t = useTranslations("risks.coverage");
  return (
    <FigureTerm name={t("occurredCost")}>
      <span className="inline-flex flex-wrap items-baseline justify-end gap-x-1.5">
        <span className="inline-flex items-baseline gap-1.5 whitespace-nowrap">
          <ComputedAmount amount={coverage.occurred_cost} />
          {/* The bullet closes the line of the cost: a broken line never opens on it. */}
          <span
            aria-hidden="true"
            className="text-xs font-normal text-muted-foreground before:content-['·']"
          />
        </span>
        <span className="inline-flex items-baseline gap-1 text-xs font-normal whitespace-nowrap text-muted-foreground">
          <span aria-hidden="true">{t("occurredReestimatedShort")}</span>
          <span className="sr-only">{t("occurredReestimated")}</span>
          <ComputedAmount amount={coverage.occurred_reestimated} />
        </span>
      </span>
    </FigureTerm>
  );
}

/** Render the four amounts of the coverage of the risks, and the reestimated of the occurred. */
export function RiskCoverageSummary({
  coverage,
  context,
}: {
  readonly coverage: RiskCoverageTotals;
  /** The calculation context of the answer the amounts come from, dated on the card. */
  readonly context?: CalculationContext;
}) {
  const t = useTranslations("risks.coverage");
  return (
    <FiguresCard title={t("title")} context={context}>
      <FiguresList>
        {AMOUNTS.map(([field, name]) =>
          field === "occurred_cost" ? (
            <OccurredCost key={field} coverage={coverage} />
          ) : (
            <ComputedTotal key={field} name={t(name)} amount={coverage[field]} />
          ),
        )}
      </FiguresList>
    </FiguresCard>
  );
}
