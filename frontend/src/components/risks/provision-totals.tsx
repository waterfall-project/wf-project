// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The totals of the provisions of the risks retained (WF-RIS-0040): those of the risks identified,
 * occurred and dismissed, distinct, and the general total, their sum — each as the server gives it,
 * for the risks the filters retained (WF-IHM-0130), never a sum made here (WF-ARC-0020). Computed:
 * each bears the one mark of a computed value, Σ, named.
 */
import { Sigma } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { formatMoney } from "@/i18n/format";

import { RISK_STATES } from "./address";
import type { ProvisionTotals } from "./risk-grid";

/**
 * An amount the server computes, marked by Σ, the one mark of a computed value, which a reader
 * hears as « computed » (WF-IHM-0030).
 */
export function ComputedAmount({ amount }: { readonly amount: string }) {
  const t = useTranslations("grid");
  const locale = useLocale();
  return (
    <span className="inline-flex items-center gap-1 tabular-nums">
      <Sigma role="img" aria-label={t("computed")} className="size-3 shrink-0" />
      {formatMoney(amount, locale)}
    </span>
  );
}

/** A total: its name, and its amount marked computed. */
function Total({ name, amount }: { readonly name: string; readonly amount: string }) {
  return (
    <div className="space-y-0.5">
      <dt className="text-xs text-muted-foreground">{name}</dt>
      <dd className="font-semibold">
        <ComputedAmount amount={amount} />
      </dd>
    </div>
  );
}

/** Render the totals of the provisions, by state, and their general total. */
export function ProvisionSummary({ totals }: { readonly totals: ProvisionTotals }) {
  const t = useTranslations("risks.provisions");
  return (
    <section aria-label={t("title")}>
      <dl className="flex flex-wrap gap-x-8 gap-y-2">
        {RISK_STATES.map((state) => (
          <Total key={state} name={t(state)} amount={totals[state]} />
        ))}
        <Total name={t("total")} amount={totals.total} />
      </dl>
    </section>
  );
}
