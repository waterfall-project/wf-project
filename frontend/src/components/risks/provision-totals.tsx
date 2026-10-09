// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The totals of the provisions of the risks retained (WF-RIS-0040): those of the risks identified,
 * occurred and dismissed, distinct, and the general total, their sum — each as the server gives it,
 * for the risks the filters retained (WF-IHM-0130), never a sum made here (WF-ARC-0020). The risk
 * reserve of the reference revision is not among them, though the server gives it: it shows in
 * the coverage of the risks alone, beside what it is read against (`RiskCoverageSummary`,
 * decision of the author of 2026-10-07, #409). Computed: each bears the one mark of a computed
 * value, Σ, named.
 */
import { useTranslations } from "next-intl";

import { ComputedTotal } from "@/components/computed-amount";

import { RISK_STATES } from "./address";
import type { ProvisionTotals } from "./risk-grid";

/** Render the totals of the provisions, by state, and their general total. */
export function ProvisionSummary({ totals }: { readonly totals: ProvisionTotals }) {
  const t = useTranslations("risks.provisions");
  return (
    <section aria-label={t("title")}>
      <dl className="flex flex-wrap gap-x-8 gap-y-2">
        {RISK_STATES.map((state) => (
          <ComputedTotal key={state} name={t(state)} amount={totals[state]} />
        ))}
        <ComputedTotal name={t("total")} amount={totals.total} />
      </dl>
    </section>
  );
}
