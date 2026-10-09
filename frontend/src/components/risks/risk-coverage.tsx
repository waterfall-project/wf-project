// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The coverage of the risks of a project (WF-RIS-0050, WF-RAE-0020), on the screen of the risks as
 * on that of the remaining to commit: the risk reserve of the
 * reference revision, against the provisions of the risks still identified in the revision read
 * and the reestimated cost of the lines merged from the risks occurred, and the coverage variance,
 * signed — each as the server computes it (`getProjectRiskCoverage`), never a difference made here
 * (WF-ARC-0020). Computed: each bears the one mark of a computed value, Σ, named.
 */
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { ComputedTotal } from "@/components/computed-amount";

/** The coverage of the risks of a project, as the server computes it. */
export type RiskCoverage = components["schemas"]["RiskCoverage"];

/**
 * Its four amounts, which the indicators of the remaining to commit repeat
 * (`RemainingIndicators.coverage`, WF-RAE-0020).
 */
type RiskCoverageTotals = components["schemas"]["RiskCoverageTotals"];

/** The four amounts of the coverage, as the contract names them, in its order. */
const AMOUNTS = [
  ["reserve", "reserve"],
  ["remaining_provisions", "remainingProvisions"],
  ["occurred_cost", "occurredCost"],
  ["coverage_variance", "coverageVariance"],
] as const satisfies readonly (readonly [keyof RiskCoverageTotals, string])[];

/** Render the four amounts of the coverage of the risks. */
export function RiskCoverageSummary({ coverage }: { readonly coverage: RiskCoverageTotals }) {
  const t = useTranslations("risks.coverage");
  return (
    <section aria-label={t("title")}>
      <dl className="flex flex-wrap gap-x-8 gap-y-2">
        {AMOUNTS.map(([field, name]) => (
          <ComputedTotal key={field} name={t(name)} amount={coverage[field]} />
        ))}
      </dl>
    </section>
  );
}
