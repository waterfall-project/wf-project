// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * An amount the server computes, shown as it gives it and marked by the one mark of a computed
 * value, Σ, named (WF-IHM-0030), alone or as a total named in a list of terms: the severity and
 * the provisions of the risks, the totals of the actual costs.
 */
"use client";

import { Sigma } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { FigureTerm } from "@/components/figures-card";
import { useCurrency } from "@/currency/context";
import { formatMoney } from "@/i18n/format";

/**
 * An amount the server computes, marked by Σ, the one mark of a computed value, which a reader
 * hears as « computed » (WF-IHM-0030).
 */
export function ComputedAmount({ amount }: { readonly amount: string }) {
  const t = useTranslations("grid");
  const locale = useLocale();
  const currency = useCurrency();
  return (
    <span className="inline-flex items-center gap-1 tabular-nums">
      <Sigma role="img" aria-label={t("computed")} className="size-3 shrink-0" />
      {formatMoney(amount, locale, currency)}
    </span>
  );
}

/** A total: its name, and its amount marked computed — an entry of a list of terms (`dl`). */
export function ComputedTotal({
  name,
  amount,
}: {
  readonly name: string;
  readonly amount: string;
}) {
  return (
    <FigureTerm name={name}>
      <ComputedAmount amount={amount} />
    </FigureTerm>
  );
}
