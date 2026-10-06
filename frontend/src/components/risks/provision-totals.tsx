// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The totals of the provisions of the risks retained (WF-RIS-0040): those of the risks identified,
 * occurred and dismissed, distinct, and the general total, their sum — each as the server gives it,
 * for the risks the filters retained (WF-IHM-0130), never a sum made here (WF-ARC-0020) —, and,
 * beside them, the risk reserve of the reference revision they are read against (WF-RIS-0050).
 * Computed: each bears the one mark of a computed value, Σ, named.
 */
import { useTranslations } from "next-intl";

import { ComputedTotal } from "@/components/computed-amount";

import { RISK_STATES } from "./address";
import type { ProvisionTotals } from "./risk-grid";

/** Render the totals of the provisions, by state, their general total, and the risk reserve. */
export function ProvisionSummary({ totals }: { readonly totals: ProvisionTotals }) {
  const t = useTranslations("risks.provisions");
  return (
    <section aria-label={t("title")}>
      <dl className="flex flex-wrap gap-x-8 gap-y-2">
        {RISK_STATES.map((state) => (
          <ComputedTotal key={state} name={t(state)} amount={totals[state]} />
        ))}
        <ComputedTotal name={t("total")} amount={totals.total} />
        <ComputedTotal name={t("reserve")} amount={totals.reserve} />
      </dl>
    </section>
  );
}
